# 剪辑等待/超时脚本门禁（Editor Timeout Automation）

目标：解决“剪辑师已开工后无后续回传”造成的流程悬置。

## 触发条件

当剪辑师按 5 行模板回传以下任一状态时触发自动化：
- `【状态】执行中`
- `【状态】进行中`
- `【@抓总】已开工，请稍候验收双轨交付...`

## 强制规则（先脚本，后兜底）

1. 进入 `EDITOR_WAITING` 子状态后，抓总**不得立即兜底**。
2. 必须先走两段式脚本化流程：
   - W1（首等窗口）= 120 秒
   - W2（提醒后窗口）= 180 秒
3. 仅当 W2 到期仍无“审片附件或主版链接”时，才允许进入 `FALLBACK_ALLOWED`。
4. 若期间收到实物交付（附件/可播放链接），立即转 `REVIEWING`，终止超时流程。

## 抓总消息模板（固定）

### 进入等待（收到“执行中”后立即发送）

```text
收到，已进入剪辑等待窗口（W1=120s）。
请在窗口内先回传审片附件；主版可随后补交。
```

### W1 到期提醒（仅一次）

```text
@剪辑师 提醒：W1 已到，请优先回传“审片附件”以解除等待；主版可后补。
现进入 W2=180s。
```

### W2 到期（允许兜底）

```text
W2 已到，仍未收到实物交付（附件/链接）。
按门禁切换兜底合成流程，由抓总接管并继续验收收口。
```

## 脚本化实现建议

在 skill 的 `scripts/` 中增加 `editor_wait_gate.py`（建议）：
- 输入：`run_id`、`channel_id`、`editor_message_id`、`w1_sec`、`w2_sec`
- 检查项：自 `editor_message_id` 之后是否出现以下任一信号：
  - 附件（mp4/mov）
  - 可播放链接（http(s) 且后缀或平台可识别）
- 输出状态：
  - `delivered`（已交付）
  - `w1_timeout`（触发一次提醒）
  - `w2_timeout`（允许兜底）

## 状态机并入点

在 `producer-state-machine.md` 增加：
- `EDITOR_WAITING`：剪辑执行中等待实物交付
- `FALLBACK_ALLOWED`：等待超时后允许抓总兜底

并增加转移：
- `DISPATCHING(editor) -> EDITOR_WAITING`（收到执行中）
- `EDITOR_WAITING -> REVIEWING`（收到附件/链接）
- `EDITOR_WAITING -> FALLBACK_ALLOWED`（W2 超时）
- `FALLBACK_ALLOWED -> DISPATCHING(producer-fallback)`（抓总兜底合成）

## 验收口径

- 只认“实物交付”：附件或可播放链接。
- 文本进度（执行中/稍候）不解除等待态。
- 达到 `FALLBACK_ALLOWED` 前，禁止抓总手动宣布兜底。