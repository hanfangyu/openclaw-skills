from __future__ import annotations
from typing import Dict, List


def to_message_tool_payloads(items: List[Dict]) -> List[Dict]:
    payloads: List[Dict] = []
    for row in items:
        payloads.append({
            "action": "send",
            "channel": row.get("channel", "discord"),
            "target": row.get("target"),
            "message": row.get("message", ""),
        })
    return payloads
