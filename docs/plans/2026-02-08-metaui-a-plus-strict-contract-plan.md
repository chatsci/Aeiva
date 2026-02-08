# MetaUI A+ Strict Contract Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ensure MetaUI only renders and executes AI-defined UI specs, and that every rendered interactive UI is usable ("可见即可用"), never a non-functional shell.

**Architecture:** Enforce a strict AI-owned contract: AI produces full UI structure and behavior (`components/root/actions/state_bindings/events`), MetaUI performs deterministic validation, rendering, event transport, and state/patch execution only. No intent heuristics, no UI inference, no hidden business logic in renderer/tooling.

**Tech Stack:** Python 3.12, Pydantic v2, asyncio/websockets, MetaUI desktop renderer (HTML/JS), pytest.

## Scope and Guardrails

- Keep: `render_full/patch/set_state` as primary path.
- Keep: platform-independent protocol + desktop runtime.
- Remove/disable: heuristic behavior that guesses UI or behavior from prose.
- Add: strict interactive contract gate before rendering.
- Add: deterministic runtime checks so "shows UI but cannot use" fails fast.
- Note: no git operations are required in this plan; user manages git.

---

### Task 1: Define Strict Interactive Contract (single source of truth)

**Files:**
- Create: `src/aeiva/metaui/interaction_contract.py`
- Test: `tests/metaui/test_interaction_contract.py`

**Step 1: Write failing tests**

```python
def test_rejects_interactive_component_without_handler(): ...
def test_rejects_unknown_action_reference(): ...
def test_rejects_dangling_component_reference(): ...
def test_rejects_shell_ui_for_interactive_intent(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_interaction_contract.py -q`
Expected: FAIL

**Step 3: Implement minimal validator**

- Validate:
  - interactive component has executable event path
  - action references resolve
  - `root/children/target_component_id` resolve
  - required event for key components (`chat_panel`, `form`, `file_uploader`)

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_interaction_contract.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Record result in test output log (no git action).

---

### Task 2: Integrate Contract Gate into render_full and patch

**Files:**
- Modify: `src/aeiva/tool/meta/metaui.py`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Test: `tests/tool/test_metaui_tool.py`
- Test: `tests/metaui/test_orchestrator_state_machine.py`

**Step 1: Write failing tests**

```python
def test_render_full_rejects_contract_invalid_spec(): ...
def test_patch_rejects_contract_breaking_update(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/tool/test_metaui_tool.py tests/metaui/test_orchestrator_state_machine.py -q`
Expected: FAIL

**Step 3: Implement strict gate**

- `render_full`: validate normalized spec with contract before broadcast.
- `patch`: apply dry-run patch to server-side spec, validate contract, then broadcast.
- Return structured error with `error_code` and contract violations list.

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/tool/test_metaui_tool.py tests/metaui/test_orchestrator_state_machine.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Ensure no legacy fallback silently turns failures into success.

---

### Task 3: Remove Remaining Heuristic/UI-Inference Paths from MetaUI runtime

**Files:**
- Modify: `src/aeiva/tool/meta/metaui.py`
- Modify: `src/aeiva/metaui/spec_normalizer.py`
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Test: `tests/tool/test_metaui_tool.py`
- Test: `tests/metaui/test_spec_normalizer.py`

**Step 1: Write failing tests**

```python
def test_render_full_does_not_infer_ui_from_prose(): ...
def test_unknown_interaction_never_gets_silent_auto_behavior(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/tool/test_metaui_tool.py tests/metaui/test_spec_normalizer.py -q`
Expected: FAIL

**Step 3: Implement**

- Keep only declarative behavior:
  - explicit `events/on_*`
  - explicit `actions/steps`
  - explicit `state_bindings`
- Remove silent behavior guesses in client runtime.

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/tool/test_metaui_tool.py tests/metaui/test_spec_normalizer.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Confirm: MetaUI contains transport/render/runtime, not intent logic.

---

### Task 4: Make Event-to-Action Runtime Deterministic and Complete

**Files:**
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Modify: `src/aeiva/metaui/spec_normalizer.py`
- Test: `tests/metaui/test_desktop_client_template.py`
- Test: `tests/metaui/test_spec_normalizer.py`

**Step 1: Write failing tests**

```python
def test_button_click_action_aliases_are_equivalent(): ...
def test_on_submit_onSubmit_events_submit_are_equivalent(): ...
def test_unresolved_action_produces_visible_error_not_silent_noop(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_desktop_client_template.py tests/metaui/test_spec_normalizer.py -q`
Expected: FAIL

