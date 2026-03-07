from __future__ import annotations
import json
import math
import time
from pathlib import Path
from typing import Dict, List


def load_retry_policy(base_dir: Path) -> Dict:
    p = base_dir / "references" / "policies" / "retry.json"
    if not p.exists():
        return {
            "max_retries": 2,
            "base_backoff_sec": 30,
            "max_backoff_sec": 300,
            "retryable_categories": ["network"],
            "classifier": {},
        }
    return json.loads(p.read_text())


def classify_error(error: str, classifier: Dict[str, List[str]]) -> str:
    e = (error or "").lower()
    for cat, needles in classifier.items():
        for n in needles:
            if n.lower() in e:
                return cat
    return "unknown"


def _count_retries(sent_path: Path, dispatch_id: str) -> int:
    if not sent_path.exists():
        return 0
    c = 0
    for line in sent_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            if str(row.get("dispatch_id") or "") == dispatch_id and row.get("status") in ("failed", "retry"):
                c += 1
        except Exception:
            continue
    return c


def _backoff_sec(base_backoff_sec: int, max_backoff_sec: int, retries: int) -> int:
    val = int(base_backoff_sec * math.pow(2, max(0, retries - 1)))
    return min(max_backoff_sec, val)


def deadletter_requeue(run_dir: Path, base_dir: Path, limit: int = 20) -> Dict:
    dead = run_dir / "dead_letter.jsonl"
    queue = run_dir / "dispatch_queue.jsonl"
    sent = run_dir / "sent.jsonl"

    if not dead.exists() or not queue.exists():
        return {"ok": True, "requeued": 0, "items": []}

    policy = load_retry_policy(base_dir)
    max_retries = int(policy.get("max_retries", 2))
    base_backoff = int(policy.get("base_backoff_sec", 30))
    max_backoff = int(policy.get("max_backoff_sec", 300))
    retryable = set(policy.get("retryable_categories", ["network"]))
    classifier = policy.get("classifier", {})

    queue_rows = [json.loads(x) for x in queue.read_text().splitlines() if x.strip()]
    by_id = {str(r.get("dispatch_id") or ""): r for r in queue_rows}

    now = int(time.time())
    requeued = []
    retry_log = run_dir / "retry_log.jsonl"

    for line in dead.read_text().splitlines():
        if len(requeued) >= limit:
            break
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue

        did = str(row.get("dispatch_id") or "")
        if not did or did not in by_id:
            continue

        err = str(row.get("reason") or "")
        cat = classify_error(err, classifier)
        if cat not in retryable:
            continue

        retries = _count_retries(sent, did)
        if retries >= max_retries:
            continue

        backoff = _backoff_sec(base_backoff, max_backoff, retries + 1)
        ready_at = int((row.get("ts") or now) + backoff)
        if now < ready_at:
            continue

        payload = dict(by_id[did])
        payload["retry_count"] = retries + 1
        payload["retry_category"] = cat
        payload["retry_reason"] = err
        payload["retry_at"] = now

        with queue.open("a", encoding="utf-8") as qf:
            qf.write(json.dumps(payload, ensure_ascii=False) + "\n")

        with retry_log.open("a", encoding="utf-8") as rf:
            rf.write(json.dumps({"dispatch_id": did, "retry_count": retries + 1, "category": cat, "ts": now}, ensure_ascii=False) + "\n")

        requeued.append({"dispatch_id": did, "retry_count": retries + 1, "category": cat})

    return {"ok": True, "requeued": len(requeued), "items": requeued}


def failure_stats(run_dir: Path, base_dir: Path) -> Dict:
    sent = run_dir / "sent.jsonl"
    policy = load_retry_policy(base_dir)
    classifier = policy.get("classifier", {})

    stats = {"total_failed": 0, "by_category": {}}
    if not sent.exists():
        return stats

    for line in sent.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("status") != "failed":
            continue
        stats["total_failed"] += 1
        cat = classify_error(str(row.get("error") or ""), classifier)
        stats["by_category"][cat] = int(stats["by_category"].get(cat, 0)) + 1

    return stats
