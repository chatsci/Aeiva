"""Shared progress hint formatting helpers for gateways and UI handlers."""

from __future__ import annotations

from typing import Any, Iterable, Sequence, Tuple

DEFAULT_PROGRESS_PHASES: Tuple[str, ...] = (
    "Thinking",
    "Acting",
    "Waiting for tools",
    "Retrying if needed",
    "Summarizing",
)
DEFAULT_PHASE_THRESHOLDS_SECONDS: Tuple[int, ...] = (0, 5, 12, 24, 40)


def normalize_progress_phases(value: Any) -> Tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        phases = tuple(str(item).strip() for item in value if str(item).strip())
        if phases:
            return phases
    return DEFAULT_PROGRESS_PHASES


def _normalize_thresholds(value: Iterable[Any], *, phase_count: int) -> Tuple[int, ...]:
    out: list[int] = []
    for item in value:
        try:
            parsed = int(item)
        except Exception:
            continue
        out.append(max(0, parsed))
    if not out:
        out = list(DEFAULT_PHASE_THRESHOLDS_SECONDS[:phase_count])
    while len(out) < phase_count:
        out.append(out[-1] if out else 0)
    if len(out) > phase_count:
        out = out[:phase_count]
    ordered: list[int] = []
    floor = 0
    for item in out:
        floor = max(floor, item)
        ordered.append(floor)
    return tuple(ordered)


def build_progress_hint(
    *,
    elapsed_seconds: float,
    hint_index: int,
    phases: Sequence[str] | None = None,
    phase_thresholds_seconds: Sequence[int] | None = None,
) -> str:
    clean_phases = tuple(phases or DEFAULT_PROGRESS_PHASES)
    if not clean_phases:
        clean_phases = DEFAULT_PROGRESS_PHASES
    thresholds = _normalize_thresholds(
        phase_thresholds_seconds or DEFAULT_PHASE_THRESHOLDS_SECONDS,
        phase_count=len(clean_phases),
    )
    elapsed = max(0, int(round(float(elapsed_seconds))))
    phase_idx = 0
    for idx, threshold in enumerate(thresholds):
        if elapsed >= threshold:
            phase_idx = idx
        else:
            break
    phase = clean_phases[min(max(0, phase_idx), len(clean_phases) - 1)]
    dots = "." * ((max(0, int(hint_index)) % 3) + 1)
    return f"{phase}{dots} ({elapsed}s)"
