---
name: configure
description: Show the scheduler channel status and walk through first-time setup. Use when the user asks "is the scheduler set up?", "check scheduler config", "what's the state of the scheduler", "scheduler status", "set up the scheduler", or is doing initial channel onboarding. Mirrors /telegram:configure — checks state dir, jobs.json, env file, and reports active jobs and next-fire times.
---

# /scheduler:configure — Scheduler channel status and setup

Reports on the state of `~/.claude/channels/scheduler/` and walks the user
through first-time setup if anything is missing. Mirrors
`/telegram:configure` for shape.

Arguments passed: `$ARGUMENTS`

---

## Dispatch on arguments

### No args — status and next-step guidance

Give the user a complete picture of where things stand:

1. **State dir** — does `~/.claude/channels/scheduler/` exist? Yes/no.
2. **jobs.json** — present? Parse-able? How many jobs total, how many
   enabled, how many disabled, how many broken (unparseable cron).
3. **Env file** — does `~/.claude/channels/scheduler/.env` exist? If yes,
   list the keys (NOT the values — they're credentials). Permissions:
   warn if not `0600`.
4. **Logs dir** — does `logs/` exist? How many job-named subdirs? Total
   size on disk. Highlight if it's >100MB (offer `clear-logs`).
5. **Next 5 fires across all jobs.** Compute next-fire for each enabled
   job, sort, show the top 5 in local time. This is the most useful
   single piece of info — when's the next thing going to happen.

Then end with a concrete next step based on state:

- **State dir missing** → *"Run `/scheduler:configure init` to create the
  state dir and an empty jobs.json."*
- **State dir exists, no jobs** → *"Empty schedule. Run `/scheduler:add`
  to create your first job."*
- **Jobs present** → *"Looks healthy. Use `/scheduler:list` to inspect or
  `/scheduler:run <name>` to test."*

Also call out whether the channel itself is wired up. The user may have
created jobs.json but not yet started a session with the channel loaded.
Mention:

> The scheduler only fires when a Claude session is running with the
> channel attached. Start one with `claude --channels
> plugin:scheduler-channel@<marketplace>` (or via your settings.json
> channel config).

### `init` — first-time setup

1. `mkdir -p ~/.claude/channels/scheduler/logs`
2. `mkdir -p ~/.claude/channels/scheduler/locks`
3. If `jobs.json` doesn't exist, write `{"jobs": []}` (pretty-printed,
   2-space indent).
4. If `.env` doesn't exist, mention that it's optional — only needed if
   the user wants to inject env vars into the spawned subprocesses
   (e.g., `LUNCH_MONEY_TOKEN`, custom paths). Create an empty file with
   `chmod 600` if the user requests it.
5. Show the status report from no-args mode.
6. Suggest:
   - `/scheduler:add` to create the first job
   - `/scheduler:run <name>` to test it after adding
   - Wire the channel into the live session: `claude --channels
     plugin:scheduler-channel@<marketplace>`

### `clear-logs` — wipe the logs directory

1. Stat `~/.claude/channels/scheduler/logs/`. Show total size and file count.
2. **Confirm.** *"Delete N log entries (X MB)? (yes/no)"* — never delete
   without explicit confirmation, even if the user typed `clear-logs`.
   The user may want to grep them first.
3. On yes: `trash ~/.claude/channels/scheduler/logs/*` (prefer `trash`
   over `rm` per house rules — recoverable).
4. Recreate the empty `logs/` dir (some tools expect it to exist).
5. Confirm done.

---

## Implementation notes

- The channels dir might not exist if the server has never run. Missing
  file = not configured, not an error.
- The server reads `jobs.json` continuously via chokidar — changes via
  `/scheduler:add` / `/scheduler:remove` take effect immediately. No
  restart needed for schedule changes.
- The server reads `.env` once at boot, like Telegram does. Env var
  changes need a session restart (or `/reload-plugins`). Say so if the
  user adds/changes env values.
- `access.json`-style policy doesn't apply here — the scheduler is a
  one-way channel with no inbound permission model. There's nothing
  external to lock down. (Contrast with `/telegram:configure`, which
  pushes the user toward `allowlist`.)
- Don't print credential values from `.env`. List keys only.
- The "next 5 fires" computation requires walking cron expressions. If
  a job's cron is malformed, skip it (and mention it explicitly so the
  user can fix).
