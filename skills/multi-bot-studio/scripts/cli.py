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


def _workflow_path(base: Path, workflow: str) -> Path:
    return base / "scripts" / "workflows" / workflow / "workflow.json"


def _load_workflow(base: Path, workflow: str) -> dict:
    return json.loads(_workflow_path(base, workflow).read_text())


def cmd_start(base: Path, workflow: str, run_id: str):
    wf = _load_workflow(base, workflow)
    rd = ensure_run(base, run_id)
    state = {
        "run_id": run_id,
        "workflow": workflow,
        "status": "ACK_WAIT",
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
        "processed_event_ids": [],
        "history": []
    }
    save_json(rd / "state.json", state)
    (rd / "events.jsonl").touch(exist_ok=True)
    print(json.dumps({"ok": True, "run_id": run_id, "status": state["status"]}, ensure_ascii=False))


def cmd_step(base: Path, run_id: str, event_json: str):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    if not state:
        raise SystemExit(f"run not found: {run_id}")
    wf = _load_workflow(base, state["workflow"])

    raw_event = json.loads(event_json)
    event = normalize_event(raw_event)
    eid = event_id_for(event)

    if is_processed(state, eid):
        print(json.dumps({"ok": True, "state": state["status"], "actions": [], "rendered": [], "outbound": [], "dedup": True}, ensure_ascii=False))
        return

    append_event(rd / "events.jsonl", {"event_id": eid, **event})
    state, actions = apply_event(state, wf, event)
    mark_processed(state, eid)
    save_json(rd / "state.json", state)

    rendered = render_actions(actions, wf)
    outbound = to_outbound_messages(run_id, rendered)
    print(json.dumps({"ok": True, "state": state["status"], "actions": actions, "rendered": rendered, "outbound": outbound}, ensure_ascii=False))


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
    state, actions = apply_fallback_approval(state, approved)
    save_json(rd / "state.json", state)
    rendered = render_actions(actions, wf)
    outbound = to_outbound_messages(run_id, rendered)
    print(json.dumps({"ok": True, "state": state["status"], "actions": actions, "rendered": rendered, "outbound": outbound}, ensure_ascii=False))


def cmd_replay(base: Path, run_id: str):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    if not state:
        raise SystemExit(f"run not found: {run_id}")

    wf = _load_workflow(base, state["workflow"])
    # Rebuild from clean initial skeleton for deterministic replay
    initial = {
        "run_id": run_id,
        "workflow": state["workflow"],
        "status": "ACK_WAIT",
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
        "processed_event_ids": [],
        "history": []
    }
    replayed_state, outputs = replay_events(initial, wf, rd / "events.jsonl")
    print(json.dumps({"ok": True, "replayed_state": replayed_state.get("status"), "events": len(outputs), "outputs": outputs[-5:]}, ensure_ascii=False))


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

    sp = sub.add_parser("status")
    sp.add_argument("--run-id", required=True)

    sp = sub.add_parser("approve")
    sp.add_argument("--run-id", required=True)
    sp.add_argument("--action", required=True, choices=["fallback"])
    sp.add_argument("--approved", required=True, choices=["true", "false"])

    sp = sub.add_parser("replay")
    sp.add_argument("--run-id", required=True)

    args = ap.parse_args()
    base = Path(args.base_dir)

    if args.cmd == "start":
        cmd_start(base, args.workflow, args.run_id)
    elif args.cmd == "step":
        cmd_step(base, args.run_id, args.event_json)
    elif args.cmd == "status":
        cmd_status(base, args.run_id)
    elif args.cmd == "approve":
        cmd_approve(base, args.run_id, args.action, args.approved == "true")
    elif args.cmd == "replay":
        cmd_replay(base, args.run_id)


if __name__ == "__main__":
    main()
