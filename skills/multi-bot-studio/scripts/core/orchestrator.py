from __future__ import annotations
from typing import Dict, List, Tuple


GATE_EVENT_MAP = {
    "brand_dna_approved": "brand_dna_passed",
    "anchor_selected": "anchor_selected",
    "prompt_pack_approved": "prompt_pack_approved",
    "storyboard_confirmed": "storyboard_confirmed",
    "assets_ready": "assets_ready",
}


def _stage_for_index(workflow: Dict, idx: int | None) -> str:
    if idx is None:
        return ""
    stages = workflow.get("step_stages") or []
    if 0 <= idx < len(stages):
        return str(stages[idx])
    return ""


def _current_stage(state: Dict, workflow: Dict) -> str:
    idx = state.get("step_index")
    return _stage_for_index(workflow, idx if isinstance(idx, int) else None)


def _dispatch_action(role: str, step_index: int, workflow: Dict) -> dict:
    stage = _stage_for_index(workflow, step_index)
    return {
        "type": "dispatch",
        "target_role": role,
        "meta": {"step": step_index + 1, "stage": stage},
        "text": f"派工：{role} 开始当前棒次（{stage or 'default'}），完成后按模板回传。",
    }


def _duration_gate_ok(state: Dict, workflow: Dict) -> bool:
    gates = workflow.get("gates", {})
    if not gates.get("require_duration_mapping"):
        return True
    return bool(state.get("gates", {}).get("duration_mapping_passed"))


def _gate_check_for_next_step(state: Dict, workflow: Dict, next_idx: int) -> Tuple[bool, str]:
    steps = workflow.get("steps", [])
    role = steps[next_idx]
    stage = _stage_for_index(workflow, next_idx)
    cfg = workflow.get("gates", {})
    g = state.setdefault("gates", {})

    if stage == "anchor_images" and cfg.get("require_brand_dna") and not g.get("brand_dna_passed"):
        return False, "未通过品牌DNA门禁（brand_dna_passed=false）"

    if stage == "prompt_pack_draft" and cfg.get("require_anchor_selected") and not g.get("anchor_selected"):
        return False, "未完成锚点图选择（anchor_selected=false）"

    if stage == "storyboard_images" and cfg.get("require_prompt_pack_approved") and not g.get("prompt_pack_approved"):
        return False, "提示词包未确认（prompt_pack_approved=false）"

    if stage == "storyboard_videos" and cfg.get("require_storyboard_confirmed") and not g.get("storyboard_confirmed"):
        return False, "分镜图未确认（storyboard_confirmed=false）"

    if role == "editor":
        if not _duration_gate_ok(state, workflow):
            return False, "未通过时长映射门禁（duration_mapping_passed=false）"
        if cfg.get("require_asset_delivery") and not g.get("assets_ready"):
            return False, "素材未齐套（assets_ready=false）"

    return True, ""


def _advance_step(state: Dict, workflow: Dict) -> List[dict]:
    actions: List[dict] = []
    idx = state.get("step_index")
    idx = int(idx) if isinstance(idx, int) else 0
    next_idx = idx + 1
    steps = workflow.get("steps", [])

    if next_idx >= len(steps):
        state["status"] = "DONE"
        state["current_role"] = None
        actions.append({"type": "done", "text": "全部棒次完成。"})
        return actions

    ok, reason = _gate_check_for_next_step(state, workflow, next_idx)
    if not ok:
        state["status"] = "BLOCKED"
        stage = _stage_for_index(workflow, next_idx)
        actions.append({"type": "blocked", "text": f"阻塞：{reason}，禁止进入下一棒（{stage or 'unknown'}）。"})
        return actions

    role = steps[next_idx]
    state["status"] = "DISPATCHING"
    state["step_index"] = next_idx
    state["current_role"] = role
    actions.append(_dispatch_action(role, next_idx, workflow))
    return actions


