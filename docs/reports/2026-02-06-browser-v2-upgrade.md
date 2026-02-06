# Browser V2 Upgrade (2026-02-06)

## Summary

Aeiva browser tooling now uses a persistent session architecture instead of one-browser-per-call execution.

Key outcomes:
- Profile-scoped persistent runtimes.
- Stable tab lifecycle (`open`/`tabs`/`focus`/`close`).
- Deterministic `snapshot -> ref -> act` automation path.
- Event observability (`console`, `errors`, `network`).
- Backward compatibility for legacy operations (`navigate`, `click`, `type`, etc.).

## New Internal Architecture

- `src/aeiva/tool/meta/_browser_runtime.py`
  - `BrowserRuntime` protocol (backend abstraction for future backends).
  - `PlaywrightRuntime` (persistent local runtime).
  - `BrowserSessionManager` (profile lifecycle + per-profile locks).
- `src/aeiva/tool/meta/_browser_service.py`
  - Operation dispatch and compatibility facade.
  - Stateless HTTP `request` and `search` retained.
- `src/aeiva/tool/meta/browser.py`
  - Tool API remains `browser(operation=..., ...)` but now calls Browser V2 service.

## Operation Surface

Supported operations:
- Lifecycle: `status`, `start`, `stop`, `profiles`
- Tabs: `tabs`, `open`, `focus`, `close`
- Navigation and interaction: `navigate`, `click`, `type`, `press`, `hover`, `select`, `wait`, `evaluate`
- Structured automation: `snapshot`, `act`
- Extraction and artifacts: `get_text`, `get_html`, `screenshot`
- Observability: `console`, `errors`, `network`
- HTTP/Search passthrough: `request`, `search`

## Compatibility Notes

Legacy patterns continue to work:
- `click` with `url` still navigates before clicking.
- `type` with `url` still navigates before typing.
- Legacy selector-based operations still work.

Recommended path for reliability:
1. `snapshot`
2. `act` using returned `ref` values
3. optional verification with `get_text`, `get_html`, or `screenshot`

## Host Approval Keys

Host router action keys now include browser operation granularity:
- `browser.navigate`
- `browser.snapshot`
- `browser.act:click`
- `browser.act:evaluate`

This enables precise allow/confirm policies for browser actions.

## Validation

Tests added:
- `tests/tool/test_browser_service.py`
- `tests/host/test_host_router_browser_keys.py`

Regression checks passed:
- `tests/host/test_host_security.py`
- `tests/llm/test_native_tool_loop.py`
- `tests/cognition/test_native_tool_calling.py`
- `tests/command/test_config_validation.py`
