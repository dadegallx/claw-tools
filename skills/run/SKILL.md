---
name: run
description: Fire a scheduled job immediately for testing, ignoring its cron schedule. Use when the user says "test the budget job", "run X now", "fire the meal prep manually", "trigger Y", "execute the scheduled Z right now", or wants to verify a job works without waiting for its scheduled time. Spawns the subprocess synchronously, waits for the channel event to land, and reports the result.
---

# /scheduler:run — Fire a job immediately

Bypasses the cron schedule and runs a job's subprocess right now. Useful
for testing a fresh job after `/scheduler:add`, or for debugging a job
that's failing on its real schedule.

Arguments passed: `$ARGUMENTS`

---

## Workflow

1. **Parse `<name>`.** First token of `$ARGUMENTS` is the job name. If
   missing, list jobs and ask which to run.
2. **Confirm the job exists.** Read `~/.claude/channels/scheduler/jobs.json`.
   If no match, show close matches and stop. Don't fuzzy-pick.
3. **Show what's about to happen.** Print:
   - The job name
   - The prompt (full text — the user is about to spend real tokens)
   - The model (`haiku` / `sonnet` / `opus`) and budget cap
   - Which MCPs the subprocess will load
   - The expected side effects (e.g. "will DM chat_id 1022678777 via
     Telegram bot")
4. **Wait for explicit confirmation.** Especially important because:
   - The user might mistype a name (`/scheduler:run daily-bduget`)
   - Some jobs have real-world effects (sending a message, posting to
     Notion). Firing manually means doing it for real.
   - The job is about to spend tokens against the user's account.
5. **Exec the fire-now command.** The plugin's server supports a
   `--fire-now` CLI mode that bypasses MCP setup, loads the named job,
   runs `fireJob` synchronously, and prints the result to stdout.
   ```
   bun ~/Projects/scheduler-channel/server.ts --fire-now <name>
   ```
   If `~/Projects/scheduler-channel/` doesn't exist (the user installed
   via `/plugin install` and the source lives elsewhere), detect the
   install path. The plugin marketplace typically lands sources in
   `~/.claude/plugins/marketplaces/<mp>/<plugin>/`. Try both; ask the
   user which is canonical if both are present.
6. **Capture stdout, show summary.** The subprocess prints a JSON
   payload (`{ status, duration_ms, exit_code?, cost_usd?, summary }`).
   Pretty-print the summary line; show duration and cost; surface
   stderr only if status is `error`.
7. **Note side effects.** Remind the user: if the job succeeded, any
   side-effect messages (Telegram DM, Notion update) have already
   happened. They're not a preview. The channel event also lands as
   part of the same fire — if you see it in-session you can follow up
   in-thread.

---

## Dispatch on arguments

### No args

List job names, ask which one to fire.

### `<name>`

Workflow above, with confirmation step.

### `<name> --yes`

Skip confirmation. Useful when scripting or for repeated test fires
during development.

---

## Example

```
User: /scheduler:run daily-budget
You:  About to fire daily-budget:
        prompt: "Pull yesterday's Lunch Money transactions; DM summary to
                 chat_id 1022678777 via Telegram MCP."
        model:  haiku (budget cap $0.30)
        mcps:   telegram, lunch-money
        effect: WILL send a Telegram DM
      Confirm? (yes/no)
User: yes
You:  Spawning ... (38s) ... done.
        status: ok
        cost:   $0.04
        summary: "Sent. Yesterday net: -$87. 3 uncategorized: Trainline £42, ?? £11, Acme £8."
      The Telegram DM has been sent. The channel event should appear
      in this session shortly — you can reply in-thread.
```

---

## Implementation notes

- Subprocess can run for a while (jobs with `timeout_seconds: 300` may
  legitimately take minutes). Don't get impatient. Show the user that
  it's running.
- If the subprocess fails fast (exit < 5s with non-zero status), that's
  often a config problem (missing env var, MCP not registered).
  Surface the stderr clearly so the user can debug.
- If a lock file exists for this job (`~/.claude/channels/scheduler/
  locks/<name>`), the job is already running on schedule. Stop and
  tell the user — don't fire a parallel run. Offer to wait for the
  current run to finish.
- `--fire-now` mode skips the file watcher and timer setup; it's a
  one-shot. Don't try to leave it running.
- This skill IS allowed to act when invoked by the user from the
  terminal, but should still not be auto-invoked from channel events.
  Manual fires spend tokens and have side effects — keep the human in
  the loop.
