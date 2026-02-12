# MetaUI A2UI Gap-Closure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make MetaUI strictly AI-defined and renderer-passive, with no heuristic inference, and ensure generated UI is both visible and functionally usable.

**Architecture:** Keep AI as the only decision-maker for UI structure and interaction semantics. MetaUI must only validate schema/contract, render components deterministically, and forward interaction events/state updates. Align lifecycle and data flow with A2UI (`create/update/begin/dataModel/delete`) while preserving AEIVA desktop strengths (session replay, local sandbox, event bridge).

**Tech Stack:** Python (Pydantic, asyncio, websockets), desktop HTML/JS runtime, pytest.

## Scope

- In scope:
  - Remove remaining renderer-side compatibility heuristics and aliases.
  - Enforce strict interaction contracts for all interactive controls.
  - Close "visible but unusable" component gaps (chat/send, form submit, button actions).
  - Improve A2UI parity in lifecycle semantics and component/action strictness.
  - Expand real-world test coverage and regression guards.
- Out of scope:
  - New cloud/browser renderer.
  - AI model prompt tuning outside MetaUI catalog/schema publication.

## Gap Matrix (Current -> Target)

1. Renderer still accepts legacy aliases and fallback action tokens.
   - Current: `desktop_template.html` accepts `action_id/handler/command`, `chat_append/add_message`, `callAlias`.
   - Target: canonical-only event/action schema (`action`, `steps`, `effects`, `emit_event`, `event_type`, `target_component_id`).
2. Some controls render but appear non-functional.
   - Current: action semantics may be under-specified and silently no-op.
   - Target: strict pre-render contract rejection for no-op interactive definitions; deterministic event/effect execution.
3. Root/render lifecycle has fallback behavior.
   - Current: renderer can auto-fill root from all components.
   - Target: explicit root contract and clear error surfaces without hidden recovery.
4. A2UI parity is high but not fully strict in renderer execution.
   - Current: protocol + orchestrator close to strict; client still has compatibility paths.
   - Target: end-to-end strictness consistent across tool, normalizer, orchestrator, and desktop runtime.

---

### Task 1: Remove Renderer-Side Heuristic Aliases

**Files:**
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Test: `tests/metaui/test_desktop_client_template.py`

**Step 1: Write failing tests**

- Add assertions that these tokens are absent in `HTML_TEMPLATE`:
  - `action_id`, `handler`, `command` (in event config parser)
  - `chat_append`, `add_message`, `chat_clear`
  - `callAlias`
  - permissive `onXxx` key normalization paths

**Step 2: Run tests to verify failure**

Run:
`python -m pytest tests/metaui/test_desktop_client_template.py -q`

Expected: failures on presence checks.

**Step 3: Minimal implementation**

- In `normalizeEventConfigBlock`, accept only strict object schema.
- Remove legacy key fallback chains.
- Remove alias maps in local action execution.
- Keep only canonical action ops from interaction contract.

**Step 4: Run tests to pass**

Run:
`python -m pytest tests/metaui/test_desktop_client_template.py -q`

Expected: pass.

---

### Task 2: Enforce Strict Event Contract at Normalization Boundary

**Files:**
- Modify: `src/aeiva/metaui/spec_normalizer.py`
- Modify: `src/aeiva/metaui/interaction_contract.py`
- Test: `tests/metaui/test_spec_normalizer.py`

**Step 1: Write failing tests**

- Cases that must fail:
  - button with no `on_click`/`events.click` in interactive mode
  - event config with unknown keys or wrong types
  - unknown action step token
  - chat-target effects without explicit target component id

**Step 2: Verify failure**

Run:
`python -m pytest tests/metaui/test_spec_normalizer.py -q`

**Step 3: Implement**

- Tighten `_normalize_event_config` and `_normalize_interaction_props`.
- Ensure no legacy top-level action keys (`command`, `local_action`) are used in validation logic.
- Keep canonical event names only.

**Step 4: Verify**

Run:
`python -m pytest tests/metaui/test_spec_normalizer.py -q`

---

### Task 3: Guarantee "Visible and Usable" Interactive Components

**Files:**
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Test: `tests/metaui/test_orchestrator_event_validation.py`
- Test: `tests/metaui/test_ui_realworld_scenarios.py`

**Step 1: Write failing tests**

- Chat panel:
  - submit dispatch emits event with payload and appends optimistic user message.
- Form and form_step:
  - submit/change produce valid payload shape.
- Button:
  - click with strict `on_click` contract works.
- Negative tests:
  - UI with declarative interactive controls but no actionable contract is rejected at `render_full`.

**Step 2: Verify failing state**

Run:
`python -m pytest tests/metaui/test_orchestrator_event_validation.py tests/metaui/test_ui_realworld_scenarios.py -q`

**Step 3: Implement**

- Keep local-effect execution deterministic and canonical.
- Ensure server receives clean payload/metadata and can validate checks.
- Preserve behavior that file upload remains functional and sanitized.

**Step 4: Verify**

Run:
`python -m pytest tests/metaui/test_orchestrator_event_validation.py tests/metaui/test_ui_realworld_scenarios.py -q`

---

### Task 4: Align Root/Lifecycle Behavior with Strict Protocol

