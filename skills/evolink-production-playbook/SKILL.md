---
name: evolink-production-playbook
description: 品牌营销视频单技能流程（抓总+编剧+导演+视效+剪辑）与 Evolink 图/视/音编排规范。用于 OpenClaw 多 agent 映射、单线程派工、品牌DNA故事化创作、回传验收门禁、分段生成与失败降级。
---

# Evolink Production Playbook (Single-Skill)

本技能是唯一入口，不再拆多个技能。
所有角色流程都在本文件夹 `references/` 下按模块维护。

## 模块索引（同一技能内）

- 抓总调度：`references/producer-orchestrator.md`
- 抓总状态机：`references/producer-state-machine.md`
- REAL交付门禁：`references/real-delivery-gate.md`
- 统一回传协议：`references/handoff-protocol.md`
- 编剧模块：`references/writer-sop.md`
- 导演模块：`references/director-sop.md`
- 视效模块（Evolink）：`references/vfx-sop.md`
- 剪辑模块：`references/editor-sop.md`
- 全局编排模板：`references/production-template.yaml`
- 能力驱动提示词：`references/model-prompting-guide.md`

## 使用顺序

1. 先读取 `production-template.yaml` 确认目标、模型、分段。
2. 在写任何提示词前，先做**品牌DNA提炼**（关键词/禁忌词/视觉语法/叙事语气）。
3. 基于品牌DNA先写“一句话品牌故事母题”，再拆三幕（世界观/方法论/宣言）。
4. 抓总只按 `producer-orchestrator.md` 调度；默认不代替岗位产出，仅在授权规则下指定执行 bot。
5. 用户确认工作流后，按 skill 配置的机器人名单逐一点名 @ 发起 ACK（writer/director/vfx/editor），待全员回复后再进入第一棒。
6. 各岗位只读取自己的 SOP 模块，不串岗。
7. 全员必须遵守 `handoff-protocol.md` 回传格式与验收门禁；在 Discord 频道内默认启用抗截断短模板回传。
8. 多 bot 视频任务默认在**任务线程**中启动与推进，主频道只做分发、确认与总结。
9. 视频时长超过单模型能力时，按模板分段；失败仅单段重试。

## 多 Agent 映射（固定约定）

在 Discord 指挥频道内，**每个 bot 就是其映射 agent 的执行体**；抓总（main/producer）负责派工与验收。

- producer(bot) -> producer/main agent（主控调度）
- writer(bot) -> writer agent
- director(bot) -> director agent
- vfx(bot) -> vfx agent
- editor(bot) -> editor agent

## 模型预设切换（固定两套）

在 `references/production-template.yaml` 里维护两套预设：

1. `default_last_verified`（默认高质量）
   - 图像：`doubao-seedream-4.5`
   - 视频：`doubao-seedance-1.0-pro-fast`
   - 音乐：`suno-v4.5`

2. `low_cost_test`（低成本流程测试）
   - 图像：`z-image-turbo`
   - 视频：`doubao-seedance-1.0-pro-fast`
   - 音乐：`suno-v4`

## 切换口令约定

- 用户说“走上次默认模型” -> 使用 `default_last_verified`
- 用户说“便宜模型跑流程测试” -> 使用 `low_cost_test`

如项目要求变化，只改 `production-template.yaml` 的 `model_presets` / `model_registry`。
