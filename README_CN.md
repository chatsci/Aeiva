<p align="center" width="100%">
<img src="https://i.ibb.co/P4zQHDk/aeiva-1024.png" alt="AEIVA" style="width: 50%; min-width: 300px; display: block; margin: auto; background-color: transparent;">
</p>

# Aeiva: A Human-Centered Agent

<p align="center">
<a href="README_CN.md"><img src="https://img.shields.io/badge/文档-中文版-blue.svg" alt="CN doc"></a>
<a href="README.md"><img src="https://img.shields.io/badge/document-English-blue.svg" alt="EN doc"></a>
<a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/badge/Code%20License-Apache_2.0-green.svg" alt="License: Apache 2.0"></a>
</p>

⭐️ 文档：https://chatsci.github.io/Aeiva/

## 仓库目标

Aeiva 的目标是打造一个以人为中心的、终身成长型 AI 伙伴，用来增强人的能力，而不是替代人。

它希望帮助人持续成长，放大人的能力与创造力，并把人的意图转化为真实行动。

在不同阶段与情境中，Aeiva 可以是：
- 你的导师、朋友、工作伙伴或可委托的代理
- 你的“第二化身”：一个不一样的你、另一种身份的你
- 你与世界之间的 gateway：连接你的目标、工具、知识与执行

我们的愿景是：让人在“人生这场 RPG 游戏”中获得酣畅淋漓、可持续的成长体验。

## 当前产品形态

Aeiva 正在演化为一个统一的 Agent 运行时，面向多个交互界面：

- terminal 聊天，用于本地直接使用
- web 对话界面，用于多模态交互
- 独立的 LifeRPG 仪表盘，用于结构化自我建模与成长追踪
- Slack 与 WhatsApp 网关，用于真实消息渠道

我们的目标不是堆叠彼此割裂的 demo，而是让同一套 agent 架构服务多个 channel，同时保持一致的人本核心。

在 web 侧，gateway 现在将 Dialogue 与 LifeRPG 拆成两个独立页面，以保持界面职责清晰：
- Dialogue UI：负责对话、工具使用、多模态交互
- LifeRPG UI：负责身份、角色、背包、项目与 TODO 面板

模型能力是可插拔的。不同后端模型可以提供不同组合的文本、视觉、音频、实时与工具使用能力，而不需要改变 Aeiva 的核心方向。

## 使用方法

### 1）安装

```bash
uv sync
```

安装全部可选能力（推荐本地开发）：

```bash
uv sync --all-extras
```

或按需安装单个扩展：

```bash
uv sync --extra realtime   # 实时语音/文本 UI
uv sync --extra slack      # Slack 网关
uv sync --extra media      # 媒体处理工具
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

这会启动统一 gateway。在当前默认 web 形态下，它会提供：
- 一个本地 Gradio Dialogue 页面
- 一个独立的本地 Gradio LifeRPG 页面

默认端口通常是：
- Dialogue UI：`http://127.0.0.1:7860`
- LifeRPG UI：`http://127.0.0.1:7862`

如果端口被占用，Gradio 会自动回退到附近端口；应以启动日志打印出的实际地址为准。

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

### 4）Browser 工具（网页自动化）

AEIVA 内置本地浏览器自动化工具，可用于真实网页任务：
- 跨站点搜索与导航
- 表单交互（输入/选择/点击/提交）
- 多步骤浏览流程与失败重试恢复
- 提取结构化页面结果用于助手回复

在 `action_config.tools` 中启用 `browser` 即可使用。

### 5）对话重放测试（真实多轮对话）

你可以把“真实对话场景”写成可重放脚本，直接对 AEIVA 运行时做自动验收，并输出机器可读报告。

```bash
aeiva-dialogue-replay \
  --config configs/agent_config.yaml \
  --scenarios docs/examples/dialogue_replay/dialogue_suite.yaml \
  --output-json .reports/dialogue-replay.json \
  --output-md .reports/dialogue-replay.md
```

常用参数：
- `--scenario-id <id>`（可重复）：只跑指定场景
- `--fail-fast`：场景内首个失败即停止
- `--route-token <token>`：指定回放路由（默认 `gradio`）

场景文件格式：
- `scenarios[]`：场景列表
- 每个场景包含 `id`、`description`、`turns[]`
- 每个 turn 支持 `user`、`timeout_seconds`、`expectation`
- `expectation` 支持内容与延迟断言：
  - `contains_all`、`contains_any`、`excludes`
  - `min_response_chars`、`max_latency_seconds`

### 6）通道说明

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
