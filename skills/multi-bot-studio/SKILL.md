---
name: multi-bot-studio
description: Script-driven multi-bot orchestration skill. Use for (1) defining and enforcing multi-bot collaboration rules, and (2) running marketing-video workflows with Evolink via deterministic state-machine scripts. Skill text only declares capabilities; runtime flow is controlled by scripts.
---

# Multi Bot Studio

This skill is script-first.

## Capability Surface

- `scripts/cli.py` — unified entrypoint (`start`, `step`, `status`)
- `scripts/core/orchestrator.py` — state-machine transition engine
- `scripts/core/storage.py` — run/event persistence
- `scripts/workflows/collaboration/workflow.json` — generic multi-bot collaboration spec
- `scripts/workflows/marketing_video/workflow.json` — marketing video pipeline spec
- `references/schemas/*.json` — event/state/action/workflow contracts

## Execution Contract

- Do not manually infer next stage from chat text.
- Always compute next actions via `cli.py step`.
- Only emit actions returned by orchestrator.
- Respect timeout/fallback gates from workflow config.

## Quick Commands

```bash
uv run python skills/multi-bot-studio/scripts/cli.py start --workflow collaboration --run-id demo-001
uv run python skills/multi-bot-studio/scripts/cli.py step --run-id demo-001 --event-json '{"type":"role_ack","role":"writer","ts":1700000000}'
uv run python skills/multi-bot-studio/scripts/cli.py status --run-id demo-001
```

## References

- `references/runbook.md`
- `references/schemas/event.schema.json`
- `references/schemas/state.schema.json`
- `references/schemas/action.schema.json`
- `references/schemas/workflow.schema.json`
