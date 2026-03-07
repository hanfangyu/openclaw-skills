# Runbook

## Commands

- Start run:
  - `uv run python skills/multi-bot-studio/scripts/cli.py start --workflow <name> --run-id <id>`
- Apply event:
  - `uv run python skills/multi-bot-studio/scripts/cli.py step --run-id <id> --event-json '<json>'`
- Show state:
  - `uv run python skills/multi-bot-studio/scripts/cli.py status --run-id <id>`
- Approve fallback:
  - `uv run python skills/multi-bot-studio/scripts/cli.py approve --run-id <id> --action fallback --approved true`
- Replay run:
  - `uv run python skills/multi-bot-studio/scripts/cli.py replay --run-id <id>`
- Ingest Discord message:
  - `uv run python skills/multi-bot-studio/scripts/cli.py ingest-discord --run-id <id> --message-json '<json>'`

## Event Examples

- ACK: `{"type":"role_ack","role":"writer","ts":1700000000}`
- Editor progress: `{"type":"role_update","role":"editor","status":"执行中","ts":1700000100}`
- Timer tick: `{"type":"timer_tick","ts":1700000400}`
- Delivery: `{"type":"role_update","role":"editor","status":"已完成","has_delivery":true,"ts":1700000500}`

## Notes

- W1/W2 timeout behavior is read from workflow config.
- Fallback is only allowed when orchestrator enters `FALLBACK_ALLOWED`.
