"""
Memory Neuron - EventBus-integrated memory system.

MemoryNeuron wraps the memory system with the neuron architecture,
enabling event-driven memory operations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from aeiva.neuron import BaseNeuron, NeuronConfig, Signal
from aeiva.cognition.memory.memory_unit import MemoryUnit
from aeiva.cognition.memory.memory_config import MemoryConfig
from aeiva.cognition.memory.memory_service import MemoryService

logger = logging.getLogger(__name__)


INPUT_EVENTS = [
    "memory.store",
    "memory.retrieve",
    "memory.query",
    "memory.get",
    "memory.update",
    "memory.delete",
    "memory.filter",
    "memory.organize",
    "memory.structurize",
    "memory.skillize",
    "memory.parameterize",
    "memory.embed",
    "memory.load",
    "memory.save",
]


@dataclass
class MemoryNeuronConfig(NeuronConfig):
    """
    Configuration for MemoryNeuron.

    Composes MemoryConfig for memory-specific settings and adds
    neuron-specific fields (input_events, output_event).
    """

    memory: MemoryConfig = field(default_factory=MemoryConfig)
    input_events: List[str] = field(default_factory=lambda: list(INPUT_EVENTS))
    output_event: str = "memory.result"

    # Convenience proxies so callers can still write config.auto_embed etc.
    @property
    def auto_embed(self) -> bool:
        return self.memory.auto_embed

    @property
    def default_retrieve_type(self) -> str:
        return self.memory.default_retrieve_type

    @property
    def default_top_k(self) -> int:
        return self.memory.default_top_k


class MemoryNeuron(BaseNeuron):
    """
    Memory neuron for event-driven memory operations.

    Subscribes to memory.* events, dispatches to MemoryService,
    and emits result/error events.
    """

    EMISSIONS = [
        "memory.result",
        "memory.stored",
        "memory.retrieved",
        "memory.error",
        "memory.filtered",
        "memory.organized",
        "memory.structurized",
        "memory.skillized",
        "memory.parameterized",
    ]
    SUBSCRIPTIONS = list(INPUT_EVENTS)

    def __init__(
        self,
        name: str = "memory",
        config: Optional[Union[MemoryNeuronConfig, Dict[str, Any]]] = None,
        event_bus: Optional[Any] = None,
        **kwargs
    ):
        if config is None:
            self.config = MemoryNeuronConfig()
        elif isinstance(config, dict):
            self.config = self._config_from_dict(config)
        else:
            self.config = config

        super().__init__(
            name=name,
            config=self.config,
            event_bus=event_bus,
            **kwargs
        )

        self.SUBSCRIPTIONS = self.config.input_events.copy()
        self.core: Optional[MemoryService] = None

        # Operation statistics
        self._stores = 0
        self._retrieves = 0
        self._errors = 0

    @staticmethod
    def _config_from_dict(d: Dict[str, Any]) -> "MemoryNeuronConfig":
        """Build MemoryNeuronConfig from a flat dict (backward-compatible)."""
        memory_keys = {f.name for f in MemoryConfig.__dataclass_fields__.values()}
        memory_kwargs = {k: v for k, v in d.items() if k in memory_keys}
        neuron_kwargs: Dict[str, Any] = {}
        if "input_events" in d:
            neuron_kwargs["input_events"] = d["input_events"]
        if "output_event" in d:
            neuron_kwargs["output_event"] = d["output_event"]
        return MemoryNeuronConfig(memory=MemoryConfig(**memory_kwargs), **neuron_kwargs)

    # ---- lifecycle ----

    async def setup(self) -> None:
        await super().setup()
        self.core = MemoryService(self.config.memory)
        self.core.setup()
        logger.info(f"MemoryNeuron '{self.name}' setup complete")

    async def teardown(self) -> None:
        if self.core is not None:
            await self.core.teardown()
        await super().teardown()
        logger.info(f"MemoryNeuron '{self.name}' teardown complete")

    # ---- dispatch ----

    # Maps operation name -> (handler_method_name, needs_data, needs_params)
    _DISPATCH = {
        "store":        "_op_store",
        "retrieve":     "_op_retrieve",
        "query":        "_op_retrieve",
        "get":          "_op_get",
        "update":       "_op_update",
        "delete":       "_op_delete",
        "filter":       "_op_filter",
        "organize":     "_op_organize",
        "structurize":  "_op_structurize",
        "skillize":     "_op_skillize",
        "parameterize": "_op_parameterize",
        "embed":        "_op_embed",
        "load":         "_op_load",
        "save":         "_op_save",
    }

    _PARAM_OPS = frozenset({
        "filter", "organize", "structurize", "skillize",
        "parameterize", "embed", "load", "save",
    })

    async def process(self, signal: Signal) -> Optional[Dict[str, Any]]:
        try:
            data = signal.data
            operation = None
            params: Dict[str, Any] = {}

            if isinstance(data, dict):
                operation = data.get("operation")
                params = data.get("params", {})
                if operation and "content" in data:
                    data = data["content"]
                elif operation and "query" in data:
                    data = data["query"]

            if operation is None:
                operation = self._infer_operation(signal.source or "")

            if isinstance(signal.data, dict) and not params and operation in self._PARAM_OPS:
                params = signal.data

            handler_name = self._DISPATCH.get(operation)
            if handler_name is None:
                raise ValueError(f"Unknown operation: {operation}")

            handler = getattr(self, handler_name)
            return await handler(data, params)

        except Exception as e:
            self._errors += 1
            logger.error(f"MemoryNeuron error: {e}")
            await self._emit_error(str(e), signal)
            return {"success": False, "error": str(e)}

    _KNOWN_OPS = frozenset({
        "store", "retrieve", "query", "get", "update", "delete",
        "filter", "organize", "structurize", "skillize",
        "parameterize", "embed", "load", "save",
    })

    @staticmethod
    def _infer_operation(source: str) -> str:
        # Use the last dot-separated segment for exact matching.
        # Prevents "restore" matching "store", "retrieve_related" matching "retrieve".
        suffix = source.rsplit(".", 1)[-1]
        if suffix in MemoryNeuron._KNOWN_OPS:
            return suffix
        return "store"

    # ---- operation handlers ----

    def _require_core(self, operation: str) -> MemoryService:
        if self.core is None:
            raise RuntimeError(f"Memory core not initialized (operation={operation})")
        return self.core

    async def _op_store(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        self._stores += 1
        core = self._require_core("store")
        unit = await core.create_async(data, **params)
        await self._emit("memory.stored", {
            "id": unit.id,
            "content": unit.content,
            "status": "stored",
            "has_embedding": unit.embedding is not None
        })
        return {
            "success": True, "operation": "store",
            "unit_id": unit.id, "has_embedding": unit.embedding is not None
        }

    async def _op_retrieve(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        self._retrieves += 1
        core = self._require_core("retrieve")
        retrieve_type = params.get("retrieve_type", self.config.default_retrieve_type)
        kwargs = {k: v for k, v in params.items() if k != "retrieve_type"}
        results = await core.retrieve_async(data, retrieve_type, **kwargs)
        await self._emit("memory.retrieved", {
            "query": data,
            "results": [r.to_dict() if hasattr(r, 'to_dict') else r for r in results],
            "count": len(results),
            "retrieve_type": retrieve_type
        })
        return {
            "success": True, "operation": "retrieve",
            "results": results, "count": len(results),
            "retrieve_type": retrieve_type
        }

    async def _op_get(self, data: Any, _params: Dict[str, Any]) -> Dict[str, Any]:
        core = self._require_core("get")
        unit_id = data if isinstance(data, str) else data.get("id")
        unit = core.get(unit_id)
        return {
            "success": unit is not None, "operation": "get",
            "unit": unit.to_dict() if unit else None
        }

    async def _op_update(self, data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        core = self._require_core("update")
        unit_id = data.get("id") if isinstance(data, dict) else data
        updates = params.get("updates", {})
        success = core.update(unit_id, updates)
        return {"success": success, "operation": "update", "unit_id": unit_id}

    async def _op_delete(self, data: Any, _params: Dict[str, Any]) -> Dict[str, Any]:
        core = self._require_core("delete")
        unit_id = data if isinstance(data, str) else data.get("id")
        success = core.delete(unit_id)
        return {"success": success, "operation": "delete", "unit_id": unit_id}

    async def _op_filter(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            raise ValueError("Missing filter criteria")
        filter_type = params.get("filter_type")
        if not filter_type:
            raise ValueError("Missing filter_type")
        core = self._require_core("filter")
        filtered = core.filter(params)
        await self._emit("memory.filtered", {
            "filter_type": filter_type, "count": len(filtered)
        })
        return {
            "success": True, "operation": "filter",
            "results": filtered, "count": len(filtered)
        }

    async def _op_organize(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        unit_ids = params.get("unit_ids", [])
        organize_type = params.get("organize_type")
        metadata = params.get("metadata")
        if not unit_ids or not organize_type:
            raise ValueError("Missing unit_ids or organize_type")
        core = self._require_core("organize")
        group_id, organized = core.organize_units(unit_ids, organize_type, metadata=metadata)
        await self._emit("memory.organized", {
            "organize_type": organize_type, "count": len(organized)
        })
        return {
            "success": True, "operation": "organize",
            "group_id": group_id, "results": organized, "count": len(organized)
        }

    async def _op_structurize(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        unit_ids = params.get("unit_ids", [])
        structure_type = params.get("structure_type")
        if not unit_ids or not structure_type:
            raise ValueError("Missing unit_ids or structure_type")
        core = self._require_core("structurize")
        core.structurize(unit_ids, structure_type, **params)
        await self._emit("memory.structurized", {
            "structure_type": structure_type, "count": 0
        })
        return {
            "success": True, "operation": "structurize",
            "results": [], "count": 0
        }

    async def _op_skillize(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        unit_ids = params.get("unit_ids", [])
        skill_type = params.get("skill_type")
        if not unit_ids or not skill_type:
            raise ValueError("Missing unit_ids or skill_type")
        core = self._require_core("skillize")
        core.skillize(unit_ids, skill_type, **params)
        await self._emit("memory.skillized", {"skill_type": skill_type})
        return {"success": True, "operation": "skillize", "results": []}

    async def _op_parameterize(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        parameterize_type = params.get("parameterize_type")
        if not parameterize_type:
            raise ValueError("Missing parameterize_type")
        core = self._require_core("parameterize")
        core.parameterize(**params)
        await self._emit("memory.parameterized", {"parameterize_type": parameterize_type})
        return {"success": True, "operation": "parameterize", "results": []}

    async def _op_embed(self, data: Any, _params: Dict[str, Any]) -> Dict[str, Any]:
        unit_id = data if isinstance(data, str) else data.get("id")
        if not unit_id:
            raise ValueError("Missing unit_id")
        success = await self.embed(unit_id)
        return {"success": success, "operation": "embed", "unit_id": unit_id}

    async def _op_load(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        core = self._require_core("load")
        path = params.get("path")
        units = core.load(path)
        return {
            "success": True, "operation": "load",
            "results": units, "count": len(units)
        }

    async def _op_save(self, _data: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        core = self._require_core("save")
        path = params.get("path")
        core.save(path)
        return {"success": True, "operation": "save", "path": path}

    # ---- event helpers ----

    async def _emit(self, event: str, payload: Any) -> None:
        if self.events:
            await self.events.emit(event, payload=payload)

    async def _emit_error(self, error: str, original_signal: Signal) -> None:
        await self._emit("memory.error", {
            "error": error,
            "source": original_signal.source,
            "trace_id": original_signal.trace_id
        })

    async def send(self, output: Any, parent: Signal = None) -> None:
        if output is None:
            return
        if parent:
            signal = parent.child(self.name, output)
        else:
            signal = Signal(source=self.name, data=output)
        self.working.last_output = output
        if self.events:
            emit_args = self.signal_to_event_args(self.config.output_event, signal)
            await self.events.emit(**emit_args)

    # ---- convenience methods ----

    async def store(self, content: Any, modality: str = "text", **kwargs) -> str:
        signal = Signal(
            source="memory.store",
            data={
                "operation": "store",
                "content": content,
                "params": {"modality": modality, **kwargs}
            }
        )
        result = await self.process(signal)
        return result.get("unit_id")

    async def retrieve_similar(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        signal = Signal(
            source="memory.retrieve",
            data={
                "operation": "retrieve",
                "query": query,
                "params": {"retrieve_type": "similar", "top_k": top_k}
            }
        )
        result = await self.process(signal)
        return result.get("results", [])

    async def retrieve_semantic(
        self, query: str, top_k: int = 10, threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        signal = Signal(
            source="memory.retrieve",
            data={
                "operation": "retrieve",
                "query": query,
                "params": {
                    "retrieve_type": "semantic",
                    "top_k": top_k,
                    "threshold": threshold
                }
            }
        )
        result = await self.process(signal)
        return result.get("results", [])

    async def embed(self, unit_id: str) -> bool:
        if self.core is None:
            return False
        return await self.core.embed_async(unit_id)

    def health_check(self) -> Dict[str, Any]:
        base_health = super().health_check()
        backend = self.core.backend if self.core else None
        backend_info = None
        if backend is not None:
            backend_info = {
                "type": type(backend).__name__,
                "size": getattr(backend, 'count', lambda: 0)()
                if callable(getattr(backend, 'count', None)) else 0,
            }
        return {
            **base_health,
            "stores": self._stores,
            "retrieves": self._retrieves,
            "errors": self._errors,
            "memory_backend": backend_info,
            "has_embedder": self.core._embedder is not None if self.core else False,
            "auto_embed": self.config.auto_embed,
        }
