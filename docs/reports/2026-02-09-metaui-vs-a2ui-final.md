# MetaUI vs A2UI Final Gap-Closure Report (2026-02-09)

## Scope

This report compares AEIVA MetaUI against Google A2UI design goals for:

- strict protocol/lifecycle semantics
- AI-defined UI contract
- renderer passiveness
- interaction round-trip reliability
- component/action usability

## What Is Now Equivalent

1. AI-defined surface contract (no intent/scaffold authoring path)
- MetaUI authoring path is now schema-first (`catalog` -> `protocol_schema` -> `render_full` -> `set_state/patch`) in `src/aeiva/tool/meta/metaui.py`.
- Spec root is explicit and required (`normalize_metaui_spec` rejects empty root/components) in `src/aeiva/metaui/spec_normalizer.py`.

2. Lifecycle stream semantics (A2UI-style)
- Server supports `surfaceUpdate`, `dataModelUpdate`, `beginRendering`, `deleteSurface` with replay on reconnect in `src/aeiva/metaui/orchestrator.py`.
- Desktop runtime applies lifecycle updates deterministically and no longer relies on implicit root fallback in `src/aeiva/metaui/assets/desktop_template.html` and `src/aeiva/metaui/lifecycle_messages.py`.

3. Schema/contract visibility to model side
- `protocol_schema` now exposes `MetaUISpec` JSON schema and strict interaction contract snapshot in `src/aeiva/metaui/a2ui_protocol.py`.
- Component catalog returns supported component/event/action contract in `src/aeiva/metaui/component_catalog.py`.

## Where MetaUI Is Better (Local Single-Machine Target)

1. Strong local UX + recoverability
- Desktop reconnect/replay, ACK tracking, and state replay are integrated in one runtime (`src/aeiva/metaui/orchestrator.py`).
- Client-side render failure isolation avoids full white-screen by fragment rendering with per-root error surfaces (`src/aeiva/metaui/assets/desktop_template.html`).

2. Strict interaction guardrails for “visible and usable”
- Interaction contract checks reject shell interactive UIs in interactive mode (`collect_interaction_contract_issues` in `src/aeiva/metaui/spec_normalizer.py`).
- Named action definitions now execute through the same canonical interaction path as component events (`executeInteractionConfig` in `src/aeiva/metaui/assets/desktop_template.html`).

3. Security-hardening for local runtime
- Upload sandbox + symlink guards in `src/aeiva/metaui/upload_store.py`.
- Iframe sandbox strict profile and allowlist-based token handling in `src/aeiva/metaui/interaction_contract.py` and `src/aeiva/metaui/spec_normalizer.py`.

## Intentional Differences

1. Product focus
- A2UI emphasizes general protocol and broad integration.
- MetaUI is optimized for local desktop productivity in AEIVA (single-user, single-machine), prioritizing deterministic behavior and low-ops setup.

2. Renderer strategy
- MetaUI keeps a finite explicit component catalog for deterministic rendering and predictable tests, rather than permissive ad-hoc component interpretation.

## Key Fixes Closed in Final Pass

1. Command success signaling and render reliability
- ACK is sent only after successful command handling; failed render/patch no longer ACKed.
- Reconnect guard prevents duplicate websocket reconnection loops.

2. Server/client spec consistency
- Successful `patch` updates server-side session spec for replay correctness.

3. Interaction execution correctness
- Action execution path unified for component events and named actions.
- Chat-target operations require explicit target for non-chat components (strict, no heuristic inference).

## Residual Trade-offs

- Strict contract rejects malformed/underspecified specs by design (this is intentional to avoid “looks rendered but not usable” shells).
- Local desktop runtime remains the primary target; cloud/browser-hosted renderer is out of scope.

## Validation Summary

- MetaUI + tool suite: `278 passed, 7 skipped`
- Full repository: `1341 passed, 23 skipped`

Both runs were executed after the final strictness/usability fixes.
