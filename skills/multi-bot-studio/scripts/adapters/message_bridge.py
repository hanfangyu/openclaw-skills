from __future__ import annotations
from typing import Dict, List


def to_message_tool_payloads(items: List[Dict]) -> List[Dict]:
    payloads: List[Dict] = []
    for row in items:
        message = row.get("message", "")
        p = {
            "action": "send",
            "channel": row.get("channel", "discord"),
            "target": row.get("target"),
            "message": message,
        }
        # URL-only message -> use media for richer visualization where channel supports it (e.g., Discord)
        if isinstance(message, str) and (message.startswith("http://") or message.startswith("https://")):
            p["media"] = message
            p["message"] = ""
        payloads.append(p)
    return payloads
