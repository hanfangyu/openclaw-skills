#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path

from core.storage import ensure_run, load_json, save_json, append_event
from core.orchestrator import apply_event
from core.idempotency import event_id_for, is_processed, mark_processed
from core.delivery_detector import normalize_event
from core.renderer import render_actions
from core.replay import replay_events
from core.fallback import apply_fallback_approval
from adapters.discord_adapter import to_outbound_messages
from core.sender import emit_outbound, dispatch_outbound, dispatch_worker, apply_receipts
from core.retry import deadletter_requeue, failure_stats
from ingest.discord_to_event import message_to_event


def _workflow_path(base: Path, workflow: str) -> Path:
    return base / "scripts" / "workflows" / workflow / "workflow.json"


def _policy_path(base: Path) -> Path:
    return base / "references" / "policies" / "defaults.json"


def _task_card_policy_path(base: Path) -> Path:
    return base / "references" / "policies" / "task-cards.json"


def _roles_policy_path(base: Path) -> Path:
    return base / "references" / "policies" / "roles.json"


def _load_workflow(base: Path, workflow: str) -> dict:
    wf = json.loads(_workflow_path(base, workflow).read_text())

    tc = _task_card_policy_path(base)
    if tc.exists():
        mapping = json.loads(tc.read_text())
        if isinstance(mapping, dict):
            wf["dispatch_templates"] = mapping.get(workflow, {})

    rp = _roles_policy_path(base)
    if rp.exists():
        role_map = json.loads(rp.read_text())
        if isinstance(role_map, dict):
            wf["role_mentions"] = role_map.get(workflow, {})

    return wf


def _load_policy(base: Path) -> dict:
    p = _policy_path(base)
    if not p.exists():
        policy = {}
    else:
        policy = json.loads(p.read_text())

    # Allow runtime override without editing committed policy file.
    messaging = dict(policy.get("messaging", {}))
    env_channel = os.environ.get("MBS_DEFAULT_CHANNEL")
    env_target = os.environ.get("MBS_DEFAULT_TARGET")
    if env_channel:
        messaging["default_channel"] = env_channel
    if env_target:
        messaging["default_target"] = env_target
    if messaging:
        policy["messaging"] = messaging
    return policy


def _with_default_target(outbound: list[dict], policy: dict, run_state: dict | None = None) -> list[dict]:
    messaging = policy.get("messaging", {})
    run_routing = (run_state or {}).get("routing", {})

    channel = run_routing.get("channel") or messaging.get("default_channel", "discord")
    target = run_routing.get("target") or messaging.get("default_target")

    fixed = []
    for m in outbound:
        x = dict(m)
        x.setdefault("channel", channel)
        if target and not x.get("target"):
            x["target"] = target
        fixed.append(x)
    return fixed


def _init_gates_from_workflow(wf: dict) -> dict:
    cfg = wf.get("gates", {})
    gates = {
        "four_questions_passed": False,
        "duration_mapping_passed": not cfg.get("require_duration_mapping", False),
    }
    if cfg.get("require_brand_dna"):
        gates["brand_dna_passed"] = False
    if cfg.get("require_anchor_selected"):
        gates["anchor_selected"] = False
    if cfg.get("require_prompt_pack_approved"):
        gates["prompt_pack_approved"] = False
    if cfg.get("require_storyboard_confirmed"):
        gates["storyboard_confirmed"] = False
    if cfg.get("require_asset_delivery"):
        gates["assets_ready"] = False
    return gates


def cmd_start(base: Path, workflow: str, run_id: str, route_channel: str | None = None, route_target: str | None = None):
    wf = _load_workflow(base, workflow)
    rd = ensure_run(base, run_id)
    routing = {}
    if route_channel:
        routing["channel"] = route_channel
    if route_target:
        routing["target"] = route_target

    state = {
        "run_id": run_id,
        "workflow": workflow,
        "status": wf.get("entry_state", "ACK_WAIT"),
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
        "gates": _init_gates_from_workflow(wf),
        "routing": routing,
        "processed_event_ids": [],
        "history": []
    }
    save_json(rd / "state.json", state)
    (rd / "events.jsonl").touch(exist_ok=True)
    (rd / "outbound.jsonl").touch(exist_ok=True)
    print(json.dumps({"ok": True, "run_id": run_id, "status": state["status"], "routing": routing}, ensure_ascii=False))


def _apply(base: Path, run_id: str, raw_event: dict):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    if not state:
        raise SystemExit(f"run not found: {run_id}")
    wf = _load_workflow(base, state["workflow"])
    policy = _load_policy(base)

    event = normalize_event(raw_event)
    eid = event_id_for(event)

    if is_processed(state, eid):
        result = {"ok": True, "state": state["status"], "actions": [], "rendered": [], "outbound": [], "dedup": True}
        print(json.dumps(result, ensure_ascii=False))
        return

    append_event(rd / "events.jsonl", {"event_id": eid, **event})
    state, actions = apply_event(state, wf, event)
    mark_processed(state, eid)
    save_json(rd / "state.json", state)

    rendered = render_actions(actions, wf)
    outbound = to_outbound_messages(run_id, rendered)
    outbound = _with_default_target(outbound, policy, state)
    emit_outbound(rd, outbound)
    result = {"ok": True, "state": state["status"], "actions": actions, "rendered": rendered, "outbound": outbound}
    print(json.dumps(result, ensure_ascii=False))


def cmd_step(base: Path, run_id: str, event_json: str):
    raw_event = json.loads(event_json)
    _apply(base, run_id, raw_event)


