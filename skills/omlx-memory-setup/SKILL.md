---
name: omlx-memory-setup
description: 本地记忆嵌入插件安装，使用 oMLX + Qwen3-Embedding 实现完全本地的语义记忆搜索
author: hanfangyu
version: 1.0.0
tags: [memory, embedding, omlx, local, qwen]
triggers:
  - "配置记忆嵌入"
  - "本地嵌入"
  - "oMLX 安装"
  - "oMLX 配置"
  - "记忆搜索设置"
  - "记忆插件安装"
  - "Qwen 嵌入模型"
requirements:
  - macOS (Apple Silicon)
  - 16GB+ 内存（推荐）
  - Homebrew
---

# omlx-memory-setup

本地记忆嵌入插件安装指南，使用 oMLX + Qwen3-Embedding 实现完全本地的语义记忆搜索。

## 描述

帮助用户在 Apple Silicon Mac 上配置 OpenClaw 的本地记忆嵌入系统，实现：
- 完全本地的嵌入推理（无需 API 调用）
- 支持 Qwen3-Embedding-4B 等高质量中文嵌入模型
- 混合搜索（BM25 + 向量）
- MMR 重排序 + 时间衰减
- 可选的查询扩展功能

## 触发词

- "配置记忆嵌入"、"本地嵌入"
- "oMLX 安装"、"oMLX 配置"
- "记忆搜索设置"、"记忆插件安装"
- "Qwen 嵌入模型"

## 前置条件

- macOS (Apple Silicon)
- 16GB+ 内存（推荐）
- Homebrew

## 安装步骤

### 1. 安装 oMLX

```bash
# 方式 A: Homebrew
brew install jundot/omlx/omlx

# 方式 B: 手动下载 DMG
# https://github.com/jundot/omlx/releases
```

### 2. 下载嵌入模型

通过 oMLX Web UI 或 API 下载模型：

**推荐模型：**
- `Qwen3-Embedding-4B` — 中文最佳，约 8GB 内存
- `Qwen3-Embedding-0.6B` — 轻量版，约 1.5GB 内存

```bash
# API 方式下载
curl -X POST "http://localhost:8000/admin/download" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen3-Embedding-4B"}'
```

### 3. 配置 OpenClaw

编辑 `~/.openclaw/openclaw.json`：

```json5
agents: {
  defaults: {
    memorySearch: {
      provider: "openai",
      model: "Qwen3-Embedding-4B",
      remote: {
        baseUrl: "http://localhost:8000/v1",
        apiKey: "YOUR_OMLX_API_KEY"
      },
      query: {
        hybrid: {
          enabled: true,
          vectorWeight: 0.7,
          textWeight: 0.3,
          mmr: { enabled: true, lambda: 0.7 },
          temporalDecay: { enabled: true, halfLifeDays: 30 }
        }
      }
    }
  }
}
```

### 4. 重启 Gateway

```bash
openclaw gateway restart
```

### 5. 验证安装

```bash
# 测试嵌入
curl -X POST "http://localhost:8000/v1/embeddings" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen3-Embedding-4B", "input": "测试文本"}'
```

## 可选：查询扩展

如果需要查询扩展功能，需要额外下载聊天模型：

```bash
# 下载轻量聊天模型
curl -X POST "http://localhost:8000/admin/download" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen3.5-4B-4bit"}'
```

使用查询扩展脚本：

```bash
python3 references/query_expansion.py "网络问题"
# 输出: ["网络问题", "网速慢", "断网", "网络延迟高", ...]
```

## 常见问题

### 内存不足

如果遇到 "Insufficient memory" 错误：

1. 打开 oMLX 应用 → Settings
2. 调整 "Max Model Memory" 到 10-12GB
3. 重启 oMLX 服务

### 服务未启动

```bash
# 检查服务状态
curl http://localhost:8000/health

# 通过应用启动
open -a oMLX
```

### 模型加载失败

确保模型格式兼容：
- MLX 格式模型优先
- PyTorch 格式需要转换

## 资源文件

- `references/config-examples.md` — 完整配置示例
- `references/query_expansion.py` — 查询扩展脚本

## 相关链接

- [oMLX GitHub](https://github.com/jundot/omlx)
- [OpenClaw 记忆文档](https://docs.openclaw.ai/features/memory)
- [Qwen3 Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-4B)