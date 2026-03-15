# MiniCPM-o 4.5 Provider Abstraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add local MiniCPM-o 4.5 support while introducing a clean model-provider abstraction so future models (Qwen/local OpenAI-compatible servers/closed APIs) can be added or removed incrementally without touching Agent/Cognition core logic.

**Architecture:** Keep `Agent -> Cognition -> LLMBrain -> LLMClient` public behavior stable. Move model-specific behavior behind pluggable provider adapters and add a parallel realtime-provider layer for live audio/video. Use explicit capability descriptors (`vision`, `tool_calling`, `audio_in`, `audio_out`) instead of model-name heuristics.

**Tech Stack:** Python 3.10+, LiteLLM, FastRTC/Gradio, existing AEIVA EventBus/Gateway runtime, pytest.

## Design Decision (Chosen vs Alternatives)

### Option A: Continue patching current LiteLLM path
- Pros: lowest immediate code churn.
- Cons: model-specific branches continue leaking into core handler logic (`supports_function_calling`, API mode heuristics, live provider hardcoded in command).
- Verdict: rejected for long-term maintainability.

### Option B: Two-layer adapter architecture (Recommended)
- Layer 1: `LLM Provider Adapter` (request/response + tool loop).
- Layer 2: `Realtime Provider Adapter` (live audio/video session transport).
- Pros: clean boundaries, additive provider onboarding, no Agent-core rewrites.
- Cons: initial refactor cost.
- Verdict: chosen.

### Option C: Full modality bus rewrite
- Pros: theoretically maximal flexibility.
- Cons: high migration risk and over-engineering now.
- Verdict: deferred.

---

## Target Architecture (Post-Refactor)

```text
                        +------------------------------+
                        |      Agent / Cognition       |
                        | (unchanged core logic path)  |
                        +---------------+--------------+
                                        |
                                   +----v-----+
                                   | LLMClient |
                                   +----+-----+
                                        |
                 +----------------------+----------------------+
                 |                                             |
        +--------v---------+                         +---------v----------+
        | LLMProviderRegistry|                        | CapabilityResolver |
        +--------+---------+                         +---------+----------+
                 |                                             |
      +----------+-----------+                                 |
      |                      |                                 |
+-----v----------------+ +---v---------------------+            |
| LiteLLMProvider      | | MiniCPMLocalProvider    | <----------+
| (existing default)   | | (OpenAI-compatible HTTP)|
+----------------------+ +-------------------------+


Live Realtime Path (separate abstraction):

aeiva_chat_realtime
      |
      v
RealtimeProviderRegistry
      |
 +----+-----------------------+
 |                            |
 v                            v
OpenAIRealtimeProvider   MiniCPMRealtimeProvider
```

---

## Implementation Tasks

### Task 1: Introduce LLM provider contracts and registry

**Files:**
- Create: `src/aeiva/llm/providers/base.py`
- Create: `src/aeiva/llm/providers/registry.py`
- Create: `src/aeiva/llm/providers/__init__.py`
- Test: `tests/llm/test_provider_registry.py`

**Step 1: Write failing tests**
```python
def test_registry_returns_default_provider_class(): ...
def test_registry_rejects_unknown_provider(): ...
```

**Step 2: Run test to verify failure**

Run: `pytest tests/llm/test_provider_registry.py -q`  
Expected: FAIL (module/class not found)

**Step 3: Write minimal implementation**
- Define provider protocol (`build_params`, `execute`, `parse_response`, `parse_stream_delta`, `uses_responses_api`)
- Add registry with `register/get/create`

**Step 4: Run test to verify pass**

Run: `pytest tests/llm/test_provider_registry.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add tests/llm/test_provider_registry.py src/aeiva/llm/providers/base.py src/aeiva/llm/providers/registry.py src/aeiva/llm/providers/__init__.py
git commit -m "refactor(llm): add provider contract and registry"
```

---

### Task 2: Wrap current backend into default LiteLLM provider

**Files:**
- Create: `src/aeiva/llm/providers/litellm_provider.py`
- Modify: `src/aeiva/llm/llm_client.py`
- Modify: `src/aeiva/llm/backend.py` (constructor wiring only)
- Test: `tests/llm/test_native_tool_loop.py`

**Step 1: Write failing tests**
```python
def test_llm_client_uses_registry_default_provider(): ...
```

**Step 2: Run targeted tests (expect fail)**

Run: `pytest tests/llm/test_native_tool_loop.py -q`  
Expected: FAIL on provider wiring assertion

**Step 3: Implement minimal adapter**
- `LiteLLMProvider` delegates to current `LLMBackend` + API handlers.
- `LLMClient` builds provider via registry but keeps same external API.

