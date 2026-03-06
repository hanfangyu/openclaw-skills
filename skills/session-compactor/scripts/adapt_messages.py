#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ROLE_KEYS = ["role", "sender_role", "speaker", "author_role"]
TEXT_KEYS = ["text", "body", "content", "message"]
SENDER_KEYS = ["sender", "from", "author", "name"]
ROOT_MESSAGE_KEYS = ["messages", "history", "items", "entries"]


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        for key in TEXT_KEYS:
            if key in value:
                return normalize_text(value.get(key))
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        parts = [normalize_text(v) for v in value]
        return " ".join([p for p in parts if p]).strip()
    return str(value).strip()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Input file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def extract_messages(payload: Any) -> List[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ROOT_MESSAGE_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise SystemExit("Could not find a message list. Expected a top-level list or one of: messages/history/items/entries")


def resolve_role(item: Dict[str, Any]) -> str:
    for key in ROLE_KEYS:
        value = normalize_text(item.get(key)).lower()
        if value:
            return value
    sender = normalize_text(next((item.get(k) for k in SENDER_KEYS if k in item), "")).lower()
    if sender in {"assistant", "system", "user", "tool"}:
        return sender
    return "user" if sender else "unknown"


def resolve_text(item: Dict[str, Any]) -> str:
    for key in TEXT_KEYS:
        if key in item:
            text = normalize_text(item.get(key))
            if text:
                return text
    return ""


def adapt_item(item: Any) -> Optional[Dict[str, str]]:
    if isinstance(item, str):
        text = normalize_text(item)
        return {"role": "unknown", "text": text} if text else None
    if not isinstance(item, dict):
        text = normalize_text(item)
        return {"role": "unknown", "text": text} if text else None

    role = resolve_role(item)
    text = resolve_text(item)
    if not text:
        return None
    return {"role": role, "text": text}


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt loose message JSON into session-compactor format")
    parser.add_argument("input", help="Path to input JSON")
    parser.add_argument("-o", "--output", help="Path to output JSON")
    parser.add_argument("--keep-recent", type=int, default=15)
    parser.add_argument("--trigger-count", type=int, default=20)
    args = parser.parse_args()

    payload = load_json(Path(args.input))
    raw_messages = extract_messages(payload)
    messages = []
    for item in raw_messages:
        adapted = adapt_item(item)
        if adapted:
            messages.append(adapted)

    result = {
        "messages": messages,
        "task_hint": payload.get("task_hint", "") if isinstance(payload, dict) else "",
        "rolling_summary": {
            "task": "",
            "progress": "",
            "done": [],
            "blocked": [],
            "constraints": [],
            "next_step": ""
        },
        "keep_recent": args.keep_recent,
        "trigger_count": args.trigger_count
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
