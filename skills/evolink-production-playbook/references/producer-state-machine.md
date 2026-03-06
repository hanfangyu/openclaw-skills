# 抓总状态机（Producer State Machine）

用于单线程派工稳定推进，避免并行、漏验收、跳棒。

## 状态定义

- `IDLE`：待命
- `PLANNING`：已接单，正在输出总计划
- `DISPATCHING`：已派当前棒次，等待岗位交付
- `REVIEWING`：收到交付，验收中
- `REVISING`：已打回，等待同岗位修订
- `ADVANCING`：验收通过，切换下一棒
- `DONE`：全部岗位完成
- `BLOCKED`：异常中止（需人类决策）

## 转移规则

1. `IDLE -> PLANNING`：收到开工指令
2. `PLANNING -> DISPATCHING`：发布总计划+第1棒任务卡
3. `DISPATCHING -> REVIEWING`：收到标准回传（必须@抓总）
4. `REVIEWING -> ADVANCING`：验收通过
5. `REVIEWING -> REVISING`：打回修改
6. `REVISING -> REVIEWING`：同岗位提交新版本
7. `ADVANCING -> DISPATCHING`：发布下一棒任务卡
8. `ADVANCING -> DONE`：最后一棒通过
9. 任意状态 -> `BLOCKED`：连续2次打回仍不通过或输入冲突

## 门禁条件

- 当前状态不是 `ADVANCING` 时，禁止派下一棒。
- 当前状态不是 `REVIEWING` 时，禁止发“验收通过/打回修改”。
- 非当前岗位交付，直接忽略并提醒“等待被派工”。

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
