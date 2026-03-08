from __future__ import annotations
import re
from typing import Dict

ROLE_MAP = {
    "1479001609127067720": "producer",
    "1479043365684121651": "writer",
    "1479044195233562657": "director",
    "1479051077096833190": "vfx",
    "1479051272190693539": "editor",
}

ROLE_TEXT_HINTS = [
    ("producer", re.compile(r"(【角色】\s*抓总|我是抓总|producer)", re.I)),
    ("writer", re.compile(r"(【角色】\s*编剧|我是编剧|\bwriter\b)", re.I)),
    ("director", re.compile(r"(【角色】\s*导演|我是导演|\bdirector\b)", re.I)),
    ("vfx", re.compile(r"(【角色】\s*视效师|我是视效师|\bvfx\b)", re.I)),
    ("editor", re.compile(r"(【角色】\s*剪辑师|我是剪辑师|\beditor\b)", re.I)),
]

ANCHOR_SELECT_RE = re.compile(r"(主锚点|选择|选定).*(01|02|03|1|2|3)", re.I)
STORYBOARD_CONFIRM_RE = re.compile(r"(分镜|storyboard).*(确认|通过|ok|没问题)", re.I)
PROMPT_APPROVE_RE = re.compile(r"(提示词包|prompt\s*pack|prompt).*(通过|确认|approved|放行)", re.I)

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


def infer_role_from_text(text: str) -> str | None:
    t = text or ""
    for role, pat in ROLE_TEXT_HINTS:
        if pat.search(t):
            return role
    return None


def message_to_event(message: Dict) -> Dict:
    sender_id = str(message.get("sender_id") or "")
    text = str(message.get("text") or message.get("message") or "")
    role = infer_role(sender_id) or infer_role_from_text(text)
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

    # 用户在关键门禁阶段的自然语言确认 -> 直接转 gate 事件
    if not role:
        if ANCHOR_SELECT_RE.search(text):
            m = re.search(r"(01|02|03|1|2|3)", text)
            anchor = m.group(1) if m else ""
            if anchor in ("1", "2", "3"):
                anchor = f"0{anchor}"
            event["type"] = "anchor_selected"
            event["payload"] = {"pass": True, "anchor_id": anchor}
            return event
        if STORYBOARD_CONFIRM_RE.search(text):
            event["type"] = "storyboard_confirmed"
            event["payload"] = {"pass": True}
            return event
        if PROMPT_APPROVE_RE.search(text):
            event["type"] = "prompt_pack_approved"
            event["payload"] = {"pass": True}
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