**Step 4: Run regression tests**

Run: `pytest tests/llm/test_native_tool_loop.py tests/llm/test_litellm_adapter.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/llm/providers/litellm_provider.py src/aeiva/llm/llm_client.py src/aeiva/llm/backend.py tests/llm/test_native_tool_loop.py
git commit -m "refactor(llm): route llm client through default litellm provider adapter"
```

---

### Task 3: Add capability resolver (replace brittle model-name gating)

**Files:**
- Create: `src/aeiva/llm/providers/capabilities.py`
- Modify: `src/aeiva/llm/api_handlers/chat_api.py`
- Modify: `src/aeiva/llm/api_handlers/responses_api.py` (if needed for capability usage parity)
- Modify: `src/aeiva/llm/llm_gateway_config.py`
- Test: `tests/llm/test_provider_capabilities.py`

**Step 1: Write failing tests**
```python
def test_unknown_model_can_enable_tools_via_capability_override(): ...
def test_unknown_model_can_disable_tools_via_capability_override(): ...
```

**Step 2: Run failing test**

Run: `pytest tests/llm/test_provider_capabilities.py -q`  
Expected: FAIL

**Step 3: Implement capability resolution**
- Config override shape:
  - `llm_capabilities.tool_calling`
  - `llm_capabilities.vision`
  - `llm_capabilities.audio_in`
  - `llm_capabilities.audio_out`
- Handler tool inclusion checks use resolver, not only `litellm.supports_function_calling()`.

**Step 4: Run tests**

Run: `pytest tests/llm/test_provider_capabilities.py tests/llm/test_llm_client_models.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/llm/providers/capabilities.py src/aeiva/llm/api_handlers/chat_api.py src/aeiva/llm/api_handlers/responses_api.py src/aeiva/llm/llm_gateway_config.py tests/llm/test_provider_capabilities.py
git commit -m "feat(llm): add explicit capability resolver for model behavior"
```

---

### Task 4: Expand config schema for provider selection (backward compatible)

**Files:**
- Modify: `src/aeiva/llm/llm_gateway_config.py`
- Modify: `src/aeiva/command/config_validation.py`
- Modify: `src/aeiva/command/command_utils.py`
- Test: `tests/command/test_config_validation.py`

**Step 1: Write failing tests**
```python
def test_validate_runtime_config_accepts_llm_provider_selector(): ...
def test_validate_runtime_config_rejects_unknown_llm_provider_selector(): ...
```

**Step 2: Run failing tests**

Run: `pytest tests/command/test_config_validation.py -q`  
Expected: FAIL on new fields

**Step 3: Implement config normalization**
- Add optional fields:
  - `llm_provider` (default `litellm`)
  - `llm_provider_config` (dict; provider-specific)
- Keep existing keys (`llm_model_name`, `llm_base_url`, `llm_custom_provider`) valid.

**Step 4: Run config + llm tests**

Run: `pytest tests/command/test_config_validation.py tests/llm/test_llm_client_models.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/llm/llm_gateway_config.py src/aeiva/command/config_validation.py src/aeiva/command/command_utils.py tests/command/test_config_validation.py
git commit -m "feat(config): add llm provider selection with backward compatibility"
```

---

### Task 5: Add MiniCPM local provider profile (turn-based multimodal first)

**Files:**
- Create: `src/aeiva/llm/providers/minicpm_local_provider.py`
- Modify: `src/aeiva/llm/providers/registry.py`
- Modify: `src/aeiva/cognition/cognition.py` (only if message normalization hook is needed)
- Create: `configs/agent_config_minicpm_local.yaml`
- Test: `tests/llm/test_minicpm_local_provider.py`

**Step 1: Write failing tests**
```python
def test_minicpm_provider_builds_openai_compatible_params(): ...
def test_minicpm_provider_accepts_text_plus_image_blocks(): ...
```

**Step 2: Run failing tests**

Run: `pytest tests/llm/test_minicpm_local_provider.py -q`  
Expected: FAIL

**Step 3: Implement provider**
- Use chat-completions compatible payloads for local endpoints.
- No Agent-core changes.
- Explicitly set default capabilities for MiniCPM profile.

**Step 4: Run tests**

Run: `pytest tests/llm/test_minicpm_local_provider.py tests/cognition/test_cognition.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/llm/providers/minicpm_local_provider.py src/aeiva/llm/providers/registry.py configs/agent_config_minicpm_local.yaml tests/llm/test_minicpm_local_provider.py
git commit -m "feat(llm): add minicpm local provider profile for text+image path"
```

