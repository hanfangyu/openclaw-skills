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

    # Step2 vfx anchor_images request package -> blocked waiting producer execution
    out_s2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 锚点图prompt+参数","ts":1700001020}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s2

    # producer executes evolink and returns assets+evidence -> still blocked until user anchor selection
    out_p1 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p1ok","type":"role_update","role":"producer","status":"已完成","text":"https://files.evolink.ai/a.png job_id=job_123","ts":1700001021}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_p1

    # pass anchor selection -> resume to director
    out_anchor = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g1","type":"anchor_selected","ts":1700001022,"payload":{"pass":True,"anchor_id":"A1"}}, ensure_ascii=False)])
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

    # storyboard images request -> blocked, then producer executes -> blocked on storyboard_confirmed gate
    out_s5 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v2","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 分镜图生成","ts":1700001050}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s5
    out_p2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p2ok","type":"role_update","role":"producer","status":"已完成","text":"https://cdn.discordapp.com/story1.png task_id=task_201","ts":1700001051}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_p2

    # confirm storyboard -> resume vfx storyboard_videos
    out_g2 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g2","type":"storyboard_confirmed","ts":1700001052,"payload":{"pass":True}}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_g2
    assert "vfx" in out_g2

    # storyboard videos request -> blocked, then producer executes -> dispatch bgm
    out_s6 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v3","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 分镜视频生成","ts":1700001060}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s6
    out_p3 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p3ok","type":"role_update","role":"producer","status":"已完成","text":"https://cdn.discordapp.com/v1.mp4 call_id=call_301","ts":1700001061}, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out_p3

    # bgm request -> blocked, then producer executes -> blocked before editor due duration mapping gate
    out_s7 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v4","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 背景音乐生成","ts":1700001070}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_s7
    out_p4 = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p4ok","type":"role_update","role":"producer","status":"已完成","text":"https://cdn.discordapp.com/bgm.mp3 evolink music job_id=job_401","ts":1700001071}, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_p4

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
    out_block = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","text":"asset_ids: evl_anchor_02 https://files.evolink.ai/anchor02.png task_id=task_88","ts":1700001020}, ensure_ascii=False)])
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


def test_producer_executes_evolink_gate():
    run_id = "test-v14-010"
    run(["python", str(CLI), "start", "--workflow", "marketing_video", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p1",
        "type": "lock_params",
        "ts": 1700003000,
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
            "event_id": f"a{i}", "type": "role_ack", "role": role, "ts": 1700003000 + i
        }, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700003010}, ensure_ascii=False)])

    # vfx in producer-exec mode submits request package -> blocked waiting producer execution
    out_vfx = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "v1",
        "type": "role_update",
        "role": "vfx",
        "status": "已完成",
        "text": "请求包：锚点图生成 prompt + 参数",
        "ts": 1700003020
    }, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_vfx
    assert "等待抓总执行EvoLink" in out_vfx
    assert "接棒提示" in out_vfx and "producer" in out_vfx

    # producer delivery without evidence -> still blocked
    out_p_bad = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p-bad",
        "type": "role_update",
        "role": "producer",
        "status": "已完成",
        "text": "已执行，见上",
        "ts": 1700003021
    }, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_p_bad
    assert "抓总回传缺少可视化素材或 EvoLink 调用证据" in out_p_bad

    # producer delivery with media + evidence -> pass (still blocked on anchor selection gate)
    out_p_ok = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p-ok",
        "type": "role_update",
        "role": "producer",
        "status": "已完成",
        "text": "https://files.evolink.ai/anchor01.png job_id=job_998",
        "ts": 1700003022
    }, ensure_ascii=False)])
    assert '"state": "BLOCKED"' in out_p_ok
    assert "未完成锚点图选择" in out_p_ok


def test_handoff_mentions_on_gate_release():
    run_id = "test-v14-011"
    run(["python", str(CLI), "start", "--workflow", "marketing_video", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p1",
        "type": "lock_params",
        "ts": 1700004000,
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
            "event_id": f"a{i}", "type": "role_ack", "role": role, "ts": 1700004000 + i
        }, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700004010}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 锚点图生成","ts":1700004020}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p1ok","type":"role_update","role":"producer","status":"已完成","text":"https://files.evolink.ai/a.png job_id=job_123","ts":1700004021}, ensure_ascii=False)])

    out = run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g1","type":"anchor_selected","ts":1700004022,"payload":{"pass":True,"anchor_id":"02"}}, ensure_ascii=False)])
    assert "接棒提示" in out
    assert "director" in out


