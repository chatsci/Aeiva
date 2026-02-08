# MetaUI Beyond A2UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build MetaUI v2 as an AI-first, protocol-first, platform-portable UI runtime that reaches and exceeds A2UI-level robustness while preserving AEIVA single-machine productivity.

**Architecture:** MetaUI v2 separates concerns into four explicit layers: (1) protocol and schema contracts, (2) surface/data model state engine, (3) transport/orchestration, and (4) renderer adapters. AI decides UI structure and behavior; MetaUI only validates, renders, updates, and emits events. Legacy `render_full/patch/set_state` remains supported via an adapter bridge.

**Tech Stack:** Python 3.12, Pydantic v2, JSON Schema validation, asyncio/websockets, PySide6 WebEngine desktop renderer, pytest.

## Why This Surpasses A2UI

- Keep A2UI strengths:
  - strict message model and lifecycle
  - component catalog discipline
  - data-model and component-structure separation
  - streaming/incremental updates
- Exceed in AEIVA context:
  - first-class local desktop operation lifecycle (`aeiva-gateway` single entry)
  - backward compatibility bridge for existing MetaUI tools
  - deterministic state recovery and reconnect replay tuned for single-user development workflows
  - stronger real-world test harness around agent-driven multi-turn UI updates

## Target Capability Matrix

1. Protocol strictness: A2UI-level (or stricter), schema-validated envelopes.
2. AI ownership of intent: no template pollution in primary path.
3. Multi-surface lifecycle: create/update/delete independent surfaces.
4. Data model semantics: path-based updates, deterministic merge/replace/remove.
5. Renderer portability: desktop-first implementation + renderer adapter contract.
6. Event semantics: action/error envelopes with context snapshot.
7. Compatibility: existing `metaui` tool calls continue to work through adapter.
8. Reliability: reconnect replay correctness and no duplicate desktop storms.
9. Testing: schema, unit, integration, scenario, stress.
10. Maintainability: smaller modules, explicit boundaries, no hidden heuristics in core runtime.

## Non-Goals (to keep design elegant)

- Not implementing cloud browser/session infrastructure.
- Not introducing domain-specific UI templates in runtime core.
- Not mixing AI planning logic into renderer/runtime modules.

## Directory Refactor Blueprint

- Create: `src/aeiva/metaui/v2/protocol.py`
- Create: `src/aeiva/metaui/v2/catalog.py`
- Create: `src/aeiva/metaui/v2/messages.py`
- Create: `src/aeiva/metaui/v2/data_model.py`
- Create: `src/aeiva/metaui/v2/surface_store.py`
- Create: `src/aeiva/metaui/v2/applier.py`
- Create: `src/aeiva/metaui/v2/event_codec.py`
- Create: `src/aeiva/metaui/v2/legacy_adapter.py`
- Create: `src/aeiva/metaui/renderers/desktop_bridge.py`
- Create: `src/aeiva/metaui/renderers/contracts.py`
- Create: `src/aeiva/metaui/renderers/assets/index.html`
- Create: `src/aeiva/metaui/renderers/assets/app.js`
- Create: `src/aeiva/metaui/renderers/assets/styles.css`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Modify: `src/aeiva/metaui/desktop_app.py`
- Modify: `src/aeiva/tool/meta/metaui.py`
- Modify: `src/aeiva/metaui/__init__.py`

## Test Refactor Blueprint

- Create: `tests/metaui/v2/test_protocol.py`
- Create: `tests/metaui/v2/test_catalog.py`
- Create: `tests/metaui/v2/test_data_model.py`
- Create: `tests/metaui/v2/test_surface_store.py`
- Create: `tests/metaui/v2/test_applier.py`
- Create: `tests/metaui/v2/test_legacy_adapter.py`
- Create: `tests/metaui/v2/test_event_codec.py`
- Create: `tests/metaui/v2/test_orchestrator_integration.py`
- Create: `tests/metaui/v2/scenarios/test_real_world_scenarios.py`
- Modify: `tests/tool/test_metaui_tool.py`
- Modify: `tests/metaui/test_desktop_app_template.py`

---

### Task 1: Define v2 Protocol and Message Envelopes

