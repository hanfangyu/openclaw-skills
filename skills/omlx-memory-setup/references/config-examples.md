# oMLX 记忆配置示例

## 完整 OpenClaw 配置

```json5
// ~/.openclaw/openclaw.json
{
  agents: {
    defaults: {
      memorySearch: {
        // 嵌入提供商配置
        provider: "openai",
        model: "Qwen3-Embedding-4B",
        remote: {
          baseUrl: "http://localhost:8000/v1",
          apiKey: "YOUR_OMLX_API_KEY"  // 替换为你的 oMLX API key
        },
        
        // 搜索配置
        query: {
          maxResults: 10,
          minScore: 0.3,
          hybrid: {
            enabled: true,
            vectorWeight: 0.7,
            textWeight: 0.3,
            mmr: {
              enabled: true,
              lambda: 0.7  // 0-1, 越大越精确，越小越多样
            },
            temporalDecay: {
              enabled: true,
              halfLifeDays: 30  // 半衰期，天数
            }
          }
        }
      }
    }
  },
  
  // Gateway 配置（可选）
  gateway: {
    port: 3000
  }
}
```

## oMLX 配置

oMLX 配置文件位于 `~/.omlx/config.json`：

```json
{
  "api_key": "YOUR_API_KEY",
  "port": 8000,
  "model_path": "~/.omlx/models",
  "max_model_memory": "10GB",
  "start_server_on_launch": true
}
```

### 内存配置

根据你的 Mac 内存调整：

| 系统内存 | max_model_memory | 推荐模型 |
|----------|-----------------|----------|
| 8GB | 5GB | Qwen3-Embedding-0.6B |
| 16GB | 10GB | Qwen3-Embedding-4B |
| 32GB+ | 20GB | 可同时运行嵌入+聊天模型 |

## QMD 后端配置（备选）

如果偏好完全离线的 QMD 后端：

```json5
memory: {
  backend: "qmd",
  citations: "auto",
  qmd: {
    includeDefaultMemory: true,
    update: { interval: "5m" },
    paths: [
      { name: "notes", path: "~/notes", pattern: "**/*.md" }
    ]
  }
}
```

注意：QMD 后端使用自带的嵌入模型，不会使用 oMLX 配置的模型。

## 查询扩展示例

### 环境变量配置

```bash
# 在 ~/.zshrc 或 ~/.bashrc 中添加
export OMLX_API_KEY="YOUR_OMLX_API_KEY"
export OMLX_BASE_URL="http://localhost:8000/v1"
```

### 脚本调用

```bash
# 基本用法
python3 ~/.openclaw/workspace/scripts/query_expansion.py "网络问题"

# 输出示例
# ["网络问题", "网速慢", "断网", "网络延迟高", "Wi-Fi 连接失败", "路由器故障"]

# 集成到其他脚本
EXPANDED=$(python3 ~/.openclaw/workspace/scripts/query_expansion.py "查询词")
echo "$EXPANDED" | jq -r '.[]'
```

### API 集成

```python
import requests
import json

def expand_query(query: str, api_key: str) -> list[str]:
    """调用 oMLX 扩展查询词"""
    response = requests.post(
        "http://localhost:8000/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "Qwen3.5-4B-4bit",
            "messages": [
                {"role": "user", "content": f"扩展查询词: {query}"}
            ],
            "temperature": 0.3,
            "max_tokens": 100
        }
    )
    # 解析返回的扩展词
    return json.loads(response.json()["choices"][0]["message"]["content"])
```

## 故障排除配置

### 启用详细日志

```json5
logging: {
  level: "debug",
  memory: true
}
```

### 测试嵌入连接

```bash
# 测试 oMLX 嵌入接口
curl -v -X POST "http://localhost:8000/v1/embeddings" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen3-Embedding-4B", "input": "测试"}'
```

### 重置记忆索引

```bash
# 删除记忆数据库，重建索引
rm ~/.openclaw/data/memory.db
openclaw gateway restart
```