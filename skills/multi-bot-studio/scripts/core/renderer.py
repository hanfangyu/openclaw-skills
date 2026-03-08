from __future__ import annotations
from typing import Dict, List


def _role_label(workflow: Dict, role: str) -> str:
    mentions = workflow.get("role_mentions", {})
    return mentions.get(role) or role


def _render_dispatch(a: Dict, workflow: Dict) -> List[str]:
    role = a.get("target_role", "")
    step = a.get("meta", {}).get("step", "?")
    stage = a.get("meta", {}).get("stage", "")
    role_mention = _role_label(workflow, role)

    templates = (workflow.get("dispatch_templates") or {}).get(role)
    if templates:
        out = []
        for line in templates:
            out.append(
                line.format(
                    role=role,
                    role_mention=role_mention,
                    step=step,
                    stage=stage,
                )
            )
        return out

    stage_suffix = f"（{stage}）" if stage else ""
    return [f"{role_mention} 第{step}棒{stage_suffix}开始执行。"]


def render_actions(actions: List[Dict], workflow: Dict) -> List[str]:
    lines: List[str] = []
    for a in actions:
        t = a.get("type")
        if t == "dispatch":
            lines.extend(_render_dispatch(a, workflow))
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