**Files:**
- Create: `src/aeiva/metaui/v2/protocol.py`
- Create: `src/aeiva/metaui/v2/messages.py`
- Test: `tests/metaui/v2/test_protocol.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.protocol import ServerMessage


def test_server_message_accepts_create_surface_v2():
    msg = ServerMessage.model_validate({
        "version": "v2",
        "createSurface": {"surfaceId": "main", "catalogId": "aeiva://catalog/standard"},
    })
    assert msg.createSurface.surfaceId == "main"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_protocol.py::test_server_message_accepts_create_surface_v2 -q`
Expected: FAIL (`ModuleNotFoundError` or validation object missing)

**Step 3: Write minimal implementation**

- Add versioned envelope models for:
  - `createSurface`
  - `updateComponents`
  - `updateDataModel`
  - `deleteSurface`
- Enforce one-of semantics and explicit `version="v2"`.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_protocol.py -q`
Expected: PASS

---

### Task 2: Implement Catalog Contract and Capability Negotiation

**Files:**
- Create: `src/aeiva/metaui/v2/catalog.py`
- Test: `tests/metaui/v2/test_catalog.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.catalog import CatalogRegistry


def test_catalog_registry_rejects_unknown_component_type():
    registry = CatalogRegistry.standard()
    assert registry.is_supported("Text") is True
    assert registry.is_supported("UnknownWidget") is False
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_catalog.py::test_catalog_registry_rejects_unknown_component_type -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Catalog model with `catalog_id`, component definitions, optional functions.
- `ClientCapabilities` model with `supported_catalog_ids`, optional inline catalogs.
- Validator hooks for component type checks.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_catalog.py -q`
Expected: PASS

---

### Task 3: Build Deterministic Surface Store and Data Model Engine

**Files:**
- Create: `src/aeiva/metaui/v2/surface_store.py`
- Create: `src/aeiva/metaui/v2/data_model.py`
- Test: `tests/metaui/v2/test_surface_store.py`
- Test: `tests/metaui/v2/test_data_model.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.data_model import DataModel


def test_update_data_model_path_replace_and_remove():
    dm = DataModel()
    dm.apply(path="/user", value={"name": "A"})
    dm.apply(path="/user/name", value="B")
    dm.apply(path="/user/name", value=None, remove=True)
    assert dm.snapshot() == {"user": {}}
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_data_model.py::test_update_data_model_path_replace_and_remove -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- JSON-pointer style path operations: set/replace/remove.
- `SurfaceState` with immutable-ish update discipline (`version` bump per mutation).
- Component dictionary by id + root id.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_surface_store.py tests/metaui/v2/test_data_model.py -q`
Expected: PASS

---

### Task 4: Implement v2 Message Applier (Core Runtime Brain)

**Files:**
- Create: `src/aeiva/metaui/v2/applier.py`
- Test: `tests/metaui/v2/test_applier.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.applier import apply_message
from aeiva.metaui.v2.surface_store import SurfaceStore


def test_create_then_update_components_then_begin_ready_state():
    store = SurfaceStore()
    apply_message(store, {"version": "v2", "createSurface": {"surfaceId": "main", "catalogId": "aeiva://catalog/standard"}})
    apply_message(store, {"version": "v2", "updateComponents": {"surfaceId": "main", "components": [{"id": "root", "component": "Column", "children": []}]}})
    state = store.get("main")
    assert state.root_id == "root"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_applier.py::test_create_then_update_components_then_begin_ready_state -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Apply each message atomically.
- Enforce lifecycle constraints (no update before create, delete idempotent).
- Return deterministic operation result for orchestrator/replay.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_applier.py -q`
Expected: PASS

---

### Task 5: Add Legacy Adapter (render_full/patch/set_state -> v2 Messages)

**Files:**
- Create: `src/aeiva/metaui/v2/legacy_adapter.py`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Modify: `src/aeiva/tool/meta/metaui.py`
- Test: `tests/metaui/v2/test_legacy_adapter.py`
- Modify: `tests/tool/test_metaui_tool.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.legacy_adapter import adapt_render_full


def test_legacy_render_full_adapts_to_v2_message_sequence():
    messages = adapt_render_full(spec={"ui_id": "u1", "components": [], "root": []}, session_id="s1")
    kinds = [m.kind for m in messages]
    assert kinds[0] == "createSurface"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_legacy_adapter.py::test_legacy_render_full_adapts_to_v2_message_sequence -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Adapter maps legacy API calls into v2 envelope sequence.
