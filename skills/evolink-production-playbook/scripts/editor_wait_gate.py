#!/usr/bin/env python3
"""
Editor wait gate checker (local deterministic helper)

Usage:
  python scripts/editor_wait_gate.py \
    --events-json ./tmp/events.json \
    --since-message-id 123 \
    --w1-sec 120 \
    --w2-sec 180 \
    --now-epoch 1772902000

Input events.json format (array):
[
  {"message_id":"...","timestamp":1772901800,"has_media":false,"text":"..."},
  {"message_id":"...","timestamp":1772901910,"has_media":true,"text":"审片版"}
]
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

URL_RE = re.compile(r"https?://\S+", re.I)
VIDEO_HINT_RE = re.compile(r"\.(mp4|mov|m4v|webm)(\?|$)", re.I)


def has_delivery_signal(evt: dict) -> bool:
    if evt.get("has_media"):
        return True
    text = str(evt.get("text", ""))
    urls = URL_RE.findall(text)
    if not urls:
        return False
    for u in urls:
        if VIDEO_HINT_RE.search(u):
            return True
        # non-suffix video hosts can still be delivery links
        if any(host in u for host in ["files.evolink.ai", "media.evolink.ai", "cdn.discordapp.com"]):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-json", required=True)
    ap.add_argument("--since-message-id", required=True)
    ap.add_argument("--since-epoch", type=int, required=True)
    ap.add_argument("--w1-sec", type=int, default=120)
    ap.add_argument("--w2-sec", type=int, default=180)
    ap.add_argument("--now-epoch", type=int, required=True)
    args = ap.parse_args()

    events = json.loads(Path(args.events_json).read_text())
    events = [e for e in events if int(e.get("timestamp", 0)) >= args.since_epoch]

    for e in events:
        if has_delivery_signal(e):
            print(json.dumps({"status": "delivered", "message_id": e.get("message_id")}, ensure_ascii=False))
            return 0

    elapsed = max(0, args.now_epoch - args.since_epoch)
    if elapsed < args.w1_sec:
        print(json.dumps({"status": "waiting_w1", "elapsed": elapsed}, ensure_ascii=False))
        return 0
    if elapsed < (args.w1_sec + args.w2_sec):
        print(json.dumps({"status": "w1_timeout", "elapsed": elapsed}, ensure_ascii=False))
        return 0

    print(json.dumps({"status": "w2_timeout", "elapsed": elapsed}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
