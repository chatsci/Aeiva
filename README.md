<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# AEIVA: An Evolving Intelligent Virtual Assistant

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

AEIVA is a modular, event-driven agent system built around the **Neuron pattern** (receive → process → send).
It focuses on **multi-channel interaction**, **memory palace**, and **tool-using autonomy**, scaling from a
single assistant to a multi-agent society.

⭐️ **Documentation**: https://chatsci.github.io/Aeiva/

## Highlights

- **Neuron pattern + event bus**: async, composable, and traceable.
- **Memory palace**: layered memory with raw/summary storage and extensible backends.
- **Unified Gateway**: one process, many channels, shared or isolated contexts.
- **Tool ecosystem**: API tools + computer-use operators for real-world tasks.
- **MAS-ready**: multi-agent design with clean boundaries for future growth.

## Interaction Modes

- Terminal chat
- Realtime UI (FastRTC): text + audio (+ optional images)
- Slack
- WhatsApp (Meta Cloud API)
- Maid desktop assistant
- Unified Gateway (multi-channel, shared context)

## Quickstart (Unified Gateway)

```bash
pip install -e .
aeiva-gateway --config configs/agent_config.yaml --verbose
```

- Realtime UI: `http://127.0.0.1:7860` (when `realtime_config.enabled: true`).
- Enable/disable channels in `configs/agent_config.yaml`:
  `terminal_config`, `slack_config`, `whatsapp_config`, `realtime_config`, `maid_config`.

## Installation

### Prerequisites

- Python 3.10+
- Neo4j (for graph memory). Set `NEO4J_HOME` if needed.

### Install

```bash
pip install aeiva
```

### Install from Source

```bash
git clone https://github.com/chatsci/Aeiva.git
cd Aeiva
pip install -e .
```

### Optional Extras

```bash
pip install -e ".[realtime]"   # FastRTC realtime UI
pip install -e ".[slack]"      # Slack gateway
```

## Configuration

- Main configs: `configs/agent_config.yaml` / `configs/agent_config.json`
- Realtime defaults: `configs/agent_config_realtime.yaml`
- LLM keys: `configs/llm_api_keys.yaml` (or environment variables)

## Storage Backends (Optional)

- **Vector DB**: Milvus (recommended), Chroma, Qdrant, Weaviate
- **Graph DB**: Neo4j (for graph memory features)
- **Relational DB**: SQLite (recommended) or PostgreSQL

## Commands

### 🪄⭐ Unified Gateway (Recommended)

```bash
aeiva-gateway --config configs/agent_config.yaml --verbose
```

- One process, multiple channels.
- Shared context by default; can be isolated per channel via `gateway_scope` and `session_scope`.

### Single-Channel Commands

```bash
aeiva-chat-terminal --config configs/agent_config.yaml --verbose
aeiva-chat-realtime --config configs/agent_config_realtime.yaml --verbose
aeiva-chat-gradio --config configs/agent_config.yaml --verbose   # legacy UI
aeiva-chat-slack --config configs/agent_config.yaml --verbose
aeiva-chat-whatsapp --config configs/agent_config.yaml --verbose
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

Logs are stored under `~/.aeiva/logs/`.

## Slack Setup

**Install dependency**:

```bash
pip install -e '.[slack]'
```

**Slack App checklist**:

1. **Socket Mode**: enable it in App Settings.
2. **Event Subscriptions → Bot Events**:
   - `message.im` (DM)
   - `app_mention` (mentions)
   - `app_home_opened` (Home tab, optional)
3. **OAuth & Permissions → Bot Token Scopes**:
   - `chat:write`
   - `app_mentions:read`
   - `im:history`
   - `im:read`
   - `app_home:read`, `app_home:write` (Home tab)
4. **App-level Token**: create `xapp-` token with `connections:write`.
5. **Install** the app to your workspace.

*Optional (for channel messages)*:
- Bot Events: `message.channels`
- Scopes: `channels:history`

**Tokens** (env or config):

```bash
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
```

In `configs/agent_config.yaml`:

```yaml
slack_config:
  enabled: true
  bot_token_env_var: "SLACK_BOT_TOKEN"
  app_token_env_var: "SLACK_APP_TOKEN"
```

Run:

```bash
aeiva-chat-slack --config configs/agent_config.yaml --verbose
```

## WhatsApp Setup (Meta Cloud API)

**Tokens** (env or config):

```bash
export WHATSAPP_ACCESS_TOKEN="EA..."
export WHATSAPP_VERIFY_TOKEN="..."
export WHATSAPP_PHONE_NUMBER_ID="..."
```

In `configs/agent_config.yaml`:

```yaml
whatsapp_config:
  enabled: true
  webhook_path: "/webhook"
  host: "0.0.0.0"
  port: 8080
```

Expose your webhook (e.g., via a public URL) and set it in Meta App settings.

## Maid Chat (Desktop Assistant)

```bash
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

- Download `Maid.app`: https://drive.google.com/file/d/1c7PXoMk7-QgWJ37XM_JqrLn3HQCg3HDL/view?usp=sharing
- Set `MAID_HOME` to your Unity app path.
- Logs: `~/.aeiva/logs/maid-chat.log`

## Citation

```bibtex
@misc{bang2024aeiva,
      title={Aeiva: An Evolving Intelligent Virtual Assistant},
      author={Bang Liu},
      year={2024},
      url={https://github.com/chatsci/Aeiva}
}
```

## Contact

![contact](assets/contact.png)
