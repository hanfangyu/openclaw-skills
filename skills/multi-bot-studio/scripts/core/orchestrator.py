from __future__ import annotations
from typing import Dict, List, Tuple


def _dispatch_action(role: str, step_index: int) -> dict:
    return {
        "type": "dispatch",
        "target_role": role,
        "meta": {"step": step_index + 1},
        "text": f"派工：{role} 开始当前棒次，完成后按模板回传。"
    }


def _duration_gate_ok(state: Dict, workflow: Dict) -> bool:
    gates = workflow.get("gates", {})
    if not gates.get("require_duration_mapping"):
        return True
    return bool(state.get("gates", {}).get("duration_mapping_passed"))


def _advance_step(state: Dict, workflow: Dict) -> List[dict]:
    actions: List[dict] = []
    idx = int(state.get("step_index") or 0)
    next_idx = idx + 1
    steps = workflow.get("steps", [])
    if next_idx >= len(steps):
        state["status"] = "DONE"
        state["current_role"] = None
        actions.append({"type": "done", "text": "全部棒次完成。"})
        return actions

    role = steps[next_idx]

    # marketing_video gate: require duration mapping pass before editor
    if role == "editor" and not _duration_gate_ok(state, workflow):
        state["status"] = "BLOCKED"
        actions.append({
            "type": "blocked",
            "text": "阻塞：未通过时长映射门禁（duration_mapping_passed=false），禁止进入剪辑。"
        })
        return actions

    state["status"] = "DISPATCHING"
    state["step_index"] = next_idx
    state["current_role"] = role
    actions.append(_dispatch_action(role, next_idx))
    return actions


def _handle_param_lock(state: Dict, workflow: Dict, event: Dict) -> List[dict]:
    actions: List[dict] = []
    required = ["topic", "model_preset", "aspect_ratio", "reference_image_provided", "duration_sec"]
    payload = event.get("payload") or {}
    missing = [k for k in required if k not in payload]
    if missing:
        actions.append({"type": "param_lock_invalid", "text": f"锁参缺失字段：{','.join(missing)}"})
        return actions

    state["params"] = payload
    state.setdefault("gates", {})["four_questions_passed"] = True
    state["status"] = "ACK_WAIT"
    actions.append({"type": "param_lock_ok", "text": "四问锁参完成，进入 ACK_WAIT。"})
    return actions


def apply_event(state: Dict, workflow: Dict, event: Dict) -> Tuple[Dict, List[dict]]:
    actions: List[dict] = []
    status = state.get("status")
    et = event.get("type")

    if et == "lock_params":
        actions.extend(_handle_param_lock(state, workflow, event))

    elif et == "duration_mapping":
        passed = bool(event.get("payload", {}).get("pass"))
        state.setdefault("gates", {})["duration_mapping_passed"] = passed
        actions.append({"type": "duration_mapping", "text": f"时长映射校验：{'PASS' if passed else 'FAIL'}"})

    elif et == "role_ack" and status == "ACK_WAIT":
        role = event.get("role")
        if role in state["ack"]["required"] and role not in state["ack"]["received"]:
            state["ack"]["received"].append(role)
            actions.append({
                "type": "ack_progress",
                "text": f"ACK进度 {len(state['ack']['received'])}/{len(state['ack']['required'])}"
            })
        if set(state["ack"]["received"]) == set(state["ack"]["required"]):
            first = workflow["steps"][0]
            state["status"] = "DISPATCHING"
            state["step_index"] = 0
            state["current_role"] = first
            actions.append(_dispatch_action(first, 0))

    elif et == "role_update" and state.get("current_role") == event.get("role"):
        role = event.get("role")
        rstatus = event.get("status", "")

        if role == "editor" and rstatus in ("执行中", "进行中") and not event.get("has_delivery"):
            state["status"] = "EDITOR_WAITING"
            state["timers"] = {
                "wait_started_at": event.get("ts"),
                "w1_notified": False,
                "w1_sec": workflow.get("editor_wait", {}).get("w1_sec", 120),
                "w2_sec": workflow.get("editor_wait", {}).get("w2_sec", 180)
            }
            actions.append({"type": "wait_notice", "text": "收到剪辑开工，进入等待窗口 W1。"})

        elif event.get("has_delivery"):
            state["status"] = "REVIEWING"
            actions.append({"type": "review", "text": f"收到 {role} 实物交付，进入验收。"})
            actions.extend(_advance_step(state, workflow))

    elif et == "timer_tick" and status == "EDITOR_WAITING":
        timers = state.get("timers", {})
        start = int(timers.get("wait_started_at") or event.get("ts") or 0)
        elapsed = int(event.get("ts") or 0) - start
        w1 = int(timers.get("w1_sec", 120))
        w2 = int(timers.get("w2_sec", 180))

        if elapsed >= w1 and not timers.get("w1_notified"):
            timers["w1_notified"] = True
            actions.append({"type": "remind", "text": "W1到期提醒：请优先回传审片附件。"})

        if elapsed >= (w1 + w2):
            state["status"] = "FALLBACK_ALLOWED"
            actions.append({"type": "fallback_allowed", "text": "W2到期：允许兜底流程。"})

    state.setdefault("history", []).append({"event": event, "status": state.get("status")})
    return state, actions
