# MetaUI VNext Rebuild Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild MetaUI as a strict, minimal, robust renderer/event bridge where AI fully defines UI behavior, while preserving a stable legacy path until vnext reaches production quality.

**Architecture:** Introduce a clean vnext package (`aeiva.metaui.vnext`) with strict contract-first validation and minimal operation surface. Keep current implementation as explicit `legacy` runtime and expose `aeiva.metaui.tool` as a stable alias during migration.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, dialogue replay (`aeiva-dialogue-replay`), local gateway (`aeiva-gateway`), existing desktop runtime.

---

## Stage 0 — Guardrails First (Completed)

**Files:**
- Create: `tests/metaui/test_invariants_ci.py`
- Create: `tests/metaui/test_vnext_schema.py`
- Create: `tests/metaui/test_vnext_api.py`

**Deliverables:**
- CI invariants for module boundaries and anti-hot-file rules.
- vnext contract tests for strict schema and operation semantics.

**Acceptance:**
- `uv run pytest tests/metaui/test_invariants_ci.py tests/metaui/test_vnext_schema.py tests/metaui/test_vnext_api.py -q`

---

## Stage 1 — Legacy Isolation (Completed)

**Files:**
- Move: `src/aeiva/metaui/tool.py` -> `src/aeiva/metaui/legacy/tool.py`
- Move: `src/aeiva/metaui/tool_state.py` -> `src/aeiva/metaui/legacy/tool_state.py`
- Create: `src/aeiva/metaui/tool.py` (module alias)
- Create: `src/aeiva/metaui/tool_state.py` (module alias)
- Create: `src/aeiva/metaui/legacy/__init__.py`
- Modify: `src/aeiva/tool/registry.py`
- Modify: `src/aeiva/command/aeiva_gateway.py`

**Deliverables:**
- Old implementation explicitly under `legacy` namespace.
- Stable import remains `aeiva.metaui.tool`.
- Tool discovery continues via registry external module loading.

**Acceptance:**
- `uv run pytest tests/metaui tests/tool/test_metaui_tool.py -q -rs`
- `uv run python - <<'PY' ... ToolRegistry discover prints metaui module ... PY`

---

## Stage 2 — VNext Contract Core (In Progress)

**Files:**
- Create: `src/aeiva/metaui/vnext/errors.py`
- Create: `src/aeiva/metaui/vnext/schema.py`
- Create: `src/aeiva/metaui/vnext/api.py`
- Create: `src/aeiva/metaui/vnext/__init__.py`

**Deliverables:**
- Minimal implemented ops: `status`, `protocol_schema`, `validate_spec`.
- Explicit `not_implemented` response for runtime mutating ops until each stage lands.
- No heuristic fallback behavior.

**Acceptance:**
- `uv run pytest tests/metaui/test_vnext_schema.py tests/metaui/test_vnext_api.py -q`

---

## Stage 3 — VNext Runtime Read Path

**Files:**
- Create: `src/aeiva/metaui/vnext/session_store.py`
- Create: `src/aeiva/metaui/vnext/event_store.py`
- Create: `src/aeiva/metaui/vnext/status.py`
- Modify: `src/aeiva/metaui/vnext/api.py`

**Deliverables:**
- Deterministic in-memory session/event model (bounded storage, no silent drops).
- `status`, `poll_events`, `wait_event` fully implemented in vnext.

**Acceptance:**
- New tests: `tests/metaui/test_vnext_session_store.py`, `tests/metaui/test_vnext_event_store.py`.
- Existing invariant suite remains green.

---

## Stage 4 — VNext Render/State Write Path

**Files:**
- Create: `src/aeiva/metaui/vnext/render_runtime.py`
- Create: `src/aeiva/metaui/vnext/state_runtime.py`
- Modify: `src/aeiva/metaui/vnext/api.py`

**Deliverables:**
- `render_full`, `patch`, `set_state` fully implemented with truthful delivery semantics:
  - accepted vs delivered vs rendered.
- Atomic render commit invariants.

**Acceptance:**
- New tests: `tests/metaui/test_vnext_render_runtime.py`, `tests/metaui/test_vnext_state_runtime.py`.
- No regression in legacy test suite.

---

## Stage 5 — Tool Cutover (Feature-Flagged)

**Files:**
- Modify: `src/aeiva/metaui/tool.py`
- Modify: `src/aeiva/command/config_validation.py`
- Modify: `configs/agent_config.yaml` (metaui_vnext toggle default false initially)

**Deliverables:**
- Explicit runtime mode switch (`legacy` / `vnext`) with default `legacy` until confidence gates pass.
- No behavior mixing.

**Acceptance:**
- Mode-specific tests: `tests/tool/test_metaui_tool_legacy_mode.py`, `tests/tool/test_metaui_tool_vnext_mode.py`.

---

## Stage 6 — Real LLM Replay Gate (Local Machine)

**Required Local Commands:**
- `uv run aeiva-dialogue-replay -c configs/agent_config.yaml -s docs/examples/dialogue_replay/metaui_dialogue_suite.yaml --fail-fast --output-json .reports/metaui-vnext.replay.json --output-md .reports/metaui-vnext.replay.md`
- `uv run aeiva-metaui-eval --output-json .reports/metaui-vnext.eval.json --output-md .reports/metaui-vnext.eval.md`

**Pass Criteria:**
- Scenario pass rate >= 95% across 3 repeated replay runs.
- No empty UI renders after successful `render_full`.
- No false success claims (`success=true` while not delivered/rendered).
- P95 latency targets:
  - first render <= 10s
  - patch/set_state <= 2s

---

## Stage 7 — Legacy Deletion

**Precondition:** Stage 6 fully green for three consecutive runs.

**Files:**
- Delete: `src/aeiva/metaui/legacy/*`
- Simplify: `src/aeiva/metaui/tool.py` to direct vnext implementation
- Update tests/docs to remove legacy references

**Acceptance:**
- Full MetaUI test matrix + replay gates pass with no legacy code present.

---

## CI Invariant Checklist (Enforced)

1. AI defines all UI structure/behavior; MetaUI does not infer intent.
2. Strict schema validation before runtime mutation.
3. Explicit error codes; no silent failures.
4. Atomic render semantics (no clear-first blanking).
5. Truthful delivery fields (`accepted`, `delivered`, `rendered`).
6. File/function size budgets for vnext modules.
7. No `aeiva.tool.meta.metaui` implementation file; canonical path is `aeiva.metaui.tool`.

