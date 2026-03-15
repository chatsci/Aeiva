from __future__ import annotations

from typing import Callable, Iterable, Optional

from aeiva.llm.llm_gateway_config import LLMGatewayConfig
from aeiva.llm.providers.base import LLMProvider

ProviderFactory = Callable[[LLMGatewayConfig], LLMProvider]


class UnknownLLMProviderError(ValueError):
    """Raised when an unregistered provider is requested."""


class LLMProviderRegistry:
    def __init__(self) -> None:
        self._factories: dict[str, ProviderFactory] = {}
        self._canonical_names: set[str] = set()

    @staticmethod
    def _normalize_name(name: str) -> str:
        return str(name).strip().lower()

    def register(
        self,
        name: str,
        factory: ProviderFactory,
        *,
        aliases: Iterable[str] = (),
    ) -> None:
        normalized = self._normalize_name(name)
        if not normalized:
            raise ValueError("Provider name cannot be empty.")

        self._factories[normalized] = factory
        self._canonical_names.add(normalized)

        for alias in aliases:
            alias_name = self._normalize_name(alias)
            if alias_name:
                self._factories[alias_name] = factory

    def is_registered(self, name: str) -> bool:
        return self._normalize_name(name) in self._factories

    def provider_names(self, *, include_aliases: bool = True) -> list[str]:
        if include_aliases:
            return sorted(self._factories.keys())
        return sorted(self._canonical_names)

    def create(
        self,
        config: LLMGatewayConfig,
        provider_name: Optional[str] = None,
    ) -> LLMProvider:
        resolved_name = self._normalize_name(
            provider_name or config.llm_provider or "litellm"
        )
        factory = self._factories.get(resolved_name)
        if factory is None:
            supported = ", ".join(self.provider_names(include_aliases=False))
            raise UnknownLLMProviderError(
                f"Unknown llm_provider='{resolved_name}'. Supported providers: {supported}"
            )
        return factory(config)


_DEFAULT_REGISTRY: Optional[LLMProviderRegistry] = None


def _register_builtin_providers(registry: LLMProviderRegistry) -> None:
    from aeiva.llm.providers.litellm_provider import LiteLLMProvider
    from aeiva.llm.providers.minicpm_local_provider import MiniCPMLocalProvider

    registry.register("litellm", LiteLLMProvider)
    registry.register("minicpm_local", MiniCPMLocalProvider, aliases=("minicpm",))


def get_llm_provider_registry() -> LLMProviderRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = LLMProviderRegistry()
        _register_builtin_providers(_DEFAULT_REGISTRY)
    return _DEFAULT_REGISTRY


def create_llm_provider(
    config: LLMGatewayConfig,
    provider_name: Optional[str] = None,
) -> LLMProvider:
    return get_llm_provider_registry().create(config, provider_name=provider_name)


def get_registered_provider_names(*, include_aliases: bool = True) -> list[str]:
    return get_llm_provider_registry().provider_names(include_aliases=include_aliases)
