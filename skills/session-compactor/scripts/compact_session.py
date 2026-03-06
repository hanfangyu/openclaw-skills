#!/usr/bin/env python3
import json
import re
import sys
from typing import Any, Dict, List

DEFAULT_KEEP_RECENT = 15
DEFAULT_TRIGGER = 20

USER_TASK_HINTS = [
    "目标", "任务", "优化", "实现", "测试", "安装", "同步", "压缩", "继续", "下一步"
]
DONE_HINTS = [
    "已处理", "已完成", "完成", "done", "fixed", "解决", "确认", "决定", "已推", "已同步", "跑通", "成功", "已安装"
]
BLOCKED_HINTS = [
    "阻塞", "失败", "问题", "error", "bug", "卡住", "冲突", "没有可用", "没搜到"
]
CONSTRAINT_HINTS = [
    "不要", "先", "必须", "只能", "不修改", "无侵入", "最简单", "minimal", "默认阈值"
]
NEXT_STEP_HINTS = [
    "下一步", "继续", "现在", "开始", "测试", "复测", "安装", "同步", "推", "优化", "修改"
]
TRIVIAL_TEXTS = {"你好", "hi", "hello", "收到", "明白", "好的", "ok", "嗯", "继续"}


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


def clean_text(text: str) -> str:
    text = re.sub(r"<@\d+>", "", text)
    text = " ".join(text.split())
    return text.strip()


def is_trivial(text: str) -> bool:
    cleaned = clean_text(text).lower().strip("。！？!?,， ")
    return cleaned in TRIVIAL_TEXTS


def concise_line(msg: Dict[str, Any]) -> str:
    role = message_role(msg)
    text = clean_text(message_text(msg))
    if not text:
        return ""
    if len(text) > 160:
        text = text[:157] + "..."
    return f"{role}: {text}"


def score_task_candidate(msg: Dict[str, Any]) -> int:
    role = message_role(msg)
    text = clean_text(message_text(msg))
    if not text or is_trivial(text):
        return -999
    score = 0
    if role == "user":
        score += 3
    for hint in USER_TASK_HINTS:
        if hint in text:
            score += 2
    if len(text) > 12:
        score += 1
    if "session-compactor" in text or "OpenClaw" in text:
        score += 2
    if text.endswith("?") or text.endswith("？"):
        score -= 1
    return score


def pick_task(messages: List[Dict[str, Any]], previous: Dict[str, Any], task_hint: str = "") -> str:
    hinted = clean_text(task_hint)
    if hinted and not is_trivial(hinted):
        return hinted[:200]

    prev = clean_text(normalize_text(previous.get("task")))
    if prev and not is_trivial(prev):
        return prev

    user_candidates = []
    for idx, msg in enumerate(messages):
        role = message_role(msg)
        text = clean_text(message_text(msg))
        if role != "user" or not text or is_trivial(text):
            continue
        score = score_task_candidate(msg)
        if text.startswith("下一步") or text.endswith("下一步"):
            score -= 3
        if text in {"下一步", "继续", "你好"}:
            score -= 5
        if "按你说的来" in text:
            score -= 2
        if idx < max(3, len(messages) // 3):
            score += 1
        user_candidates.append((score, -idx, text))

    if user_candidates:
        user_candidates.sort(reverse=True)
        best_text = user_candidates[0][2]
        if best_text:
            return best_text[:200]

    best_text = ""
    best_score = -999
    for msg in messages:
        text = clean_text(message_text(msg))
        score = score_task_candidate(msg)
        if score > best_score:
            best_score = score
            best_text = text
    if best_text:
        return best_text[:200]
    return "继续当前任务"


def build_progress(older: List[Dict[str, Any]], recent: List[Dict[str, Any]], previous: Dict[str, Any]) -> str:
    prev = clean_text(normalize_text(previous.get("progress")))
    latest = [concise_line(m) for m in recent if concise_line(m)]
    tail = latest[-3:]
    if prev and tail:
        return prev + "；最近推进：" + " | ".join(tail)
    if prev:
        return prev
    if tail:
        return "最近推进：" + " | ".join(tail)
    return "等待下一步推进"


def merge_done(previous: Dict[str, Any], merged: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("done"))
    for msg in merged:
        role = message_role(msg)
        text = clean_text(message_text(msg))
        lower = text.lower()
        if not text or is_trivial(text):
            continue
        if role != "assistant":
            continue
        if any(token in lower for token in DONE_HINTS):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-8:]


def merge_blocked(previous: Dict[str, Any], merged: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("blocked"))
    for msg in merged:
        text = clean_text(message_text(msg))
        lower = text.lower()
        if not text or is_trivial(text):
            continue
        if any(token in lower for token in BLOCKED_HINTS):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-8:]


def merge_constraints(previous: Dict[str, Any], merged_messages: List[Dict[str, Any]]) -> List[str]:
    items = to_list(previous.get("constraints"))
    for msg in merged_messages:
        text = clean_text(message_text(msg))
        lower = text.lower()
        if not text or is_trivial(text):
            continue
        if any(token in lower for token in CONSTRAINT_HINTS):
            line = concise_line(msg)
            if line and line not in items:
                items.append(line)
    return items[-10:]


def pick_next_step(previous: Dict[str, Any], recent: List[Dict[str, Any]], task: str) -> str:
    for msg in reversed(recent):
        role = message_role(msg)
        text = clean_text(message_text(msg))
        lower = text.lower()
        if not text or is_trivial(text):
            continue
        if role == "assistant":
            if "现在" in text and ("测试" in text or "复测" in text or "重跑" in text):
                return text[:200]
            if "开始" in text and ("测试" in text or "优化" in text or "同步" in text):
                return text[:200]
    for msg in reversed(recent):
        role = message_role(msg)
        text = clean_text(message_text(msg))
        lower = text.lower()
        if not text or is_trivial(text):
            continue
        if role == "user" and any(token in lower for token in NEXT_STEP_HINTS):
            if text not in {"下一步", "继续", "你好"}:
                return text[:200]
    prev = clean_text(normalize_text(previous.get("next_step")))
    if prev and not is_trivial(prev):
        return prev
    return f"继续围绕“{task}”推进当前任务"


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
    task_hint = normalize_text(data.get("task_hint"))
    task = pick_task(merged_messages, previous_summary, task_hint=task_hint)
    rolling_summary = {
        "task": task,
        "progress": build_progress(older_messages, recent_messages, previous_summary),
        "done": merge_done(previous_summary, merged_messages),
        "blocked": merge_blocked(previous_summary, merged_messages),
        "constraints": merge_constraints(previous_summary, merged_messages),
        "next_step": pick_next_step(previous_summary, recent_messages, task),
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
