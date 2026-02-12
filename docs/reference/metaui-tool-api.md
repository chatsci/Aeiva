# MetaUI Tool API

MetaUI tool entrypoint: `aeiva.tool.meta.metaui.metaui(...)`

This API controls the local desktop UI runtime for structured interaction.

MetaUI now uses a single protocol/runtime path. Legacy v2 adapter operations were removed
to keep the surface area minimal and deterministic.

## Request Shape

Common fields:

- `operation` (required): operation name.
- `ui_id`: target UI session id.
- `session_id`: logical conversation/session id.
- `host` / `port` / `token`: optional runtime endpoint overrides.
- `ensure_visible`: auto-launch desktop client when no client connected.
- gateway config: `metaui_config.auto_start_desktop` controls eager startup at gateway boot (default off).

## Core Operations

Runtime:

- `start`: ensure orchestrator is started and return endpoint.
- `status`: runtime status and connected client/session counts.
- `catalog`: return the renderer-supported component catalog (A2UI-style authoring baseline).
- `protocol_schema`: return negotiated A2UI protocol schemas (`client_hello`, `hello_ack`, server envelopes), `MetaUISpec` JSON schema, and strict interaction-contract snapshot.
- `validate_messages`: validate a candidate lifecycle message sequence (`spec.messages`) before sending.
- `validate_spec`: normalize + validate an input `spec` (no rendering side effect).
- `launch_desktop`: launch desktop app and wait for connection.
- `set_auto_ui`: toggle automatic UI behavior (`auto_ui: true/false`).

Rendering:

- `render_full`: render a full `MetaUISpec` (`spec` required).
- `patch`: apply patch payload (`ui_id`, `patch` required).
  - `patch` is for incremental updates only.
  - Use `render_full` for structural/layout changes.
- `set_state`: merge runtime UI state (`ui_id`, `state` required).
- `notify`: show desktop notification (`message` required).
- `close`: close a UI session (`ui_id` required).

Recommended robust flow for strict schema authoring:

1. `catalog` + `protocol_schema` to inspect available components, `MetaUISpec` schema, and protocol contracts.
2. AI model builds explicit canonical `spec` JSON (primary path).
3. `render_full` to display.
4. `set_state` / `patch` for non-structural incremental updates only.
5. optional `validate_messages` before advanced lifecycle orchestration.

Session/state:

- `list_sessions`: list active UI sessions.
- `get_session`: inspect one session (`ui_id` required).
- `update_phase`: set session phase (`ui_id`, `phase` required).

Events:

- `poll_events`: pull buffered UI events with filters.
- `wait_event`: await next matching event with timeout.

## Supported Component Types

`MetaUIComponent.type` currently supports:

- `container`
- `tabs`
- `accordion`
- `divider`
- `text`
- `markdown`
- `badge`
- `metric_card`
- `list_view`
- `code_block`
- `image`
- `iframe`
- `chat_panel`
- `file_uploader`
- `data_table`
- `chart`
- `form`
- `form_step`
- `button`
- `input`
- `textarea`
- `select`
- `checkbox`
- `radio_group`
- `slider`
- `progress_panel`
- `result_export`

For non-trivial custom UIs, use `render_full` with explicit `spec` and keep structure decisions on the AI side.

Strict contract (no runtime heuristics):

- No intent/scaffold fallback path.
- No component type aliases.
- Invalid/incomplete specs are rejected (no fallback UI injection).
- Interactive controls and actions should declare explicit behavior (`on_<event>` / `events` with `action` / `steps` / `effects` or explicit event emission semantics).

## Theme Tokens

`MetaUISpec.theme` supports renderer-level visual tokens (portable JSON map).

Common tokens:

- `color_bg_top`
- `color_bg_bottom`
- `color_surface`
- `color_text`
- `color_muted`
- `color_border`
- `color_border_strong`
- `color_primary`
- `color_primary_hover`
- `color_primary_soft`
- `color_focus_ring`
- `color_danger`
- `shadow_soft`
- `shadow_panel`
- `radius_md`

Theme is transported in lifecycle `beginRendering.styles.theme` and applied by desktop renderer.

## Transport Model

MetaUI now supports two runtime transport paths, negotiated by client hello:

- A2UI lifecycle stream (preferred):
  - `surfaceUpdate`
  - `dataModelUpdate`
  - `beginRendering`
  - `deleteSurface`
- Legacy command stream (compatibility):
  - `render_full`
  - `patch`
  - `set_state`
  - `notify`
  - `close`

Desktop client capabilities are sent via `hello` (`protocol_versions`, `supported_components`, `supported_commands`, `features`).
Server replies with `hello_ack` including catalog snapshot and negotiated features.

## Context IO Contract

MetaUI is designed as a bidirectional context channel between user and agent:

- Input ports (user -> AI):
  - `upload` events from `file_uploader`
  - `submit` / `change` events from `form`, `form_step`, `chat_panel`
  - `action` / `retry` / `export` events from action bar and export controls
- Output ports (AI -> user):
  - `set_state` updates resolved through `state_bindings`
  - `patch` structural updates (`update_component`, `append_component`, `merge_spec`, etc.)
  - `notify` user-visible status messages

For portability, keep state payloads schema-first (plain JSON) and avoid host-specific assumptions.

## Session Phases

Supported phases:

- `idle`
- `rendering`
- `interactive`
- `executing`
- `recovering`
- `error`

## Upload Handling

`upload` UI events are persisted in a sandboxed directory:

- default: `storage/metaui/uploads`
- controls:
  - `upload_max_file_bytes`
  - `upload_max_total_bytes`
  - `upload_max_files_per_event`

On success, event payload includes `upload_result.files[*].path`.

## Error Semantics

Response contract:

- success: `{"success": true, ...}`
- failure: `{"success": false, "error": "..."}`

Common failures:

- missing required parameters (`spec`, `ui_id`, etc.)
- `no_connected_clients`
- timeout from `wait_event`
- upload payload validation failure