**Files:**
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Modify: `src/aeiva/metaui/lifecycle_messages.py`
- Test: `tests/metaui/test_lifecycle_messages.py`
- Test: `tests/metaui/test_desktop_client_template.py`

**Step 1: Write failing tests**

- Reject/flag missing root instead of silently auto-rooting from all components.
- Ensure lifecycle replay and begin-rendering expectations remain explicit.

**Step 2: Verify failure**

Run:
`python -m pytest tests/metaui/test_lifecycle_messages.py tests/metaui/test_desktop_client_template.py -q`

**Step 3: Implement**

- Remove or narrow root auto-fill in client sanitizer.
- Keep clear in-UI error display for invalid spec rather than rendering misleading partial shells.

**Step 4: Verify**

Run:
`python -m pytest tests/metaui/test_lifecycle_messages.py tests/metaui/test_desktop_client_template.py -q`

---

### Task 5: Tighten AI/MetaUI Boundary (No Intent Logic in MetaUI)

**Files:**
- Modify: `src/aeiva/tool/meta/metaui.py`
- Modify: `src/aeiva/metaui/component_catalog.py`
- Modify: `README.md`
- Modify: `README_CN.md`
- Test: `tests/tool/test_metaui_tool.py`

**Step 1: Write failing tests**

- `metaui` tool response/docs must explicitly state strict flow:
  - `catalog` -> `protocol_schema` -> `render_full` -> `set_state/patch`.
- No references to scaffold/intent fallback paths.

**Step 2: Verify failure**

Run:
`python -m pytest tests/tool/test_metaui_tool.py -q`

**Step 3: Implement**

- Keep tool help strictly schema-first and explicit.
- Ensure catalog exposes full interaction contract for model-side generation.
- Update docs to describe AI-responsible UI definition and MetaUI-passive rendering.

**Step 4: Verify**

Run:
`python -m pytest tests/tool/test_metaui_tool.py -q`

---

### Task 6: Expand Real-World Integration Scenario Matrix

**Files:**
- Modify: `tests/metaui/test_ui_realworld_scenarios.py`
- Add/Modify: `tests/metaui/test_protocol_component_matrix.py`
- Add/Modify: `tests/metaui/test_orchestrator_state_machine.py`

**Step 1: Add failing scenario tests**

- Cover at least:
  - chat workspace (send/clear/export)
  - onboarding form with validations
  - multi-step wizard
  - CSV analysis workbench
  - settings tabs + mixed inputs
  - media + notes + submit
  - dashboard with chart/table filters
  - permission/disabled states
  - reconnect/replay interaction continuity

**Step 2: Verify failing state**

Run:
`python -m pytest tests/metaui -q`

**Step 3: Implement only contract/runtime fixes (no test hacks)**

- Any failing scenario should be fixed in normalizer/orchestrator/template, never by weakening assertions.

**Step 4: Verify full MetaUI suite**

Run:
`python -m pytest tests/metaui tests/tool/test_metaui_tool.py -q`

---

### Task 7: Final A2UI Comparison Gate

**Files:**
- Add: `docs/reports/2026-02-09-metaui-vs-a2ui-final.md`

**Step 1: Write comparison checklist**

- Protocol strictness
- Lifecycle ordering guarantees
- Data model sync semantics
- Action semantics (server event + local function)
- Component coverage and extension story
- Observability and failure behavior

**Step 2: Validate against code**

- Reference concrete file/line evidence from both repositories.

**Step 3: Produce final gap-closure report**

- Must include:
  - what is now equal
  - what is better
  - what remains intentionally different

---

### Task 8: Verification Before Completion

**Files:**
- No code changes required unless regressions are found.

**Step 1: Run full target tests**

Run:
`python -m pytest tests/metaui tests/tool/test_metaui_tool.py -q`

**Step 2: Run full project regression**

Run:
`python -m pytest -q`

**Step 3: Manual acceptance script**

- Start gateway.
- Ask for:
  - chat window with working send/clear/export
  - switch to onboarding form with working submit/reset
  - switch to data table + chart workspace with working controls
- Confirm:
  - no empty shell UI
  - no dead interactive controls
  - no fallback injected components

---

## A+ Acceptance Criteria

1. No heuristic aliases remain in MetaUI runtime paths (renderer + normalizer + tool surface behavior).
2. Invalid interactive specs fail fast with actionable errors.
3. Valid specs produce interactive controls that are functionally usable.
4. A2UI lifecycle semantics are explicit and deterministic.
5. Test matrix covers component-level + cross-component + state/lifecycle integration.
6. Docs clearly define the boundary:
   - AI defines structure/logic.
   - MetaUI validates, renders, and forwards events only.

## Risks and Mitigations

- Risk: breaking compatibility for older specs.
  - Mitigation: strict error messages + docs/examples upgrade path.
- Risk: over-tight validation blocks useful specs.
  - Mitigation: contract tests derived from real scenarios, not toy examples.
- Risk: silent renderer regressions.
  - Mitigation: string-level template guards + orchestrator contract tests + manual acceptance script.

## Execution Order (Recommended)

1. Task 1 -> Task 2 (strictness baseline)
2. Task 3 -> Task 4 (usability + lifecycle correctness)
3. Task 5 -> Task 6 (boundary hardening + test breadth)
4. Task 7 -> Task 8 (comparison proof + release gate)

