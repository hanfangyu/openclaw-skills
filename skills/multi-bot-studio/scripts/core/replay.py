from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple

from .orchestrator import apply_event
from .delivery_detector import normalize_event
from .idempotency import event_id_for, is_processed, mark_processed


def replay_events(initial_state: Dict, workflow: Dict, events_path: Path) -> Tuple[Dict, List[Dict], Dict]:
    state = json.loads(json.dumps(initial_state, ensure_ascii=False))
    outputs: List[Dict] = []
    summary = {"total": 0, "dedup": 0, "by_state": {}, "exceptions": 0}

    if not events_path.exists():
        return state, outputs, summary

    for line in events_path.read_text().splitlines():
        if not line.strip():
            continue
        summary["total"] += 1
        try:
            raw = json.loads(line)
            event = normalize_event(raw)
            eid = str(raw.get("event_id") or event_id_for(event))
            if is_processed(state, eid):
                summary["dedup"] += 1
                outputs.append({"event_id": eid, "dedup": True, "actions": []})
                continue
            state, actions = apply_event(state, workflow, event)
            mark_processed(state, eid)
            st = str(state.get("status") or "")
            summary["by_state"][st] = int(summary["by_state"].get(st, 0)) + 1
            outputs.append({"event_id": eid, "dedup": False, "actions": actions, "state": st})
        except Exception as e:
            summary["exceptions"] += 1
            outputs.append({"event_id": None, "dedup": False, "actions": [], "error": str(e)})

    return state, outputs, summary
