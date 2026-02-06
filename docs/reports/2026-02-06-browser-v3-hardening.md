# Browser V3 Hardening Report (2026-02-06)

## Goal

Raise Browser V2 to a cleaner, stronger Browser V3 through repeated cycles:
- compare against OpenClaw patterns,
- reflect on gaps,
- implement focused upgrades,
- run broad tests.

## Quality Review (V2 -> V3)

### What V2 did well
- Persistent profile/tab sessions.
- Snapshot + ref + act baseline.
- Compatibility with legacy `browser(operation=...)` calls.

### V2 issues identified
- Ref robustness depended on generated CSS selectors; brittle after DOM shifts.
- Missing high-value browser actions for real workflows (`drag`, `upload`, `scroll`, `pdf`, history navigation).
- Error contract not explicit enough (`invalid_request` vs runtime failures).
- Headless mode could unintentionally flip for an already running profile.
- Session replacement/stop paths had lock ordering risks under concurrent calls.

### V3 upgrades implemented
- Stable ref system:
  - Snapshot now injects and reuses `data-aeiva-ref` attributes, with fallback selector metadata.
  - Runtime selector resolution supports primary + fallback paths.
- Expanded action surface:
  - Added `back`, `forward`, `reload`, `drag`, `scroll`, `upload`, `pdf`.
  - Extended `act` kinds to include `navigate`, `reload`, `back`, `forward`, `drag`, `scroll`, `upload`.
- Stronger runtime robustness:
  - Added launch hardening options (`chromium_sandbox=False`, `--disable-dev-shm-usage`).
  - Added guarded retry in navigation.
  - Improved locator resolution fallback behavior.
- Cleaner error model:
  - Added `error_code` with structured categories:
    - `unknown_operation`
    - `invalid_request`
    - `runtime_error`
  - Unknown operation responses include supported operation list.
- Session correctness:
  - Running profile now preserves existing headless mode across subsequent operations.
  - Session manager stop/replace operations execute with per-session lock safety.

## Comparison vs OpenClaw

### Now strongly aligned (single-machine scope)
- Persistent runtime and tab lifecycle.
- Deterministic snapshot/ref/action flow.
- Rich operation set for practical browser task automation.
- Better structured error contracts and host approval key granularity.

### Still intentionally out of scope
- Node proxy and distributed browser routing.
- Chrome extension relay ecosystem.
- Remote CDP multi-node orchestration.

For Aeiva’s current target (single user, single machine), V3 is now cleaner and more focused while preserving compatibility.

## Tests

Added/expanded:
- `tests/tool/test_browser_service.py`
- `tests/tool/test_browser_session_manager.py`
- `tests/host/test_host_router_browser_keys.py`

Validation run:
- `pytest -q tests/action tests/agent tests/cognition tests/command tests/host tests/llm tests/mas tests/neuron tests/perception tests/tool/test_browser_service.py tests/tool/test_browser_session_manager.py`
- Result: `353 passed, 2 skipped`.

## Current Assessment

Browser module quality is now high for the project scope:
- clean layering,
- better operational coverage,
- stronger behavior under concurrency and repeated use,
- clear compatibility and test evidence.

No additional high-confidence upgrades remain without real usage telemetry indicating new edge cases.
