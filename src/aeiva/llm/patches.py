"""
Patches for third-party library issues.

These patches fix bugs in dependencies that haven't been fixed upstream yet.
Each patch should be documented with the issue it fixes.
"""

from typing import Any


def patch_litellm_responses_api() -> None:
    """
    Patch litellm's ResponsesAPIResponse.model_dump to fix Pydantic warning.

    Issue: litellm's logging calls model_dump() on ResponsesAPIResponse, but the
    'usage' field may be a dict instead of ResponseAPIUsage, causing:
    "Expected `ResponseAPIUsage` but got `dict`"

    Fix: Coerce usage to ResponseAPIUsage before Pydantic serializes.

    Remove when: litellm fixes this upstream.
    """
    try:
        from litellm.types.llms.openai import ResponsesAPIResponse, ResponseAPIUsage
    except ImportError:
        return

    if getattr(ResponsesAPIResponse, "_model_dump_patched", False):
        return

    def _coerce_usage(usage: Any) -> Any:
        if usage is None or not isinstance(usage, dict):
            return usage
        return ResponseAPIUsage(
            input_tokens=usage.get("input_tokens") or usage.get("prompt_tokens") or 0,
            output_tokens=usage.get("output_tokens") or usage.get("completion_tokens") or 0,
            total_tokens=usage.get("total_tokens") or 0,
        )

    original_model_dump = ResponsesAPIResponse.model_dump

    def patched_model_dump(self, *args, **kwargs):
        if isinstance(self.usage, dict):
            try:
                object.__setattr__(self, "usage", _coerce_usage(self.usage))
            except (AttributeError, TypeError, ValueError):
                pass
        return original_model_dump(self, *args, **kwargs)

    ResponsesAPIResponse.model_dump = patched_model_dump
    ResponsesAPIResponse._model_dump_patched = True


def apply_all_patches() -> None:
    """Apply all patches. Call once at module load time."""
    patch_litellm_responses_api()
