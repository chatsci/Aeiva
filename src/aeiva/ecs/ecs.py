
from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
import inspect
from contextlib import contextmanager
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    overload,
    TypeVarTuple,
    Unpack,
)

# --------------------------
# Typing
# --------------------------
T = TypeVar("T")
Cs = TypeVarTuple("Cs")

EntityId = int


# --------------------------
# Systems
# --------------------------
class System:
    """Synchronous system; override `update(self, world, *args, **kwargs)`."""
    priority: int = 0
    def setup(self, world: "World") -> None:  # optional hook
        pass
    def update(self, world: "World", *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


class AsyncSystem:
    """Asynchronous system; override `async update(self, world, *args, **kwargs)`."""
    priority: int = 0
    async def setup(self, world: "World") -> None:  # optional hook
        pass
    async def update(self, world: "World", *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError


# --------------------------
# Archetype storage
# --------------------------
class Archetype:
    """
    Columnar storage for entities that share the same component-type set (signature).
    - signature: frozenset of component types
    - entities: list[int] of entity indices (internal, not handles)
    - columns: dict[Type, list[object]] where lists are aligned with `entities`
    """
    __slots__ = ("signature", "entities", "columns")

    def __init__(self, signature: frozenset[Type[Any]]) -> None:
        self.signature = signature
        self.entities: List[int] = []
        self.columns: Dict[Type[Any], List[Any]] = {ct: [] for ct in signature}

    def add_row(self, entity_index: int, values: Dict[Type[Any], Any]) -> int:
        """Append a row, given a dict of component values for this signature. Returns row index."""
        row = len(self.entities)
        self.entities.append(entity_index)
        for ct in self.signature:
            self.columns[ct].append(values[ct])
        return row

    def pop_row_swap(self, row: int) -> Tuple[int, Dict[Type[Any], Any]]:
        """
        Remove a row by swapping with the last row (O(1)).
        Returns (moved_entity_index_or_-1_if_none, removed_values).
        If a row was swapped in, you must update that entity's location.
        """
        last = len(self.entities) - 1
        removed_values = {ct: self.columns[ct][row] for ct in self.signature}
        if row != last:
            moved_entity = self.entities[last]
            self.entities[row] = moved_entity
            for ct in self.signature:
                self.columns[ct][row] = self.columns[ct][last]
        else:
            moved_entity = -1

        # pop tails
        self.entities.pop()
        for ct in self.signature:
            self.columns[ct].pop()
        return moved_entity, removed_values


# --------------------------
# World with archetypes + generations + async systems
# --------------------------
class World:
    """
    Modern ECS World with:
      - Archetype storage (dense, cache-friendly)
      - Entity generation counters (stale id protection)
      - Sync and async systems (priority-based), with optional concurrent async stepping
      - Snapshot (`view`) and live (`iter_view`) queries with structural versioning

    Entity ids are packed as 64-bit integers: [generation:32][index:32].
    """

    INDEX_BITS = 32
    GEN_BITS = 32
    INDEX_MASK = (1 << INDEX_BITS) - 1
    GEN_MASK = (1 << GEN_BITS) - 1

    # --- lifecycle ---
    def __init__(self) -> None:
        # entity bookkeeping
        self._gen: List[int] = []          # generation per index
        self._entity_arch: List[Optional[Archetype]] = []  # current archetype per index
        self._entity_row: List[int] = []    # row within archetype
        self._free_indices: List[int] = []

        # archetypes
        self._archetypes: Dict[frozenset[Type[Any]], Archetype] = {}
        self._archetype_by_type: Dict[Type[Any], Set[Archetype]] = {}
        self._empty = self._get_or_create_archetype(frozenset())

        # systems
        self._sync_systems: List[System] = []
        self._async_systems: List[AsyncSystem] = []
        self._is_updating: bool = False
        self._async_setup_done: bool = False

        # caches & versioning
        self._version: int = 0  # bump on structural/content changes
        self._cache_view_single: Dict[Type[Any], Tuple[int, List[Tuple[EntityId, Any]]]] = {}
        self._cache_view_multi: Dict[Tuple[Type[Any], ...], Tuple[int, List[Tuple[EntityId, Tuple[Any, ...]]]]] = {}

        # timing
        self.process_times_ms: Dict[str, int] = {}
        self._pending_kill: Set[EntityId] = set()

    # --------------------------
    # EntityId helpers (pack/unpack)
    # --------------------------
    def _pack(self, index: int, gen: int) -> EntityId:
        return (gen << self.INDEX_BITS) | index

    def _unpack(self, eid: EntityId) -> Tuple[int, int]:
        index = eid & self.INDEX_MASK
        gen = (eid >> self.INDEX_BITS) & self.GEN_MASK
        return index, gen

    def _is_live(self, eid: EntityId) -> bool:
        index, gen = self._unpack(eid)
        return index < len(self._gen) and self._gen[index] == gen and self._entity_arch[index] is not None

    def _assert_live(self, eid: EntityId) -> int:
        index, gen = self._unpack(eid)
        if index >= len(self._gen) or self._gen[index] != gen or self._entity_arch[index] is None:
            raise KeyError(f"Stale or invalid EntityId {eid} (index={index}, gen={gen}).")
        return index

    # --------------------------
    # Archetype helpers
    # --------------------------
    def _get_or_create_archetype(self, signature: frozenset[Type[Any]]) -> Archetype:
        arch = self._archetypes.get(signature)
        if arch is not None:
            return arch
        arch = Archetype(signature)
        self._archetypes[signature] = arch
        for ct in signature:
            self._archetype_by_type.setdefault(ct, set()).add(arch)
        return arch

    def _move_entity(
        self,
        index: int,
        src: Archetype,
        dst: Archetype,
        extra: Optional[Tuple[Type[Any], Any]] = None,
        drop: Optional[Type[Any]] = None,
    ) -> None:
        """
        Move entity from src to dst archetype.
        - If `extra` is provided, add/replace that component in destination.
        - If `drop` is provided, omit that component from destination.
        """
        row = self._entity_row[index]
        moved_idx, values = src.pop_row_swap(row)

        # if a row got swapped in, update its location
        if moved_idx != -1:
            self._entity_row[moved_idx] = row

        # prepare dict of values for destination signature
        if extra is not None:
            ect, eval = extra
            values[ect] = eval
        if drop is not None:
            values.pop(drop, None)

        dst_row = dst.add_row(index, values)
        self._entity_arch[index] = dst
        self._entity_row[index] = dst_row

    def _bump_version(self) -> None:
        self._version += 1

    # --------------------------
    # Entity management
    # --------------------------
    def create_entity(self, *components: Any) -> EntityId:
        """Create an entity, optionally with initial components."""
        if self._free_indices:
            index = self._free_indices.pop()
        else:
            index = len(self._gen)
            self._gen.append(0)
            self._entity_arch.append(None)
            self._entity_row.append(-1)

        # place in target archetype
        if components:
            sig = frozenset(type(c) for c in components)
            arch = self._get_or_create_archetype(sig)
            values = {type(c): c for c in components}
        else:
            arch = self._empty
            values = {}

        row = arch.add_row(index, values)
        self._entity_arch[index] = arch
        self._entity_row[index] = row

        eid = self._pack(index, self._gen[index])
        self._bump_version()
        return eid

    def destroy_entity(self, eid: EntityId, *, immediate: bool = False) -> None:
        """Destroy an entity. If called during update, destruction is deferred unless `immediate=True`."""
        if self._is_updating and not immediate:
            self._pending_kill.add(eid)
            return

        index = self._assert_live(eid)
        arch = self._entity_arch[index]
        assert arch is not None
        row = self._entity_row[index]
        moved_idx, _values = arch.pop_row_swap(row)
        if moved_idx != -1:
            self._entity_row[moved_idx] = row
        self._entity_arch[index] = None
        self._entity_row[index] = -1

        # bump generation so stale handles are invalid
        self._gen[index] = (self._gen[index] + 1) & self.GEN_MASK
        self._free_indices.append(index)
        self._bump_version()

    def entity_exists(self, eid: EntityId) -> bool:
        return self._is_live(eid)

    def entity_count(self) -> int:
        return sum(1 for a in self._entity_arch if a is not None)

    # --------------------------
    # Component management
    # --------------------------
    def add_component(self, eid: EntityId, component: Any) -> None:
        """Attach or replace a component instance on an entity (structural or content change)."""
        index = self._assert_live(eid)
        ctype = type(component)

        src = self._entity_arch[index]; assert src is not None
        if ctype in src.signature:  # replace in-place (content change)
            row = self._entity_row[index]
            src.columns[ctype][row] = component
            # Invalidate snapshot caches so subsequent view() reflects new objects
            self._bump_version()
            return

        dst_sig = frozenset((*src.signature, ctype))
        dst = self._get_or_create_archetype(dst_sig)
        self._move_entity(index, src, dst, extra=(ctype, component))
        self._bump_version()

    def remove_component(self, eid: EntityId, component_type: Type[T]) -> T:
        """Remove component by type and return it. Raises KeyError if missing."""
        index = self._assert_live(eid)
        src = self._entity_arch[index]; assert src is not None
        if component_type not in src.signature:
            raise KeyError(f"Entity {eid} does not have component {component_type.__name__}.")
        row = self._entity_row[index]
        removed = src.columns[component_type][row]
        dst_sig = frozenset(ct for ct in src.signature if ct is not component_type)
        dst = self._get_or_create_archetype(dst_sig)
        self._move_entity(index, src, dst, drop=component_type)
        self._bump_version()
        return removed  # type: ignore[return-value]

    def has_component(self, eid: EntityId, component_type: Type[Any]) -> bool:
        index = self._assert_live(eid)
        arch = self._entity_arch[index]; assert arch is not None
        return component_type in arch.signature

    def has_components(self, eid: EntityId, *component_types: Type[Any]) -> bool:
        """Return True if the entity has all specified component types."""
        index = self._assert_live(eid)
        arch = self._entity_arch[index]; assert arch is not None
        sig = arch.signature
        return all(ct in sig for ct in component_types)

    def get_component(self, eid: EntityId, component_type: Type[T]) -> T:
        """Return component instance by type. Raises KeyError if missing."""
        index = self._assert_live(eid)
        arch = self._entity_arch[index]; assert arch is not None
        if component_type not in arch.signature:
            raise KeyError(f"Entity {eid} does not have component {component_type.__name__}.")
        row = self._entity_row[index]
        return arch.columns[component_type][row]  # type: ignore[return-value]

    def try_component(self, eid: EntityId, component_type: Type[T]) -> Optional[T]:
        """Return component instance or None if the entity doesn't have it."""
        index = self._assert_live(eid)
        arch = self._entity_arch[index]; assert arch is not None
        if component_type not in arch.signature:
            return None
        row = self._entity_row[index]
        return arch.columns[component_type][row]  # type: ignore[return-value]

    def components_for(self, eid: EntityId) -> Tuple[Any, ...]:
        """Return tuple of all component instances for this entity (order unspecified)."""
        index = self._assert_live(eid)
        arch = self._entity_arch[index]; assert arch is not None
        row = self._entity_row[index]
        return tuple(arch.columns[ct][row] for ct in arch.signature)

    def entities(self) -> List[EntityId]:
        """Snapshot of all live entity ids."""
        out: List[EntityId] = []
        for arch in self._archetypes.values():
            for idx in arch.entities:
                out.append(self._pack(idx, self._gen[idx]))
        return out

    def iter_entities(self) -> Iterator[EntityId]:
        """Live generator of all live entity ids."""
        for arch in self._archetypes.values():
            for idx in arch.entities:
                yield self._pack(idx, self._gen[idx])

    # --------------------------
    # Queries
    # --------------------------
    def _candidate_archetypes(self, types: Tuple[Type[Any], ...]) -> List[Archetype]:
        if not types:
            return []
        # Intersect archetype sets per type for a tighter candidate list
        sets = [self._archetype_by_type.get(t, set()) for t in types]
        if not all(sets):
            return []
        candidates = set.intersection(*sets)
        # Filter to supersets (should already hold, but keep safe)
        ts = frozenset(types)
        return [a for a in candidates if ts.issubset(a.signature)]

    @overload
    def view(self, c1: Type[T]) -> List[Tuple[EntityId, T]]: ...
    @overload
    def view(self, *component_types: Type[Unpack[Cs]]) -> List[Tuple[EntityId, Tuple[Unpack[Cs]]]]: ...
    def view(self, *component_types: Type[Any]) -> List[Tuple[EntityId, Any]]:
        """
        Snapshot query. Returns:
         - For one type: List[(entity, comp)]
         - For >=2:     List[(entity, (c1, c2, ...))]
        Results are cached until a change occurs (add/remove/replace/destroy/create).
        """
        if not component_types:
            raise ValueError("view() requires at least one component type.")

        if len(component_types) == 1:
            ct = component_types[0]
            cached = self._cache_view_single.get(ct)
            if cached is not None and cached[0] == self._version:
                return cached[1]  # type: ignore[return-value]
            out: List[Tuple[EntityId, Any]] = []
            for arch in self._archetype_by_type.get(ct, ()):
                col = arch.columns[ct]
                for i, idx in enumerate(arch.entities):
                    eid = self._pack(idx, self._gen[idx])
                    out.append((eid, col[i]))
            self._cache_view_single[ct] = (self._version, out)
            return out  # type: ignore[return-value]

        key = tuple(component_types)
        cached = self._cache_view_multi.get(key)
        if cached is not None and cached[0] == self._version:
            return cached[1]  # type: ignore[return-value]

        out2: List[Tuple[EntityId, Tuple[Any, ...]]] = []
        for arch in self._candidate_archetypes(key):
            cols = [arch.columns[ct] for ct in key]
            for i, idx in enumerate(arch.entities):
                eid = self._pack(idx, self._gen[idx])
                out2.append((eid, tuple(col[i] for col in cols)))
        self._cache_view_multi[key] = (self._version, out2)
        return out2  # type: ignore[return-value]

    @overload
    def iter_view(self, c1: Type[T]) -> Iterator[Tuple[EntityId, T]]: ...
    @overload
    def iter_view(self, *component_types: Type[Unpack[Cs]]) -> Iterator[Tuple[EntityId, Tuple[Unpack[Cs]]]]: ...
    def iter_view(self, *component_types: Type[Any]) -> Iterator[Tuple[EntityId, Any]]:
        """
        Live generator over matching entities. Faster, but mutation-sensitive.
        For one type: yields (eid, comp)
        For >=2 types: yields (eid, (c1, c2, ...))
        """
        if not component_types:
            raise ValueError("iter_view() requires at least one component type.")
        key = tuple(component_types)
        if len(key) == 1:
            ct = key[0]
            for arch in self._archetype_by_type.get(ct, ()):
                col = arch.columns[ct]
                for i, idx in enumerate(arch.entities):
                    eid = self._pack(idx, self._gen[idx])
                    yield eid, col[i]
            return
        for arch in self._candidate_archetypes(key):
            cols = [arch.columns[ct] for ct in key]
            for i, idx in enumerate(arch.entities):
                eid = self._pack(idx, self._gen[idx])
                yield eid, tuple(col[i] for col in cols)

    # --------------------------
    # Systems
    # --------------------------
    def add_system(self, system: System | AsyncSystem, *, priority: Optional[int] = None) -> None:
        """Add a system (sync or async). Higher `priority` runs first."""
        if priority is not None:
            system.priority = priority
        if isinstance(system, AsyncSystem):
            self._async_systems.append(system)
            self._async_systems.sort(key=lambda s: s.priority, reverse=True)
            # Async setup will run automatically on the first async update
        else:
            self._sync_systems.append(system)
            self._sync_systems.sort(key=lambda s: s.priority, reverse=True)
            system.setup(self)  # sync setup

    def remove_system(self, system_type: Type[System] | Type[AsyncSystem]) -> None:
        for lst in (self._sync_systems, self._async_systems):
            for s in list(lst):
                if type(s) is system_type:
                    lst.remove(s)

    def get_system(self, system_type: Type[T]) -> Optional[T]:
        for s in self._sync_systems:
            if isinstance(s, system_type):
                return s  # type: ignore[return-value]
        for s in self._async_systems:
            if isinstance(s, system_type):
                return s  # type: ignore[return-value]
        return None

    def update(self, *args: Any, **kwargs: Any) -> None:
        """Run all **synchronous** systems in priority order."""
        self._is_updating = True
        try:
            for sys in self._sync_systems:
                sys.update(self, *args, **kwargs)
        finally:
            self._is_updating = False
            self._flush_pending_kills()

    def timed_update(self, *args: Any, **kwargs: Any) -> None:
        """Like `update`, but records per-system time (ms) in `process_times_ms`."""
        self._is_updating = True
        try:
            for sys in self._sync_systems:
                t0 = perf_counter()
                sys.update(self, *args, **kwargs)
                ms = int((perf_counter() - t0) * 1000)
                self.process_times_ms[type(sys).__name__] = ms
        finally:
            self._is_updating = False
            self._flush_pending_kills()

    async def setup_async(self) -> None:
        """Run async systems' setup hooks once (if defined). Idempotent."""
        for sys in self._async_systems:
            setup = getattr(sys, "setup", None)
            if inspect.iscoroutinefunction(setup):
                await setup(self)  # type: ignore[misc]
        self._async_setup_done = True

    async def aupdate(self, *args: Any, **kwargs: Any) -> None:
        """
        Run all systems: synchronous first, then asynchronous **sequentially** by priority.
        Suitable for direct integration with your event loop.
        """
        if not self._async_setup_done:
            await self.setup_async()
        self._is_updating = True
        try:
            for sys in self._sync_systems:
                sys.update(self, *args, **kwargs)
            for sys in self._async_systems:
                t0 = perf_counter()
                await sys.update(self, *args, **kwargs)  # type: ignore[misc]
                ms = int((perf_counter() - t0) * 1000)
                self.process_times_ms[type(sys).__name__] = ms
        finally:
            self._is_updating = False
            self._flush_pending_kills()

    async def aupdate_concurrent(self, *args: Any, **kwargs: Any) -> None:
        """
        Run sync systems first; then run async systems concurrently **within the same priority**.
        Higher-priority groups run before lower-priority groups.
        """
        import asyncio

        if not self._async_setup_done:
            await self.setup_async()
        self._is_updating = True
        try:
            for sys in self._sync_systems:
                sys.update(self, *args, **kwargs)

            # group by priority
            buckets: Dict[int, List[AsyncSystem]] = {}
            for s in self._async_systems:
                buckets.setdefault(s.priority, []).append(s)

            for prio in sorted(buckets.keys(), reverse=True):
                tasks = [asyncio.create_task(s.update(self, *args, **kwargs)) for s in buckets[prio]]
                t0 = perf_counter()
                await asyncio.gather(*tasks)
                ms = int((perf_counter() - t0) * 1000)
                # record group timing
                self.process_times_ms[f"AsyncGroup(p={prio})"] = ms
        finally:
            self._is_updating = False
            self._flush_pending_kills()

    # --------------------------
    # Utilities
    # --------------------------
    @contextmanager
    def defer_deletions(self) -> Iterator[None]:
        """Context manager to defer entity destruction until the block exits."""
        prev = self._is_updating
        self._is_updating = True
        try:
            yield
        finally:
            self._is_updating = prev
            if not self._is_updating:
                self._flush_pending_kills()

    def component_count(self, component_type: Type[Any]) -> int:
        """Total entities having a given component type."""
        count = 0
        for arch in self._archetype_by_type.get(component_type, ()):
            count += len(arch.entities)
        return count

    def clear(self) -> None:
        """Remove all entities and components. Systems remain attached."""
        # Reinitialize entity/archetype structures but keep system lists.
        self._gen.clear()
        self._entity_arch.clear()
        self._entity_row.clear()
        self._free_indices.clear()
        self._archetypes.clear()
        self._archetype_by_type.clear()
        self._empty = self._get_or_create_archetype(frozenset())
        self._cache_view_single.clear()
        self._cache_view_multi.clear()
        self._pending_kill.clear()
        self._bump_version()

    def reset(self) -> None:
        """Reset the world completely (entities, components, caches, systems)."""
        # Clear entity/component data
        self.clear()
        # Clear systems and timing
        self._sync_systems.clear()
        self._async_systems.clear()
        self.process_times_ms.clear()
        self._async_setup_done = False
        self._version = 0
        self._is_updating = False

    # --------------------------
    # Internals
    # --------------------------
    def _flush_pending_kills(self) -> None:
        if not self._pending_kill:
            return
        for eid in list(self._pending_kill):
            if self._is_live(eid):
                self.destroy_entity(eid, immediate=True)
        self._pending_kill.clear()

    def __repr__(self) -> str:
        return f"<World entities={self.entity_count()} archetypes={len(self._archetypes)} sync={len(self._sync_systems)} async={len(self._async_systems)}>"
