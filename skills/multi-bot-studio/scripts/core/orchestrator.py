from __future__ import annotations
import re
from typing import Dict, List, Tuple


GATE_EVENT_MAP = {
    "brand_dna_approved": "brand_dna_passed",
    "anchor_selected": "anchor_selected",
    "prompt_pack_approved": "prompt_pack_approved",
    "storyboard_confirmed": "storyboard_confirmed",
    "assets_ready": "assets_ready",
}

VIDEO_REF_RE = re.compile(r"(image_urls|ref(_|\s)?images?|参考图|对应分镜图|shot\d+\s*->\s*img\d+)", re.I)
TASK_ID_RE = re.compile(r"task_id\s*=\s*([a-zA-Z0-9\-_]+)", re.I)
URL_RE = re.compile(r"https?://\S+", re.I)
LOCAL_PATH_RE = re.compile(r"(?:(?:/|~)[^\s;，。]+)")
OCR_CHECKED_RE = re.compile(r"ocr[_\s-]?checked\s*[:=]\s*(true|false|1|0)", re.I)
OCR_TEXT_RE = re.compile(r"ocr[_\s-]?(text|overlay)[_\s-]?(detected|found)?\s*[:=]\s*(true|false|1|0)", re.I)


def _editor_delivery_ok(text: str) -> Tuple[bool, str]:
    t = (text or "").strip()
    if not t:
        return False, "剪辑师交付缺少内容，请提供成片与打包信息。"

    urls = URL_RE.findall(t)
    has_discord_video = any(("discord" in u.lower() and ".mp4" in u.lower()) for u in urls)
    if not has_discord_video:
        return False, "剪辑师交付缺少 Discord 成片视频链接（.mp4）。"

    has_zip = (".zip" in t.lower()) or ("压缩包" in t) or ("打包" in t)
    if not has_zip:
        return False, "剪辑师交付缺少素材压缩包信息（zip）。"

    paths = LOCAL_PATH_RE.findall(t)
    if len(paths) < 2:
        return False, "剪辑师交付缺少本地路径：请至少提供成片路径 + 压缩包路径。"

    return True, ""


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
        msg = "分镜图未确认（storyboard_confirmed=false）"
        if cfg.get("require_clean_storyboard_frames"):
            msg += "；请先检查并确认无参数文字叠加/水印"
        return False, msg

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
    if role == "editor":
        actions.append({"type": "material_lock", "text": _render_material_lock(state)})
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

    # 在线状态确认：逐个@需要接棒的角色，要求真实回 ACK。
    for r in (state.get("ack", {}).get("required") or []):
        actions.append({
            "type": "ack_request",
            "target_role": r,
            "text": f"请 {r} 在线确认：回复『ACK + 在线』。",
        })

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


def _extract_task_ids(text: str) -> List[str]:
    return [m.group(1) for m in TASK_ID_RE.finditer(text or "")]


def _extract_urls(text: str) -> List[str]:
    return URL_RE.findall(text or "")


def _parse_bool_token(tok: str | None) -> bool:
    if tok is None:
        return False
    return str(tok).strip().lower() in ("1", "true", "yes", "y")


def _extract_ocr_flags(text: str) -> Tuple[bool | None, bool | None]:
    t = text or ""
    m_checked = OCR_CHECKED_RE.search(t)
    m_text = OCR_TEXT_RE.search(t)
    checked = _parse_bool_token(m_checked.group(1)) if m_checked else None
    text_found = _parse_bool_token(m_text.group(2)) if m_text else None
    return checked, text_found


def _save_producer_materials(state: Dict, stage: str, text: str, workflow: Dict) -> None:
    mats = state.setdefault("materials", {})
    task_ids = _extract_task_ids(text)
    urls = _extract_urls(text)

    if stage == "storyboard_videos":
        if task_ids:
            mats["video_task_ids"] = task_ids[:6]
        if urls:
            mats["video_urls"] = urls[:6]
    elif stage == "bgm":
        # single_bgm_output 模式只保留一个版本
        single = bool((workflow.get("gates") or {}).get("single_bgm_output", False))
        if task_ids:
            mats["bgm_task_id"] = task_ids[0] if single else task_ids[-1]
        if urls:
            mats["bgm_url"] = urls[0] if single else urls[-1]


