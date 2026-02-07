# Browser V5 (From browser-use) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade Aeiva browser tooling from operation-level automation to workflow-grade automation that reliably completes real multi-turn tasks (search, complex forms, flight comparison) with visible progress and low loop/stall risk.

**Architecture:** Keep Aeiva's current clean layering (`browser.py` -> `_browser_service.py` -> `_browser_runtime.py`) and add a thin "interaction engine" layer for deterministic action planning, targeting, and recovery. Borrow robustness patterns from `browser-use` (watchdog-style resilience, richer action typing, better DOM semantics), but avoid full CDP/event-stack complexity and cloud coupling.

**Tech Stack:** Python 3.12, Playwright (existing), Aeiva native tool loop, pytest, local HTML fixture pages for deterministic integration tests.

## Why this plan (comparison summary)

### Aeiva strengths to keep
- Very clean service/runtime separation.
- Stable `snapshot -> ref -> action` path.
- Good unit-test coverage for runtime/service behavior.
- Strong compatibility with native tool loop and host routing.

### Current gaps hurting real usage
- Missing workflow-level primitives for form completion (date pickers, steppers, comboboxes, confirm/apply flows).
- Scroll oscillation is detected late; no strong preemption policy.
- Browser action progress is not consistently surfaced as user-visible "thinking/acting" hints across channels.
- Recovery strategy is mostly keyword-based and single-step; not enough stateful retries.
- Limited end-to-end browser tests for realistic form workflows (flight booking style).

### What to learn from browser-use
- Action model + registry discipline (typed, explicit action semantics).
- Watchdog-style resilience around actions and DOM refresh.
- Better DOM semantic extraction for compound controls (number/date/select/file).
- Planning/replanning controls and loop detection as first-class runtime concepts.

## Target V5 architecture

```text
LLM Tool Loop
    |
    v
browser tool API (`browser.py`)
    |
    v
BrowserService (`_browser_service.py`)
    |
    +--> Interaction Engine (NEW)
    |      - Target Resolver
    |      - Action Planner
    |      - Recovery/Watchdog
    |
    +--> BrowserRuntime (`_browser_runtime.py`)
           - Playwright primitives
           - Snapshot/DOM metadata
           - Input/selection/scroll primitives
```

```text
User task -> Workflow intent -> Action plan -> Execute step
                                      |            |
                                      |            +--> validate outcome
                                      |
                                      +--> retry policy / alternate strategy
                                               |
                                               +--> fail with structured reason
```

## Task 1: Introduce Interaction Engine (deterministic action planning)

**Files:**
- Create: `src/aeiva/tool/meta/_browser_interaction.py`
- Modify: `src/aeiva/tool/meta/_browser_service.py`
- Test: `tests/tool/test_browser_service.py`

**Step 1: Add interaction data model**
- Define `InteractionStep`, `InteractionPlan`, `InteractionOutcome`, `RecoveryHint`.
- Keep models runtime-agnostic (no Playwright object leakage).

**Step 2: Add execution entrypoint**
- Add `BrowserService._execute_interaction_plan(...)`.
- Add bounded retries and per-step timeout budget.

**Step 3: Preserve compatibility**
- Existing operations (`click/type/select/scroll/confirm`) still work.
- New internal path is opt-in first, then incrementally adopted by existing ops.

**Step 4: Tests**
- Add tests for:
  - deterministic step ordering,
  - bounded retries,
  - structured failure payloads.

## Task 2: Upgrade target resolution and DOM semantics

**Files:**
- Modify: `src/aeiva/tool/meta/_browser_runtime.py`
- Modify: `src/aeiva/tool/meta/_browser_service.py`
- Test: `tests/tool/test_browser_runtime.py`
- Test: `tests/tool/test_browser_service.py`

**Step 1: Enrich snapshot nodes**
- Add normalized fields: `tag`, `bbox`, `visible`, `in_viewport`, `aria_role`, `label_for`, `dataset`.
- Keep output bounded and stable.

**Step 2: Add resolver scoring V2**
- Replace simple keyword-only ranking with weighted scoring:
  - role/type compatibility,
  - label/text exactness,
  - visibility/in-viewport priority,
  - negative-action penalties.

**Step 3: Add resolver modes**
- `click_target`, `input_target`, `confirm_target`, `select_target`.
- Each mode has its own score profile.

**Step 4: Tests**
- Add table-driven tests for ambiguous controls (`Done` vs `Cancel`, hidden vs visible).

## Task 3: Add first-class form primitives

**Files:**
- Modify: `src/aeiva/tool/meta/_browser_runtime.py`
- Modify: `src/aeiva/tool/meta/_browser_service.py`
- Modify: `src/aeiva/tool/meta/browser.py`
- Test: `tests/tool/test_browser_runtime.py`
- Test: `tests/tool/test_browser_service.py`

**Step 1: Runtime primitives**
- Add methods:
  - `set_value(...)` for text-like fields,
  - `set_number(...)` for numeric/spinbutton/stepper controls,
  - `set_date(...)` for date/time controls (native + picker fallback),
  - `choose_option(...)` for select/listbox/combobox variants,
  - `submit_form(...)`.

**Step 2: Service operations**
- Expose operations: `set_value`, `set_number`, `set_date`, `choose_option`, `submit`.
- Keep legacy `type/select/confirm` mapped to new primitives where safe.

**Step 3: Numeric robustness**
- Improve kg/stepper handling:
  - parse units,
  - detect plus/minus controls,
  - verify final value with tolerance.

**Step 4: Tests**
- Add focused tests for:
  - number steppers (`20kg`),
  - date confirmation button,
  - combobox typed selection.

