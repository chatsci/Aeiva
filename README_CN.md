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
uv sync --extra metaui     # 桌面 MetaUI 运行时
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

### 4）Browser 工具（网页自动化）

AEIVA 内置本地浏览器自动化工具，可用于真实网页任务：
- 跨站点搜索与导航
- 表单交互（输入/选择/点击/提交）
- 多步骤浏览流程与失败重试恢复
- 提取结构化页面结果用于助手回复

在 `action_config.tools` 中启用 `browser` 即可使用。

### 5）MetaUI（桌面 UI）

MetaUI 支持助手在本地桌面打开/更新结构化界面（表单、上传、表格、图表、进度面板）。

```bash
aeiva-metaui-desktop --ws-url ws://127.0.0.1:8765/metaui
```

`metaui` 工具已可在 `action_config.tools` 中使用。
默认情况下 `aeiva-gateway` 不会在启动时立即拉起 MetaUI 窗口；当助手实际调用 `metaui` 且 `ensure_visible=true` 时才按需启动。

MetaUI 主路径是“纯渲染层”：
- UI 结构定义由 AI 端显式给出（`components`、`root`、`actions`、`state_bindings`）。
- MetaUI 负责校验、渲染与交互/文件事件回传。
- 建议使用 `metaui.catalog` + `metaui.render_full(spec=...)` + `metaui.patch/set_state` 形成确定性流程。

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
