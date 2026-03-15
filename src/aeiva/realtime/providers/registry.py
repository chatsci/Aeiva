from __future__ import annotations

import logging
from typing import Callable, Optional

from aeiva.realtime.providers.base import LiveRealtimeProvider

LiveProviderFactory = Callable[[dict, logging.Logger], LiveRealtimeProvider]


class UnknownRealtimeProviderError(ValueError):
    """Raised when an unregistered realtime provider is requested."""


class RealtimeProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, LiveProviderFactory] = {}
        self._canonical_names: set[str] = set()

    @staticmethod
    def _normalize_name(name: str) -> str:
        return str(name).strip().lower()

    def register(
        self,
        name: str,
        factory: LiveProviderFactory,
        *,
        aliases: tuple[str, ...] = (),
    ) -> None:
        normalized = self._normalize_name(name)
        if not normalized:
            raise ValueError("Realtime provider name cannot be empty.")
        self._factories[normalized] = factory
        self._canonical_names.add(normalized)
        for alias in aliases:
            alias_name = self._normalize_name(alias)
            if alias_name:
                self._factories[alias_name] = factory

    def provider_names(self, *, include_aliases: bool = True) -> list[str]:
        if include_aliases:
            return sorted(self._factories.keys())
        return sorted(self._canonical_names)

    def create(
        self,
        *,
        config_dict: dict,
        logger: logging.Logger,
        provider_name: Optional[str] = None,
    ) -> LiveRealtimeProvider:
        realtime_cfg = config_dict.get("realtime_config") or {}
        resolved_name = self._normalize_name(
            provider_name or realtime_cfg.get("provider") or "openai"
        )
        factory = self._factories.get(resolved_name)
        if factory is None:
            supported = ", ".join(self.provider_names(include_aliases=False))
            raise UnknownRealtimeProviderError(
                f"Unknown realtime provider='{resolved_name}'. Supported providers: {supported}"
            )
        return factory(config_dict, logger)


_DEFAULT_REGISTRY: Optional[RealtimeProviderRegistry] = None


def _register_builtin_providers(registry: RealtimeProviderRegistry) -> None:
    from aeiva.realtime.providers.minicpm_live_provider import MiniCPMLiveProvider
    from aeiva.realtime.providers.openai_live_provider import OpenAILiveProvider

    registry.register("openai", OpenAILiveProvider)
    registry.register("minicpm_local", MiniCPMLiveProvider, aliases=("minicpm",))


def get_realtime_provider_registry() -> RealtimeProviderRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = RealtimeProviderRegistry()
        _register_builtin_providers(_DEFAULT_REGISTRY)
    return _DEFAULT_REGISTRY


def create_live_realtime_provider(
    *,
    config_dict: dict,
    logger: logging.Logger,
    provider_name: Optional[str] = None,
) -> LiveRealtimeProvider:
    return get_realtime_provider_registry().create(
        config_dict=config_dict,
        logger=logger,
        provider_name=provider_name,
    )
