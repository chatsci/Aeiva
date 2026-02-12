# MetaUI Real-Usage Checklist and A2UI Status (2026-02-09)

## Scope
This checklist validates real dialog-driven usage of MetaUI in AEIVA, with focus on:
- visible-and-usable components
- AI-side UI definition and behavior wiring
- data model roundtrip quality
- multi-turn UI mutation reliability
- A2UI v0.10 alignment status

## Baseline
- Test suite baseline: `131 passed, 2 skipped` from `tests/metaui`.
- Transport mode: strict A2UI stream path (`createSurface`, `updateComponents`, `updateDataModel`, `deleteSurface`).

## Preconditions
1. `uv sync --all-extras`
2. `uv run aeiva-gateway -c configs/agent_config.yaml`
3. Start a fresh chat session.
4. Keep MetaUI desktop client open during test.

## Round-1 Manual Real-Dialog Checklist
Run these prompts in order. Each prompt is intended to be copied directly into chat.

| ID | Prompt | Expected Result | Pass Criteria |
|---|---|---|---|
| C01 | `给我一个聊天窗口：输入框+发送按钮+清空按钮+导出按钮` | Chat UI appears with all controls | All 4 controls visible and not disabled |
| C02 | `发送按钮要把输入内容追加到聊天列表` | Send action updates UI state | Input `hello` then click send, message appears in list |
| C03 | `清空按钮要清空消息列表` | Clear action works | Click clear, message list becomes empty |
| C04 | `导出按钮导出聊天记录为txt` | Export action works | Click export, local download starts |
| C05 | `把这个聊天界面改为深色主题` | Theme update applies | Background/text/button contrast changes correctly |
| C06 | `改成员工入职表单：姓名、邮箱、部门、入职日期、是否全职、提交` | Surface is replaced, not only title changed | Old chat widgets disappear, form widgets appear |
| C07 | `提交按钮点击后做校验：邮箱必须合法、姓名必填` | Validation surfaced from checks | Invalid input triggers visible error |
| C08 | `输入合法后提交，显示“已提交”` | Submit flow works | Valid data leads to success state/message |
| C09 | `给我一个Tab界面：基本信息/合同信息/审批` | Tabs render | 3 tabs visible |
| C10 | `切换tab时显示对应内容` | Tab change action works | Click each tab, body content changes |
| C11 | `加一个Modal：点击“查看协议”弹出内容` | Modal behavior works | Trigger opens modal, close works |
| C12 | `给我一个选择器：单选城市、多选技能、滑块薪资、日期时间选择` | Complex form renders | ChoicePicker/Slider/DateTimeInput all operable |
| C13 | `给我一个文件上传+解析进度+结果表格` | Upload flow renders | File dialog opens and upload event arrives |
| C14 | `上传后展示前20行表格` | Data display update works | Table or list area updates from uploaded data |
| C15 | `改成仪表盘：指标卡+折线图+柱状图+刷新按钮` | Dashboard UI replaces previous surface | New widgets appear, old form removed |
| C16 | `刷新按钮触发一次数据刷新并重绘图表` | Action and rerender both work | Clicking refresh changes chart data/timestamp |
| C17 | `把仪表盘切回聊天界面` | Multi-turn replacement remains stable | Surface replaced correctly again |
| C18 | `再改回员工表单` | Consecutive replace stable | No white screen, no stale components |
| C19 | `加一个按钮：打开官网 https://a2ui.org` | functionCall openUrl works | Clicking opens browser tab |
| C20 | `我现在输入什么你就回显什么` | AI receives action context/data model | User input appears in AI response content |
| C21 | `连续快速点击发送10次` | No freeze/crash | UI responsive, no blank page |
| C22 | `断开网络后再恢复` | Reconnect resilient | UI reconnects without permanent white screen |
| C23 | `生成一个只读预览界面（preview）` | interaction_mode respected | Non-interactive widgets do not pretend to submit |
| C24 | `删除当前界面` | Surface deletion works | UI disappears cleanly without stale artifacts |

## Round-2 Structural Assertions
Use these assertions while executing C01-C24.

1. No `Missing component: {...}` raw JSON should appear.
2. No white screen after `render_full` or `patch`.
3. Buttons with declared actions must produce observable effects.
4. Component replacement must change actual component tree, not title only.
5. Invalid checks must produce error events/messages, not silent ignore.
6. Uploaded file metadata must reach AI/tool pipeline.
7. UI should remain usable after repeated replace cycles.

## A2UI v0.10 Comparison (Current State)

### Strongly Aligned
1. Strict A2UI component namespace in catalog (`Text`, `Row`, `Column`, `List`, `Card`, `Modal`, `Button`, `TextField`, etc.).
2. Strict action shape for `Button.props.action`: exactly one of `event` or `functionCall`.
3. Lifecycle mapping to A2UI messages: `createSurface` + `updateComponents` + optional `updateDataModel`.
4. Client event envelope uses `version + action/error` shape.
5. No intent heuristics in MetaUI normalizer path.

### Partial Gaps (Needs Another Hardening Round)
1. Media property naming mismatch with A2UI standard catalog.
   - A2UI standard uses `url`.
   - Current desktop renderer path still reads `sourceUrl/src`.
2. `List` dynamic template semantics are incomplete in renderer.
   - A2UI `ChildList` supports object form `{componentId, path}`.
   - Renderer currently handles array children directly; object-template path is not fully rendered as repeated instances.
3. Function semantics are not fully equivalent to A2UI catalog definitions.
   - `numeric` currently checks parse-ability but does not enforce min/max constraints.
   - `formatNumber/formatCurrency/formatDate/pluralize/formatString` are simplified compared to standard catalog semantics.
4. Official A2UI eval suite is not yet wired as a mandatory regression gate in this repo.

## Evidence Pointers (Current Code)
- `src/aeiva/metaui/lifecycle_messages.py`
- `src/aeiva/metaui/spec_normalizer.py`
- `src/aeiva/metaui/a2ui_runtime.py`
- `src/aeiva/metaui/assets/desktop_template.html`
- `src/aeiva/metaui/component_catalog.py`
- A2UI references:
  - `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/server_to_client.json`
  - `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/client_to_server.json`
  - `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/common_types.json`
  - `/Users/bangliu/Downloads/A2UI-main/specification/v0_10/json/standard_catalog.json`

## Exit Criteria for Next Round
1. C01-C24 all pass in one continuous session.
2. Media components accept A2UI-native `url` end-to-end.
3. `List` template children `{componentId, path}` render correctly.
4. Function semantics for validation/formatting match A2UI catalog definitions.
5. A2UI official eval subset is automated in CI/local regression.
