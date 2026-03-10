# Configuration Examples

## Basic oMLX Setup

Minimal configuration for oMLX with embedding model:

```json5
// ~/.omlx/settings.json
{
  "host": "127.0.0.1",
  "port": 8000,
  "api_key": "local-key",
  "model_dir": "~/.omlx/models",
  "max_model_memory": "8GB",
  "start_server_on_launch": true
}
```

## OpenClaw Memory Search Configurations

### Basic Hybrid Search

```json5
agents: {
  defaults: {
    memorySearch: {
      provider: "openai",
      model: "Qwen3-Embedding-4B",
      remote: {
        baseUrl: "http://localhost:8000/v1",
        apiKey: "local-key"
      }
    }
  }
}
```

### Full Ranking Configuration

```json5
agents: {
  defaults: {
    memorySearch: {
      provider: "openai",
      model: "Qwen3-Embedding-4B",
      remote: {
        baseUrl: "http://localhost:8000/v1",
        apiKey: "local-key"
      },
      query: {
        hybrid: {
          enabled: true,
          vectorWeight: 0.7,
          textWeight: 0.3,
          mmr: {
            enabled: true,
            lambda: 0.7
          },
          temporalDecay: {
            enabled: true,
            halfLifeDays: 30
          }
        }
      }
    }
  }
}
```

### Memory-Constrained Setup (8GB RAM)

For Macs with limited memory:

```json5
// Use smaller embedding model
agents: {
  defaults: {
    memorySearch: {
      provider: "openai",
      model: "Qwen3-Embedding-0.6B",
      remote: {
        baseUrl: "http://localhost:8000/v1",
        apiKey: "local-key"
      }
    }
  }
}

// oMLX settings
{
  "max_model_memory": "4GB"
}
```

## Query Expansion Setup

### Install Chat Model for Query Expansion

```bash
# Via oMLX Web UI: download Qwen3.5-4B-4bit
# Or via CLI:
huggingface-cli download mlx-community/Qwen3.5-4B-4bit-DWQ \
  --local-dir ~/.omlx/models/Qwen3.5-4B-4bit
```

### Use Query Expansion Script

```bash
# Basic usage
python3 scripts/query_expansion.py "搜索关键词"

# Example output for "网络问题":
# ["网络问题", "网速慢", "断网", "网络延迟高", "Wi-Fi 连接失败", "路由器故障"]
```

## Memory Search API Test

```bash
# Test embedding endpoint
curl http://localhost:8000/v1/embeddings \
  -H "Authorization: Bearer local-key" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "测试文本",
    "model": "Qwen3-Embedding-4B"
  }'

# Expected response:
# {
#   "object": "list",
#   "data": [{
#     "object": "embedding",
#     "embedding": [0.123, -0.456, ...],
#     "index": 0
#   }],
#   "model": "Qwen3-Embedding-4B",
#   "usage": { "prompt_tokens": 4, "total_tokens": 4 }
# }
```

## Model Comparison

| Model | Parameters | Disk Size | RAM Usage | Max Length | Chinese Score |
|-------|------------|-----------|-----------|------------|---------------|
| Qwen3-Embedding-4B | 4B | ~8GB | ~8.5GB | 32768 | 95% |
| Qwen3-Embedding-0.6B | 0.6B | ~1.2GB | ~1.5GB | 32768 | 85% |
| BGE-M3 | 1.2B | ~2.2GB | ~2.5GB | 8192 | 90% |
| bge-small-en | 0.03B | ~0.1GB | ~0.5GB | 512 | 30% |

## Memory Estimation

For 16GB Mac:
- System reserved: ~3GB
- oMLX overhead: ~1GB
- Qwen3-Embedding-4B: ~8GB
- Qwen3.5-4B-4bit (query expansion): ~2.5GB
- **Total: ~14.5GB** ✓ Fits

For 8GB Mac:
- System reserved: ~2GB
- oMLX overhead: ~0.5GB
- Qwen3-Embedding-0.6B: ~1.5GB
- **Total: ~4GB** ✓ Fits with room