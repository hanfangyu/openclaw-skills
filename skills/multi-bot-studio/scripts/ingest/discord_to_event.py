from __future__ import annotations
import re
from typing import Dict

ROLE_MAP = {
    "1479043365684121651": "writer",
    "1479044195233562657": "director",
    "1479051077096833190": "vfx",
    "1479051272190693539": "editor",
}

ANCHOR_SELECT_RE = re.compile(r"(主锚点|选择|选定).*(01|02|03|1|2|3)", re.I)

CONTROL_WORDS = (
    "统计 ACK",
    "统一统计",
    "派工",
    "开第1棒",
    "开第一棒",
    "我来统计",
    "我再开",
)


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
        "sender_id": sender_id,
    }

    # 用户在锚点阶段手动选择编号 -> 直接转 gate 事件
    if not role and ANCHOR_SELECT_RE.search(text):
        m = re.search(r"(01|02|03|1|2|3)", text)
        anchor = m.group(1) if m else ""
        if anchor in ("1", "2", "3"):
            anchor = f"0{anchor}"
        event["type"] = "anchor_selected"
        event["payload"] = {"pass": True, "anchor_id": anchor}
        return event

    # Non-producer role talking about ACK counting/dispatch is a role-boundary violation.
    if role and any(w in text for w in CONTROL_WORDS):
        event["type"] = "role_violation"
        event["status"] = "越权"
        return event

    if role and (
        "ACK + 在线" in text
        or "【状态】已收到" in text
        or "状态】已收到" in text
        or "已收到" in text
        or text.strip().startswith("收到")
    ):
        event["type"] = "role_ack"
    elif role:
        event["type"] = "role_update"
        if "已完成" in text:
            event["status"] = "已完成"
            # 文案/导演/视效的主要交付为文本，标记为可验收交付。
            if role in ("writer", "director", "vfx"):
                event["has_delivery"] = True
        elif "执行中" in text or "进行中" in text or "审核中" in text:
            event["status"] = "执行中"
        else:
            event["status"] = "更新"

    return event
