# Browser Tool API

Browser tool entrypoint: `aeiva.tool.meta.browser.browser(...)`

This reference documents the stable operation contract for local browser automation.

## Request Shape

Common fields:

- `operation` (required): operation name.
- `profile`: logical browser session name. Default `default`.
- `headless`: request headless/headed execution. Runtime preserves active mode by profile.
- `timeout`: operation timeout in milliseconds.
- `target_id`: active tab id when multiple tabs exist.
- `selector`: CSS selector target.
- `ref`: snapshot ref target (`data-aeiva-ref`).
- `request`: operation-specific payload.

## Core Operations

Session and tabs:

- `start`: create browser session for profile.
- `stop`: close session for profile.
- `profiles`: list active profiles.
- `tabs`: list tabs in current profile.
- `open`: open URL (new tab/session bootstrap).
- `open_tab`: open URL in new tab.
- `focus`: focus a tab by `target_id`.
- `close` / `close_tab`: close current or target tab.

Navigation:

- `navigate`: navigate current/target tab to `url`.
- `back`, `forward`, `reload`: browser navigation controls.

Interaction:

- `click`: click by `selector`, `ref`, or text-based resolution.
- `type`: enter text into resolved input target.
- `select` / `choose_option`: select option(s) in dropdown-like controls.
- `set_date`: set date-like field; supports optional confirm flow.
- `set_number`: set numeric value; supports stepper-like controls.
- `confirm`: trigger context-aware confirmation action (for dialogs/date pickers).
- `scroll`: scroll viewport/element with oscillation guard.
- `press`: keyboard key press.
- `hover`: hover on target.
- `drag`: drag from source to destination.
- `upload`: upload local file paths (policy-constrained roots).
- `wait`: wait by selector/load-state/time.

Workflow:

- `fill_fields`: execute multi-step form workflow (`steps` list).
- `workflow`: alias of `fill_fields`.
- `act`: normalized single action wrapper (`request.kind`).

Inspection and extraction:

- `snapshot`: capture DOM snapshot with stable refs.
- `screenshot`: PNG/JPEG capture.
- `pdf`: page PDF export.
- `get_text`: extract visible text.
- `get_html`: extract HTML.
- `console`: recent console messages.
- `errors`: recent page/runtime errors.
- `network`: recent network events.

External retrieval:

- `request`: policy-checked HTTP request through browser tool interface.
- `search`: search-engine-assisted query flow with browser navigation fallback.

## Error Semantics

Response contract:

- Success: `{"success": true, ...}`
- Failure: `{"success": false, "error": "...", "error_code": "...", "error_details": {...}}`

Common `error_code` values:

- `invalid_request`: missing required fields or malformed payload.
- `unknown_operation`: operation not in supported contract.
- `runtime_error`: runtime/Playwright execution failure.
- `runtime_launch_error`: browser launch failed.
- `runtime_launch_blocked`: launch denied by policy.
- `security_policy_violation`: blocked JS eval, URL, network, or file operation.
- `scroll_blocked` / `scroll_guard`: repeated no-progress scrolling detected.

The tool favors deterministic failure over silent fallback. Callers should branch on `success` and `error_code`.

## Concurrency Model

- Operations are serialized per `profile` via a profile-scoped async lock.
- Different profiles can execute concurrently.
- Interaction caches and guards (`field target lock`, `scroll guard`) are profile-local and best-effort runtime state, not cross-process shared state.
- `stop` clears profile runtime session and profile-scoped interaction state.

## Notes

- Browser automation is local-machine oriented and profile-scoped.
- `evaluate` is disabled by default; enable explicitly via security policy.
- File upload and outbound request behavior are constrained by security policy settings.
