# MetaUI A2UI Alignment Design

## Goal

Align MetaUI with A2UI-style boundaries:
- AI decides UI design and behavior.
- MetaUI only renders deterministic specs and returns UI events.
- No implicit template pollution when user intent changes.

## A2UI-Inspired Principles

1. Declarative UI contract first.
- Spec is source of truth.
- Renderer is stateless/deterministic from spec + state.

2. Catalog-driven component handling.
- Supported component set is explicit and validated.
- Unknown component types degrade safely, never crash rendering.

3. Incremental updates by stable ids.
- `render_full` replaces surface.
- `patch`/`set_state` update by id/state paths.

4. Event channel symmetry.
- User interaction emits structured events.
- Agent reads events and decides next patch/state.

## Gaps Found in Current MetaUI

1. Intent switch could be contaminated by earlier context.
- Long prompts with previous workbench context could bias scaffold output.

2. Chat panel UX lacked local optimistic feedback.
- Clicking send had no immediate local echo, causing perceived failure.

3. Desktop launch retry could produce multiple windows.
- When client handshake was slow, repeated turns could trigger repeated launches.

## Refactor Implemented (This Iteration)

1. Intent focus rule in scaffold parser.
- Use latest meaningful clause as primary signal source.
- Reduces stale-context contamination when users switch tasks mid-conversation.

2. Chat optimistic append in desktop renderer.
- On chat submit, append local user message immediately.
- Keep event emission intact for AI-side handling.

3. Launch grace throttling.
- Added connect-grace window after launch attempts.
- Prevent repeated desktop re-launch during handshake lag.

## Architecture Boundary (Enforced)

- AI side:
  - Understand intent.
  - Generate/modify spec and state.
  - Consume UI events and decide next actions.

- MetaUI side:
  - Validate and render spec.
  - Apply patch/state updates deterministically.
  - Emit user events.
  - Handle runtime lifecycle and transport reliability.

## Next Refactor Steps

1. Make scaffold a strict fallback path.
- Primary path should be direct `render_full` from AI-generated spec.

2. Introduce explicit catalog id negotiation in spec.
- Allow future renderer/backend portability with stable contracts.

3. Add integration scenario suite for intent-switch workflows.
- Analytics -> chat -> media transitions in one session.
- Validate no residual components from prior surfaces.
