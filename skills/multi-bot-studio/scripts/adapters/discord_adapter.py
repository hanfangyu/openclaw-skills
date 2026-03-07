from __future__ import annotations
from typing import Dict, List


def to_outbound_messages(run_id: str, rendered_lines: List[str]) -> List[Dict]:
    msgs: List[Dict] = []
    for line in rendered_lines:
        if not line:
            continue
        msgs.append({
            "run_id": run_id,
            "channel": "discord",
            "text": line
        })
    return msgs
