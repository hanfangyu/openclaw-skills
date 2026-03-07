from __future__ import annotations
from typing import Dict, List, Tuple


def apply_fallback_approval(state: Dict, approved: bool) -> Tuple[Dict, List[Dict]]:
    actions: List[Dict] = []
    if state.get("status") != "FALLBACK_ALLOWED":
        return state, actions

    if not approved:
        actions.append({"type": "fallback_denied", "text": "兜底未批准，保持等待人工处理。"})
        return state, actions

    state["status"] = "FALLBACK_EXECUTING"
    actions.append({"type": "fallback_execute", "text": "已批准兜底，进入抓总兜底执行。"})
    return state, actions
