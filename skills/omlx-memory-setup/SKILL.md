---
name: omlx-memory-setup
description: Configure OpenClaw memory search with oMLX local embedding models on Apple Silicon. Use when setting up memory search, configuring embedding providers, installing oMLX, or troubleshooting memory search issues. Triggers on phrases like "memory search setup", "local embedding", "oMLX configuration", "memory plugin install".
---

# oMLX Memory Search Setup

Configure OpenClaw memory search with local embedding models via oMLX on Apple Silicon Macs.

## Quick Start

1. Install oMLX: `brew install --cask omlx`
2. Download embedding model via oMLX Web UI (http://localhost:8000/admin)
3. Configure OpenClaw to use oMLX embedding
4. Enable hybrid search with MMR ranking

## Prerequisites

- Apple Silicon Mac (M1/M2/M3/M4)
- macOS 12.0 or later
- 8GB+ RAM (16GB recommended for 4B models)
- OpenClaw 2026.3.0+

## Installation Steps

### Step 1: Install oMLX

```bash
# Download from GitHub
curl -L -o ~/Downloads/oMLX.dmg \
  https://github.com/jundot/omlx/releases/latest/download/oMLX.dmg

# Mount and install
hdiutil attach ~/Downloads/oMLX.dmg
cp -R /Volumes/oMLX/oMLX.app /Applications/
hdiutil detach /Volumes/oMLX

# Launch oMLX
open -a oMLX
```

### Step 2: Configure oMLX

Edit `~/.omlx/settings.json`:

```json
{
  "host": "127.0.0.1",
  "port": 8000,
  "api_key": "your-api-key",
  "model_dir": "~/.omlx/models",
  "max_model_memory": "10GB",
  "start_server_on_launch": true
}
```

### Step 3: Download Embedding Model

Via oMLX Web UI (http://localhost:8000/admin):
1. Login with your API key
2. Go to Models → Download
3. Search for `Qwen3-Embedding-4B` (recommended for Chinese)
4. Click Download

Or via CLI:
```bash
# Using huggingface-cli
pip install huggingface_hub
huggingface-cli download Qwen/Qwen3-Embedding-4B \
  --local-dir ~/.omlx/models/Qwen3-Embedding-4B
```

### Step 4: Configure OpenClaw

Edit OpenClaw config (usually `~/.openclaw/gateway.json5`):

```json5
agents: {
  defaults: {
    memorySearch: {
      provider: "openai",
      model: "Qwen3-Embedding-4B",
      remote: {
        baseUrl: "http://localhost:8000/v1",
        apiKey: "your-omlx-api-key"
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

Then restart Gateway:
```bash
openclaw gateway restart
```

## Model Selection Guide

| Model | Size | Memory | Chinese Support | Recommended For |
|-------|------|--------|-----------------|-----------------|
| Qwen3-Embedding-4B | 4B | ~8GB | ⭐⭐⭐⭐⭐ | Chinese-heavy use |
| Qwen3-Embedding-0.6B | 0.6B | ~1.5GB | ⭐⭐⭐⭐ | Memory-constrained |
| BGE-M3 | 1.2B | ~2.2GB | ⭐⭐⭐⭐⭐ | Multilingual |

## Query Expansion (Optional)

For better search recall, use the included query expansion script:

```bash
# Expand query using local LLM
python3 scripts/query_expansion.py "网络问题"
# Output: ["网络问题", "网速慢", "断网", "网络延迟高", ...]
```

Requires a chat model (e.g., Qwen3.5-4B) installed in oMLX.

## Troubleshooting

### oMLX service not starting

```bash
# Check if port is in use
lsof -i :8000

# Check oMLX logs
log show --predicate 'process == "oMLX"' --last 5m

# Restart oMLX
killall oMLX && open -a oMLX
```

### Model loading failed (memory)

If you see "Not enough memory to load model":
1. Increase `max_model_memory` in `~/.omlx/settings.json`
2. Or use a smaller model (Qwen3-Embedding-0.6B)
3. Close other memory-intensive apps

### Embedding API errors

```bash
# Test oMLX embedding endpoint
curl http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"input": "test", "model": "Qwen3-Embedding-4B"}'
```

## Files

- `scripts/query_expansion.py` - Query expansion using local LLM
- `references/config-examples.md` - Additional configuration examples