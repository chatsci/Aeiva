# AEIVA Codebase Analysis Report

Date: 2026-02-05
Repository: `Aeiva` (`main` branch, dirty worktree)
Analyst: Codex (GPT-5)

> Update note (2026-02-05, post-Phase-C): this report captures a pre-fix snapshot.
> For current runtime status, test results, and network model validation, see
> `docs/reports/2026-02-05-phase-c-enhancement-report.md`.

## 1. Scope and Method

This report is based on:
- Reading project intent from `README.md` and all artifacts under `notes/`.
- Architecture and code inspection across core runtime paths:
  - `agent`, `neuron`, `event`, `cognition`, `llm`, `action`, `memory`, `interface`, `host`, `command`, `tool`, `mas`.
- Validation by execution:
  - Entry-point import sweep.
  - Targeted tests for native tool-calling.
  - Full test suite run.
- Quick targeted probes for security/policy behavior.

## 2. Snapshot of Current Project State

### 2.1 Size and Composition
- Python source files under `src/aeiva`: `229`
- Python test files under `tests`: `45`
- Approximate Python LOC in `src/aeiva`: `33,833`
- Approximate Python LOC in `tests`: `9,328`

Largest source files include:
- `src/aeiva/config/general_configs.py` (1249 lines)
- `src/aeiva/neuron/base_neuron.py` (1067 lines)
- `src/aeiva/cognition/memory/memory_storage.py` (924 lines)
- `src/aeiva/cognition/memory/raw_memory.py` (897 lines)
- `src/aeiva/cognition/memory/summary_memory.py` (808 lines)

### 2.2 Runtime Validation

#### Test results
Command: `pytest -q`
- Passed: `506`
- Failed: `3`
- Skipped: `4`

Failing tests:
1. `tests/integration/test_application_modes.py::TestErrorHandling::test_cognition_error_gradio_mode`
2. `tests/llm/test_llm_client_models.py::TestToolRegistryIntegration::test_call_tool`
3. `tests/llm/test_llm_client_models.py::TestToolRegistryIntegration::test_call_tool_sync`

#### Targeted native tool-calling tests
Command: `pytest -q tests/llm/test_native_tool_loop.py tests/cognition/test_native_tool_calling.py tests/llm/test_llm_client_models.py`
- Passed: `57`
- Skipped: `2`

#### Entry point import validation
Checked all `pyproject.toml` scripts.
- Broken entrypoint: `aeiva-server` (`aeiva.command.aeiva_server:run`)
- Import error: `cannot import name 'setup_logging' from aeiva.command.command_utils`

## 3. Architectural Assessment

## 3.1 What is strong

### Clear modular decomposition
The codebase has a coherent module layout (`perception`, `cognition`, `memory`, `action`, `interface`, `host`, `tool`, `mas`) and a shared event backbone (`event`, `neuron`).

### Event + signal lineage model is real, not superficial
The `Signal` lineage (`trace_id`, `parent_id`, `hop_count`) plus `EventBus` history/replay hooks are implemented in runtime code, not just docs:
- `src/aeiva/neuron/signal.py`
- `src/aeiva/event/event_bus.py`

### Native tool-calling migration is materially implemented
The LLM path now has concrete API-handler abstraction and tool loop execution:
- `src/aeiva/llm/backend.py`
- `src/aeiva/llm/tool_loop.py`
- `src/aeiva/llm/api_handlers/chat_api.py`
- `src/aeiva/llm/api_handlers/responses_api.py`

### Multi-channel gateway architecture is practical
Unified gateway orchestration and route-trace handling are mature enough for production iteration:
- `src/aeiva/command/aeiva_gateway.py`
- `src/aeiva/interface/gateway_base.py`

### Test surface is substantial
`500+` passing tests is a major quality signal for active refactoring.

## 3.2 Drift vs intent documents

### Contract-aligned areas
- Async event-driven flow is present.
- Signal traceability is present.
- Config injection through command entrypoints is mostly followed.

