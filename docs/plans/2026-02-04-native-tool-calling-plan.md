# Native Tool Calling Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove JSON envelope tool calling and ship native tool calling end‑to‑end (chat + responses APIs) with clean streaming and no UI leaks.

**Architecture:** LLMClient owns the tool loop; Cognition and LLMBrain deliver text only. Tools are passed as native schemas; ToolRegistry + HostRouter execute tool calls. JSON prompts, envelope parsing, and stream classifiers are removed.

**Tech Stack:** Python, LiteLLM, existing AEIVA LLMClient/LLMBrain/Cognition, Gradio gateways.

---

### Task 1: Add tests for native tool loop (chat + responses)

**Files:**
- Create: `tests/llm/test_native_tool_loop.py`
- (Optional) Create: `tests/llm/fixtures_tool_calls.py`

**Step 1: Write failing tests**
```python
import pytest
from aeiva.llm.llm_client import LLMClient
from aeiva.llm.llm_gateway_config import LLMGatewayConfig

class DummyToolRegistry:
    def __init__(self):
        self.called = []
    async def execute(self, name, **kwargs):
        self.called.append((name, kwargs))
        return {"ok": True, "name": name, "args": kwargs}

@pytest.mark.asyncio
async def test_chat_tool_loop_executes_and_returns_text(monkeypatch):
    cfg = LLMGatewayConfig(llm_model_name="gpt-4o", llm_api_key="test")
    client = LLMClient(cfg)
    # patch registry + handler to return tool_calls then final text
    # expect: tool executed and final text returned (no JSON)
    assert True
```

**Step 2: Run tests (should fail)**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: FAIL (missing mocks / behavior)

**Step 3: Implement minimal test scaffolding (mocks)**
- Mock `ChatAPIHandler.parse_response` to return tool_calls then final content.
- Mock `ResponsesAPIHandler.parse_response` similarly.

**Step 4: Re-run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add tests/llm/test_native_tool_loop.py

git commit -m "test: add native tool loop coverage"
```

---

### Task 2: Remove JSON envelope path from Cognition

**Files:**
- Modify: `src/aeiva/cognition/cognition.py`
- Modify: `src/aeiva/action/action_envelope.py`

**Step 1: Write failing test**
Add assertion in tests that JSON parsing is not called when in native mode (can be simple monkeypatch guard).

**Step 2: Run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: FAIL

**Step 3: Implement minimal changes**
- Delete `_think_streaming` and envelope path in `handle_think`.
- Remove `parse_action_envelope` usage in Cognition.
- Make `handle_think` always call `_handle_think_native`.

**Step 4: Re-run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/cognition/cognition.py src/aeiva/action/action_envelope.py

git commit -m "refactor: remove envelope tool calling from cognition"
```

---

### Task 3: Simplify LLMBrain prompt composition

**Files:**
- Modify: `src/aeiva/cognition/brain/llm_brain.py`
- Modify: `configs/agent_config.yaml`

**Step 1: Write failing test**
Verify system prompt does not include action JSON schema in native mode.

**Step 2: Run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: FAIL

**Step 3: Implement minimal changes**
- Remove `ACTION_SYSTEM_PROMPT` / `ACTION_SYSTEM_PROMPT_AUTO` usage.
- `system_prompt` becomes only `llm_system_prompt`.
- Remove `tool_calling_mode` branching; always pass tool schemas to LLM.
- Remove `action_system_prompt` from config file.

**Step 4: Re-run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/cognition/brain/llm_brain.py configs/agent_config.yaml

git commit -m "refactor: native tool prompts only"
```

---

### Task 4: Remove envelope utilities / classifier / stream buffer

**Files:**
- Delete: `src/aeiva/action/action_envelope.py`
- Modify: `src/aeiva/cognition/cognition.py` (imports)
- Modify: any module still importing envelope utilities

**Step 1: Remove file + imports**

**Step 2: Run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: PASS

**Step 3: Commit**
```bash
git add -A src/aeiva/action/action_envelope.py src/aeiva/cognition/cognition.py

git commit -m "chore: remove envelope utils"
```

---

### Task 5: Validate host routing in native tool loop

**Files:**
- Modify: `tests/llm/test_native_tool_loop.py`

**Step 1: Add test**
Mock `ToolRegistry.execute` and assert it is called for tool_calls.

**Step 2: Run tests**
Run: `pytest tests/llm/test_native_tool_loop.py -v`
Expected: PASS

**Step 3: Commit**
```bash
git add tests/llm/test_native_tool_loop.py

git commit -m "test: ensure tool calls route through registry"
```

---

### Task 6: End‑to‑end manual verification

**Files:**
- No code changes

**Step 1: Run gateway**
```bash
aeiva-gateway -c configs/agent_config.yaml
```

**Step 2: Test behaviors**
- Ask: "List files on ~/Desktop" (should execute tool + respond without JSON)
- Ask: "Play random song" (should ask confirmation, execute on confirm)
- Verify no JSON appears in UI
- Verify streaming works

**Step 3: Commit (if any config tweaks)**
```bash
git add configs/agent_config.yaml

git commit -m "chore: finalize native tool calling config"
```

---

Plan complete and saved to `docs/plans/2026-02-04-native-tool-calling-plan.md`.

Two execution options:

1. **Subagent‑Driven (this session)** – I dispatch a fresh subagent per task and review between tasks.
2. **Parallel Session** – You open a new session and I execute with `superpowers:executing-plans`.

Which approach? (1 or 2)
