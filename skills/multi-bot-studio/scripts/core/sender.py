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
                    "message": m.get("text", ""),
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
            payloads.append(
                {
                    "dispatch_id": row["dispatch_id"],
                    "action": "send",
                    "channel": row.get("channel", "discord"),
                    "target": row.get("target"),
                    "message": row.get("message", ""),
                }
            )
        return {"ok": True, "mode": mode, "count": len(payloads), "payloads": payloads}

    if mode == "commit":
        now = int(time.time())
        with sent_path.open("a", encoding="utf-8") as f:
            for row in pending:
                f.write(
                    json.dumps(
                        {
                            "dispatch_id": row["dispatch_id"],
                            "status": "committed",
                            "ts": now,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        return {"ok": True, "mode": mode, "count": len(pending), "items": pending}

    raise ValueError(f"unsupported worker mode: {mode}")


def apply_receipts(run_dir: Path, receipts: List[Dict]) -> Dict:
    sent_path = run_dir / "sent.jsonl"
    dead_path = run_dir / "dead_letter.jsonl"
    existing = _load_sent_ids(sent_path)
    now = int(time.time())
    applied = 0
    failed = 0

    with sent_path.open("a", encoding="utf-8") as sent_f, dead_path.open("a", encoding="utf-8") as dead_f:
        for r in receipts:
            did = str(r.get("dispatch_id") or "")
            if not did or did in existing:
                continue

            ok = bool(r.get("ok", True))
            row = {
                "dispatch_id": did,
                "status": "sent" if ok else "failed",
                "provider_message_id": r.get("provider_message_id"),
                "error": r.get("error"),
                "ts": int(r.get("ts") or now),
            }
            sent_f.write(json.dumps(row, ensure_ascii=False) + "\n")
            if not ok:
                failed += 1
                dead_f.write(json.dumps({"dispatch_id": did, "reason": row.get("error"), "ts": row["ts"]}, ensure_ascii=False) + "\n")
            applied += 1
            existing.add(did)

    return {"ok": True, "applied": applied, "failed": failed}