### Drift areas
- `notes/260203 - AEIVA_Architecture_Contract.md` claims neuron purity (no direct system I/O in neurons), but current neurons still perform direct file/system operations, notably:
  - `src/aeiva/action/actuator.py` (file logging in neuron)
  - `src/aeiva/cognition/memory/raw_memory.py` / journal writing path
- `notes/NATIVE_TOOL_CALLING_MIGRATION.md` describes dual-mode migration strategy; current code is effectively native-loop-first with legacy envelope behavior removed from core flow.

These are not necessarily wrong decisions, but docs and implementation are currently out of sync.

## 4. Findings (Bugs, Design Problems, and Risks)

Severity legend:
- `Critical`: immediate security/data risk
- `High`: functional breakage or high operational risk
- `Medium`: correctness/maintainability issues with nontrivial impact
- `Low`: polish, consistency, and future-risk concerns

### 4.1 Critical Findings

1. Plaintext secrets and production tokens committed in config
- Evidence:
  - `configs/agent_config.yaml:4`
  - `configs/agent_config.yaml:18`
  - `configs/agent_config.yaml:27`
  - `configs/agent_config.yaml:121`
  - `configs/agent_config.yaml:123`
  - `configs/llm_api_keys.yaml:1`
  - `configs/agent_config.json:5`
- Impact:
  - Immediate credential compromise risk.
  - Requires secret rotation, not just file cleanup.
- Recommendation:
  - Revoke/rotate exposed keys immediately.
  - Replace values with env placeholders only.
  - Add automated secret scanning in CI.

2. Host daemon auth gap + weak shell allowlist model enables command-chain bypass
- Evidence:
  - No auth enforcement in invoke endpoint: `src/aeiva/host/host_daemon.py:41`
  - Shell policy allows by command prefix/head only: `src/aeiva/host/command_policy.py:60`
  - Policy allows strings like `ls && rm -rf /` when `ls` is allowlisted (verified by runtime probe).
- Impact:
  - If daemon is network-reachable, remote code execution risk exists within allowed command-head constraints.
  - Control operators (`;`, `&&`, `||`, pipes) bypass intended safety model.
- Recommendation:
  - Enforce token auth in daemon endpoint.
  - Replace shell-string policy with structured argv enforcement and operator rejection.
  - Prefer `subprocess` without shell for approved command families.

### 4.2 High Findings

3. Broken CLI entrypoint: `aeiva-server`
- Evidence:
  - Import error from missing symbol path:
    - `src/aeiva/command/aeiva_server.py` imports `setup_logging` from command_utils.
    - `setup_logging` actually lives in `src/aeiva/common/logger.py`.
- Impact:
  - Published script in `pyproject.toml` is nonfunctional.
- Recommendation:
  - Fix import and add smoke test that imports all declared script entrypoints.

4. Global tool executor singleton causes cross-context leakage and test contamination
- Evidence:
  - Global state: `src/aeiva/tool/registry.py:231`
  - First-wins registration: `src/aeiva/tool/registry.py:240`
  - Agent sets global executor unconditionally: `src/aeiva/agent/agent.py:211`
  - Registry blindly assumes executor interface: `src/aeiva/tool/registry.py:158`, `src/aeiva/tool/registry.py:186`
- Observable failure:
  - Full test suite fails `test_call_tool`/`test_call_tool_sync` due stale `MockActuatorNeuron` being retained globally.
- Impact:
  - Wrong executor can be used across agents/gateways/MAS contexts.
  - Nondeterministic behavior in multi-runtime process.
- Recommendation:
  - Make executor/router context-bound rather than module-global.
  - At minimum: guard interface (`hasattr`) and provide explicit reset for tests/lifecycle.

5. Cognition swallows brain exceptions in non-streaming mode
- Evidence:
  - `src/aeiva/cognition/cognition.py:312` catches all exceptions and returns fallback text.
- Observable failure:
  - `tests/integration/test_application_modes.py::test_cognition_error_gradio_mode` expects raised `RuntimeError`; behavior now silently converts to assistant text.
- Impact:
  - Hidden runtime failures, difficult debugging, inconsistent error semantics.