def _render_material_lock(state: Dict) -> str:
    mats = state.get("materials") or {}
    videos = mats.get("video_task_ids") or []
    bgm = mats.get("bgm_task_id") or "（待回填）"
    lines = ["最终锁定素材清单："]
    if videos:
        for i, tid in enumerate(videos, start=1):
            lines.append(f"- shot{i:02d}: {tid}")
    else:
        lines.append("- 分镜视频 task_id：待抓总回填")
    lines.append(f"- BGM: {bgm}")
    lines.append("- logo: 无（本轮不叠加）")
    return "\n".join(lines)


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
            source_text = str(event.get("text") or "")
            # 视频阶段强制要求“分镜图参考映射”声明，避免丢失 image_urls/reference
            if (
                current_stage == "storyboard_videos"
                and bool(cfg.get("require_video_reference_images", False))
                and not VIDEO_REF_RE.search(source_text)
            ):
                state["status"] = "BLOCKED"
                actions.append({
                    "type": "blocked",
                    "text": "阻塞：第6棒请求包缺少分镜图参考映射（image_urls/ref），请补充后再执行。",
                })
            else:
                # vfx 在该模式下只需提交请求包，不做素材交付校验
                state["status"] = "REVIEWING"
                state.setdefault("runtime", {})["awaiting_producer_delivery"] = True
                # 显式@抓总接棒执行，避免“看起来停住”
                actions.append({
                    "type": "handoff",
                    "target_role": "producer",
                    "meta": {"step": (state.get("step_index") or 0) + 1, "stage": current_stage},
                    "text": "已收到请求包，请抓总立即执行EvoLink并回传可视化素材。",
                })
                actions.append({
                    "type": "review",
                    "text": f"收到 {role} 请求包，进入抓总执行EvoLink。",
                    "source_role": role,
                    "source_text": source_text,
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
                src = str(event.get("text") or "")

                # storyboard_images 质检门禁：先 OCR 检查；若有文字仅允许一次重生，再由用户确认是否继续重生
                if current_stage == "storyboard_images" and bool(cfg.get("require_clean_storyboard_frames", False)):
                    checked, text_found = _extract_ocr_flags(src)
                    qc = state.setdefault("runtime", {}).setdefault("storyboard_qc", {})
                    if checked is None:
                        state["status"] = "BLOCKED"
                        actions.append({
                            "type": "blocked",
                            "text": "阻塞：分镜图需先做 OCR 检查；请回传 ocr_checked=true 与 ocr_text_detected=true/false。",
                        })
                        actions.append({
                            "type": "handoff",
                            "target_role": "producer",
                            "meta": {"step": (state.get("step_index") or 0) + 1, "stage": current_stage},
                            "text": "请先执行 OCR 质检再回传。",
                        })
                        state.setdefault("runtime", {})["awaiting_producer_delivery"] = True
                        state.setdefault("history", []).append({"event": event, "status": state.get("status")})
                        return state, actions

                    if text_found is True:
                        regen_count = int(qc.get("regen_count") or 0)
                        if regen_count < 1:
                            qc["regen_count"] = regen_count + 1
                            state["status"] = "BLOCKED"
                            actions.append({
                                "type": "blocked",
                                "text": "阻塞：OCR 检出分镜图含文字/参数叠加；请仅重生 1 次后再回传（避免无限消耗）。",
                            })
                            actions.append({
                                "type": "handoff",
                                "target_role": "producer",
                                "meta": {"step": (state.get("step_index") or 0) + 1, "stage": current_stage},
                                "text": "请执行一次重生（仅一次），并附 OCR 结果。",
                            })
                            state.setdefault("runtime", {})["awaiting_producer_delivery"] = True
                            state.setdefault("history", []).append({"event": event, "status": state.get("status")})
                            return state, actions
                        else:
                            state["status"] = "BLOCKED"
                            actions.append({
                                "type": "blocked",
                                "text": "阻塞：OCR 二次仍检出文字；请用户确认是否继续重生（默认不再自动重生）。",
                            })
                            actions.append({
                                "type": "handoff",
                                "target_role": "producer",
                                "meta": {"step": (state.get("step_index") or 0) + 1, "stage": current_stage},
                                "text": "请向用户请求明确确认：是否继续重生分镜图。",
                            })
                            state.setdefault("runtime", {})["awaiting_producer_delivery"] = True
                            state.setdefault("history", []).append({"event": event, "status": state.get("status")})
                            return state, actions

                # BGM 阶段只保留单一输出，避免多个候选导致后续剪辑重复决策
                if current_stage == "bgm" and bool(cfg.get("single_bgm_output", False)):
                    # 粗粒度：发现多个 bgm 片段标签时给出警告（不阻塞流程）
                    if "bgm01" in src and "bgm02" in src:
                        actions.append({"type": "warning", "text": "提示：BGM 建议只保留单一输出，已检测到多候选。后续请固定一个版本。"})
                _save_producer_materials(state, current_stage, src, workflow)
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
            source_text = str(event.get("text") or "")
            if role == "editor":
                ok_delivery, reason = _editor_delivery_ok(source_text)
                if not ok_delivery:
                    state["status"] = "BLOCKED"
                    actions.append({
                        "type": "blocked",
                        "text": f"阻塞：{reason}",
                    })
                    actions.append({
                        "type": "handoff",
                        "target_role": "editor",
                        "meta": {"step": (state.get("step_index") or 0) + 1, "stage": _current_stage(state, workflow)},
                        "text": "请补齐：1) Discord 成片视频；2) 全素材压缩包；3) 成片与压缩包本地路径。",
                    })
                else:
                    state["status"] = "REVIEWING"
                    actions.append({
                        "type": "review",
                        "text": f"收到 {role} 实物交付，进入验收。",
                        "source_role": role,
                        "source_text": source_text,
                    })
                    actions.extend(_mark_stage_delivery_gates(state, workflow))
                    actions.extend(_advance_step(state, workflow))
            else:
                state["status"] = "REVIEWING"
                actions.append({
                    "type": "review",
                    "text": f"收到 {role} 实物交付，进入验收。",
                    "source_role": role,
                    "source_text": source_text,
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
