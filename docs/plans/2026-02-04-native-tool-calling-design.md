# Native Tool Calling Migration Design

**Goal:** Replace the JSON envelope path with native tool calling end‑to‑end, so all tool execution is structured, streaming‑safe, and provider‑recommended.

**Context & Prior Art (OpenClaw):**
OpenClaw exposes a single `/tools/invoke` endpoint and routes tool calls through policy/allowlist + session‑scoped permissions. Tool calls are structured (not JSON in text), executed by the gateway, and results are fed back as `tool_result`. This pattern eliminates JSON parsing leaks and keeps UI output purely human‑readable.

## Architecture

### 1) Tool Calling Path (Native‑Only)
- **LLMBrain** always passes tool schemas to the LLM (OpenAI/Anthropic native tool calling).
- **LLMClient** owns the tool loop:
  1. Call model with `messages + tools`
  2. Parse `tool_calls`
  3. Execute tool via `ToolRegistry` (which routes through `HostRouter` if enabled)
  4. Append `tool_result` messages
  5. Repeat until no tool calls
  6. Return final text only
- **Cognition** treats LLM output as text only. It no longer parses JSON or infers actions.

### 2) Tool Execution & Host Routing
- `ToolRegistry` remains the single execution interface.
- `HostRouter` (already implemented) decides whether a tool executes locally or via `aeiva-host` daemon.
- The model does not need to know about host routing; it sees a single tool list.

### 3) Streaming Behavior
- Streaming is **pure text**. No JSON suppression, no classifier.
- Tool call phases do not emit raw JSON; the user sees only:
  - Optional “Thinking…” hint (if desired)
  - Final or streamed natural language output

### 4) Config & Prompting
- `action_system_prompt` removed from runtime prompt composition.
- `tool_calling_mode` forced to **native** (no auto/envelope fallback).
- Tools are described via schema in the API request, not in the prompt.

## Data Flow

User input → Cognition → LLMBrain → LLMClient (native tools loop) → ToolRegistry → HostRouter (optional) → tool results → LLMClient → final text → Cognition → UI

## Error Handling
- Tool execution errors become `tool_result` error content and are surfaced in final text.
- If a tool call references an unknown tool, respond with a structured tool error and prompt user.
- Streaming failures fall back to non‑streaming final response.

## Testing Strategy
- Unit: tool call parsing in Chat + Responses API handlers
- Integration: tool loop with filesystem/shell tools, both local and host‑routed
- UI: ensure no JSON leakage in Gradio/Realtime/Terminal

## Rollout
- Remove envelope parsing code paths, prompt instructions, and stream classifier.
- Keep a minimal compatibility shim for any old tests if needed, but default to native.

