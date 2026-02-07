# Browser V4 Production Pass

Date: 2026-02-06

## Goal
Harden browser automation for real-world multi-turn workflows (especially flight search forms) with robust confirm/fallback behavior and no scroll oscillation dead-loops.

## Capability Matrix

| Category | Human-style operation | Browser support |
|---|---|---|
| Session | start/stop/profile/tabs/focus | Implemented (`status/start/stop/profiles/tabs/open/focus/close`) |
| Navigation | open page/back/forward/reload | Implemented (`open/navigate/back/forward/reload`) |
| Discovery | inspect actionable UI nodes | Implemented (`snapshot` with stable refs) |
| Actions | click/hover/drag/scroll | Implemented (`click/hover/drag/scroll`) |
| Forms | type/select/wait/upload/press | Implemented (`type/select/wait/upload/press`) |
| Confirm | click Done/Confirm/Apply automatically | Implemented (`confirm` op and `act:confirm`) |
| Resilience | recover from oscillating scroll | Implemented (detection + optional auto-recovery via confirm click) |
| Search | web search + flight comparison links | Implemented (`search` with fallbacks and comparison links) |
| Capture | screenshot/pdf/text/html/network/errors | Implemented |

## Key Changes

1. Added `confirm` as first-class browser operation and `act` kind.
2. Added text-targeted click resolution:
   - If `click`/`act:click` has no selector/ref but has `text`, snapshot is used to resolve the best clickable ref.
3. Added strict validation:
   - Click now fails fast when no actionable target can be resolved, instead of issuing empty/ambiguous click.
4. Added scroll guard auto-recovery refinement:
   - `scroll_oscillation` can auto-recover by clicking a high-confidence confirm control.
   - `scroll_no_effect` remains blocked (no auto-recovery), preventing incorrect self-actions.
   - Added per-request control: `auto_recover` / `autoRecover`.
5. Added ranking helpers for robust target selection:
   - confirm-target ranking prefers positive actions and avoids cancel/close/reset-like controls.

## Validation

### Targeted regression checks
- `6 passed` (new click/confirm/recovery regression tests)

### Browser + tool loop suites
Command:
`python -m pytest -q tests/tool/test_browser_runtime.py tests/tool/test_browser_service.py tests/tool/test_browser_tool.py tests/llm/test_native_tool_loop.py tests/host/test_host_router_browser_keys.py`

Result:
- `72 passed`

### Full browser tool suite
Command:
`python -m pytest -q tests/tool`

Result:
- `69 passed`

## Changed Files

- `src/aeiva/tool/meta/_browser_service.py`
- `src/aeiva/tool/meta/browser.py`
- `tests/tool/test_browser_service.py`