def test_storyboard_confirm_auto_event():
    run_id = "test-v14-012"
    run(["python", str(CLI), "start", "--workflow", "marketing_video", "--run-id", run_id])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "p1",
        "type": "lock_params",
        "ts": 1700005000,
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
            "event_id": f"a{i}", "type": "role_ack", "role": role, "ts": 1700005000 + i
        }, ensure_ascii=False)])

    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w1","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700005010}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v1","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 锚点图生成","ts":1700005020}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p1ok","type":"role_update","role":"producer","status":"已完成","text":"https://files.evolink.ai/a.png job_id=job_123","ts":1700005021}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"g1","type":"anchor_selected","ts":1700005022,"payload":{"pass":True,"anchor_id":"02"}}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"d1","type":"role_update","role":"director","status":"已完成","has_delivery":True,"ts":1700005030}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"w2","type":"role_update","role":"writer","status":"已完成","has_delivery":True,"ts":1700005040}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"gprompt","type":"prompt_pack_approved","ts":1700005041,"payload":{"pass":True}}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"v2","type":"role_update","role":"vfx","status":"已完成","text":"请求包: 分镜图生成","ts":1700005050}, ensure_ascii=False)])
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({"event_id":"p2ok","type":"role_update","role":"producer","status":"已完成","text":"https://cdn.discordapp.com/story1.png task_id=task_201","ts":1700005051}, ensure_ascii=False)])

    # user natural-language confirmation should auto-convert and release to storyboard_videos with handoff mention
    out = run(["python", str(CLI), "ingest-discord", "--run-id", run_id, "--message-json", json.dumps({
        "message_id": "m-story-ok-1",
        "sender_id": "1089470658276229140",
        "text": "分镜确认通过",
        "timestamp": 1700005052
    }, ensure_ascii=False)])
    assert '"state": "DISPATCHING"' in out
    assert "storyboard_videos" in out
    assert "接棒提示" in out


def test_media_export_from_url_lines():
    run_id = "test-v14-009"
    run(["python", str(CLI), "start", "--workflow", "collaboration", "--run-id", run_id])
    # inject a URL-only outbound line and verify export converts to media payload
    run(["python", str(CLI), "step", "--run-id", run_id, "--event-json", json.dumps({
        "event_id": "u1",
        "type": "role_violation",
        "role": "writer",
        "ts": 1700002000
    }, ensure_ascii=False)])

    # append a URL-only line via another step output: using generic text through event not feasible here,
    # so directly append through queue path by leveraging emit from outbound file content.
    from pathlib import Path
    import json as _json
    out_path = Path(__file__).resolve().parents[2] / "runs" / run_id / "outbound.jsonl"
    with out_path.open("a", encoding="utf-8") as f:
        f.write(_json.dumps({"run_id": run_id, "channel": "discord", "target": "c1", "text": "https://cdn.discordapp.com/test.png"}, ensure_ascii=False) + "\n")

    run(["python", str(CLI), "emit", "--run-id", run_id, "--mode", "queue"])
    out = run(["python", str(CLI), "dispatch", "--run-id", run_id, "--mode", "export"])
    data = json.loads(out)
    assert data.get("count", 0) >= 1
    payloads = data.get("payloads", [])
    assert any((p.get("media") == "https://cdn.discordapp.com/test.png") for p in payloads)


if __name__ == "__main__":
    test_happy_path_and_gates()
    test_emit_queue_and_dryrun()
    test_dispatch_worker_dedup()
    test_receipts_apply()
    test_replay_summary()
    test_retry_requeue_and_stats()
    test_dedup()
    test_anchor_auto_selection_event()
    test_media_export_from_url_lines()
    test_producer_executes_evolink_gate()
    test_handoff_mentions_on_gate_release()
    test_storyboard_confirm_auto_event()
    print("OK")
