<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# AEIVA: An Evolving Intelligent Virtual Assistant

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

⭐️ Documentation: https://chatsci.github.io/Aeiva/

## Objective

AEIVA is a practical AI assistant repository for building and running a multi-channel virtual assistant.

It is intended for:
- conversational assistant use cases (terminal/web/realtime/social channels)
- tool-using assistant workflows
- single-agent and multi-agent runtime experiments

## Usage

### 1) Install

```bash
uv sync
```

Install all optional capabilities (recommended for local development):

```bash
uv sync --all-extras
```

Or install specific extras only:

```bash
uv sync --extra realtime   # Realtime audio/text UI
uv sync --extra slack      # Slack gateway
uv sync --extra media      # Media utilities
uv sync --extra metaui     # Desktop MetaUI runtime
```

### 2) Configure

Main config files:
- `configs/agent_config.yaml`
- `configs/agent_config.json`
- `configs/agent_config_realtime.yaml`

Set required environment variables as needed, for example:

```bash
export OPENAI_API_KEY="..."
export NEO4J_HOME="..."                    # if Neo4j is used
export SLACK_BOT_TOKEN="..."               # for Slack
export SLACK_APP_TOKEN="..."               # for Slack
export WHATSAPP_ACCESS_TOKEN="..."         # for WhatsApp
export WHATSAPP_VERIFY_TOKEN="..."         # for WhatsApp
export WHATSAPP_PHONE_NUMBER_ID="..."      # for WhatsApp
export MAID_HOME="..."                     # for Maid desktop mode
```

### 3) Run

Recommended unified mode:

```bash
aeiva-gateway --config configs/agent_config.yaml --verbose
```

Single-channel commands:

```bash
aeiva-chat-terminal --config configs/agent_config.yaml --verbose
aeiva-chat-realtime --config configs/agent_config_realtime.yaml --verbose
aeiva-chat-gradio --config configs/agent_config.yaml --verbose
aeiva-chat-slack --config configs/agent_config.yaml --verbose
aeiva-chat-whatsapp --config configs/agent_config.yaml --verbose
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
aeiva-server --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

Logs default to:
- `~/.aeiva/logs/`

### 4) Browser Tool

AEIVA includes a local browser automation tool for real web tasks:
- search and navigation across websites
- form interaction (typing/select/click/submit)
- multi-step browsing workflows with retry/recovery
- extraction of structured page results for assistant replies

Enable it in `action_config.tools` with `browser`.

### 5) MetaUI (Desktop UI)

MetaUI lets the assistant open/update a local desktop UI for forms, uploads, tables, charts, and progress panels.

```bash
aeiva-metaui-desktop --ws-url ws://127.0.0.1:8765/metaui
```

`metaui` is also available as a tool in `action_config.tools`.
By default `aeiva-gateway` does not auto-start the desktop window. It is launched lazily when the assistant uses `metaui` with `ensure_visible=true`.

MetaUI is renderer-only on the main path:
- AI generates explicit UI spec (`components`, `root`, component-level `Action`, `state_bindings`).
- MetaUI validates, renders, and returns interaction/file events.
- `metaui.protocol_schema` exposes `MetaUISpec` JSON schema and strict interaction contract for model-side authoring.
- For deterministic behavior, use `metaui.catalog` + `metaui.protocol_schema` + `metaui.render_full(spec=...)` + `metaui.patch/set_state`.
- Use `interaction_mode` in spec:
  - `interactive` (default): key controls (`button`, `form`, `form_step`) must declare explicit interaction contract.
  - `preview`: layout-only preview is allowed (non-functional mock UI).

MetaUI event bridge (A2UI-style interaction loop):
- In `aeiva-gateway` + Gradio mode, UI events can be forwarded back to AI as structured stimuli.
- This lets AI react to button/form/upload actions and update UI continuously via `metaui` calls.
- Control with `metaui_config.event_bridge_enabled` and related `event_bridge_*` options.

### 6) Dialogue Replay Testing (Real Conversations)

You can replay real multi-turn dialogue scenarios against a live AEIVA runtime
and get machine-readable pass/fail reports.

```bash
aeiva-dialogue-replay \
  --config configs/agent_config.yaml \
  --scenarios docs/examples/dialogue_replay/metaui_dialogue_suite.yaml \
  --output-json .reports/dialogue-replay.json \
  --output-md .reports/dialogue-replay.md
```

Useful options:
- `--scenario-id <id>` (repeatable): run only selected scenarios
- `--fail-fast`: stop a scenario at the first failing turn assertion
- `--route-token <token>`: select replay route (default `gradio`)

Scenario file format:
- `scenarios[]`: list of test scenarios
- each scenario has `id`, `description`, `turns[]`
- each turn supports `user`, `timeout_seconds`, `expectation`
- `expectation` supports content, latency, and MetaUI invariants:
  - `contains_all`, `contains_any`, `excludes`
  - `min_response_chars`, `max_latency_seconds`
  - `metaui_min_sessions`, `metaui_require_non_empty_components`

One-command MetaUI quality gate (pytest + optional live replay):

```bash
aeiva-metaui-eval \
  --config configs/agent_config.yaml \
  --replay-scenarios docs/examples/dialogue_replay/metaui_dialogue_suite.yaml \
  --replay-mode auto \
  --output-json .reports/metaui-evaluation.json \
  --output-md .reports/metaui-evaluation.md
```

### 7) Channel Notes

Slack usage:
- install Slack extra: `pip install -e '.[slack]'`
- enable `slack_config.enabled: true`
- provide `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN`
- run `aeiva-chat-slack`

WhatsApp usage:
- enable `whatsapp_config.enabled: true`
- configure webhook host/port/path
- provide WhatsApp Cloud API tokens
- run `aeiva-chat-whatsapp`

Realtime usage:
- install realtime extra: `pip install -e '.[realtime]'`
- use `configs/agent_config_realtime.yaml`
- run `aeiva-chat-realtime`
