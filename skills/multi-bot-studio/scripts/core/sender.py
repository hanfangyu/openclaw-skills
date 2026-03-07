from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List


def emit_outbound(run_dir: Path, outbound: List[Dict]) -> Path:
    out = run_dir / "outbound.jsonl"
    with out.open("a", encoding="utf-8") as f:
        for m in outbound:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    return out


def _dispatch_id(payload: Dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


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
                    "dispatch_id": _dispatch_id(m),
                    "action": "send",
                    "channel": m.get("channel", "discord"),
                    "target": m.get("target"),
                    "message": m.get("text", "")
                }
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return {"ok": True, "mode": mode, "count": len(items), "queue_path": str(queue)}

    raise ValueError(f"unsupported dispatch mode: {mode}")


def _load_sent_ids(sent_path: Path) -> set[str]:
    if not sent_path.exists():
        return set()
    ids = set()
    for line in sent_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            did = str(row.get("dispatch_id") or "")
            if did:
                ids.add(did)
        except Exception:
            continue
    return ids


def dispatch_worker(run_dir: Path, mode: str = "dry_run", limit: int = 20) -> Dict:
    queue_path = run_dir / "dispatch_queue.jsonl"
    sent_path = run_dir / "sent.jsonl"

    if not queue_path.exists():
        return {"ok": True, "mode": mode, "count": 0, "items": []}

    sent_ids = _load_sent_ids(sent_path)
    queue_rows = [json.loads(x) for x in queue_path.read_text().splitlines() if x.strip()]

    pending = []
    for row in queue_rows:
        did = str(row.get("dispatch_id") or "")
        if not did:
            did = _dispatch_id(row)
            row["dispatch_id"] = did
        if did in sent_ids:
            continue
        pending.append(row)
        if len(pending) >= limit:
            break

    if mode == "dry_run":
        return {"ok": True, "mode": mode, "count": len(pending), "items": pending}

    if mode == "export":
        payloads = []
        for row in pending:
            payloads.append({
                "dispatch_id": row["dispatch_id"],
                "action": "send",
                "channel": row.get("channel", "discord"),
                "target": row.get("target"),
                "message": row.get("message", ""),
            })
        return {"ok": True, "mode": mode, "count": len(payloads), "payloads": payloads}

    if mode == "commit":
        now = int(time.time())
        with sent_path.open("a", encoding="utf-8") as f:
            for row in pending:
                f.write(json.dumps({"dispatch_id": row["dispatch_id"], "status": "committed", "ts": now}, ensure_ascii=False) + "\n")
        return {"ok": True, "mode": mode, "count": len(pending), "items": pending}

    raise ValueError(f"unsupported worker mode: {mode}")
