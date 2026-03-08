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

    # Step1 writer brand_dna delivery should auto-pass brand_dna gate and dispatch vfx(anchor_images)
    out_s1 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700001010}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_s1
    assert "vfx" in out_s1

    # Step2 vfx anchor_images
    out_s2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001020}, ensure_ascii=False)])
    # should block entering director until anchor_selected gate is set
    assert '"state": "BLOCKED"' in out_s2

    # pass anchor selection -> resume to director
    out_anchor = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g1","type":"anchor_selected","ts":1700001021,"payload":{"pass":True,"anchor_id":"A1"}}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_anchor
    assert "director" in out_anchor

    # director draft -> should block before writer finalize if prompt pack not approved
    out_s3 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"d1","type":"role_update","role":"director","status":"已完成","has_delivery":True,"ts":1700001030}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_s3
    assert "writer" in out_s3

    # writer finalize prompt -> should block until prompt pack approved
    out_s4 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w2","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700001040}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s4

    # producer approves prompt pack -> resume to vfx storyboard_images
    out_g_prompt = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g_prompt","type":"prompt_pack_approved","ts":1700001041,"payload":{"pass":True}}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_g_prompt
    assert "vfx" in out_g_prompt

    # storyboard images complete -> block on storyboard_confirmed
    out_s5 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v2","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001050}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s5

    # confirm storyboard -> resume vfx storyboard_videos
    out_g2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g2","type":"storyboard_confirmed","ts":1700001051,"payload":{"pass":True}}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_g2
    assert "vfx" in out_g2

    # storyboard videos done -> dispatch bgm
    out_s6 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v3","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001060}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_s6

    # bgm done -> blocked before editor due duration mapping gate
    out_s7 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v4","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001070}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s7

    # pass duration mapping -> should resume to editor
    out_map = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"map1","type":"duration_mapping","ts":1700001080,"payload":{"pass":True}}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_map
    assert "editor" in out_map


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

    receipt = json.dumps([
        {"dispatch_id": first["dispatch_id"], "ok": False, "error": "network"}
    ], ensure_ascii=False)
    receipts_out = run(["python", str(CLI), "receipts", "--run-id", run_id, "--receipts-json", receipt])
    assert '"applied": 1' in receipts_out
    assert '"failed": 1' in receipts_out


def test_replay_summary():
    run_id = "test-v14-006"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"x1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)])
    out = run(["python", str(CLI), "replay", "--run-id", run_id])
    assert '"summary"' in out


def test_retry_requeue_and_stats():
    run_id = "test-v14-007"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"e1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)])
    run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "queue"])
    out_export = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "export"])
    payloads = json.loads(out_export).get("payloads", [])
    did = payloads[0]["dispatch_id"]

    # write failed receipt (network) -> should go dead letter
    bad = json.dumps([{"dispatch_id": did, "ok": False, "error": "network timeout"}], ensure_ascii=False)
    run(["python", str(CLI), "receipts", "--run-id", run_id, "--receipts-json", bad])

    stats = run(["python", str(CLI), "failure-stats", "--run-id", run_id])
    assert '"network"' in stats

    rq = run(["python", str(CLI), "requeue-dead", "--run-id", run_id, "--limit", "5"])
    assert '"ok": true' in rq


def test_dedup():
    run_id = "test-v14-002"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    e = json.dumps({"event_id":"dup1","type":"role_ack","role":"writer","ts":1700000000}, ensure_ascii=False)
    out1 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    out2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", e])
    assert '"dedup": true' in out2


def test_anchor_auto_selection_event():
    run_id = "test-v14-008"
    run(["python", str(CLI), "start", "--workflow", "marketing_video", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
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
    for i, role in enumerate(["writer", "director", "vfx", "editor"], start=1):
        run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
            "event_id": f"a{i}", "type": "role_ack", "role": role, "ts": 1700001000 + i
        }, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700001010}, ensure_ascii=False)])
    out_block = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","has_delivery":True,"ts":1700001020}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_block

    # user selects anchor -> should resume to director
    out = run(["python", str(CLI), "ingest-discord", "--run-id", run_id, "--message-json", json.dumps({
        "message_id": "m-anchor-1",
        "sender_id": "1089470658276229140",
        "text": "主锚点=02",
        "timestamp": 1700001021
    }, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out
    assert "director" in out


if __name__ == "__main__":
    test_happy_path_and_gates()
    test_emit_queue_and_dryrun()
    test_dispatch_worker_dedup()
    test_receipts_apply()
    test_replay_summary()
    test_retry_requeue_and_stats()
    test_dedup()
    test_anchor_auto_selection_event()
    print("OK")
