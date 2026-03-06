---
name: session-compactor
description: Compress long-running task or chat sessions without modifying OpenClaw core. Use when a conversation keeps growing but work needs to continue smoothly by retaining only the latest 15 raw messages plus a rolling task summary with fixed fields: task, progress, done, blocked, constraints, and next_step. Especially useful for orchestrating robot/agent dialogue, handoffs, and follow-up work after context compaction.
---

# Session Compactor

Use this skill to keep a long conversation usable without carrying the full history forward.

## Default policy

Apply this exact first-pass policy unless the user asks otherwise:

- Keep the latest **15 messages** as raw context
- Trigger compaction when the session exceeds **20 messages**
- Convert older messages into one `rolling_summary`
- Continue future work from:
  - `rolling_summary`
  - latest 15 raw messages

This is a **minimal usable mode**. Do not introduce long-term memory extraction, relevance ranking, or complex retention rules unless explicitly requested.

## Core rule

Do **not** summarize the conversation as a narrative recap.

Instead, preserve **task continuity**. The summary must help another agent continue the work immediately.

## Required summary schema

Always produce or update a `rolling_summary` using exactly these fields:

```yaml
task: 当前任务目标
progress: 当前进度，做到哪一步
done:
  - 已完成事项
blocked:
  - 阻塞点或失败点
constraints:
  - 约束条件
next_step: 下一步最应该做什么
```

All fields must be present. Use empty lists where needed.

## How to compact

When the session exceeds the threshold:

1. Split messages into:
   - `older_messages`: all but the latest 15
   - `recent_messages`: latest 15
2. Read the previous `rolling_summary` if one exists
3. Merge `older_messages` into the summary
4. Drop redundant narrative detail, greetings, and repeated confirmations
5. Preserve only information needed to continue the task
6. Continue the session using:
   - updated `rolling_summary`
   - `recent_messages`

## What to preserve

Preserve:

- Current task goal
- Current progress/state
- Completed work that matters
- Failed attempts that should not be repeated
- Active constraints, preferences, and boundaries
- The next actionable step

## What to discard

Discard unless still operationally relevant:

- Greetings and filler
- Duplicate confirmations
- Casual banter
- Obsolete guesses
- Resolved side branches
- Raw historical detail that is already captured in the summary

## Merge rules

When updating an existing summary:

- Keep the current `task` unless the task clearly changed
- Update `progress` to reflect the latest state
- Append to `done` only when something is actually completed
- Remove stale items from `blocked` once resolved
- Keep only currently active `constraints`
- Rewrite `next_step` to the single best immediate continuation

Avoid carrying forward stale or contradictory state.

## Operating mode for orchestrated agent dialogue

When this skill is used for robot/agent orchestration:

- Treat the summary as a **handoff state**, not a human-readable recap
- Prefer concise operational language
- Make `next_step` specific enough that another agent can act immediately
- If there are multiple branches, collapse them into one active branch plus optional blocked items

## Output format

When asked to compact, return two sections:

### 1. Rolling summary

Return the summary in the required YAML shape.

### 2. Recent window

State that the session should continue with the latest 15 raw messages retained.

Example:

```markdown
Rolling summary:
```yaml
...
```

Recent window:
- Keep latest 15 raw messages unchanged
```

## Script

Use the bundled scripts for a simple half-automatic workflow.

### Script 1: compact raw session input

```bash
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/compact_session.py < input.json
```

### Script 2: build a compacted context package for the next agent step

```bash
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/build_compacted_context.py input.json -o compacted.json
```

### Script 3: adapt loose message JSON into the expected input format

```bash
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/adapt_messages.py raw.json -o input.json
```

This supports either:

- a top-level message array
- or an object with one of: `messages`, `history`, `items`, `entries`

Expected compacted-input JSON:

```json
{
  "messages": [
    {"role": "user", "text": "..."},
    {"role": "assistant", "text": "..."}
  ],
  "task_hint": "可选：由上游显式提供的主任务标题",
  "rolling_summary": {
    "task": "",
    "progress": "",
    "done": [],
    "blocked": [],
    "constraints": [],
    "next_step": ""
  },
  "keep_recent": 15,
  "trigger_count": 20
}
```

If `task_hint` is present, use it as the preferred task title instead of guessing only from messages.

`compact_session.py` returns:

- `compacted`
- `rolling_summary`
- `recent_messages`

`build_compacted_context.py` additionally returns:

- `agent_context_text`

Use `agent_context_text` as the ready-to-pass compacted prompt context for the next agent step.

Recommended minimal pipeline:

```bash
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/adapt_messages.py raw.json -o input.json
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/build_compacted_context.py input.json -o compacted.json
```

One-step shortcut:

```bash
uv run python /Users/myclaw/.openclaw/workspace/skills/session-compactor/scripts/session_compact_pipeline.py raw.json -o compacted.json
```

Example files:

- `/Users/myclaw/.openclaw/workspace/skills/session-compactor/examples/raw.json`
- `/Users/myclaw/.openclaw/workspace/skills/session-compactor/examples/compacted.json`

Use this as the first implementation path before adding any DB, retrieval, or OpenClaw-core integration.

## Guardrails

- Do not invent facts to make the summary look cleaner
- Do not silently drop active constraints
- Do not retain more than 15 raw messages unless the user asks
- Do not expand into long-form prose when a short state update is enough
- Do not introduce DB storage, long-term memory, or qmd workflows in this minimal mode unless requested

## Escalation

Only propose a more advanced architecture if the user asks for one of these:

- Automatic storage in DB
- Multi-session/thread inheritance
- Long-term memory extraction
- Retrieval over archived sessions
- Token budgeting by model/context window

Until then, stay with the minimal rule:

**latest 15 raw messages + rolling task summary**