def _try_resume_from_block(state: Dict, workflow: Dict) -> List[dict]:
    if state.get("status") != "BLOCKED":
        return []
    actions = _advance_step(state, workflow)
    # 从阻塞恢复时，显式发布“下一棒接棒”动作，避免仅门禁更新导致体感不明确
    if actions and actions[0].get("type") == "dispatch":
        d = actions[0]
        actions.insert(0, {
            "type": "handoff",
            "target_role": d.get("target_role"),
            "meta": d.get("meta", {}),
            "text": "门禁放行，下一棒请立即接棒执行。",
        })
    return actions


def _handle_param_lock(state: Dict, workflow: Dict, event: Dict) -> List[dict]:
    actions: List[dict] = []
    required = ["topic", "model_preset", "aspect_ratio", "reference_image_provided", "duration_sec"]
    payload = event.get("payload") or {}
    missing = [k for k in required if k not in payload]
    if missing:
        actions.append({"type": "param_lock_invalid", "text": f"锁参缺失字段：{','.join(missing)}"})
        return actions

    preset = payload.get("model_preset")
    known = (workflow.get("model_presets") or {}).keys()
    if known and preset not in known:
        actions.append({"type": "param_lock_invalid", "text": f"未知模型预设：{preset}"})
        return actions

    state["params"] = payload
    gates = state.setdefault("gates", {})
    gates["four_questions_passed"] = True
    state["status"] = "ACK_WAIT"
    actions.append({"type": "param_lock_ok", "text": "四问锁参完成，进入 ACK_WAIT。"})
    return actions


def _mark_stage_delivery_gates(state: Dict, workflow: Dict) -> List[dict]:
    actions: List[dict] = []
    stage = _current_stage(state, workflow)
    gates = state.setdefault("gates", {})

    if stage == "brand_dna" and not gates.get("brand_dna_passed"):
        gates["brand_dna_passed"] = True
        actions.append({"type": "gate_update", "text": "品牌DNA门禁：PASS。"})

    if stage == "bgm" and not gates.get("assets_ready"):
        gates["assets_ready"] = True
        actions.append({"type": "gate_update", "text": "素材齐套门禁：PASS（图/视频/音频已齐）。"})

    return actions


def _handle_gate_event(state: Dict, workflow: Dict, event: Dict) -> List[dict]:
    actions: List[dict] = []
    et = event.get("type")
    key = GATE_EVENT_MAP.get(et)
    if not key:
        return actions

    payload = event.get("payload") or {}
    passed = bool(payload.get("pass", True))
    state.setdefault("gates", {})[key] = passed
    actions.append({"type": "gate_update", "text": f"门禁更新：{key}={'PASS' if passed else 'FAIL'}"})

    if et == "anchor_selected" and payload.get("anchor_id"):
        state.setdefault("meta", {})["anchor_id"] = payload.get("anchor_id")

    actions.extend(_try_resume_from_block(state, workflow))
    return actions