def cmd_ingest_discord(base: Path, run_id: str, message_json: str):
    msg = json.loads(message_json)
    event = message_to_event(msg)
    _apply(base, run_id, event)


def cmd_status(base: Path, run_id: str):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    print(json.dumps(state, ensure_ascii=False, indent=2))


def cmd_approve(base: Path, run_id: str, action: str, approved: bool):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    if not state:
        raise SystemExit(f"run not found: {run_id}")

    if action != "fallback":
        raise SystemExit("unsupported action, only fallback is supported in v1.2")

    wf = _load_workflow(base, state["workflow"])
    policy = _load_policy(base)
    state, actions = apply_fallback_approval(state, approved)
    save_json(rd / "state.json", state)
    rendered = render_actions(actions, wf)
    outbound = to_outbound_messages(run_id, rendered)
    outbound = _with_default_target(outbound, policy, state)
    emit_outbound(rd, outbound)
    print(json.dumps({"ok": True, "state": state["status"], "actions": actions, "rendered": rendered, "outbound": outbound}, ensure_ascii=False))


def cmd_replay(base: Path, run_id: str):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    if not state:
        raise SystemExit(f"run not found: {run_id}")

    wf = _load_workflow(base, state["workflow"])
    initial = {
        "run_id": run_id,
        "workflow": state["workflow"],
        "status": wf.get("entry_state", "ACK_WAIT"),
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
        "gates": _init_gates_from_workflow(wf),
        "processed_event_ids": [],
        "history": []
    }
    replayed_state, outputs, summary = replay_events(initial, wf, rd / "events.jsonl")
    print(json.dumps({"ok": True, "replayed_state": replayed_state.get("status"), "events": len(outputs), "summary": summary, "outputs": outputs[-5:]}, ensure_ascii=False))


def cmd_emit(base: Path, run_id: str, mode: str, limit: int):
    rd = ensure_run(base, run_id)
    result = dispatch_outbound(rd, mode=mode, limit=limit)
    print(json.dumps(result, ensure_ascii=False))


def cmd_dispatch(base: Path, run_id: str, mode: str, limit: int):
    rd = ensure_run(base, run_id)
    result = dispatch_worker(rd, mode=mode, limit=limit)
    print(json.dumps(result, ensure_ascii=False))


def cmd_receipts(base: Path, run_id: str, receipts_json: str):
    rd = ensure_run(base, run_id)
    receipts = json.loads(receipts_json)
    if not isinstance(receipts, list):
        raise SystemExit("receipts-json must be a JSON array")
    result = apply_receipts(rd, receipts)
    print(json.dumps(result, ensure_ascii=False))


def cmd_requeue_dead(base: Path, run_id: str, limit: int):
    rd = ensure_run(base, run_id)
    result = deadletter_requeue(rd, base, limit=limit)
    print(json.dumps(result, ensure_ascii=False))


def cmd_failure_stats(base: Path, run_id: str):
    rd = ensure_run(base, run_id)
    result = failure_stats(rd, base)
    print(json.dumps({"ok": True, **result}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("start")
    sp.add_argument("--workflow", required=True, choices=["collaboration", "marketing_video"])
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--route-channel", required=False)
    sp.add_argument("--route-target", required=False)

    sp = sub.add_parser("step")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--event-json", required=True)

    sp = sub.add_parser("ingest-discord")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--message-json", required=True)

    sp = sub.add_parser("status")
    sp.add_argument("--run-id", required=True)

    sp = sub.add_parser("approve")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--action", required=True, choices=["fallback"])
    sp.add_argument("--approved", required=True, choices=["true", "false"])

    sp = sub.add_parser("replay")
    sp.add_argument("--run-id", required=True)

    sp = sub.add_parser("emit")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--mode", choices=["dry_run", "queue"], default="dry_run")
    sp.add_argument("--limit", type=int, default=20)

    sp = sub.add_parser("dispatch")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--mode", choices=["dry_run", "export", "commit"], default="dry_run")
    sp.add_argument("--limit", type=int, default=20)

    sp = sub.add_parser("receipts")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--receipts-json", required=True)

    sp = sub.add_parser("requeue-dead")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--limit", type=int, default=20)

    sp = sub.add_parser("failure-stats")
    sp.add_argument("--run-id", required=True)

    args = ap.parse_args()
    base = Path(args.base_dir)

    if args.cmd == "start":
        cmd_start(base, args.workflow, args.run_id, args.route_channel, args.route_target)
    elif args.cmd == "step":
        cmd_step(base, args.run_id, args.event_json)
    elif args.cmd == "ingest-discord":
        cmd_ingest_discord(base, args.run_id, args.message_json)
    elif args.cmd == "status":
        cmd_status(base, args.run_id)
    elif args.cmd == "approve":
        cmd_approve(base, args.run_id, args.action, args.approved == "true")
    elif args.cmd == "replay":
        cmd_replay(base, args.run_id)
    elif args.cmd == "emit":
        cmd_emit(base, args.run_id, args.mode, args.limit)
    elif args.cmd == "dispatch":
        cmd_dispatch(base, args.run_id, args.mode, args.limit)
    elif args.cmd == "receipts":
        cmd_receipts(base, args.run_id, args.receipts_json)
    elif args.cmd == "requeue-dead":
        cmd_requeue_dead(base, args.run_id, args.limit)
    elif args.cmd == "failure-stats":
        cmd_failure_stats(base, args.run_id)


if __name__ == "__main__":
    main()