- Keep external tool signatures stable to avoid gateway breaking changes.
- Add explicit deprecation markers in response metadata (not hard fail).

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_legacy_adapter.py tests/tool/test_metaui_tool.py -q`
Expected: PASS

---

### Task 6: Renderer Contract and Desktop Asset Decoupling

**Files:**
- Create: `src/aeiva/metaui/renderers/contracts.py`
- Create: `src/aeiva/metaui/renderers/desktop_bridge.py`
- Create: `src/aeiva/metaui/renderers/assets/index.html`
- Create: `src/aeiva/metaui/renderers/assets/app.js`
- Create: `src/aeiva/metaui/renderers/assets/styles.css`
- Modify: `src/aeiva/metaui/desktop_app.py`
- Test: `tests/metaui/test_desktop_app_template.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.desktop_app import HTML_TEMPLATE


def test_desktop_app_loads_external_assets_contract_markers():
    assert "__METAUI_ASSET_BOOTSTRAP__" in HTML_TEMPLATE
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/test_desktop_app_template.py::test_desktop_app_loads_external_assets_contract_markers -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Move inline JS/CSS to asset files.
- Keep a small bootstrap template in Python.
- Introduce renderer contract interface to prepare Windows/Linux adapters.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/test_desktop_app_template.py -q`
Expected: PASS

---

### Task 7: Event Envelope Upgrade (A2UI-like action semantics)

**Files:**
- Create: `src/aeiva/metaui/v2/event_codec.py`
- Modify: `src/aeiva/metaui/orchestrator.py`
- Modify: `src/aeiva/metaui/desktop_app.py`
- Test: `tests/metaui/v2/test_event_codec.py`
- Test: `tests/metaui/v2/test_orchestrator_integration.py`

**Step 1: Write the failing test**

```python
from aeiva.metaui.v2.event_codec import decode_client_event


def test_action_event_includes_surface_component_timestamp_context():
    evt = decode_client_event({
        "version": "v2",
        "action": {
            "name": "submit",
            "surfaceId": "main",
            "sourceComponentId": "chat_main",
            "timestamp": "2026-02-07T00:00:00Z",
            "context": {"text": "hello"},
        },
    })
    assert evt.action.name == "submit"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_event_codec.py::test_action_event_includes_surface_component_timestamp_context -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add normalized action/error event codec.
- Ensure desktop renderer sends event metadata consistently.
- Preserve existing `MetaUIEvent` compatibility mapping.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_event_codec.py tests/metaui/v2/test_orchestrator_integration.py -q`
Expected: PASS

---

### Task 8: Demote Scaffold from Primary Path (AI-first Rendering)

**Files:**
- Modify: `src/aeiva/tool/meta/metaui.py`
- Modify: `src/aeiva/metaui/scaffold.py`
- Modify: `docs/reference/metaui-tool-api.md`
- Test: `tests/tool/test_metaui_tool.py`
- Test: `tests/metaui/test_scaffold.py`

**Step 1: Write the failing test**

```python
import importlib
import pytest


@pytest.mark.asyncio
async def test_metaui_scaffold_not_used_when_render_full_spec_provided(monkeypatch):
    mod = importlib.import_module("aeiva.tool.meta.metaui")
    called = {"scaffold": 0}

    def _fake_build(*_args, **_kwargs):
        called["scaffold"] += 1
        return {"title": "x", "components": [], "root": []}

    monkeypatch.setattr(mod, "build_scaffold_spec", _fake_build)
    await mod.metaui(operation="render_full", spec={"title": "x", "components": [{"id": "a", "type": "text", "props": {"text": "x"}}], "root": ["a"]})
    assert called["scaffold"] == 0
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/tool/test_metaui_tool.py::test_metaui_scaffold_not_used_when_render_full_spec_provided -q`
Expected: FAIL (if any accidental scaffold coupling exists)

**Step 3: Write minimal implementation**

- Document and enforce `render_full` as primary AI path.
- `scaffold` remains explicit fallback operation only.
- Add response metadata when scaffold path is used.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/tool/test_metaui_tool.py tests/metaui/test_scaffold.py -q`
Expected: PASS

