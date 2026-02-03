<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# AEIVA: 一个不断进化的智能虚拟助手

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

AEIVA 是一个模块化、事件驱动的智能体系统，核心是 **Neuron pattern**（receive → process → send）。
它聚焦于 **多通道交互**、**记忆宫殿** 和 **工具调用自治**，可从单一助手扩展到多智能体社会。

⭐️ **文档**：https://chatsci.github.io/Aeiva/

## 核心亮点

- **Neuron pattern + 事件总线**：异步、可组合、可追踪。
- **记忆宫殿**：分层记忆结构，支持原始/总结存储与可扩展后端。
- **统一网关**：一个进程支持多通道，可共享或隔离上下文。
- **工具生态**：API 工具 + 电脑操作能力，覆盖真实世界任务。
- **MAS 就绪**：面向多智能体演进的清晰边界与架构基础。

## 交互模式

- 终端聊天
- Realtime UI（FastRTC）：文本 + 语音（+ 可选图片）
- Slack
- WhatsApp（Meta Cloud API）
- Maid 桌面助手
- 统一网关（多通道共享上下文）

## 快速开始（统一网关）

```bash
pip install -e .
aeiva-gateway --config configs/agent_config.yaml --verbose
```

- Realtime UI：`http://127.0.0.1:7860`（当 `realtime_config.enabled: true`）。
- 在 `configs/agent_config.yaml` 中开关通道：
  `terminal_config`、`slack_config`、`whatsapp_config`、`realtime_config`、`maid_config`。

## 安装

### 前置要求

- Python 3.10+
- Neo4j（用于图记忆；如需可设置 `NEO4J_HOME`）

### 安装

```bash
pip install aeiva
```

### 从源码安装

```bash
git clone https://github.com/chatsci/Aeiva.git
cd Aeiva
pip install -e .
```

### 可选依赖

```bash
pip install -e ".[realtime]"   # FastRTC 实时界面
pip install -e ".[slack]"      # Slack 网关
pip install -e ".[media]"      # 影音处理工具（moviepy）
```

## 配置

- 主配置：`configs/agent_config.yaml` / `configs/agent_config.json`
- Realtime 默认配置：`configs/agent_config_realtime.yaml`
- LLM 密钥：`configs/llm_api_keys.yaml`（或环境变量）

## 存储后端（可选）

- **向量数据库**：Milvus（推荐）、Chroma、Qdrant、Weaviate
- **图数据库**：Neo4j（用于图记忆相关功能）
- **关系型数据库**：SQLite（推荐）或 PostgreSQL

## 命令

### 🪄⭐ 统一网关（推荐）

```bash
aeiva-gateway --config configs/agent_config.yaml --verbose
```

- 一个进程即可支持多通道。
- 默认共享上下文，可通过 `gateway_scope` 与 `session_scope` 做隔离。

### 单通道命令

```bash
aeiva-chat-terminal --config configs/agent_config.yaml --verbose
aeiva-chat-realtime --config configs/agent_config_realtime.yaml --verbose
aeiva-chat-gradio --config configs/agent_config.yaml --verbose   # 旧版 UI
aeiva-chat-slack --config configs/agent_config.yaml --verbose
aeiva-chat-whatsapp --config configs/agent_config.yaml --verbose
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

日志默认存放在 `~/.aeiva/logs/`。

## Slack 配置

**安装依赖**：

```bash
pip install -e '.[slack]'
```

**Slack App 配置检查清单**：

1. **Socket Mode**：在 App Settings 里启用。
2. **Event Subscriptions → Bot Events**：
   - `message.im`（接收 DM）
   - `app_mention`（接收 @mention）
   - `app_home_opened`（Home tab，可选）
3. **OAuth & Permissions → Bot Token Scopes**：
   - `chat:write`
   - `app_mentions:read`
   - `im:history`
   - `im:read`
   - `app_home:read`, `app_home:write`（Home tab）
4. **App-level Token**：创建带 `connections:write` 的 `xapp-` token。
5. **安装 App** 到你的 workspace。

*可选（频道消息）*：
- Bot Events：`message.channels`
- Scopes：`channels:history`

**设置 Token**（环境变量或配置文件）：

```bash
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_APP_TOKEN="xapp-..."
```

在 `configs/agent_config.yaml` 中：

```yaml
slack_config:
  enabled: true
  bot_token_env_var: "SLACK_BOT_TOKEN"
  app_token_env_var: "SLACK_APP_TOKEN"
```

启动：

```bash
aeiva-chat-slack --config configs/agent_config.yaml --verbose
```

## WhatsApp 配置（Meta Cloud API）

**设置 Token**（环境变量或配置文件）：

```bash
export WHATSAPP_ACCESS_TOKEN="EA..."
export WHATSAPP_VERIFY_TOKEN="..."
export WHATSAPP_PHONE_NUMBER_ID="..."
```

在 `configs/agent_config.yaml` 中：

```yaml
whatsapp_config:
  enabled: true
  webhook_path: "/webhook"
  host: "0.0.0.0"
  port: 8080
```

请将 webhook 暴露为公网地址，并在 Meta App 中配置。

## Maid 桌面助手

```bash
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

- 下载 `Maid.app`：https://drive.google.com/file/d/1c7PXoMk7-QgWJ37XM_JqrLn3HQCg3HDL/view?usp=sharing
- 设置 `MAID_HOME` 为 Unity 应用路径
- 日志：`~/.aeiva/logs/maid-chat.log`

## 引用

```bibtex
@misc{bang2024aeiva,
      title={Aeiva: 一个不断进化的智能虚拟助手},
      author={Bang Liu},
      year={2024},
      url={https://github.com/chatsci/Aeiva}
}
```

## 联系方式

<p align="center" width="100%">
<img src="assets/contact.png" alt="联系方式" style="width: 50%; display: block; margin: auto;">
</p>
