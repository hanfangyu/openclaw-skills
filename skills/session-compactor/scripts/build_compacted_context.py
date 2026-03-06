#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict

from compact_session import compact


def load_json(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"Input file not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")
    if not isinstance(data, dict):
        raise SystemExit("Top-level JSON must be an object")
    return data


def build_agent_context(result: Dict[str, Any]) -> Dict[str, Any]:
    summary = result["rolling_summary"]
    recent = result["recent_messages"]
    lines = [
        "Use this compacted session context to continue the task.",
        "Rely on the rolling summary for prior state and on recent_messages for the latest local context.",
        "Do not assume missing history beyond what is captured below.",
        "",
        "Rolling summary:",
        yaml_like(summary),
        "",
        f"Recent window: keep latest {len(recent)} raw messages",
    ]
    return {
        "rolling_summary": summary,
        "recent_messages": recent,
        "agent_context_text": "\n".join(lines),
    }


def yaml_like(obj: Dict[str, Any]) -> str:
    out = []
    for key in ["task", "progress", "done", "blocked", "constraints", "next_step"]:
        value = obj.get(key)
        if isinstance(value, list):
            out.append(f"{key}:")
            if value:
                for item in value:
                    out.append(f"  - {item}")
            else:
                out.append("  -")
        else:
            out.append(f"{key}: {value if value is not None else ''}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build compacted agent context from a session JSON file")
    parser.add_argument("input", help="Path to input JSON file")
    parser.add_argument("-o", "--output", help="Path to output JSON file")
    parser.add_argument("--keep-recent", type=int, help="Override keep_recent")
    parser.add_argument("--trigger-count", type=int, help="Override trigger_count")
    args = parser.parse_args()

    payload = load_json(Path(args.input))
    if args.keep_recent is not None:
        payload["keep_recent"] = args.keep_recent
    if args.trigger_count is not None:
        payload["trigger_count"] = args.trigger_count

    compacted = compact(payload)
    built = build_agent_context(compacted)
    result = {
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