---

### Task 9: Real-World Scenario Suite (100+ interaction flows)

**Files:**
- Create: `tests/metaui/v2/scenarios/test_real_world_scenarios.py`
- Create: `tests/metaui/v2/scenarios/fixtures/*.jsonl`
- Modify: `tests/metaui/v2/test_orchestrator_integration.py`

**Step 1: Write the failing test**

```python
import pytest


@pytest.mark.parametrize("fixture_name", [
    "chat_basic",
    "chat_intent_switch_from_dashboard",
    "csv_upload_and_chart",
    "multi_surface_modal_and_main",
])
def test_scenario_fixture_runs_without_missing_component(fixture_name):
    assert False, "scenario runner not implemented"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/scenarios/test_real_world_scenarios.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Build deterministic scenario runner against orchestrator/applier.
- Include flows for chat, forms, upload, chart, media, calendar, multistep, multi-surface.
- Validate invariants: no missing root, no stale component id, expected event emission.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/scenarios/test_real_world_scenarios.py -q`
Expected: PASS

---

### Task 10: Performance, Recovery, and Reconnect Guarantees

**Files:**
- Modify: `src/aeiva/metaui/orchestrator.py`
- Modify: `src/aeiva/tool/meta/metaui.py`
- Test: `tests/metaui/v2/test_orchestrator_integration.py`
- Test: `tests/tool/test_metaui_tool.py`

**Step 1: Write the failing test**

```python
import pytest


@pytest.mark.asyncio
async def test_reconnect_replay_rehydrates_latest_surface_without_duplicates():
    assert False, "replay dedup not verified"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_orchestrator_integration.py::test_reconnect_replay_rehydrates_latest_surface_without_duplicates -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Ensure replay idempotency.
- Guarantee launch throttling and connect grace under rapid retries.
- Ensure no duplicate windows or duplicate command application.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_orchestrator_integration.py tests/tool/test_metaui_tool.py -q`
Expected: PASS

---

### Task 11: Documentation and Migration Guide

**Files:**
- Create: `docs/reference/metaui-v2-protocol.md`
- Create: `docs/reference/metaui-v2-catalog.md`
- Create: `docs/reference/metaui-v2-migration.md`
- Modify: `docs/reference/metaui-tool-api.md`

**Step 1: Write the failing doc test (link/smoke)**

```python
from pathlib import Path

def test_metaui_v2_docs_exist():
    assert Path("docs/reference/metaui-v2-protocol.md").exists()
    assert Path("docs/reference/metaui-v2-migration.md").exists()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/metaui/v2/test_docs_smoke.py -q`
Expected: FAIL

**Step 3: Write minimal implementation**

- Document protocol and envelope examples.
- Document legacy-to-v2 mapping table.
- Document recommended AI prompting contract for UI generation.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/metaui/v2/test_docs_smoke.py -q`
Expected: PASS

---

## Final Verification Checklist (Release Gate)

Run in order:

1. `python -m pytest tests/metaui/v2/test_protocol.py tests/metaui/v2/test_catalog.py -q`
2. `python -m pytest tests/metaui/v2/test_data_model.py tests/metaui/v2/test_surface_store.py tests/metaui/v2/test_applier.py -q`
3. `python -m pytest tests/metaui/v2/test_legacy_adapter.py tests/tool/test_metaui_tool.py -q`
4. `python -m pytest tests/metaui/v2/test_event_codec.py tests/metaui/v2/test_orchestrator_integration.py -q`
5. `python -m pytest tests/metaui/v2/scenarios/test_real_world_scenarios.py -q`
6. `python -m pytest tests/metaui tests/command tests/test_terminal_gateway.py -q`

Expected:
- All pass.
- No new flaky test.
- No regression in legacy `metaui` tool calls.

## Quality Bar (A+ Criteria)

- Module boundaries are explicit; no cross-layer shortcuts.
- No implicit template logic in runtime core.
- Protocol messages are schema-validated before apply.
- All renderer updates are idempotent and replay-safe.
- AI owns intent + structure; runtime owns deterministic execution.

## Notes

- Git commit steps are intentionally omitted in this plan because repository workflow is user-managed.
- Execute in small PR-like increments anyway (task-by-task) to keep reviewability high.