- Recommendation:
  - Make behavior configurable (`fail_fast` vs `user_fallback`).
  - Preserve structured error events even when returning user-safe text.

6. SummaryMemory primary mechanism (`startup_catchup`) is never invoked
- Evidence:
  - Declared as primary in module doc and method exists:
    - `src/aeiva/cognition/memory/summary_memory.py:69`
    - `src/aeiva/cognition/memory/summary_memory.py:126`
  - No call sites in repo (`rg startup_catchup` only returns declaration/doc lines).
- Impact:
  - Missed summaries after unclean shutdown are not auto-healed as designed.
- Recommendation:
  - Invoke `startup_catchup()` during agent startup when summary neuron is enabled.

### 4.3 Medium Findings

7. SummaryMemory disable-path bug sets enabled flag to `True`
- Evidence:
  - On LLM init failure, code logs "disabled" but sets `self._enabled = True`:
    - `src/aeiva/cognition/memory/summary_memory.py:118`
    - `src/aeiva/cognition/memory/summary_memory.py:119`
- Impact:
  - Misleading state and control flow inconsistency.
- Recommendation:
  - Set `self._enabled = False` in that branch.

8. EventBus subscription regex is unsafe/inexact for literal event names
- Evidence:
  - Pattern compilation: `src/aeiva/event/event_bus.py:72`
  - Demonstrated: pattern `perception.output` also matches `perceptionXoutput`.
- Impact:
  - Potential accidental callback routing and hard-to-debug cross-event handling.
- Recommendation:
  - Escape literals (`re.escape`) then expand wildcard semantics intentionally.

9. Realtime config drift: stale tool names + duplicate YAML key
- Evidence:
  - Missing tool names in registry from realtime config:
    - `configs/agent_config_realtime.yaml:88` through `configs/agent_config_realtime.yaml:98`
  - Duplicate key:
    - `configs/agent_config_realtime.yaml:120`
    - `configs/agent_config_realtime.yaml:122`
- Impact:
  - Tool load warnings, reduced capability, silent config ambiguity.
- Recommendation:
  - Align realtime tool list with actual registry tools.
  - Remove duplicate key and add YAML schema validation in CI.

10. Gateway token resolution methods do not actually read environment variables
- Evidence:
  - Slack: `src/aeiva/interface/slack_gateway.py:262`
  - WhatsApp: `src/aeiva/interface/whatsapp_gateway.py:296`
- Impact:
  - Class behavior depends on pre-resolved config only; direct usage unexpectedly fails.
- Recommendation:
  - Add explicit `os.getenv(env_var)` fallback in gateway classes.

11. Action success semantics can mask tool-level failures
- Evidence:
  - `Action.execute()` marks success on any returned payload without checking payload semantics: `src/aeiva/action/action.py:107`
- Impact:
  - Tool results like `{"success": false, ...}` can still be treated as successful action execution.
- Recommendation:
  - Add optional result contract check (e.g., fail when dict has `success: false`).

### 4.4 Low Findings

12. Deprecated timestamp API causes repeated warnings
- Evidence:
  - `datetime.utcnow` in `Event` default factory: `src/aeiva/event/event.py:20`
- Impact:
  - Warning noise in test/runtime; future compatibility risk.
- Recommendation:
  - Replace with timezone-aware `datetime.now(datetime.UTC)`.

13. Repetitive command startup/shutdown boilerplate (Neo4j/gateway lifecycle)
- Evidence:
  - Similar helper patterns duplicated across command modules (`aeiva_chat_*`, `aeiva_gateway`).
- Impact:
  - Higher maintenance cost and drift risk.
- Recommendation:
  - Consolidate command lifecycle scaffolding into shared utilities.

## 5. Additional Imperfections / “Ugly Design” Areas

1. Mixed-generation architecture style
- New neuron/event architecture coexists with older, heavy modules (`config/general_configs.py`, legacy server wiring), producing inconsistent code quality and style.

2. Global mutable singletons in tool layer
- `ToolRegistry`, router, and executor are all process-global (`src/aeiva/tool/registry.py`), which conflicts with multi-agent/multi-gateway isolation goals.

