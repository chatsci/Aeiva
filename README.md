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
pip install -e .
```

Optional extras:

```bash
pip install -e ".[realtime]"   # Realtime audio/text UI
pip install -e ".[slack]"      # Slack gateway
pip install -e ".[media]"      # Media utilities
pip install -e ".[metaui]"     # Desktop MetaUI runtime
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
By default `aeiva-gateway` does not auto-start the desktop window. It is launched lazily when the assistant uses `metaui` and `ensure_visible=true`, or you can enable eager startup via `metaui_config.auto_start_desktop`.

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
