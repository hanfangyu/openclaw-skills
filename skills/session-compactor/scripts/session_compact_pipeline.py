#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict

from adapt_messages import load_json as load_raw_json, extract_messages, adapt_item
from build_compacted_context import build_agent_context
from compact_session import compact


def build_input(payload: Any, keep_recent: int, trigger_count: int) -> Dict[str, Any]:
    raw_messages = extract_messages(payload)
    messages = []
    for item in raw_messages:
        adapted = adapt_item(item)
        if adapted:
            messages.append(adapted)
    return {
        "messages": messages,
        "rolling_summary": {
            "task": "",
            "progress": "",
            "done": [],
            "blocked": [],
            "constraints": [],
            "next_step": ""
        },
        "keep_recent": keep_recent,
        "trigger_count": trigger_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="One-step session compaction pipeline")
    parser.add_argument("input", help="Path to raw message JSON")
    parser.add_argument("-o", "--output", help="Path to output JSON")
    parser.add_argument("--keep-recent", type=int, default=15)
    parser.add_argument("--trigger-count", type=int, default=20)
    args = parser.parse_args()

    raw_payload = load_raw_json(Path(args.input))
    normalized = build_input(raw_payload, args.keep_recent, args.trigger_count)
    compacted = compact(normalized)
    built = build_agent_context(compacted)
    result = {
        "normalized_input": normalized,
        **compacted,
        **built,
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
