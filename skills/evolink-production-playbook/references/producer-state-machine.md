# 抓总状态机（Producer State Machine）

用于单线程派工稳定推进，避免并行、漏验收、跳棒。

## 状态定义

- `IDLE`：待命
- `ACK_WAIT`：已确认走工作流，等待全员在线 ACK（ACK 回执需 @抓总）
- `PLANNING`：已接单，正在输出总计划
- `DISPATCHING`：已派当前棒次，等待岗位交付
- `REVIEWING`：收到交付，验收中
- `REVISING`：已打回，等待同岗位修订
- `ADVANCING`：验收通过，切换下一棒
- `DONE`：全部岗位完成
- `BLOCKED`：异常中止（需人类决策）

## 转移规则

1. `IDLE -> ACK_WAIT`：用户确认执行标准工作流（确认前禁止 @ 执行机器人）
2. `ACK_WAIT -> PLANNING`：全员 ACK 完成
3. `PLANNING -> DISPATCHING`：发布总计划+第1棒任务卡
4. `DISPATCHING -> REVIEWING`：收到标准回传（必须@抓总）
5. `REVIEWING -> ADVANCING`：验收通过
6. `REVIEWING -> REVISING`：打回修改
7. `REVISING -> REVIEWING`：同岗位提交新版本
8. `ADVANCING -> DISPATCHING`：发布下一棒任务卡
9. `ADVANCING -> DONE`：最后一棒通过
10. 任意状态 -> `BLOCKED`：连续2次打回仍不通过或输入冲突

## 门禁条件

- 当前状态不是 `ADVANCING` 时，禁止派下一棒。
- 当前状态不是 `REVIEWING` 时，禁止发“验收通过/打回修改”。
- `ACK_WAIT` 未完成时，禁止发布第1棒任务卡。
- 非当前岗位交付，直接忽略并提醒“等待被派工”。
- ACK 或执行回传若出现除 `@抓总` 外的额外 @，判定为格式不合规并要求按规范重发。
- 分镜图未通过（含图像清洁度不通过）时，禁止进入视频生成。
- 未产出并通过三类素材（分镜图/分段视频/音乐）时，禁止宣布“可剪辑/可成片”。
- 未拿到剪辑输出（30s主版URL + 15s切片URL）时，禁止宣布“REAL流程完成”。

## 最小状态记录模板

```yaml
run_id: brand_20260306_001
state: DISPATCHING
current_role: director
current_task: 导演可拍版
version_expected: v1
attempts_current_role: 1
accepted_roles:
  - writer
pending_roles:
  - director
  - vfx
  - editor
last_update: 2026-03-06T14:20:00+08:00
```

## 抓总输出模板

- 派工：`<@role> 第N棒任务卡：... 完成后按标准格式@我回传。`
- 通过：`<@role> 验收通过｜版本：vX｜准备下一棒。`
- 打回：`<@role> 打回修改｜版本：vX｜修改点：1)...2)...`
- 阻塞：`流程已阻塞，需人类确认：<冲突摘要>`
