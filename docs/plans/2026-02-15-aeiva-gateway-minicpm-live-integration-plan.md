# AEIVA Gateway MiniCPM Live Duplex Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `aeiva-gateway` the single entrypoint that can launch realtime Gradio (audio/video) and support local MiniCPM live duplex in a provider-pluggable architecture.

**Architecture:** Keep existing Agent/EventBus/Cognition core unchanged. Add a realtime provider layer (`registry + provider adapters`) parallel to existing LLM provider layer, then let both `aeiva-chat-realtime` and `aeiva-gateway` dispatch live mode through the same abstraction. This keeps MiniCPM-specific logic out of gateway orchestration and allows incremental add/remove of providers.

**Tech Stack:** Python, Gradio/FastRTC, existing AEIVA event-driven runtime, LiteLLM (for non-live path), pytest.

### Task 1: Lock Current Behavior with Failing Tests

**Files:**
- Create: `tests/command/test_gateway_realtime_live_mode.py`
- Modify: `tests/command/test_config_validation.py`

**Step 1: Write failing test for gateway live-mode dispatch**

```python
def test_gateway_does_not_skip_live_mode_when_provider_registered(monkeypatch):
    # Arrange config with realtime.enabled=true, mode=live, provider=minicpm_local
    # Patch provider registry to return a fake provider that marks "launched".
    # Assert aeiva_gateway main path invokes provider launch once.
    ...
```

**Step 2: Write failing test for config validation**

```python
def test_validate_runtime_config_live_mode_accepts_minicpm_provider():
    cfg = {
        "realtime_config": {
            "enabled": True,
            "mode": "live",
            "provider": "minicpm_local",
            "gateway_scope": "shared",
            "session_scope": "shared",
            "minicpm": {"base_url": "http://127.0.0.1:8022"},
        },
        "llm_gateway_config": {"llm_provider": "minicpm_local"},
    }
    validate_runtime_config(cfg)
```

**Step 3: Run tests to verify failures**

Run: `pytest tests/command/test_gateway_realtime_live_mode.py tests/command/test_config_validation.py -q`  
Expected: FAIL (`live` mode still restricted / gateway skip path not dispatching provider).

**Step 4: Commit checkpoint**

```bash
git add tests/command/test_gateway_realtime_live_mode.py tests/command/test_config_validation.py
git commit -m "test(realtime): add failing coverage for gateway live-mode provider dispatch"
```

### Task 2: Introduce Realtime Provider Contract + Registry

**Files:**
- Create: `src/aeiva/realtime/providers/base.py`
- Create: `src/aeiva/realtime/providers/registry.py`
- Create: `src/aeiva/realtime/providers/__init__.py`
- Create: `tests/realtime/test_provider_registry.py`

**Step 1: Write failing registry tests**

```python
def test_realtime_provider_registry_create_known_provider(): ...
def test_realtime_provider_registry_reject_unknown_provider(): ...
```

**Step 2: Implement minimal contract**

```python
class RealtimeProvider(Protocol):
    provider_name: str
    def build_handler(self) -> Any: ...
    def build_ui(self) -> Any: ...
```

**Step 3: Implement registry**

```python
registry.register("openai", OpenAILiveProvider)
registry.register("minicpm_local", MiniCPMLiveProvider, aliases=("minicpm",))
```

**Step 4: Run tests**

Run: `pytest tests/realtime/test_provider_registry.py -q`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/aeiva/realtime/providers/base.py src/aeiva/realtime/providers/registry.py src/aeiva/realtime/providers/__init__.py tests/realtime/test_provider_registry.py
git commit -m "feat(realtime): add provider contract and registry"
```

### Task 3: Refactor Existing OpenAI Live Path into Provider

**Files:**
- Create: `src/aeiva/realtime/providers/openai_live_provider.py`
- Modify: `src/aeiva/command/aeiva_chat_realtime.py`
- Modify: `src/aeiva/realtime/openai_realtime.py` (if needed: move builder glue only)
- Create: `tests/realtime/test_openai_live_provider.py`

**Step 1: Write failing provider parity test**

```python
def test_openai_live_provider_builds_webrtc_audio_video_ui():
    provider = OpenAILiveProvider(config_dict=cfg, logger=log)
    demo = provider.build_ui()
    assert demo is not None
```

**Step 2: Move hardcoded branch to provider**

- Replace `run_live_realtime_ui(..., provider)` hardcoded `if provider != "openai"` in `aeiva_chat_realtime.py`.
- New flow: resolve provider from registry, then call provider’s `launch()` or `build_ui().launch(...)`.

**Step 3: Run tests**

Run: `pytest tests/realtime/test_openai_live_provider.py tests/command/test_realtime_reply_on_pause_safety.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add src/aeiva/realtime/providers/openai_live_provider.py src/aeiva/command/aeiva_chat_realtime.py src/aeiva/realtime/openai_realtime.py tests/realtime/test_openai_live_provider.py
git commit -m "refactor(realtime): move openai live mode behind provider interface"
```

### Task 4: Add MiniCPM Live Provider (Local Duplex Transport)

**Files:**
- Create: `src/aeiva/realtime/providers/minicpm_live_provider.py`
- Create: `src/aeiva/realtime/minicpm_live_client.py`
- Create: `tests/realtime/test_minicpm_live_provider.py`
- Modify: `src/aeiva/command/config_validation.py`

**Step 1: Define provider config schema**

```yaml
realtime_config:
  mode: live
  provider: minicpm_local
  minicpm:
    transport: "webrtc_demo_backend"   # or "openai_compat_llama" (degraded fallback)
    base_url: "http://127.0.0.1:8022"
    model: "openbmb/MiniCPM-o-4_5"
    timeout: 20
