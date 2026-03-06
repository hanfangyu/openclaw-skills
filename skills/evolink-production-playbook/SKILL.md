---
name: evolink-production-playbook
description: 单技能一体化的 Discord 多机器人协作流程（抓总+编剧+导演+视效+剪辑）与 Evolink 图/视/音编排规范。用于 OpenClaw 多 agent 映射、单线程派工、回传验收门禁、分段生成与失败降级。
---

# Evolink Production Playbook (Single-Skill)

本技能是唯一入口，不再拆多个技能。
所有角色流程都在本文件夹 `references/` 下按模块维护。

## 模块索引（同一技能内）

- 抓总调度：`references/producer-orchestrator.md`
- 抓总状态机：`references/producer-state-machine.md`
- 统一回传协议：`references/handoff-protocol.md`
- 编剧模块：`references/writer-sop.md`
- 导演模块：`references/director-sop.md`
- 视效模块（Evolink）：`references/vfx-sop.md`
- 剪辑模块：`references/editor-sop.md`
- 全局编排模板：`references/production-template.yaml`
- 能力驱动提示词：`references/model-prompting-guide.md`

## 使用顺序

1. 先读取 `production-template.yaml` 确认目标、模型、分段。
2. 抓总只按 `producer-orchestrator.md` 调度，不代替岗位产出。
3. 各岗位只读取自己的 SOP 模块，不串岗。
4. 全员必须遵守 `handoff-protocol.md` 回传格式与验收门禁。
5. 视频时长超过单模型能力时，按模板分段；失败仅单段重试。

## 多 Agent 映射（固定约定）

- producer(bot) -> producer/main agent
- writer(bot) -> writer agent
- director(bot) -> director agent
- vfx(bot) -> vfx agent
- editor(bot) -> editor agent

## Evolink 当前优先模型（可覆盖）

- 图像：`doubao-seedream-4.5`
- 视频：`doubao-seedance-1.0-pro-fast`
- 音乐：`suno-v4.5`

如项目要求变化，只改 `production-template.yaml` 的 `model_registry`。
