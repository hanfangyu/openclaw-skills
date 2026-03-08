from __future__ import annotations
import re
from typing import Dict, List


URL_RE = re.compile(r"https?://\S+", re.I)


def _extract_urls(text: str) -> List[str]:
    return URL_RE.findall(text or "")

ROLE_DISPLAY = {
    "writer": "编剧",
    "director": "导演",
    "vfx": "视效师",
    "editor": "剪辑师",
    "producer": "抓总",
}


def _should_use_mention(workflow: Dict, stage: str) -> bool:
    policy = workflow.get("mention_policy") or {}
    mode = policy.get("mode", "allow")
    if mode == "allow":
        return True
    if mode == "single_target":
        # dispatch 行只包含当前 target_role，因此这里允许单点 @。
        # 该模式用于避免“挨个@所有bot”，但保留“按棒次@指定bot”的触发能力。
        return True
    if mode == "suppress":
        allowed = set(policy.get("allow_per_role_mention_stages") or [])
        return stage in allowed
    return True


def _role_label(workflow: Dict, role: str, stage: str = "") -> str:
    mentions = workflow.get("role_mentions", {})
    mention = mentions.get(role)
    if mention and _should_use_mention(workflow, stage):
        return mention
    return ROLE_DISPLAY.get(role, role)


def _render_dispatch(a: Dict, workflow: Dict) -> List[str]:
    role = a.get("target_role", "")
    step = a.get("meta", {}).get("step", "?")
    stage = a.get("meta", {}).get("stage", "")
    role_mention = _role_label(workflow, role, stage)

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
        if t == "handoff":
            # handoff 也必须显式@下一棒角色
            role = a.get("target_role", "")
            stage = a.get("meta", {}).get("stage", "")
            role_mention = _role_label(workflow, role, stage)
            lines.append(f"{role_mention} 接棒提示：门禁已放行，请立即开始本棒（{stage or 'default'}）。")
        elif t == "dispatch":
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
            source_role = a.get("source_role")
            source_text = str(a.get("source_text") or "")
            if source_role in ("vfx", "editor"):
                urls = _extract_urls(source_text)
                for u in urls:
                    # URL-only 行，供 sender 层转换为 media 消息（Discord 可视化素材）
                    lines.append(u)
        else:
            lines.append(a.get("text", ""))
    return [x for x in lines if x]