```

**Step 2: Implement minimal client boundary**

```python
class MiniCPMLiveClient:
    async def connect(self): ...
    async def send_audio(self, frame): ...
    async def send_video(self, frame): ...
    async def send_text(self, text): ...
    async def recv_audio(self): ...
    async def recv_text_delta(self): ...
```

**Step 3: Implement `MiniCPMLiveProvider`**

- Build `AsyncAudioVideoStreamHandler`-compatible handler.
- Keep MiniCPM transport details only in provider/client modules.
- No changes to Agent core/Cognition/EventBus.

**Step 4: Add graceful fallback mode**

- If configured transport unavailable, raise explicit startup error with actionable message.
- Optional degraded fallback: route to current turn-based pipeline with warning.

**Step 5: Run tests**

Run: `pytest tests/realtime/test_minicpm_live_provider.py tests/command/test_config_validation.py -q`  
Expected: PASS.

**Step 6: Commit**

```bash
git add src/aeiva/realtime/providers/minicpm_live_provider.py src/aeiva/realtime/minicpm_live_client.py src/aeiva/command/config_validation.py tests/realtime/test_minicpm_live_provider.py tests/command/test_config_validation.py
git commit -m "feat(realtime): add minicpm local live duplex provider"
```

### Task 5: Wire `aeiva-gateway` to Live Realtime Providers

**Files:**
- Modify: `src/aeiva/command/aeiva_gateway.py`
- Modify: `src/aeiva/command/aeiva_chat_realtime.py` (shared launch helper extraction)
- Create: `tests/command/test_gateway_realtime_live_mode.py` (complete assertions)

**Step 1: Remove live-mode skip logic**

Current skip branch in `aeiva_gateway.py`:

```python
if realtime_mode != "turn_based":
    logger.warning("... Skipping.")
```

Replace with:

```python
if realtime_mode == "turn_based":
    # existing build_turn_based_realtime_ui
elif realtime_mode == "live":
    # resolve provider from realtime provider registry and launch
else:
    ...
```

**Step 2: Extract shared launcher**

- Create internal helper (same file or new module): `launch_realtime_ui(config_dict, agent, queue_gateway, mode, provider, logger, route_token)`.
- Reuse in both `aeiva-chat-realtime` and `aeiva-gateway` to avoid behavior drift.

**Step 3: Run tests**

Run: `pytest tests/command/test_gateway_realtime_live_mode.py tests/command/test_realtime_reply_on_pause_safety.py -q`  
Expected: PASS.

**Step 4: Commit**

```bash
git add src/aeiva/command/aeiva_gateway.py src/aeiva/command/aeiva_chat_realtime.py tests/command/test_gateway_realtime_live_mode.py
git commit -m "feat(gateway): support realtime live mode via provider registry"
```

### Task 6: Config + Example Profiles for One-Command Startup

**Files:**
- Modify: `configs/agent_config.yaml`
- Create: `configs/profiles/agent_config_minicpm_live_gateway.yaml`
- Modify: `docs/reference.md`

**Step 1: Add clean profile (do not overload base config)**

```yaml
gradio_config:
  enabled: false
realtime_config:
  enabled: true
  mode: live
  provider: minicpm_local
  gateway_scope: shared
  session_scope: shared
  minicpm:
    transport: webrtc_demo_backend
    base_url: http://127.0.0.1:8022
```

**Step 2: Add startup command docs**

Run:

```bash
aeiva-gateway --config configs/profiles/agent_config_minicpm_live_gateway.yaml --verbose
```

Expected:
- Gateway starts runtime
- Realtime Gradio port prints URL
- Mic/camera accepted
- Audio output returned from MiniCPM live provider

**Step 3: Commit**

```bash
git add configs/profiles/agent_config_minicpm_live_gateway.yaml configs/agent_config.yaml docs/reference.md
git commit -m "docs(config): add minicpm live gateway profile and runbook"
```

### Task 7: End-to-End Verification Matrix (Before Claiming Done)

**Files:**
- Create: `tests/e2e/test_gateway_minicpm_live_smoke.py` (or manual script in `scripts/`)
- Update: `docs/reference.md` verification section

**Step 1: Automated smoke (mock transport)**

Run: `pytest tests/e2e/test_gateway_minicpm_live_smoke.py -q`  
Expected: PASS (gateway launches live provider, route path works).

**Step 2: Manual real-machine checklist**

1. Start MiniCPM backend stack and verify health endpoints.
2. Start `aeiva-gateway` with live profile.
3. Open realtime Gradio URL.
4. Speak 10 short turns and 3 interruptions.
5. Verify text + audio + camera frame path.
6. Verify no cross-route leakage between sessions.

**Step 3: Performance acceptance**

- P50 first-audio latency < 1.5s (local)
- No deadlock for 20-minute session
- No uncaught exceptions in `aeiva-gateway.log`

**Step 4: Commit**

```bash
git add tests/e2e/test_gateway_minicpm_live_smoke.py docs/reference.md
git commit -m "test(realtime): add gateway minicpm live smoke and acceptance checklist"
```

## Execution Notes (Engineering Constraints)

- Keep MiniCPM-specific logic out of:
  - `src/aeiva/agent/*`
  - `src/aeiva/cognition/*`
  - `src/aeiva/event/*`
- Constrain it to:
  - `src/aeiva/realtime/providers/*`
  - `src/aeiva/realtime/minicpm_live_client.py`
  - provider selection/config validation code paths only.
- Preserve backward compatibility:
  - existing `turn_based` realtime path unchanged;
  - existing `openai` live path unchanged via adapter.

## Rollback Strategy

If live MiniCPM provider is unstable:

1. Keep registry and gateway live dispatch.
2. Disable `minicpm_local` live provider in config (`provider: openai` or `mode: turn_based`).
3. No core rollback required because architecture is additive.