## Task 4: Replace scroll guard with Scroll Coordinator V2

**Files:**
- Modify: `src/aeiva/tool/meta/_browser_service.py`
- Modify: `src/aeiva/tool/meta/_browser_runtime.py`
- Test: `tests/tool/test_browser_service.py`
- Test: `tests/tool/test_browser_runtime.py`

**Step 1: State model**
- Track per-target scroll state:
  - monotonic progress window,
  - stall counter,
  - bounce score.

**Step 2: Preemptive oscillation prevention**
- Detect repeated direction flips early (before 4th bounce where possible).
- Stop scroll and switch to resolver-guided targeted action.

**Step 3: Context-aware recovery**
- Prefer in-dialog/container scroll when modal/dropdown active.
- Auto-fallback sequence: `snapshot -> target confirm/search/apply -> wait`.

**Step 4: Tests**
- Add deterministic tests for:
  - early oscillation break,
  - no-effect loop break,
  - recovery branch selection.

## Task 5: Add workflow-level operation for complex tasks

**Files:**
- Modify: `src/aeiva/tool/meta/_browser_service.py`
- Modify: `src/aeiva/tool/meta/browser.py`
- Create: `tests/tool/test_browser_workflows.py`

**Step 1: Add generic workflow op**
- Add `operation="workflow"` with request schema:
  - `goal`, `fields`, `constraints`, `max_steps`, `max_retries`.

**Step 2: Implement `fill_and_submit` workflow**
- Deterministic sequence:
  - discover fields,
  - fill with typed primitives,
  - validate each field,
  - confirm/submit,
  - extract top results.

**Step 3: Flight scenario profile**
- Add optional strategy hints for flight-like forms:
  - origin/destination/date/cabin/baggage/stopover filters.
- Keep implementation generic; avoid hardcoding site-specific selectors.

**Step 4: Tests**
- Add fixture-driven workflow tests using local HTML pages.

## Task 6: Unify user-visible progress hints ("thinking/acting")

**Files:**
- Modify: `src/aeiva/interface/terminal_gateway.py`
- Modify: `src/aeiva/command/aeiva_chat_gradio.py`
- Modify: `src/aeiva/cognition/cognition.py` (if needed for trace-level hint events)
- Test: `tests/command/test_gradio_progress_hints.py`
- Create: `tests/interface/test_terminal_progress_hints.py`

**Step 1: Define hint phases**
- Distinguish:
  - `Thinking` (LLM reasoning),
  - `Acting` (tool execution),
  - `Summarizing`.

**Step 2: Emit tool-stage hints**
- Surface current tool/operation (`browser:set_date`, `browser:choose_option`, etc.).

**Step 3: Prevent "silent wait"**
- Immediate first hint on long action paths.
- No blank UI state while waiting for tool loop completion.

**Step 4: Tests**
- Verify both Gradio and terminal receive staged hints with elapsed time.

## Task 7: Host/permission diagnostics for browser and local-open actions

**Files:**
- Modify: `src/aeiva/host/host_router.py`
- Modify: `src/aeiva/command/aeiva_gateway.py`
- Test: `tests/command/test_gateway_host_auth.py`
- Test: `tests/host/test_host_router_browser_keys.py`

**Step 1: Improve error translation**
- Preserve actionable context for `401/403/connection_error`.
- Provide explicit remediation fields in error payload.

**Step 2: Startup health probe**
- On gateway startup, validate host route auth alignment and warn once with clear fix.

**Step 3: Tests**
- Add tests for unauthorized/forbidden diagnostics and route mismatch warnings.

## Task 8: Add realistic browser integration tests

**Files:**
- Create: `tests/tool/test_browser_integration_forms.py`
- Create: `tests/fixtures/browser_forms/flight_form.html`
- Create: `tests/fixtures/browser_forms/controls_gallery.html`
- Modify: `tests/tool/test_browser_runtime.py`

**Step 1: Fixture pages**
- Build deterministic local pages covering:
  - datepicker confirm,
  - number stepper baggage,
  - combobox with async suggestions,
  - modal/dialog + inner scroll.

**Step 2: End-to-end tool tests**
- Run full operation chains against fixture pages (no external network dependency).

**Step 3: Performance budget tests**
- Assert no pathological retry loops.
- Assert bounded execution time for key workflows.

## Verification plan

Run in this order:

1. `python -m pytest -q tests/tool/test_browser_runtime.py tests/tool/test_browser_service.py tests/tool/test_browser_tool.py`
2. `python -m pytest -q tests/tool/test_browser_workflows.py tests/tool/test_browser_integration_forms.py`
3. `python -m pytest -q tests/command/test_gradio_progress_hints.py tests/interface/test_terminal_progress_hints.py`
4. `python -m pytest -q tests/host/test_host_router_browser_keys.py tests/command/test_gateway_host_auth.py`
5. `python -m pytest -q tests/tool`

Acceptance gates:
- Flight-style form fixture can be completed end-to-end without scroll oscillation.
- Number/baggage controls are set deterministically.
- User always sees `thinking/acting` hints on long runs.
- No regressions in existing browser tool suites.

## Out of scope for V5

- Full CDP event-stack rewrite.
- Cloud browser stealth/captcha bypass services.
- Multi-node remote browser orchestration.

## Practical implementation order

1. Task 1 + Task 2 (core engine + resolver)
2. Task 3 + Task 4 (form primitives + scroll coordinator)
3. Task 5 (workflow op)
4. Task 6 + Task 7 (UX hints + host diagnostics)
5. Task 8 (integration suite + hardening)
