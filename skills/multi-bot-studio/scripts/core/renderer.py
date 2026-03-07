from __future__ import annotations
from typing import Dict, List


def _role_label(workflow: Dict, role: str) -> str:
    mentions = workflow.get("role_mentions", {})
    return mentions.get(role) or role


def render_actions(actions: List[Dict], workflow: Dict) -> List[str]:
    lines: List[str] = []
    for a in actions:
        t = a.get("type")
        if t == "dispatch":
            role = _role_label(workflow, a.get("target_role", ""))
            lines.append(f"{role} 第{a.get('meta', {}).get('step', '?')}棒开始执行。")
        elif t == "ack_progress":
            lines.append(a.get("text", ""))
        elif t == "wait_notice":
            lines.append("收到剪辑开工，进入等待窗口 W1=120s。")
        elif t == "remind":
            lines.append("W1到期提醒：请优先回传审片附件，随后补主版。")
        elif t == "fallback_allowed":
            lines.append("W2到期，允许兜底（需显式执行兜底动作）。")
        elif t == "review":
            lines.append(a.get("text", ""))
        else:
            lines.append(a.get("text", ""))
    return [x for x in lines if x]
