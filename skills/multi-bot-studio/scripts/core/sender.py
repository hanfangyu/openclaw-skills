from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List


def emit_outbound(run_dir: Path, outbound: List[Dict]) -> Path:
    out = run_dir / "outbound.jsonl"
    with out.open("a", encoding="utf-8") as f:
        for m in outbound:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return out


def dispatch_outbound(run_dir: Path, mode: str = "dry_run", limit: int = 20) -> Dict:
    out = run_dir / "outbound.jsonl"
    sent = run_dir / "sent.jsonl"
    queue = run_dir / "dispatch_queue.jsonl"

    if not out.exists():
        return {"ok": True, "mode": mode, "count": 0, "items": []}

    lines = [json.loads(x) for x in out.read_text().splitlines() if x.strip()]
    items = lines[:limit]

    if mode == "dry_run":
        with sent.open("a", encoding="utf-8") as f:
            for m in items:
                f.write(json.dumps({"mode": "dry_run", **m}, ensure_ascii=False) + "\n")
        return {"ok": True, "mode": mode, "count": len(items), "items": items}

    if mode == "queue":
        with queue.open("a", encoding="utf-8") as f:
            for m in items:
                payload = {
                    "action": "send",
                    "channel": m.get("channel", "discord"),
                    "target": m.get("target"),
                    "message": m.get("text", "")
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return {"ok": True, "mode": mode, "count": len(items), "queue_path": str(queue)}

    raise ValueError(f"unsupported dispatch mode: {mode}")
