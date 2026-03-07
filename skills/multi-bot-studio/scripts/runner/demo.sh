#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
RUN_ID="${1:-demo-quick-001}"

cd "$BASE_DIR"

echo "[1/6] start run: $RUN_ID"
uv run python scripts/cli.py start --workflow collaboration --run-id "$RUN_ID"

echo "[2/6] ingest ACKs"
uv run python scripts/cli.py step --run-id "$RUN_ID" --event-json '{"event_id":"d1","type":"role_ack","role":"writer","ts":1700000001}'
uv run python scripts/cli.py step --run-id "$RUN_ID" --event-json '{"event_id":"d2","type":"role_ack","role":"director","ts":1700000002}'
uv run python scripts/cli.py step --run-id "$RUN_ID" --event-json '{"event_id":"d3","type":"role_ack","role":"vfx","ts":1700000003}'
uv run python scripts/cli.py step --run-id "$RUN_ID" --event-json '{"event_id":"d4","type":"role_ack","role":"editor","ts":1700000004}'

echo "[3/6] queue outbound"
uv run python scripts/cli.py emit --run-id "$RUN_ID" --mode queue

echo "[4/6] simulate send + apply receipts"
uv run python scripts/runner/send_once.py --run-id "$RUN_ID" --dry-send --apply-receipts

echo "[5/6] show status"
uv run python scripts/cli.py status --run-id "$RUN_ID"

echo "[6/6] done. artifacts: runs/$RUN_ID/"