def apply_event(state: Dict, workflow: Dict, event: Dict) -> Tuple[Dict, List[dict]]:
    actions: List[dict] = []
    status = state.get("status")
    et = event.get("type")

    if et == "lock_params":
        actions.extend(_handle_param_lock(state, workflow, event))

    elif et in GATE_EVENT_MAP:
        actions.extend(_handle_gate_event(state, workflow, event))

    elif et == "duration_mapping":
        passed = bool(event.get("payload", {}).get("pass"))
        state.setdefault("gates", {})["duration_mapping_passed"] = passed
        actions.append({"type": "duration_mapping", "text": f"时长映射校验：{'PASS' if passed else 'FAIL'}"})
        actions.extend(_try_resume_from_block(state, workflow))

    elif et == "role_ack" and status == "ACK_WAIT":
        role = event.get("role")
        if role in state["ack"]["required"] and role not in state["ack"]["received"]:
            state["ack"]["received"].append(role)
            actions.append({
                "type": "ack_progress",
                "text": f"ACK进度 {len(state['ack']['received'])}/{len(state['ack']['required'])}",
            })
        if set(state["ack"]["received"]) == set(state["ack"]["required"]):
            first = workflow["steps"][0]
            state["status"] = "DISPATCHING"
            state["step_index"] = 0
            state["current_role"] = first
            actions.append(_dispatch_action(first, 0, workflow))

    elif et == "role_update" and (
        state.get("current_role") == event.get("role")
        or event.get("role") == "producer"
    ):
        role = event.get("role")
        rstatus = event.get("status", "")

        # producer 统一执行 Evolink 的阶段，必须既有素材也有调用证据
        cfg = workflow.get("gates", {})
        producer_exec = bool(cfg.get("producer_executes_evolink", False))
        current_stage = _current_stage(state, workflow)
        producer_stages = {"anchor_images", "storyboard_images", "storyboard_videos", "bgm"}

        if role == "vfx" and producer_exec and current_stage in producer_stages and rstatus == "已完成":
            # vfx 在该模式下只需提交请求包，不做素材交付校验
            state["status"] = "REVIEWING"
            state.setdefault("runtime", {})["awaiting_producer_delivery"] = True
            actions.append({
                "type": "review",
                "text": f"收到 {role} 请求包，进入抓总执行EvoLink。",
                "source_role": role,
                "source_text": str(event.get("text") or ""),
            })
            actions.append({
                "type": "blocked",
                "text": "阻塞：等待抓总执行EvoLink并回传可视化素材+调用证据。",
            })
            state["status"] = "BLOCKED"

        elif role == "producer" and producer_exec and current_stage in producer_stages and rstatus == "已完成":
            awaiting = bool((state.get("runtime") or {}).get("awaiting_producer_delivery", False))
            if not awaiting:
                actions.append({"type": "noop", "text": "忽略：当前阶段未等待抓总EvoLink交付。"})
            elif not bool(event.get("producer_ready", False)):
                state["status"] = "BLOCKED"
                actions.append({
                    "type": "blocked",
                    "text": "阻塞：抓总回传缺少可视化素材或 EvoLink 调用证据（job/task/call id 等），不放行。",
                })
            else:
                state.setdefault("runtime", {})["awaiting_producer_delivery"] = False
                state["status"] = "REVIEWING"
                actions.append({
                    "type": "review",
                    "text": "收到抓总EvoLink实物交付，进入验收。",
                    "source_role": role,
                    "source_text": str(event.get("text") or ""),
                })
                actions.extend(_mark_stage_delivery_gates(state, workflow))
                actions.extend(_advance_step(state, workflow))

        elif role == "editor" and rstatus in ("执行中", "进行中") and not event.get("has_delivery"):
            state["status"] = "EDITOR_WAITING"
            state["timers"] = {
                "wait_started_at": event.get("ts"),
                "w1_notified": False,
                "w1_sec": workflow.get("editor_wait", {}).get("w1_sec", 120),
                "w2_sec": workflow.get("editor_wait", {}).get("w2_sec", 180),
            }
            actions.append({"type": "wait_notice", "text": "收到剪辑开工，进入等待窗口 W1。"})

        elif event.get("has_delivery"):
            state["status"] = "REVIEWING"
            actions.append({
                "type": "review",
                "text": f"收到 {role} 实物交付，进入验收。",
                "source_role": role,
                "source_text": str(event.get("text") or ""),
            })
            actions.extend(_mark_stage_delivery_gates(state, workflow))
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

    elif et == "role_violation":
        role = event.get("role") or "unknown"
        actions.append({
            "type": "role_violation",
            "text": f"越权提示：{role} 只需汇报本角色产出；ACK统计与派工仅抓总负责。",
        })

    state.setdefault("history", []).append({"event": event, "status": state.get("status")})
    return state, actions