---

### Task 6: Realtime provider abstraction (remove hardcoded openai branch)

**Files:**
- Create: `src/aeiva/realtime/providers/base.py`
- Create: `src/aeiva/realtime/providers/registry.py`
- Create: `src/aeiva/realtime/providers/openai_provider.py`
- Modify: `src/aeiva/command/aeiva_chat_realtime.py`
- Modify: `src/aeiva/command/config_validation.py`
- Test: `tests/command/test_realtime_provider_registry.py`

**Step 1: Write failing tests**
```python
def test_live_mode_dispatches_by_provider_registry(): ...
def test_live_mode_rejects_unregistered_provider(): ...
```

**Step 2: Run failing tests**

Run: `pytest tests/command/test_realtime_provider_registry.py -q`  
Expected: FAIL

**Step 3: Implement abstraction**
- Move OpenAI live wiring under provider class.
- `aeiva_chat_realtime` asks registry for live provider.

**Step 4: Run tests**

Run: `pytest tests/command/test_realtime_provider_registry.py tests/command/test_realtime_reply_on_pause_safety.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/realtime/providers/base.py src/aeiva/realtime/providers/registry.py src/aeiva/realtime/providers/openai_provider.py src/aeiva/command/aeiva_chat_realtime.py src/aeiva/command/config_validation.py tests/command/test_realtime_provider_registry.py
git commit -m "refactor(realtime): add live provider registry and decouple openai branch"
```

---

### Task 7: Add MiniCPM live provider (full multimodal transport)

**Files:**
- Create: `src/aeiva/realtime/providers/minicpm_provider.py`
- Create: `tests/realtime/test_minicpm_live_provider.py`
- Modify: `configs/agent_config_realtime.yaml`
- Modify: `src/aeiva/command/config_validation.py`

**Step 1: Write failing tests**
```python
def test_minicpm_live_provider_builds_session_from_config(): ...
def test_minicpm_live_provider_handles_audio_text_video_hooks(): ...
```

**Step 2: Run failing tests**

Run: `pytest tests/realtime/test_minicpm_live_provider.py -q`  
Expected: FAIL

**Step 3: Implement provider**
- Implement a dedicated adapter for MiniCPM live endpoint contract.
- Keep transport code in provider module only; do not leak provider conditionals into command/gateway core.

**Step 4: Run tests**

Run: `pytest tests/realtime/test_minicpm_live_provider.py tests/test_realtime_handler.py -q`  
Expected: PASS

**Step 5: Commit**
```bash
git add src/aeiva/realtime/providers/minicpm_provider.py tests/realtime/test_minicpm_live_provider.py configs/agent_config_realtime.yaml src/aeiva/command/config_validation.py
git commit -m "feat(realtime): add minicpm live provider adapter"
```

---

### Task 8: Documentation, examples, and end-to-end verification

**Files:**
- Modify: `README.md`
- Modify: `README_CN.md`
- Create: `docs/tutorials/minicpm_local_setup.md`
- Create: `docs/tutorials/model_provider_extension.md`

**Step 1: Document runtime profiles**
- default OpenAI profile
- MiniCPM local profile
- extension guide for adding Qwen or custom APIs

**Step 2: Run full regression suites**

Run: `pytest tests/llm tests/command tests/cognition tests/test_realtime_handler.py -q -rs`  
Expected: PASS

**Step 3: Run smoke commands**

Run: `aeiva-chat-terminal --config configs/agent_config_minicpm_local.yaml --verbose`  
Expected: startup success with provider initialization logs.

Run: `aeiva-chat-realtime --config configs/agent_config_realtime.yaml --verbose`  
Expected: live/turn-based startup success for selected provider.

**Step 4: Commit**
```bash
git add README.md README_CN.md docs/tutorials/minicpm_local_setup.md docs/tutorials/model_provider_extension.md
git commit -m "docs: add minicpm setup and model provider extension guide"
```

---

## Acceptance Criteria

- `Agent`, `Cognition`, `Memory`, `Action` do not require provider-specific branches.
- Adding a new model provider requires:
  1) one provider class
  2) one registry entry
  3) one config profile
  and no core-neuron edits.
- MiniCPM local text+image path works through standard cognition tool loop.
- Realtime live provider selection is registry-driven (not hardcoded `if provider == openai`).
- Capability behavior is explicit/configurable and test-covered.

## Risk Controls

- Keep backward compatibility for current `llm_gateway_config` keys.
- Enforce strict targeted tests at each task before broader regression.
- Isolate live transport adapters so provider protocol changes do not impact event pipeline.

