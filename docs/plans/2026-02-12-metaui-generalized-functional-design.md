# MetaUI Generalized Functional Design

> **For Claude/Codex:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for implementation and keep strict TDD.

**Goal:** Make MetaUI reliably produce **functional, customizable, platform-portable** UIs where AI defines all structure/logic and MetaUI only validates/renders/bridges events.

**Architecture:** Single strict A2UI-style path. No intent inference, no scaffold fallback, no heuristic synthesis in MetaUI. AI always emits explicit canonical specs and actions; MetaUI enforces contract and executes deterministically.

**Tech Stack:** Python (tool/orchestrator/validators), WebSocket transport, desktop JS renderer modules, Playwright E2E, dialogue replay harness.

## 1. Principles (Non-Negotiable)

1. AI owns UI design and interaction logic.
2. MetaUI owns schema validation, rendering, state mutation execution, and event relay.
3. One protocol path only (strict canonical spec); no legacy dual-mode behavior.
4. No hidden defaults that change semantics.
5. Every interactive control must be executable (not visual shell only).

## 2. Why Custom UI Failed (Root Causes)

1. Preset overuse: model chooses `chat_ui` instead of generating full custom spec for customization requests.
2. Contract under-communication: model sometimes assumes unsupported/unsupported-looking patterns because compact schema reply lacks enough “canonical examples + constraints”.
3. Expressiveness gap: current schema is strong on structure but weak on generalized visual semantics (alignment/color/density tokens) needed for “WhatsApp-like” customization.
4. Functional gate gap: generated UI can be valid JSON but still practically non-functional if actions/bindings are incomplete.

## 3. Target Capability Model

### 3.1 Structural Layer
- Component tree by stable IDs only.
- Layout primitives: `Row`, `Column`, `List`, `Card`, `Tabs`, `Modal`, `Divider`.
- Template list binding: `List.props.children={componentId,path}`.

### 3.2 Interaction Layer
- `Action` is explicit and only two forms:
  - `event` (server round-trip)
  - `functionCall` (deterministic local operation)
- Inputs must bind `props.value.path`.
- All state changes are explicit operations (`setState`, `appendState`, etc.).

### 3.3 Presentation Layer (Generalized, Not Chat-Specific)
- Introduce schema-level appearance tokens that are portable and strict:
  - `density`: `compact|normal|comfortable`
  - `tone`: `neutral|primary|success|warning|danger`
  - `surface`: `flat|elevated|outlined`
  - `alignment`: `start|center|end` (where applicable)
  - `emphasis`: `low|medium|high`
- Tokens map to renderer style variables deterministically.
- Avoid raw arbitrary CSS in spec (maintain safety/portability).

## 4. Contract & Validation Design

### 4.1 Schema Contract
- Keep strict component prop allowlists.
- Keep strict function catalog allowlists.
- Reject unknown keys/functions/types deterministically with JSON-pointer errors.

### 4.2 Functional Completeness Contract
- Interactive mode must satisfy all:
  - at least one actionable control
  - all button actions valid and executable
  - all input value bindings valid
  - all references resolvable (`root`, `children`, `child`, tab children, modal trigger/content)

### 4.3 Runtime Contract
- Renderer never eagerly resolves dynamic bindings during normalize.
- Resolution happens at render context with full data scope (`state`, `item`, `payload`, `event`).
- Local mutation triggers safe rerender and state consistency update.

## 5. Performance & Responsiveness Design

1. `render_full` must not block on desktop connect for long windows.
2. Use short connect probe + replay queue path.
3. Keep compact schema responses bounded for low-latency tool loops.
4. SLA targets:
   - P95 `render_full` tool return < 10s when model is healthy.
   - UI first paint < 2s after desktop client connection.

## 6. Testing Strategy (Real Usage, Not Toy)

### 6.1 Static
- Schema validity tests.
- Contract strictness tests (unknown keys/types/functions).
- Interaction completeness checks.

### 6.2 Functional E2E (Desktop)
- Input/edit/delete/send/upload/select/date/slider/modal/tabs/list-template flows.
- Cross-component chains (`runSequence`, mixed mutations).
- Dynamic template rendering with primitive/object list items.

### 6.3 Dialogue Replay (LLM-in-the-loop)
- Scenario suites for real requests:
  - chat workspace customization
  - form/dashboard/table workflows
  - media and file flows
  - multi-turn UI mutation/refinement
- Capture latency, timeout, tool-call success, UI session metrics.

### 6.4 Regression Policy
- Every production bug gets:
  - failing test first
  - minimal fix
  - replay scenario extension

## 7. Implementation Phases

### Phase A: Contract Hardening
- Expand compact protocol payload with canonical minimal examples and hard constraints.
- Enforce explicit full-spec generation for customization intents.

### Phase B: Presentation Generalization
- Add strict appearance tokens to relevant components.
- Map tokens in renderer with deterministic style rules.

### Phase C: Functional Completeness Enforcement
- Strengthen pre-render interaction contract checks.
- Add clearer actionable validation errors and fix guides.

### Phase D: Performance Closure
- Bound connect waits and rely on replay semantics.
- Add per-operation timing telemetry in eval harness.

### Phase E: Full Real-Usage Evaluation
- Execute expanded dialogue replay matrix.
- Gate releases on pass rate + latency SLO.

## 8. Success Criteria

1. No “looks okay but non-functional” interactive UI in certified scenarios.
2. Customization requests produce custom specs (not preset fallback unless explicitly requested).
3. Stable latency: no repeated multi-minute waits on healthy model calls.
4. Strict separation preserved: AI decides, MetaUI executes.
5. A2UI-aligned core semantics with cleaner, stricter engineering boundaries.
