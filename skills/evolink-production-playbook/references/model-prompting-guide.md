# Evolink 模型能力驱动提示词指南（Capability-Driven Prompting）

本指南要求：提示词与参数必须基于模型能力文档，不做超能力请求。

新增硬规则：提示词清洁。
- 禁止把分段编号、时间片标签、流程控制词写入提示词（如 `S5`、`26-30s`、`final lock`）。
- 避免任何可能被模型直接渲染为文字的元信息；只写镜头语义、动作、风格与约束。

新增硬规则：先品牌、后提示词。
- 先做品牌DNA提炼（关键词、禁忌词、视觉语法、叙事语气）
- 先写品牌故事母题与三幕结构
- 再把三幕映射为分段提示词
- 禁止直接复用“通用科技模板”覆盖品牌个性

参考来源（本地）：
- `../../evolink-video/references/video-api-params.md`
- `../../evolink-image/references/image-api-params.md`
- `../../evolink-music/references/music-api-params.md`

---

## 1) 视频（generate_video）

### 支持参数（通用）
- `prompt`
- `model`
- `duration`
- `quality`
- `aspect_ratio`
- `image_urls`（1张=i2v，2张=首尾帧仅部分模型支持）
- `generate_audio`（仅特定模型）

### 提示词模板（t2v）

```text
[Scene Goal]
30-second brand promo, segment {s01}, duration {5s}.

[Subject]
{主角/产品/品牌元素，固定锚点}

[Action]
{该段唯一核心动作，不超过2个动作}

[Camera]
{镜头类型 + 运动强度 + 节奏点}

[Style]
futuristic, clean tech, high contrast, cyan/deep-blue palette, consistent HUD motif

[Constraints]
stable shot, subject consistency, readable foreground, no chaotic motion, no style drift
```

### 提示词模板（i2v）

```text
Animate the provided reference image while preserving subject identity and outfit.
Keep camera motion low-to-medium, maintain composition stability.
Target: {duration}s, {aspect_ratio}, {quality}.
Style: futuristic clean-tech, cyan/deep-blue, subtle HUD overlays.
Avoid: identity drift, excessive shake, cluttered foreground.
```

### 参数护栏
- 先校验模型是否支持目标时长与质量；不支持则分段/降级。
- 分段节奏必须由脚本驱动：先由编剧+导演给出分段表，再将每段时长映射到 `duration` 参数生成对应视频段。
- 若需首尾帧，先确认模型支持双图模式；否则改为单图i2v+剪辑衔接。

---

## 2) 图像（generate_image）

### 支持参数（通用）
- `prompt`
- `model`
- `size`
- `n`
- `image_urls`（i2i/edit）
- `mask_url`（仅特定模型）

### 提示词模板（t2i）

```text
Create a keyframe for segment {sXX} of a futuristic brand film.
Subject: {固定角色/产品锚点}
Composition: {中轴 or 三分法}, leave safe area for subtitle/HUD.
Color: electric cyan + deep blue, amber only for alert accents.
Lighting: rim light + controlled glow, avoid overexposure.
Output intent: consistent with previous keyframes.
```

### 提示词模板（i2i/edit）

```text
Edit the provided image while preserving identity and core composition.
Apply clean-tech visual upgrade: subtle HUD, refined lighting, controlled contrast.
Do not change: {发型/服饰主色/产品外观等禁止变化项}.
```

### 参数护栏
- `mask_url` 仅在支持模型使用。
- `n` 控制在 1-4，品牌片建议 2 起步用于择优。
- 大比例图先验证模型尺寸格式（比率制 or 像素制）。

---

## 3) 音乐（generate_music）

### 支持参数（核心）
- `prompt`
- `model`
- `custom_mode`（必填）
- `instrumental`（必填）
- `style` / `title`（custom_mode=true时要求）
- `duration`

### 提示词模板（simple mode）

```text
Futuristic corporate promo background music, 30s.
Mood: confident, precise, forward-driving.
Structure: hook(0-3s), build(3-24s), brand resolve(24-30s).
No vocals.
```

### 提示词模板（custom mode）

```text
[Verse]
...（可选）

[Chorus]
...（可选）
```
并配：
- `style`: `electronic, cinematic, clean, 120bpm`
- `title`: `Brand Future Pulse`
- `instrumental`: `true/false`

### 参数护栏
- `custom_mode` 与 `instrumental` 必须显式传递。
- 时长超模型上限时，拆分生成并在剪辑层拼接。

---

## 4) 失败回退（统一）

1. 参数错误：按模型能力文档纠正后重试。
2. 资源/超时：单段重试（最多2次）-> 切 fallback 模型。
3. 连续失败：降低复杂度（时长、运动、质量）并保留风格锚点。
