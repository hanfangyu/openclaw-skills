---
name: evolink-production-playbook
description: 统一编排 Evolink 图像/视频/音乐生产流程（30s/15s品牌短片）。用于多模型能力不一致（时长、参数、模态）时的任务拆解、路由选模、分段生成、降级重试与团队交付回传规范；尤其适用于编剧/导演/视效/剪辑协作流水线。
---

# Evolink Production Playbook

按以下顺序执行：

1. 读取 `references/production-template.yaml` 作为主编排模板。
2. 根据当前可用模型，填充 `model_registry` 的 primary/fallback。
3. 若视频目标时长超出单模型上限，启用 `segmentation` 自动分段。
4. 统一使用 `collaboration_protocol` 的回传格式，禁止跳过验收。
5. 如任一段失败，先按 `failure_policy` 单段重试，避免全片重跑。

## 交付要求

- 默认输出：30s 主版 + 15s 切片 + 关键帧 + BGM。
- 默认验收：3秒钩子、10秒价值清晰、品牌露出≥2次。
- 默认导出：16:9 1080p（可按项目覆盖）。

## 角色执行

按角色读取并遵循：
- 编剧：`references/writer-sop.md`
- 导演：`references/director-sop.md`
- 视效师：`references/vfx-sop.md`
- 剪辑师：`references/editor-sop.md`

若角色未明确，默认使用主模板中的 `collaboration_protocol` 与 `pipeline` 结构执行。
