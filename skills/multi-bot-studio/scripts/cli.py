#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

from core.storage import ensure_run, load_json, save_json, append_event
from core.orchestrator import apply_event
from core.idempotency import event_id_for, is_processed, mark_processed
from core.delivery_detector import normalize_event
from core.renderer import render_actions
from core.replay import replay_events
from core.fallback import apply_fallback_approval
from adapters.discord_adapter import to_outbound_messages
from core.sender import emit_outbound, dispatch_outbound, dispatch_worker
from ingest.discord_to_event import message_to_event


def _workflow_path(base: Path, workflow: str) -> Path:
    return base / "scripts" / "workflows" / workflow / "workflow.json"


def _policy_path(base: Path) -> Path:
    return base / "references" / "policies" / "defaults.json"


def _load_workflow(base: Path, workflow: str) -> dict:
    return json.loads(_workflow_path(base, workflow).read_text())


def _load_policy(base: Path) -> dict:
    p = _policy_path(base)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def _with_default_target(outbound: list[dict], policy: dict) -> list[dict]:
    messaging = policy.get("messaging", {})
    channel = messaging.get("default_channel", "discord")
    target = messaging.get("default_target")
    fixed = []
    for m in outbound:
        x = dict(m)
        x.setdefault("channel", channel)
        if target and not x.get("target"):
            x["target"] = target
        fixed.append(x)
    return fixed


def cmd_start(base: Path, workflow: str, run_id: str):
    wf = _load_workflow(base, workflow)
    rd = ensure_run(base, run_id)
    state = {
        "run_id": run_id,
        "workflow": workflow,
        "status": wf.get("entry_state", "ACK_WAIT"),
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
        "gates": {
            "four_questions_passed": False,
            "duration_mapping_passed": not wf.get("gates", {}).get("require_duration_mapping", False)
        },
        "processed_event_ids": [],
        "history": []
    }
    save_json(rd / "state.json", state)
    (rd / "events.jsonl").touch(exist_ok=True)
    (rd / "outbound.jsonl").touch(exist_ok=True)
    print(json.dumps({"ok": True, "run_id": run_id, "status": state["status"]}, ensure_ascii=False))


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
    outbound = _with_default_target(outbound, policy)
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
    outbound = _with_default_target(outbound, policy)
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
        "gates": {
            "four_questions_passed": False,
            "duration_mapping_passed": not wf.get("gates", {}).get("require_duration_mapping", False)
        },
        "processed_event_ids": [],
        "history": []
    }
    replayed_state, outputs = replay_events(initial, wf, rd / "events.jsonl")
    print(json.dumps({"ok": True, "replayed_state": replayed_state.get("status"), "events": len(outputs), "outputs": outputs[-5:]}, ensure_ascii=False))


def cmd_emit(base: Path, run_id: str, mode: str, limit: int):
    rd = ensure_run(base, run_id)
    result = dispatch_outbound(rd, mode=mode, limit=limit)
    print(json.dumps(result, ensure_ascii=False))


def cmd_dispatch(base: Path, run_id: str, mode: str, limit: int):
    rd = ensure_run(base, run_id)
    result = dispatch_worker(rd, mode=mode, limit=limit)
    print(json.dumps(result, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("start")
    sp.add_argument("--workflow", required=True, choices=["collaboration", "marketing_video"])
    sp.add_argument("--run-id", required=True)

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

    args = ap.parse_args()
    base = Path(args.base_dir)

    if args.cmd == "start":
        cmd_start(base, args.workflow, args.run_id)
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


if __name__ == "__main__":
    main()
