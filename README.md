<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# Aeiva: A Human-Centered Agent

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

⭐️ Documentation: https://chatsci.github.io/Aeiva/

## Objective

Aeiva is built as a human-centered, lifelong AI partner that augments human potential.

Its purpose is to help people grow continuously, amplify human capability and creativity, and turn intent into meaningful action.

Aeiva can play different roles across different moments of life:
- a mentor, friend, work partner, or delegated agent
- a "second self": another identity of you for exploration and expression
- a gateway between you and the world, connecting your goals to tools, knowledge, and execution

Our vision is simple: help people experience deep, high-agency growth in the RPG of life.

## Current Product Shape

Aeiva is currently evolving as a unified agent runtime with multiple interaction surfaces:

- terminal chat for direct local use
- web dialogue UI for multimodal interaction
- a separate LifeRPG dashboard for structured self-modeling and growth tracking
- Slack and WhatsApp gateways for real-world messaging channels

The goal is not to ship disconnected demos. The goal is to let one agent architecture serve multiple channels while preserving a coherent human-centered core.

On the web, the gateway now exposes dialogue and LifeRPG as separate pages so each interface can stay focused:
- Dialogue UI: conversation, tools, multimodal interaction
- LifeRPG UI: identity, roles, inventory, projects, and TODOs

Model capabilities remain pluggable. Different backends can enable different combinations of text, vision, audio, realtime, and tool use without changing Aeiva's core direction.

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

This launches the unified gateway. In the current default web setup, it serves:
- Dialogue UI on a local Gradio page
- LifeRPG dashboard on a separate local Gradio page

Default ports are typically:
- Dialogue UI: `http://127.0.0.1:7860`
- LifeRPG UI: `http://127.0.0.1:7862`

If a port is occupied, Gradio may choose a nearby port. Use the startup logs as the source of truth.

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

### 5) Dialogue Replay Testing (Real Conversations)

You can replay real multi-turn dialogue scenarios against a live AEIVA runtime
and get machine-readable pass/fail reports.

```bash
aeiva-dialogue-replay \
  --config configs/agent_config.yaml \
  --scenarios docs/examples/dialogue_replay/dialogue_suite.yaml \
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
  - `expectation` supports content and latency:
  - `contains_all`, `contains_any`, `excludes`
  - `min_response_chars`, `max_latency_seconds`

### 6) Channel Notes

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
