# MetaUI vs A2UI Gap-Closure Report (2026-02-08)

## Scope

This report closes the previously agreed 6-point alignment scope against A2UI:

1. protocol strictness
2. AI-owned UI definition primary path (runtime as deterministic renderer)
3. multi-surface lifecycle correctness
4. data model semantics and dynamic value/check execution
5. renderer portability (lifecycle + legacy compatibility path)
6. event semantics and transport validation

Reference baseline from local A2UI source:

- `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/server_to_client.json`
- `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/client_to_server.json`
- `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/standard_catalog.json`

## Implementation Status

### 1) Protocol strictness: completed

- Added strict envelope and lifecycle validation:
  - `src/aeiva/metaui/message_evaluator.py`
  - `src/aeiva/metaui/a2ui_protocol.py`
- Supports strict checks for:
  - `createSurface` -> `updateComponents` ordering
  - root presence
  - child reference validity
  - JSON-pointer path shape for data model updates
- Covered by:
  - `tests/metaui/test_message_evaluator.py`

### 2) AI-owned UI definition primary path: completed

- Primary path explicitly documented and enforced at tool API:
  - `catalog` + `protocol_schema` -> model builds explicit `spec` -> `render_full`
  - `scaffold` kept as compatibility fallback only
  - `patch` structural intent guard rejects view/layout changes and redirects to `render_full`
- Key files:
  - `src/aeiva/tool/meta/metaui.py`
  - `docs/reference/metaui-tool-api.md`
- Covered by:
  - `tests/tool/test_metaui_tool.py`

### 3) Multi-surface lifecycle correctness: completed

- Capability negotiation and dual transport routing implemented:
  - lifecycle stream for A2UI-capable clients
  - legacy command fallback for older clients
- Replay behavior constrained to freshest session for single-view desktop client.
- Key files:
  - `src/aeiva/metaui/orchestrator.py`
  - `src/aeiva/metaui/lifecycle_messages.py`
- Covered by:
  - `tests/metaui/test_orchestrator_a2ui_runtime.py`
  - `tests/metaui/test_orchestrator_capability_routing.py`
  - `tests/metaui/test_orchestrator_state_machine.py`

### 4) Data model semantics + dynamic checks/functions: completed

- Added dynamic resolver/function/check engine:
  - path/call dynamic values
  - built-in validation and formatting functions
  - check evaluation pipeline
- Added server-side event validation for form/input components.
- Key files:
  - `src/aeiva/metaui/a2ui_runtime.py`
  - `src/aeiva/metaui/orchestrator.py`
  - `src/aeiva/metaui/spec_normalizer.py`
- Covered by:
  - `tests/metaui/test_a2ui_runtime.py`
  - `tests/metaui/test_orchestrator_event_validation.py`
  - `tests/metaui/test_spec_normalizer.py`

### 5) Renderer portability and compatibility path: completed

- Desktop renderer supports:
  - A2UI lifecycle message handling (`surfaceUpdate`, `dataModelUpdate`, `beginRendering`, `deleteSurface`)
  - legacy `render_full` / `patch` / `set_state` command stream
- Added A2UI-style component alias compatibility in both server normalizer and desktop renderer.
- Key files:
  - `src/aeiva/metaui/assets/desktop_template.html`
  - `src/aeiva/metaui/spec_normalizer.py`
- Covered by:
  - `tests/metaui/test_desktop_client_template.py`
  - `tests/metaui/test_orchestrator_a2ui_runtime.py`
  - `tests/metaui/test_spec_normalizer.py`

### 6) Event semantics and context transport: completed

- `sendDataModel` is now propagated through lifecycle begin message and attached to outbound event metadata when enabled.
- Event payload validation and error conversion semantics are enforced server-side.
- Key files:
  - `src/aeiva/metaui/protocol.py`
  - `src/aeiva/metaui/lifecycle_messages.py`
  - `src/aeiva/metaui/assets/desktop_template.html`
  - `src/aeiva/metaui/orchestrator.py`
- Covered by:
  - `tests/metaui/test_lifecycle_messages.py`
  - `tests/metaui/test_desktop_client_template.py`
  - `tests/metaui/test_orchestrator_event_validation.py`

## Real Regression Cases Added

To cover the exact failures seen in interactive use:

- `tests/tool/test_metaui_tool.py::test_metaui_scaffold_switch_from_chat_to_table_replaces_structure`
- `tests/metaui/test_orchestrator_state_machine.py::test_render_full_same_ui_id_replaces_component_tree`

These prevent regressions where UI changes only title but not structure.

## Verification

Executed:

- `python -m pytest tests/metaui tests/tool/test_metaui_tool.py tests/test_terminal_gateway.py -q`

Result:

- `173 passed, 5 skipped`

## Remaining Gap vs A2UI (Non-runtime)

Runtime/protocol side is aligned at the agreed 6-point level. Residual gap is now mainly model policy quality (agent decision quality):

- whether the agent always chooses `render_full` for structural intent
- whether the agent emits complete explicit spec without semantic drift

This is prompt/policy quality, not MetaUI transport/runtime correctness.
