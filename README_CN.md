<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# AEIVA: 一个不断进化的智能虚拟助手

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

⭐️ 文档：https://chatsci.github.io/Aeiva/

## 仓库目标

AEIVA 是一个面向实际应用的 AI 助手仓库，用于构建和运行多通道虚拟助手。

主要用途：
- 对话助手场景（终端/Web/实时语音/社交通道）
- 可调用工具的助手工作流
- 单智能体与多智能体运行实验

## 使用方法

### 1）安装

```bash
pip install -e .
```

可选扩展：

```bash
pip install -e ".[realtime]"   # 实时语音/文本 UI
pip install -e ".[slack]"      # Slack 网关
pip install -e ".[media]"      # 媒体处理工具
```

### 2）配置

主要配置文件：
- `configs/agent_config.yaml`
- `configs/agent_config.json`
- `configs/agent_config_realtime.yaml`

按需设置环境变量，例如：

```bash
export OPENAI_API_KEY="..."
export NEO4J_HOME="..."                    # 使用 Neo4j 时
export SLACK_BOT_TOKEN="..."               # Slack
export SLACK_APP_TOKEN="..."               # Slack
export WHATSAPP_ACCESS_TOKEN="..."         # WhatsApp
export WHATSAPP_VERIFY_TOKEN="..."         # WhatsApp
export WHATSAPP_PHONE_NUMBER_ID="..."      # WhatsApp
export MAID_HOME="..."                     # Maid 桌面模式
```

### 3）运行

推荐统一网关模式：

```bash
aeiva-gateway --config configs/agent_config.yaml --verbose
```

单通道命令：

```bash
aeiva-chat-terminal --config configs/agent_config.yaml --verbose
aeiva-chat-realtime --config configs/agent_config_realtime.yaml --verbose
aeiva-chat-gradio --config configs/agent_config.yaml --verbose
aeiva-chat-slack --config configs/agent_config.yaml --verbose
aeiva-chat-whatsapp --config configs/agent_config.yaml --verbose
maid-chat --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
aeiva-server --config configs/agent_config.yaml --host 0.0.0.0 --port 8000 --verbose
```

日志默认路径：
- `~/.aeiva/logs/`

### 4）通道说明

Slack：
- 安装依赖：`pip install -e '.[slack]'`
- 配置 `slack_config.enabled: true`
- 提供 `SLACK_BOT_TOKEN` 与 `SLACK_APP_TOKEN`
- 运行 `aeiva-chat-slack`

WhatsApp：
- 配置 `whatsapp_config.enabled: true`
- 设置 webhook host/port/path
- 提供 WhatsApp Cloud API token
- 运行 `aeiva-chat-whatsapp`

Realtime：
- 安装依赖：`pip install -e '.[realtime]'`
- 使用 `configs/agent_config_realtime.yaml`
- 运行 `aeiva-chat-realtime`
