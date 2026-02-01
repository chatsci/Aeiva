"""
MemoryService: Core memory logic without EventBus concerns.

This class implements the Memory interface and serves as the canonical
memory engine for both neuron and non-neuron workflows.

Architecture: single ``_backend: MemoryBackend`` — no dual-path fork.
When ``storage_config`` is provided the external ``MemoryStorage`` is
wrapped via ``MemoryStorageBackend``; otherwise a lightweight local
backend (InMemory / JsonFile / vector variants) is created directly.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Union

from aeiva.cognition.memory.base_memory import Memory
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_cleaner import MemoryCleaner
from aeiva.cognition.memory.memory_organizer import MemoryOrganizer
from aeiva.cognition.memory.memory_utils import extract_embedding_from_response

logger = logging.getLogger(__name__)


class MemoryService(Memory):
    """
    Canonical memory engine: single backend + optional embedder.

    It can back:
        - MemoryNeuron (async, event-driven)
        - Direct usage via Memory interface (sync)
    """

    def __init__(self, config: Optional[Union[MemoryConfig, Dict[str, Any], Any]] = None):
        self.config = self._coerce_config(config)
        self._backend: Optional[Any] = None
        self._embedder: Optional[Any] = None

        self.cleaner = MemoryCleaner()
        self.organizer = MemoryOrganizer()

    # ---------- lifecycle ----------

    def setup(self) -> None:
        """Initialize embedder and backend."""
        embedder_config = self.config.embedder_config
        if embedder_config and hasattr(embedder_config, "to_dict"):
            embedder_config = embedder_config.to_dict()
        if embedder_config:
            try:
                from aeiva.embedding.embedder import Embedder
                self._embedder = Embedder(embedder_config)
                logger.info("MemoryService: Embedder initialized")
            except Exception as e:
                logger.warning(f"MemoryService: Failed to initialize embedder: {e}")
                self._embedder = None

        storage_config = self.config.storage_config
        if storage_config and hasattr(storage_config, "to_dict"):
            storage_config = storage_config.to_dict()
        if storage_config:
            try:
                from aeiva.cognition.memory.memory_storage import MemoryStorage
                from aeiva.cognition.memory.backend import MemoryStorageBackend
                ms = MemoryStorage(storage_config)
                self._backend = MemoryStorageBackend(ms)
                logger.info("MemoryService: MemoryStorageBackend initialized")
            except Exception as e:
                logger.warning(f"MemoryService: Failed to initialize MemoryStorage: {e}")
                self._backend = None

        if self._backend is None:
            self._backend = self._create_local_backend()

    async def teardown(self) -> None:
        """Clean up resources."""
        if self._backend is not None:
            # MemoryStorageBackend wraps MemoryStorage which has .close()
            inner = getattr(self._backend, "_storage", None)
            if inner is not None and hasattr(inner, "close"):
                inner.close()

    # ---------- CRUD ----------

    def create(self, content: Any, **kwargs) -> MemoryUnit:
        unit = self._build_unit(content, kwargs)
        if self.config.auto_embed and self._embedder and unit.embedding is None:
            embedding = self._generate_embedding_sync(str(unit.content))
            if embedding:
                unit.embedding = embedding
        self._backend.add(unit)
        return unit

    async def create_async(self, content: Any, **kwargs) -> MemoryUnit:
        unit = self._build_unit(content, kwargs)
        if self.config.auto_embed and self._embedder and unit.embedding is None:
            embedding = await self._generate_embedding_async(str(unit.content))
            if embedding:
                unit.embedding = embedding
        self._backend.add(unit)
        return unit

    def get(self, unit_id: str) -> Optional[MemoryUnit]:
        return self._backend.get(unit_id)

    def update(self, unit_id: str, updates: Dict[str, Any]) -> bool:
        return self._backend.update(unit_id, updates)

    def delete(self, unit_id: str) -> bool:
        return self._backend.delete(unit_id)

    def get_all(self) -> List[MemoryUnit]:
        return self._backend.get_all()

    def delete_all(self) -> int:
        return self._backend.clear()

    # ---------- persistence ----------

    def load(self, path: Optional[str] = None) -> List[MemoryUnit]:
        return self._backend.get_all()

    def save(self, path: Optional[str] = None) -> None:
        if path:
            import json
            units = self._backend.get_all()
            export_data = [u.to_dict() for u in units]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

    # ---------- operations ----------

    def filter(self, criteria: Dict[str, Any]) -> List[MemoryUnit]:
        if not criteria:
            return []
        filter_type = criteria.get("filter_type")
        if not filter_type:
            return []
        units = self._backend.get_all()
        # Exclude filter_type from kwargs — it's already passed as a positional arg.
        kwargs = {k: v for k, v in criteria.items() if k != "filter_type"}
        return self.cleaner.filter(units, filter_type, **kwargs)

    def organize(
        self,
        unit_ids: List[str],
        organize_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        group_id, _ = self.organize_units(unit_ids, organize_type, metadata=metadata)
        return group_id

    def organize_units(
        self,
        unit_ids: List[str],
        organize_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[str, List[MemoryUnit]]:
        memory_units = [self._backend.get(uid) for uid in unit_ids]
        memory_units = [u for u in memory_units if u is not None]
        if not memory_units:
            return "", []

        organized = self.organizer.organize(memory_units, organize_type, metadata=metadata)
        existing_ids = {u.id for u in memory_units}
        new_units = [u for u in organized if u.id not in existing_ids]

        for unit in new_units:
            self._backend.add(unit)

        for unit in memory_units:
            self._backend.update(unit.id, {"edges": unit.edges})

        group_id = new_units[0].id if new_units else ""
        return group_id, organized

    def embed(self, unit_id: str) -> bool:
        if not self._embedder:
            return False
        unit = self._backend.get(unit_id)
        if not unit:
            return False
        embedding = self._generate_embedding_sync(str(unit.content))
        if embedding:
            return self._backend.update(unit_id, {"embedding": embedding})
        return False

    async def embed_async(self, unit_id: str) -> bool:
        if not self._embedder:
            return False
        unit = self._backend.get(unit_id)
        if not unit:
            return False
        embedding = await self._generate_embedding_async(str(unit.content))
        if embedding:
            return self._backend.update(unit_id, {"embedding": embedding})
        return False

    def retrieve(self, query: Any, retrieve_type: str, **kwargs) -> List[MemoryUnit]:
        retrieve_type = retrieve_type or self.config.default_retrieve_type
        top_k = kwargs.get("top_k", self.config.default_top_k)
        threshold = kwargs.get("threshold", 0.0)
        relationship = kwargs.get("relationship")

        # --- related (graph-edge) retrieval ---
        if retrieve_type == "related":
            if hasattr(self._backend, "search_related"):
                return self._backend.search_related(query, relationship)
            # Fallback: edge-based traversal on the unit itself
            unit = self._backend.get(query)
            if unit is None:
                return []
            related_ids = set()
            for edge in unit.edges:
                if relationship is None or edge.relationship == relationship:
                    related_ids.add(edge.target_id)
            return [u for uid in related_ids if (u := self._backend.get(uid)) is not None]

        # --- vector / semantic retrieval ---
        if retrieve_type in ("vector", "semantic") and self._embedder:
            query_embedding = self._generate_embedding_sync(str(query))
            if query_embedding and hasattr(self._backend, "search_similar"):
                return self._backend.search_similar(query_embedding, top_k=top_k, threshold=threshold)

        # --- keyword / similar retrieval ---
        if hasattr(self._backend, "search_keyword"):
            return self._backend.search_keyword(str(query), top_k=top_k)

        # Inline word-overlap fallback
        query_str = str(query).lower()
        query_words = set(query_str.split())
        scored = []
        for unit in self._backend.get_all():
            content_words = set(str(unit.content).lower().split())
            overlap = len(query_words.intersection(content_words))
            if overlap > 0:
                scored.append((overlap / max(len(query_words), 1), unit))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [u for _, u in scored[:top_k]]

    async def retrieve_async(self, query: Any, retrieve_type: str, **kwargs) -> List[MemoryUnit]:
        """Async-friendly retrieval — uses async embedding when needed."""
        retrieve_type = retrieve_type or self.config.default_retrieve_type
        top_k = kwargs.get("top_k", self.config.default_top_k)
        threshold = kwargs.get("threshold", 0.0)
        relationship = kwargs.get("relationship")

        # Async embedding for semantic/vector search
        if retrieve_type in ("vector", "semantic") and self._embedder:
            query_embedding = await self._generate_embedding_async(str(query))
            if query_embedding and hasattr(self._backend, "search_similar"):
                return self._backend.search_similar(query_embedding, top_k=top_k, threshold=threshold)
            # Fall through to sync retrieve for keyword fallback
            return self.retrieve(query, "similar", top_k=top_k)

        # For non-embedding paths (related, keyword), call directly — pure in-memory ops.
        return self.retrieve(query, retrieve_type, **kwargs)

    # ---------- convenience ----------

    def store(self, content: Any, **kwargs) -> MemoryUnit:
        return self.create(content, **kwargs)

    def search(self, query: str, top_k: int = 10) -> List[MemoryUnit]:
        return self.retrieve(query, retrieve_type="similar", top_k=top_k)

    @property
    def backend(self) -> Optional[Any]:
        return self._backend

    # ---------- internal helpers ----------

    @staticmethod
    def _coerce_config(config: Optional[Any]) -> MemoryConfig:
        if config is None:
            return MemoryConfig()
        if isinstance(config, MemoryConfig):
            return config
        if isinstance(config, dict):
            return MemoryConfig(**MemoryService._filter_memory_fields(config))
        if hasattr(config, "memory") and isinstance(config.memory, MemoryConfig):
            return config.memory
        if hasattr(config, "to_dict"):
            return MemoryConfig(**MemoryService._filter_memory_fields(config.to_dict()))
        if hasattr(config, "__dict__"):
            data = {k: v for k, v in config.__dict__.items() if not k.startswith("_")}
            return MemoryConfig(**MemoryService._filter_memory_fields(data))
        return MemoryConfig()

    @staticmethod
    def _filter_memory_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        allowed = {f.name for f in MemoryConfig.__dataclass_fields__.values()}
        return {k: v for k, v in data.items() if k in allowed}

    def _create_local_backend(self):
        """Create a lightweight local backend (no MemoryStorage)."""
        try:
            from aeiva.cognition.memory.backend import (
                InMemoryBackend,
                JsonFileBackend,
                InMemoryVectorBackend,
                JsonFileVectorBackend,
            )

            backend_type = self.config.backend_type

            if backend_type == "json":
                file_path = self.config.json_file_path or "memory.json"
                if self._embedder:
                    return JsonFileVectorBackend(file_path)
                return JsonFileBackend(file_path)
            elif backend_type == "vector" or self._embedder:
                return InMemoryVectorBackend()
            else:
                return InMemoryBackend()
        except Exception as e:
            logger.warning(f"MemoryService: Failed to create local backend: {e}")
            from aeiva.cognition.memory.backend import InMemoryBackend
            return InMemoryBackend()

    def _build_unit(self, content: Any, metadata: Dict[str, Any]) -> MemoryUnit:
        if isinstance(content, MemoryUnit):
            return content
        if isinstance(content, dict) and "content" in content:
            return MemoryUnit.from_dict(content)

        return MemoryUnit(
            content=content,
            modality=metadata.get("modality", "text"),
            type=metadata.get("type"),
            status=metadata.get("status", "raw"),
            tags=metadata.get("tags", []),
            source_role=metadata.get("source_role"),
            source_name=metadata.get("source_name"),
            source_id=metadata.get("source_id"),
            location=metadata.get("location"),
            edges=metadata.get("edges", []),
            metadata=metadata.get("metadata", {}),
        )

    def _generate_embedding_sync(self, text: str) -> Optional[List[float]]:
        if not self._embedder:
            return None
        try:
            response = self._embedder.embed(text)
            return extract_embedding_from_response(response)
        except Exception as e:
            logger.error(f"MemoryService: embedding failed: {e}")
            return None

    async def _generate_embedding_async(self, text: str) -> Optional[List[float]]:
        if not self._embedder:
            return None
        try:
            if hasattr(self._embedder, "aembed"):
                response = await self._embedder.aembed(text)
            else:
                response = await asyncio.to_thread(self._embedder.embed, text)
            return extract_embedding_from_response(response)
        except Exception as e:
            logger.error(f"MemoryService: async embedding failed: {e}")
            return None
