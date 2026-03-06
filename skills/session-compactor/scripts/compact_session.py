#!/usr/bin/env python3
import json
import sys
from typing import Any, Dict, List

DEFAULT_KEEP_RECENT = 15
DEFAULT_TRIGGER = 20


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def to_list(value: Any) -> List[str]:
    if isinstance(value, list):
        out = []
        for item in value:
            text = normalize_text(item)
            if text:
                out.append(text)
        return out
    text = normalize_text(value)
    return [text] if text else []


def load_input() -> Dict[str, Any]:
    raw = sys.stdin.read().strip()
    if not raw:
        raise SystemExit("Expected JSON on stdin")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON input: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON must be an object")
    return data


def message_text(msg: Dict[str, Any]) -> str:
    for key in ("text", "body", "content", "message"):
        text = normalize_text(msg.get(key))
        if text:
            return text
    return ""


def message_role(msg: Dict[str, Any]) -> str:
    for key in ("role", "sender_role", "speaker"):
        value = normalize_text(msg.get(key)).lower()
        if value:
            return value
    sender = normalize_text(msg.get("sender") or msg.get("from") or msg.get("author"))
    return sender or "unknown"


def concise_line(msg: Dict[str, Any]) -> str:
    role = message_role(msg)
    text = message_text(msg)
    if not text:
        return ""
    text = " ".join(text.split())
    if len(text) > 160:
        text = text[:157] + "..."
    return f"{role}: {text}"


def pick_task(messages: List[Dict[str, Any]], previous: Dict[str, Any]) -> str:
    prev = normalize_text(previous.get("task"))
    if prev:
        return prev
    for msg in reversed(messages):
        text = message_text(msg)
        if text:
            return text[:200]
    return "继续当前任务"


def build_progress(older: List[Dict[str, Any]], recent: List[Dict[str, Any]], previous: Dict[str, Any]) -> str:
    prev = normalize_text(previous.get("progress"))
    latest = [concise_line(m) for m in (older + recent) if concise_line(m)]
    tail = latest[-3:]
    if prev and tail:
        return prev + "；最近推进：" + " | ".join(tail)
    if prev:
        return prev
    if tail:
        return "最近推进：" + " | ".join(tail)
    return "等待下一步推进"


def merge_done(previous: Dict[str, Any], older: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("done"))
    for msg in older:
        text = message_text(msg)
        lower = text.lower()
        if any(token in lower for token in ["已", "完成", "done", "fixed", "解决", "确认", "决定"]):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-8:]


def merge_blocked(previous: Dict[str, Any], older: List[Dict[str, Any]], recent: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("blocked"))
    merged = older + recent
    for msg in merged:
        text = message_text(msg)
        lower = text.lower()
        if any(token in lower for token in ["阻塞", "失败", "问题", "error", "bug", "卡住", "冲突"]):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-8:]


def merge_constraints(previous: Dict[str, Any], merged_messages: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("constraints"))
    for msg in merged_messages:
        text = message_text(msg)
        lower = text.lower()
        if any(token in lower for token in ["不要", "先", "必须", "只能", "不修改", "无侵入", "最简单", "minimal", "constraint"]):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-10:]


def pick_next_step(previous: Dict[str, Any], recent: List[Dict[str, Any]]) -> str:
    for msg in reversed(recent):
        text = message_text(msg)
        if text:
            if len(text) > 200:
                return text[:197] + "..."
            return text
    prev = normalize_text(previous.get("next_step"))
    return prev or "继续根据 recent window 推进当前任务"


def compact(data: Dict[str, Any]) -> Dict[str, Any]:
    messages = data.get("messages")
    if not isinstance(messages, list):
        raise SystemExit("Input field 'messages' must be a list")
    previous_summary = data.get("rolling_summary")
    if not isinstance(previous_summary, dict):
        previous_summary = {}

    keep_recent = int(data.get("keep_recent", DEFAULT_KEEP_RECENT))
    trigger_count = int(data.get("trigger_count", DEFAULT_TRIGGER))
    if keep_recent < 1:
        keep_recent = DEFAULT_KEEP_RECENT
    if trigger_count < keep_recent:
        trigger_count = keep_recent

    if len(messages) <= trigger_count:
        recent_messages = messages
        older_messages: List[Dict[str, Any]] = []
        compacted = False
    else:
        recent_messages = messages[-keep_recent:]
        older_messages = messages[:-keep_recent]
        compacted = True

    merged_messages = older_messages + recent_messages
    rolling_summary = {
        "task": pick_task(merged_messages, previous_summary),
        "progress": build_progress(older_messages, recent_messages, previous_summary),
        "done": merge_done(previous_summary, older_messages),
        "blocked": merge_blocked(previous_summary, older_messages, recent_messages),
        "constraints": merge_constraints(previous_summary, merged_messages),
        "next_step": pick_next_step(previous_summary, recent_messages),
    }

    return {
        "compacted": compacted,
        "message_count": len(messages),
        "keep_recent": keep_recent,
        "trigger_count": trigger_count,
        "rolling_summary": rolling_summary,
        "recent_messages": recent_messages[-keep_recent:],
    }


def main() -> None:
    data = load_input()
    result = compact(data)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