**Step 3: Implement**

- Normalize event names and aliases once.
- Execute action graph deterministically.
- Emit explicit error toast/event for no-op action paths.

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_desktop_client_template.py tests/metaui/test_spec_normalizer.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Ensure no duplicated dispatch paths remain.

---

### Task 5: Add Functional Render Probe (usable-by-default guarantee)

**Files:**
- Create: `src/aeiva/metaui/functional_probe.py`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Test: `tests/metaui/test_functional_probe.py`

**Step 1: Write failing tests**

```python
def test_probe_detects_nonfunctional_chat_ui(): ...
def test_probe_detects_nonfunctional_form_ui(): ...
def test_probe_passes_for_complete_interactive_spec(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_functional_probe.py -q`
Expected: FAIL

**Step 3: Implement**

- Static probe against spec contract:
  - key interactive components must have complete event/action/state closure.
- Optional runtime probe hook before marking phase `INTERACTIVE`.

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_functional_probe.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Probe failures must be explicit and actionable.

---

### Task 6: End-to-End Real-Usage Scenario Tests (non-toy)

**Files:**
- Create: `tests/metaui/scenarios/test_chat_workspace_flow.py`
- Create: `tests/metaui/scenarios/test_employee_form_flow.py`
- Create: `tests/metaui/scenarios/test_data_workbench_flow.py`
- Create: `tests/metaui/scenarios/test_theme_and_layout_switch_flow.py`

**Step 1: Write failing scenario tests**

- Chat: send/clear/help fully functional.
- Employee form: input/validate/submit/feedback functional.
- Data workbench: upload->table->chart->export functional.
- Layout/theme switch updates actual rendered components.

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/scenarios -q`
Expected: FAIL

**Step 3: Implement missing glue**

- Fix only via generic contract/runtime mechanisms (no scenario-specific patch).

**Step 4: Re-run scenario tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/scenarios -q`
Expected: PASS

**Step 5: Checkpoint**
- Confirm scenario tests assert behavior, not just text response.

---

### Task 7: Reliability and Observability Tightening

**Files:**
- Modify: `src/aeiva/metaui/orchestrator.py`
- Modify: `src/aeiva/metaui/assets/desktop_template.html`
- Test: `tests/metaui/test_orchestrator_state_machine.py`

**Step 1: Write failing tests**

```python
def test_event_not_consumed_is_reported(): ...
def test_render_ack_only_after_successful_functional_ready(): ...
```

**Step 2: Run failing tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_orchestrator_state_machine.py -q`
Expected: FAIL

**Step 3: Implement**

- Explicit error events for non-consumed/invalid interaction actions.
- Keep ACK semantics aligned with actual render success.

**Step 4: Re-run tests**

Run: `/opt/anaconda3/envs/aeiva/bin/python -m pytest tests/metaui/test_orchestrator_state_machine.py -q`
Expected: PASS

**Step 5: Checkpoint**
- Verify no silent failure path remains for interaction.

---

### Task 8: Documentation Update (Browser + MetaUI capability clarity)

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`

**Step 1: Write doc checks**

- Add explicit section:
  - AI-owned UI definition
  - MetaUI renderer-only responsibility
  - strict contract mode and failure behavior
  - how to test "可见即可用"

**Step 2: Verify wording against implementation**

- Ensure docs match strict mode defaults and operations (`render_full/patch/set_state`).

**Step 3: Lint and run all tests**

Run:
- `/opt/anaconda3/envs/aeiva/bin/python -m pytest -q`
- `/opt/anaconda3/envs/aeiva/bin/python -m ruff check src/aeiva/metaui/spec_normalizer.py tests/metaui/test_spec_normalizer.py tests/metaui/test_desktop_client_template.py`

Expected: PASS

**Step 4: Final acceptance checklist**

- Chat UI: send/clear works.
- Form UI: submit works.
- Theme/layout updates reflect visually.
- No heuristic intent path in runtime.
- No empty-shell interactive UI accepted.

---

## Definition of Done (A+)

- `MetaUI = deterministic renderer/runtime only` (no intent intelligence).
- `AI = complete UI + behavior designer`.
- Strict contract prevents non-functional UI from rendering.
- Real-usage scenario suite passes.
- Full test suite passes in `aeiva` environment.
