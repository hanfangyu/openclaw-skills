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


def test_emit_queue_and_dryrun():
    run_id = "test-v14-003"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    # produce one outbound
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"e1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)])

    out_dry = run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "dry_run"])
    assert '"mode": "dry_run"' in out_dry

    out_queue = run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "queue"])
    assert '"mode": "queue"' in out_queue


def test_dispatch_worker_dedup():
    run_id = "test-v14-004"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"e1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)])
    run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "queue"])

    out_export = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "export"])
    assert '"mode": "export"' in out_export

    out1 = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "commit"])
    out2 = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "commit"])
    # second commit should find nothing new due to sent-id dedup
    assert '"count": 0' in out2


def test_receipts_apply():
    run_id = "test-v14-005"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"e1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)])
    run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "queue"])

    export_out = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "export"])
    data = json.loads(export_out)
    assert data.get("count", 0) >= 1
    first = data["payloads"][0]

    receipt = json.dumps([{"dispatch_id": first["dispatch_id"], "ok": True, "provider_message_id": "msg-1"}], ensure_ascii=False)
    receipts_out = run(["python", str(CLI), "receipts", "--run-id", run_id, "--receipts-json", receipt])
    assert '"applied": 1' in receipts_out


def test_dedup():
    run_id = "test-v14-002"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    e = json.dumps({"event_id":"dup1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)
    out1 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    out2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    assert '"dedup": true' in out2


if __name__ == "__main__":
    test_happy_path_and_gates()
    test_emit_queue_and_dryrun()
    test_dispatch_worker_dedup()
    test_receipts_apply()
    test_dedup()
    print("OK")
