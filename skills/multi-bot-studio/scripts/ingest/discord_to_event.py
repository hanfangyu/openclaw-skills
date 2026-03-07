from __future__ import annotations
from typing import Dict

ROLE_MAP = {
    "1479043365684121651": "writer",
    "1479044195233562657": "director",
    "1479051077096833190": "vfx",
    "1479051272190693539": "editor",
}


def infer_role(sender_id: str) -> str | None:
    return ROLE_MAP.get(str(sender_id))


def message_to_event(message: Dict) -> Dict:
    sender_id = str(message.get("sender_id") or "")
    role = infer_role(sender_id)
    text = str(message.get("text") or message.get("message") or "")
    ts = int(message.get("ts") or message.get("timestamp") or 0)

    event = {
        "event_id": str(message.get("message_id") or ""),
        "type": "message",
        "role": role,
        "text": text,
        "ts": ts,
        "media_count": int(message.get("media_count") or 0),
    }

    if "ACK + 在线" in text and role:
        event["type"] = "role_ack"
    elif role:
        event["type"] = "role_update"
        if "已完成" in text:
            event["status"] = "已完成"
        elif "执行中" in text or "进行中" in text:
            event["status"] = "执行中"
        else:
            event["status"] = "更新"

    return event
