#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
from pathlib import Path

from core.storage import ensure_run, load_json, save_json, append_event
from core.orchestrator import apply_event


def _workflow_path(base: Path, workflow: str) -> Path:
    return base / "scripts" / "workflows" / workflow / "workflow.json"


def cmd_start(base: Path, workflow: str, run_id: str):
    wf = json.loads(_workflow_path(base, workflow).read_text())
    rd = ensure_run(base, run_id)
    state = {
        "run_id": run_id,
        "workflow": workflow,
        "status": "ACK_WAIT",
        "step_index": None,
        "current_role": None,
        "ack": {"required": wf["roles"], "received": []},
        "timers": {},
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
    wf = json.loads(_workflow_path(base, state["workflow"]).read_text())
    event = json.loads(event_json)
    append_event(rd / "events.jsonl", event)
    state, actions = apply_event(state, wf, event)
    save_json(rd / "state.json", state)
    print(json.dumps({"ok": True, "state": state["status"], "actions": actions}, ensure_ascii=False))


def cmd_status(base: Path, run_id: str):
    rd = ensure_run(base, run_id)
    state = load_json(rd / "state.json", {})
    print(json.dumps(state, ensure_ascii=False, indent=2))


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

    args = ap.parse_args()
    base = Path(args.base_dir)

    if args.cmd == "start":
        cmd_start(base, args.workflow, args.run_id)
    elif args.cmd == "step":
        cmd_step(base, args.run_id, args.event_json)
    elif args.cmd == "status":
        cmd_status(base, args.run_id)


if __name__ == "__main__":
    main()
