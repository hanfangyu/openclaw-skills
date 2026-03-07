#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path


def run_cmd(cmd: list[str], cwd: Path) -> dict:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = p.stdout.strip()
    err = p.stderr.strip()
    return {"code": p.returncode, "stdout": out, "stderr": err}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--base-dir", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--apply-receipts", action="store_true", help="auto write receipts back via cli receipts")
    ap.add_argument("--dry-send", action="store_true", help="do not call real message.send, simulate success")
    args = ap.parse_args()

    base = Path(args.base_dir)
    cli = base / "scripts" / "cli.py"

    # 1) export pending payloads
    export = run_cmd(["python", str(cli), "dispatch", "--run-id", args.run_id, "--mode", "export"], base)
    if export["code"] != 0:
        print(json.dumps({"ok": False, "stage": "export", **export}, ensure_ascii=False))
        return 1

    data = json.loads(export["stdout"] or "{}")
    payloads = data.get("payloads", [])
    receipts = []

    # 2) send (or simulate)
    for row in payloads:
        dispatch_id = row.get("dispatch_id")
        if args.dry_send:
            receipts.append({"dispatch_id": dispatch_id, "ok": True, "provider_message_id": f"dry-{dispatch_id}"})
            continue

        # NOTE: This script does not directly call OpenClaw tool APIs.
        # It prints payloads for an external invoker or future bridge.
        # Keep deterministic and side-effect safe by default.
        receipts.append({"dispatch_id": dispatch_id, "ok": False, "error": "real-send-not-implemented-in-script"})

    # 3) optionally apply receipts
    apply_result = None
    if args.apply_receipts and receipts:
        rj = json.dumps(receipts, ensure_ascii=False)
        apply_cmd = ["python", str(cli), "receipts", "--run-id", args.run_id, "--receipts-json", rj]
        apply = run_cmd(apply_cmd, base)
        apply_result = apply

    print(json.dumps({
        "ok": True,
        "run_id": args.run_id,
        "export_count": len(payloads),
        "receipts": receipts,
        "apply_receipts": apply_result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
