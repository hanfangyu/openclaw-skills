#!/usr/bin/env python3
from __future__ import annotations
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts" / "cli.py"


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return p.stdout.strip()


def test_happy_path_and_gates():
    run_id = "test-v14-001"
    run(["python", str(CLI), "start", "--workflow", "marketing_video", "--run-id", run_id])

    # lock params -> ACK_WAIT
    out = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p1",
        "type": "lock_params",
        "ts": 1700001000,
        "payload": {
            "topic": "品牌形象",
            "model_preset": "default_last_verified",
            "aspect_ratio": "16:9",
            "reference_image_provided": False,
            "duration_sec": 30,
        }
    }, ensure_ascii=False)])
    assert '"state": "ACK_WAIT"' in out

    # ACK all
    for i, role in enumerate(["writer", "director", "vfx", "editor"], start=1):
        run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
            "event_id": f"a{i}", "type": "role_ack", "role": role, "ts": 1700001000 + i
        }, ensure_ascii=False)])

    # progress to vfx complete; should block before editor if no duration mapping pass
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700001010}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"d1","type":"role_update","role":"director","status":"已完成","has_delivery":True,"ts":1700001020}, ensure_ascii=False)])
    out_block = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001030}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_block

    # pass duration mapping then retry vfx update
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"map1","type":"duration_mapping","ts":1700001040,"payload":{"pass":True}}, ensure_ascii=False)])
    out_retry = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1-retry","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001041}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_retry
    assert "editor" in out_retry


def test_dedup():
    run_id = "test-v14-002"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    e = json.dumps({"event_id":"dup1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)
    out1 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    out2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    assert '"dedup": true' in out2


if __name__ == "__main__":
    test_happy_path_and_gates()
    test_dedup()
    print("OK")
