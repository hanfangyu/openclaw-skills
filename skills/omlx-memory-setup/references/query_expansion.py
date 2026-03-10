#!/usr/bin/env python3
"""
查询扩展工具 - 使用 oMLX 的 Qwen3.5-4B 扩展查询词
用法: python3 query_expansion.py "查询词"
"""

import httpx
import json
import sys
import re

OMLX_BASE = "http://localhost:8000"
API_KEY = "hfy19971023"
MODEL = "Qwen3.5-4B-4bit"

def expand_query(query: str, max_expansions: int = 5) -> list[str]:
    """使用 LLM 扩展查询词"""
    
    prompt = f"""扩展"{query}"为{max_expansions}个相关搜索词，JSON数组格式，如["网速慢","断网"]。直接输出JSON。"""

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{OMLX_BASE}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 800,
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                print(f"API 错误: {response.status_code}", file=sys.stderr)
                return [query]
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # 从输出中提取最后一个 JSON 数组
            # Qwen3 会先输出思考过程，最后输出 JSON
            json_arrays = re.findall(r'\[[\s\S]*?\]', content)
            
            if json_arrays:
                # 取最后一个 JSON 数组（通常是最终结果）
                for json_str in reversed(json_arrays):
                    try:
                        expansions = json.loads(json_str)
                        if isinstance(expansions, list) and len(expansions) > 0:
                            # 过滤并确保是中文
                            filtered = []
                            for item in expansions:
                                if isinstance(item, str):
                                    # 只保留中文部分
                                    chinese = "".join(re.findall(r"[\u4e00-\u9fff]+", item))
                                    if chinese and len(chinese) > 1:
                                        filtered.append(chinese)
                            
                            if filtered:
                                # 确保原始查询在列表中
                                if query not in filtered:
                                    filtered.insert(0, query)
                                return filtered[:max_expansions + 1]
                    except json.JSONDecodeError:
                        continue
            
            # 如果 JSON 解析失败，返回原始查询
            return [query]
            
    except Exception as e:
        print(f"扩展失败: {e}", file=sys.stderr)
        return [query]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 query_expansion.py '查询词'")
        sys.exit(1)
    
    query = sys.argv[1]
    expansions = expand_query(query)
    
    print(json.dumps(expansions, ensure_ascii=False, indent=2))