#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import subprocess
import time
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Start a multi-bot-studio run and trigger producer @mentions for ACK round."
    )
    ap.add_argument("--run-id", default="", help="Run id; auto-generated if omitted")
    ap.add_argument("--topic", required=True, help="Video topic, e.g. 娃哈哈30秒产品视频")
    ap.add_argument("--duration", type=int, default=30)
    ap.add_argument("--aspect", default="16:9")
    ap.add_argument("--preset", default="default_last_verified")
    ap.add_argument("--workflow", default="marketing_video")
    ap.add_argument("--channel", default="discord")
    ap.add_argument("--target", required=True, help="Channel id / target id")
    ap.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[2]))
    args = ap.parse_args()

    base = Path(args.base_dir)
    cli = base / "scripts" / "cli.py"

    run_id = args.run_id or f"run-{time.strftime('%Y%m%d-%H%M%S')}-auto"

    code, out, err = run_cmd(
        [
            "python",
            str(cli),
            "start",
            "--workflow",
            args.workflow,
            "--run-id",
            run_id,
            "--route-channel",
            args.channel,
            "--route-target",
            args.target,
        ],
        base,
    )
    if code != 0:
        print(json.dumps({"ok": False, "stage": "start", "stderr": err, "stdout": out}, ensure_ascii=False))
        return 1

    lock_event = {
        "event_id": f"lock-{int(time.time())}",
        "type": "lock_params",
        "ts": int(time.time()),
        "payload": {
            "topic": args.topic,
            "model_preset": args.preset,
            "aspect_ratio": args.aspect,
            "reference_image_provided": False,
            "duration_sec": int(args.duration),
        },
    }

    code, out, err = run_cmd(
        ["python", str(cli), "step", "--run-id", run_id, "--event-json", json.dumps(lock_event, ensure_ascii=False)],
        base,
    )
    if code != 0:
        print(json.dumps({"ok": False, "stage": "step(lock_params)", "stderr": err, "stdout": out}, ensure_ascii=False))
        return 1

    # enqueue + export outbound so producer can send mentions immediately
    run_cmd(["python", str(cli), "emit", "--run-id", run_id, "--mode", "queue"], base)
    code, out, err = run_cmd(["python", str(cli), "dispatch", "--run-id", run_id, "--mode", "export"], base)
    if code != 0:
        print(json.dumps({"ok": False, "stage": "dispatch(export)", "stderr": err, "stdout": out}, ensure_ascii=False))
        return 1

    payloads = []
    try:
        payloads = (json.loads(out) or {}).get("payloads", [])
    except Exception:
        pass

    print(
        json.dumps(
            {
                "ok": True,
                "run_id": run_id,
                "topic": args.topic,
                "channel": args.channel,
                "target": args.target,
                "ack_messages": payloads,
                "hint": "Use message tool to send ack_messages in channel, then bots reply ACK + 在线.",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
