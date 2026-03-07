from __future__ import annotations
import hashlib
import json
from typing import Dict


def event_id_for(event: Dict) -> str:
    explicit = event.get("event_id") or event.get("message_id")
    if explicit:
        return str(explicit)
    raw = json.dumps(event, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def is_processed(state: Dict, event_id: str) -> bool:
    return event_id in state.get("processed_event_ids", [])


def mark_processed(state: Dict, event_id: str) -> None:
    state.setdefault("processed_event_ids", []).append(event_id)