3. Safety policy model is brittle
- Approval and command policies are exact-string and prefix based, with no structured command AST/argv validation.

4. Documentation/code skew in active migration areas
- Notes accurately capture strategy intent but are partially stale against current runtime behavior.

## 6. Recommended Improvement Roadmap

### Phase A (Immediate: security + broken runtime)
1. Rotate all exposed credentials and scrub repository config secrets.
2. Add daemon authentication check and harden shell policy against operator chaining.
3. Fix `aeiva-server` import path and add entrypoint import smoke test.

### Phase B (Stability and correctness)
1. Refactor tool executor/router globals into runtime-scoped dependency.
2. Decide and codify cognition error policy (fail-fast vs user-fallback).
3. Wire `SummaryMemoryNeuron.startup_catchup()` into startup flow.
4. Fix SummaryMemory enabled flag bug.

### Phase C (Design cleanup)
1. Make EventBus event pattern matching strict and explicit.
2. Normalize realtime config tools and add schema checks.
3. Consolidate duplicated command lifecycle code.
4. Align notes/docs with current native-tool-calling implementation reality.

## 7. Quick Wins You Can Apply Today

1. Add a CI job with three gates:
- `pytest -q`
- entrypoint import check for all scripts in `pyproject.toml`
- secret scanner (e.g., gitleaks)

2. Add a deterministic test fixture that resets tool registry global state between tests.

3. Add a strict config validation step at startup:
- verify tool names exist in registry
- reject duplicate keys (custom YAML loader)

## 8. Final Verdict

AEIVA is a serious, nontrivial codebase with a strong architectural core (event-driven neurons, native tool loop, multi-channel gateways) and meaningful test depth. The biggest current blockers are not conceptual architecture; they are operational safety and boundary correctness:
- credential hygiene,
- host/tool execution safety,
- global state isolation,
- and a few concrete regressions that already surface in the full test run.

Fixing those specific issues will significantly increase production readiness without requiring a full redesign.

### Architecture Graphs (ASCII Summary)

#### A. End-to-end request flow
```text
User / External Platform
        |
        v
+------------------------+
| Interface Gateway      |  (CLI / Slack / WhatsApp / Gradio / API)
+------------------------+
        |
        v
+------------------------+
| Agent                  |
| - runtime wiring       |
| - neuron registration  |
+------------------------+
        |
        v
+------------------------+      +------------------------+
| Perception Neurons     | ---> | Cognition Neurons      |
| - input normalization  |      | - LLM + reasoning      |
+------------------------+      +------------------------+
                                          |
                                          v
                               +------------------------+
                               | Action Neurons         |
                               | - tool dispatch        |
                               | - host/system actions  |
                               +------------------------+
                                          |
                                          v
                               +------------------------+
                               | Interface Gateway Out  |
                               +------------------------+
```

#### B. Event/signal lineage backbone
```text
[Neuron A] --emit Signal(trace_id,parent_id,hop_count)--> [EventBus]
                                                         /    |    \
                                                        v     v     v
                                                [Neuron B] [Neuron C] [History/Replay]
                                                     |         |
                                           emits child Signal  |
                                                     \         /
                                                      v       v
                                                   [Downstream Neurons]
```

#### C. Native tool-calling control path
```text
Cognition
  |
  v
LLM Brain
  |
  v
LLM Backend  -->  API Handler (Chat / Responses)
  |                          |
  |<----- model output ------|
  |
  +--> Tool Loop ---------> Tool Registry ---------> Action/Actuator ---------> External Tool/System
           ^                        |                         |
           |                        +---- tool metadata ------+
           +------ tool results back to model context -------+
```

#### D. Gateway + host control plane (risk focus)
```text
External Request
      |
      v
Gateway Router ------------------------------+
      |                                      |
      v                                      v
Interface Gateway                        Host Daemon (/invoke)
      |                                      |
      v                                      v
Agent Runtime                            Command Policy
      |                                      |
      +---------- shared tool execution <----+
```
