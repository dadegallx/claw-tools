---
name: list
description: List all scheduled jobs in the scheduler channel with next fire times, last-run status, and enabled state. Use when the user asks "what's scheduled", "show me my crons", "what jobs do I have", "what's running", "list scheduler jobs", "audit my schedule", or wants to see what the scheduler is doing. Read-only — never mutates jobs.json.
---

# /scheduler:list — Show scheduled jobs

Read-only inspection of `~/.claude/channels/scheduler/jobs.json` and the
per-job log directories. Never writes.

Arguments passed: `$ARGUMENTS` (unused; reserved for future filters)

---

## Workflow

1. **Read jobs.json.** Handle missing file as `{"jobs": []}` — report the
   scheduler is configured but empty, and suggest `/scheduler:add`.
2. **For each job, gather:**
   - `name`, `cron`, `model`, `mcps`, `enabled`
   - **Next fire time** (1 fire, local TZ). Compute from the cron expression;
     if the cron is unparseable, show `?` and flag the job as broken.
   - **Last-run status.** If `~/.claude/channels/scheduler/logs/<name>/`
     exists, list the most recent 3 entries by mtime. Read each JSON and
     pull `ts`, `status`, `duration_ms` (or whatever the server writes).
3. **Render as a tight markdown table.** One row per job. Columns: `name`,
   `cron`, `next`, `model`, `mcps`, `enabled`, `last status`. Keep widths
   minimal — terminals are narrow.
4. **Below the table, for each job with log history**, show a one-line
   recent-runs strip like:
   `daily-budget: ok 38s · ok 41s · error 12s (3h ago / 1d / 2d)`
5. **Footer.** Total enabled job count, total disabled, count with no log
   history yet.

If `jobs.json` is missing entirely, the response is:

> Scheduler state dir not initialized. Run `/scheduler:configure` to set up,
> then `/scheduler:add` to create your first job.

---

## Format example

```
| name          | cron        | next         | model  | mcps                  | en | last  |
|---------------|-------------|--------------|--------|-----------------------|----|-------|
| daily-budget  | 57 7 * * *  | Wed 07:57    | haiku  | telegram,lunch-money  | y  | ok    |
| meal-prep     | 30 17 * * 0 | Sun 17:30    | sonnet | telegram,notion       | y  | ok    |
| notion-digest | 0 9 * * 1   | Mon 09:00    | haiku  | telegram,notion       | n  | -     |

daily-budget: ok 38s · ok 41s · error 12s  (3h / 1d / 2d ago)
meal-prep:    ok 2m4s · ok 1m51s           (3d / 10d ago)
notion-digest: never run

3 jobs (2 enabled, 1 disabled). 1 has never run.
```

---

## Implementation notes

- This is a read-only skill. Do not Write or modify `jobs.json` under any
  circumstance — even if the user follows up with "and disable the meal
  prep one." Tell them to run `/scheduler:add meal-prep ... --disabled`
  or edit jobs.json directly.
- The channel server may be mid-write when you read. If JSON parse fails,
  wait briefly and try once more before reporting corruption.
- Log files: each fire writes `logs/<job-name>/<ISO-ts>.json`. The shape is
  `{ ts, status, duration_ms, exit_code?, cost_usd?, summary? }`. Some
  fields may be absent for older entries — degrade gracefully.
- Reading a log file shouldn't block on size — they're small. If a log
  directory has 100+ entries, just take the latest 3 by name (ISO
  timestamps sort lexically).
- If a job's cron string is invalid, still list it but mark it clearly so
  the user can fix it.
