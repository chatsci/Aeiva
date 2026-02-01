# ECS — modern, elegant Entity–Component–System for Python

**Design goals**: clean, fast-enough, and pleasant to use — without overcomplicating the API.

- ✅ **Archetype storage** (dense, cache-friendly columns; O(1) moves on add/remove)
- ✅ **Entity generation counters** (stale-handle safety; 64‑bit packed ids)
- ✅ **Sync & Async systems** with priorities (sequential or concurrent async stepping)
- ✅ **Snapshot queries** (`view`) with caching + **live queries** (`iter_view`)
- ✅ **Deferred deletions** (`with world.defer_deletions():`)
- ✅ Modern typing with overloads and variadics (`TypeVarTuple`, `Unpack`)

Works great on Python **3.11+**; Python **3.12+** recommended.

---

## Install

Copy `ecs.py` into your project. Then:

```python
from ecs import World, System, AsyncSystem, EntityId
```

---

## Core ideas

### Archetypes
Entities sharing the **same set of component types** live in the same archetype. Each archetype stores components **column-wise** for great iteration performance. When you add/remove a component, the entity moves between archetypes in **O(1)** via swap‑remove.

### Safe EntityId via generation counters
Each `EntityId` is a 64‑bit int: `[generation:32][index:32]`. When an entity is destroyed its generation increments, so stale ids are rejected.

### Queries
- `view(A, B, ...)` → **snapshot** list (safe against mutations).  
  Cached until: create/destroy, add/remove component, or **replace** a component instance.
- `iter_view(A, B, ...)` → **live** generator (fast, low allocation).  
  For one type yields `(eid, comp)`; for many types yields `(eid, (c1, c2, ...))`.

### Systems
- `System.update(world, *args, **kwargs)` — synchronous work.
- `AsyncSystem.update(world, *args, **kwargs)` — asynchronous work.
- Stepping:
  - `world.update(...)` — sync systems only.
  - `await world.aupdate(...)` — sync first, then async systems **sequentially** by priority.
  - `await world.aupdate_concurrent(...)` — sync first, then async systems **concurrently** within each priority bucket (buckets run high→low).
- **Async setup**: If an `AsyncSystem` defines `async setup(self, world)`, it is **automatically called once** on the *first* `aupdate(...)`/`aupdate_concurrent(...)`.

---

## Quick start

```python
from dataclasses import dataclass
from ecs import World, System, AsyncSystem

@dataclass
class Position: x: float; y: float
@dataclass
class Velocity: vx: float; vy: float

class Physics(System):
    priority = 10
    def update(self, world: World, dt: float, **_):
        for eid, (p, v) in world.view(Position, Velocity):
            p.x += v.vx * dt
            p.y += v.vy * dt

w = World()
w.add_system(Physics(), priority=10)

e = w.create_entity(Position(0,0), Velocity(2,0))
w.update(dt=0.5)
print(w.get_component(e, Position))  # Position(x=1.0, y=0.0)
```

### Async example

```python
import asyncio
from dataclasses import dataclass
from ecs import World, AsyncSystem

@dataclass
class Health: hp: int

class Regen(AsyncSystem):
    priority = 5
    async def update(self, world: World, **_):
        for eid, h in world.iter_view(Health):
            h.hp += 1

async def main():
    w = World()
    w.add_system(Regen())
    e = w.create_entity(Health(10))
    await w.aupdate()  # runs async systems after sync; setup() auto-called if defined
    print(w.get_component(e, Health).hp)  # 11

# asyncio.run(main())
```

---

## API (short)

**World**
- `create_entity(*components) -> EntityId`
- `destroy_entity(eid, *, immediate=False) -> None`
- `entity_exists(eid) -> bool`
- `entity_count() -> int`
- `add_component(eid, component) -> None`  *(replacing also invalidates view caches)*
- `remove_component(eid, ComponentType) -> component`
- `get_component(eid, ComponentType) -> component`
- `try_component(eid, ComponentType) -> component | None`
- `has_component(eid, ComponentType) -> bool`
- `has_components(eid, *ComponentTypes) -> bool`
- `components_for(eid) -> tuple[components, ...]`
- `view(A)` → `list[(eid, A)]`  
  `view(A,B,...)` → `list[(eid, (A,B,...))]`
- `iter_view(A)` → `iter[(eid, A)]`  
  `iter_view(A,B,...)` → `iter[(eid, (A,B,...))]`
- `entities() -> list[EntityId]` (snapshot of all)  
  `iter_entities() -> iter[EntityId]` (live over all)
- `defer_deletions() -> context manager`
- `component_count(ComponentType) -> int`
- `add_system(sys, *, priority=None)`, `remove_system(SystemClass)`, `get_system(SystemClass)`
- `update(...)`, `timed_update(...)`
- `await aupdate(...)`, `await aupdate_concurrent(...)`  *(auto-calls async systems’ setup once)*
- `clear()` — remove all entities & components, keep systems  
- `reset()` — reset the entire world (incl. systems)

**System / AsyncSystem**
- override `update(...)` / `async update(...)`
- optional `setup(self, world)` / `async setup(self, world)`

---

## Notes

- **Why invalidate view cache on replace?** Safer by default: a fresh `view(...)` returns the *new* component object after replacement. If you need ultra-high-frequency replacements, consider live iteration (`iter_view`) or a future opt-in `replace_component(..., invalidate=False)` variant.
- Use dataclasses (or `__slots__`) for components to reduce per-instance overhead.

---

## Testing

See **`test.py`** for a runnable suite covering:
- Sync/async updates, system priorities
- Archetype moves and component replacement cache invalidation
- Generation counters (stale-id rejection)
- Deferred deletions safety
- Entities API (snapshot + live)
- Async concurrent speed-up

Run as a script (`python test.py`) or with pytest (`pytest -q`).

---

## Integrating your event bus

Keep ECS decoupled. Subscribe/publish from your systems using your existing bus and timers. If you *must* emit at world-level (e.g., on create/destroy), subclass `World` and override selectively.

---

## License

Use freely in your project. If you extract this file into a library, a short attribution is appreciated.
