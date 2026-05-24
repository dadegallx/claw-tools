---
title: Profile-Based Telegram Assistants Spec
date: 2026-05-23
status: draft
scope: minimum viable happy path
---

# Profile-Based Telegram Assistants Spec

## Goal

Make it easy to create and run multiple Claude Code personal assistants reachable from Telegram, using the official Claude Code Telegram channel plugin and without building a custom Telegram router.

The minimum viable happy path is:

```sh
claw profile create finance --telegram
claw profile launch finance
claw profile attach finance
```

After that, Davide can open the newly created BotFather bot on Telegram, pair it with the running Claude Code profile, and start chatting with a separate finance assistant.

## Product decision

Use **profile** as the top-level noun, aligned with Hermes.

A profile is a named assistant identity with its own Claude Code home/config, channel state, launch recipe, and active runtime.

Examples:

- `main` — general personal assistant
- `finance` — financial admin, Lunch Money, budgeting, taxes
- `diet` — food, meal prep, groceries, macrobiotic constraints

A Telegram bot is not the product noun. It is the transport binding required by Telegram.

User-facing framing:

> Telegram requires one bot per independent Claude profile. `claw profile create finance --telegram` creates the profile and walks you through creating/registering the required BotFather bot.

## Constraints and facts

### Telegram hard constraint

The official Telegram channel plugin is bound to one Telegram bot token and one parent Claude Code process.

The plugin:

- reads token from `${TELEGRAM_STATE_DIR}/.env` as `TELEGRAM_BOT_TOKEN`
- defaults `TELEGRAM_STATE_DIR` to `~/.claude/channels/telegram`
- writes `${TELEGRAM_STATE_DIR}/bot.pid`
- uses Telegram `getUpdates` long polling
- assumes Telegram allows exactly one long-polling consumer per token
- sends inbound events into the owning Claude Code session as `<channel source="telegram" ...>`

Therefore:

- one independent Telegram DM assistant = one BotFather bot token
- same Telegram bot token cannot reliably serve multiple Claude Code profiles
- Telegram topics are not a V1 routing primitive because the official plugin does not expose `message_thread_id` in inbound metadata or reply tools
- V1 must not attempt same-bot multi-session routing

### Official plugin skills stay the setup surface inside Claude

The official Telegram plugin already exposes useful Claude Code slash/skill commands:

- `/telegram:configure <token>` writes token to the plugin state `.env`
- `/telegram:access pair <code>` approves a DM pairing request
- `/telegram:access policy allowlist` locks the bot after pairing
- other `/telegram:access ...` commands manage allowlists/groups

V1 should build on these, not replace them.

The CLI should prepare profile-specific state dirs and launch recipes, then instruct the user to use the existing plugin commands in the running Claude session for pairing/access.

## Definitions

### Profile

A durable named assistant home.

Owns:

- Claude Code config directory
- profile-level `CLAUDE.md`
- settings file
- skills directory or skill source config
- memory/plugin configuration
- channel state directories
- launch recipe
- tmux runtime name
- stable Claude Code session ID

### Binding

An external surface connected to a profile.

V1 bindings:

- `telegram`
- `scheduler`

Future bindings:

- `discord`
- `imessage`
- webhooks

### Runtime

The observed live process serving the profile.

V1 runtime implementation:

- one tmux session per running profile
- one interactive Claude Code process in that tmux session
- one official Telegram plugin child process when Telegram binding is enabled
- one scheduler plugin child process when scheduler binding is enabled

### State dir

Plugin-owned durable state.

Examples:

- `TELEGRAM_STATE_DIR`
- `SCHEDULER_STATE_DIR`
- later `DISCORD_STATE_DIR`

State dirs must be profile-specific. Shared plugin state is a bug unless explicitly requested.

## Non-goals for V1

Do not build these in the minimum viable version:

- custom Telegram router/broker
- same Telegram bot routed to many Claude profiles
- Telegram topic/thread routing
- automatic BotFather bot creation
- web UI
- database-backed registry
- automatic killing/restarting of unknown Claude sessions
- generalized plugin marketplace manager
- Discord multi-profile experiment
- rich profile templates beyond a minimal default

## Storage layout

Use a claw-owned profile root under Claude's existing home.

```text
~/.claude/claw/
  profiles.json
  profiles/
    main/
      profile.json
      config/
        CLAUDE.md
        settings.json
        skills/
      channels/
        telegram/
          .env
          access.json
          inbox/
          approved/
          bot.pid
        scheduler/
          jobs.json
          .env
          logs/
          locks/
      logs/
      runtime/
```

For the finance profile:

```text
~/.claude/claw/profiles/finance/
  profile.json
  config/
    CLAUDE.md
    settings.json
    skills/
  channels/
    telegram/
      .env
      access.json
      inbox/
    scheduler/
      jobs.json
      logs/
      locks/
```

## Environment isolation

A launched profile must set both Claude-level and plugin-level state env vars.

For `finance`:

```sh
CLAUDE_CONFIG_DIR="$HOME/.claude/claw/profiles/finance/config"
TELEGRAM_STATE_DIR="$HOME/.claude/claw/profiles/finance/channels/telegram"
SCHEDULER_STATE_DIR="$HOME/.claude/claw/profiles/finance/channels/scheduler"
```

Do not rely on `CLAUDE_CONFIG_DIR` alone. The official Telegram and scheduler plugins resolve their own state dirs separately.

## Registry schema

`~/.claude/claw/profiles.json` is the top-level index.

Minimal schema:

```json
{
  "version": 1,
  "profiles": {
    "finance": {
      "name": "finance",
      "description": "Finance assistant",
      "profileDir": "~/.claude/claw/profiles/finance",
      "claudeConfigDir": "~/.claude/claw/profiles/finance/config",
      "cwd": "/Users/davide",
      "tmux": {
        "sessionName": "claw_finance",
        "width": 128,
        "height": 48
      },
      "claude": {
        "sessionId": "<uuid>",
        "settings": "~/.claude/claw/profiles/finance/config/settings.json",
        "args": [
          "--channels",
          "plugin:telegram@claude-plugins-official",
          "--dangerously-load-development-channels",
          "plugin:scheduler@claw-cron",
          "--dangerously-skip-permissions"
        ]
      },
      "bindings": {
        "telegram": {
          "enabled": true,
          "plugin": "telegram@claude-plugins-official",
          "stateDir": "~/.claude/claw/profiles/finance/channels/telegram",
          "envFile": "~/.claude/claw/profiles/finance/channels/telegram/.env",
          "accessFile": "~/.claude/claw/profiles/finance/channels/telegram/access.json",
          "botUsername": null,
          "botTokenConfigured": false
        },
        "scheduler": {
          "enabled": true,
          "plugin": "scheduler@claw-cron",
          "stateDir": "~/.claude/claw/profiles/finance/channels/scheduler",
          "jobsFile": "~/.claude/claw/profiles/finance/channels/scheduler/jobs.json"
        }
      }
    }
  }
}
```

`profile.json` inside each profile may duplicate the profile entry for easier inspection/export. `profiles.json` is the index of record.

## Generated finance CLAUDE.md

The profile should start with a small, editable `CLAUDE.md`, not an overbuilt persona.

Example generated file:

```md
# Finance Profile

You are Davide's finance-focused personal assistant.

## Scope

Help Davide with personal finance admin, budgeting, subscriptions, invoices, tax prep, financial planning, and related recurring reminders.

## Operating principles

- Be precise with numbers and dates.
- Use tools to calculate; do not do arithmetic mentally.
- Treat financial data as sensitive.
- Ask before sending, deleting, or modifying external financial records.
- Prefer summaries with source references and exact time windows.

## Telegram behavior

Davide is chatting with you through the finance Telegram bot. Reply through the Telegram reply tool when a Telegram channel message arrives.
```

## CLI commands in V1

### `claw profile create <name> --telegram`

Creates a new isolated profile and Telegram binding.

For `finance`, it must:

1. Validate name: `finance` matches `/^[a-z][a-z0-9_-]*$/`.
2. Refuse if profile exists unless `--force` is provided.
3. Create profile directories.
4. Generate `config/CLAUDE.md`.
5. Generate `config/settings.json` with minimal safe settings.
6. Generate empty `channels/scheduler/jobs.json`.
7. Generate Telegram state dir.
8. Write or prompt for `channels/telegram/.env` containing `TELEGRAM_BOT_TOKEN`.
9. Create or leave absent `access.json`; absent is acceptable because the official plugin treats it as pairing mode.
10. Write registry entry.
11. Print exact BotFather and launch instructions.

Important: V1 may choose not to accept the token interactively. It can print the path and expected file format instead. That is safer for a first implementation.

### `claw profile list`

Shows configured profiles and runtime status.

Minimum columns:

```text
NAME      TELEGRAM          SCHEDULER   RUNTIME       TMUX
main      configured        configured  running       aoe_Telegram_345a329e
finance   token-missing     configured  stopped       claw_finance
```

### `claw profile show <name>`

Shows behind-the-hood details:

- profile dir
- Claude config dir
- Telegram state dir
- scheduler state dir
- token configured yes/no, never token value
- access file exists yes/no
- tmux session name
- launch command
- observed runtime PID if running
- warnings

### `claw profile launch <name>`

Starts the profile in tmux using the profile launch recipe.

V1 behavior:

- refuse if tmux session already exists
- set all env vars explicitly
- start Claude Code interactive session
- attach official Telegram channel if configured
- attach scheduler channel by dev-channel flag
- print how to attach

Generated command shape:

```sh
tmux new-session -d \
  -s claw_finance \
  -c /Users/davide \
  -x 128 -y 48 \
  'exec env \
    CLAUDE_CONFIG_DIR="$HOME/.claude/claw/profiles/finance/config" \
    TELEGRAM_STATE_DIR="$HOME/.claude/claw/profiles/finance/channels/telegram" \
    SCHEDULER_STATE_DIR="$HOME/.claude/claw/profiles/finance/channels/scheduler" \
    claude \
      --settings "$HOME/.claude/claw/profiles/finance/config/settings.json" \
      --channels plugin:telegram@claude-plugins-official \
      --dangerously-load-development-channels plugin:scheduler@claw-cron \
      --dangerously-skip-permissions \
      --session-id <uuid>'
```

### `claw profile attach <name>`

Attaches to the tmux session.

```sh
tmux attach -t claw_finance
```

### `claw status`

Read-only control tower view.

Minimum V1 checks:

- registry loads
- profile dirs exist
- token file exists for Telegram bindings
- scheduler jobs file exists
- tmux session exists
- Claude process appears to be running
- command line includes expected channel flags
- warnings for mismatches

## Minimum viable finance setup walkthrough

This is the target user flow after implementation.

### 1. Create the BotFather bot

In Telegram, message `@BotFather`.

Send:

```text
/newbot
```

When prompted:

```text
Name: Finance Assistant
Username: <unique_username_ending_in_bot>
```

Example username:

```text
davide_finance_assistant_bot
```

BotFather returns a token like:

```text
123456789:AAH...
```

Copy the full token.

### 2. Create the claw profile

Run:

```sh
claw profile create finance --telegram
```

Expected output:

```text
Created profile: finance
Profile dir: ~/.claude/claw/profiles/finance
Telegram state: ~/.claude/claw/profiles/finance/channels/telegram
Scheduler state: ~/.claude/claw/profiles/finance/channels/scheduler

Telegram requires a dedicated BotFather bot per independent Claude profile.
Save your BotFather token to:

  ~/.claude/claw/profiles/finance/channels/telegram/.env

Format:

  TELEGRAM_BOT_TOKEN=123456789:AAH...

Then run:

  claw profile launch finance
```

If the implementation supports `--telegram-token` or interactive secret entry, this command may write the `.env` directly. It must never echo the token back.

### 3. Save the token

If token was not provided during creation:

```sh
mkdir -p ~/.claude/claw/profiles/finance/channels/telegram
chmod 700 ~/.claude/claw/profiles/finance/channels/telegram
printf 'TELEGRAM_BOT_TOKEN=%s\n' '<PASTE_TOKEN_HERE>' > ~/.claude/claw/profiles/finance/channels/telegram/.env
chmod 600 ~/.claude/claw/profiles/finance/channels/telegram/.env
```

### 4. Launch the profile

Run:

```sh
claw profile launch finance
```

Expected output:

```text
Started profile: finance
tmux: claw_finance
Attach with: claw profile attach finance

Next:
1. Open your new Telegram bot.
2. Send any DM, for example: hello
3. The bot will reply with a pairing code.
4. Attach to Claude and run /telegram:access pair <code>
5. Run /telegram:access policy allowlist
```

### 5. Attach to Claude Code

Run:

```sh
claw profile attach finance
```

This opens the running Claude Code TUI for the finance profile.

### 6. Pair Telegram

Open the new finance bot in Telegram and send:

```text
hello
```

The bot should reply with something like:

```text
Pairing required — run in Claude Code:

/telegram:access pair abc123
```

In the attached Claude Code session, run exactly:

```text
/telegram:access pair abc123
```

Then lock access down:

```text
/telegram:access policy allowlist
```

### 7. Start chatting

In Telegram, send:

```text
What finance context do you have loaded?
```

Expected behavior:

- Telegram plugin forwards the message into the finance Claude Code profile.
- Claude sees a `<channel source="telegram" chat_id="..." ...>` event.
- Claude replies through the official Telegram `reply` tool.
- The response appears in the finance bot DM.

### 8. Verify status

Run:

```sh
claw profile show finance
```

Expected output includes:

```text
Profile: finance
Runtime: running
Telegram: configured, paired/allowlisted if access.json exists
Scheduler: configured
Claude config: ~/.claude/claw/profiles/finance/config
Telegram state: ~/.claude/claw/profiles/finance/channels/telegram
Launch flags: telegram + scheduler
Warnings: none
```

## Happy-path implementation details

### Profile creation should not install official plugins

Assumption: official Telegram plugin and scheduler plugin are already installed in Claude Code, as in the current main assistant setup.

V1 should check and warn, not manage marketplace installation.

Warning example:

```text
Warning: profile launch expects plugin:telegram@claude-plugins-official to be installed.
If launch fails, start Claude manually and run:
  /plugin install telegram@claude-plugins-official
  /plugin marketplace add /Users/davide/Tools/claw-dash
  /plugin install scheduler@claw-cron
```

### Access file handling

Do not over-manage Telegram `access.json` in V1.

The official plugin supports pairing mode when the file is absent or empty. Let the official `/telegram:access` skill create and mutate access config.

The CLI should inspect and display access state, but avoid hand-editing unless later tests lock the schema.

### Token handling

Minimum viable token handling:

- create the state directory
- print the `.env` path and required format
- never print token values
- mark token configured by file existence and presence of `TELEGRAM_BOT_TOKEN=`

Optional later:

```sh
claw profile create finance --telegram-token env:FINANCE_TELEGRAM_BOT_TOKEN
claw profile telegram set-token finance
```

### Scheduler default

For Telegram profiles, enable scheduler by default because recurring proactive assistant work is part of the personal assistant value.

Create:

```json
{
  "jobs": []
}
```

at:

```text
~/.claude/claw/profiles/<name>/channels/scheduler/jobs.json
```

The scheduler state must be profile-specific so finance jobs do not mix with main jobs.

## Acceptance criteria

V1 is done when this works end to end:

1. `claw profile create finance --telegram` creates the profile directory tree and registry entry.
2. The finance profile has isolated Claude config, Telegram state, and scheduler state.
3. The user can add a BotFather token to the finance Telegram `.env`.
4. `claw profile launch finance` starts a tmux session with `CLAUDE_CONFIG_DIR`, `TELEGRAM_STATE_DIR`, and `SCHEDULER_STATE_DIR` set correctly.
5. The launched Claude command includes `--channels plugin:telegram@claude-plugins-official`.
6. The launched Claude command includes `--dangerously-load-development-channels plugin:scheduler@claw-cron`.
7. Sending a DM to the finance Telegram bot returns a pairing code.
8. Running `/telegram:access pair <code>` inside the finance Claude session approves the DM.
9. Running `/telegram:access policy allowlist` locks access down.
10. A subsequent Telegram DM reaches only the finance profile.
11. Claude replies through the official Telegram `reply` tool.
12. `claw profile show finance` reports runtime and state paths without exposing secrets.

## Failure modes to detect

### Missing token

```text
Profile finance has Telegram enabled but no TELEGRAM_BOT_TOKEN in:
~/.claude/claw/profiles/finance/channels/telegram/.env
```

### Shared Telegram state

If a profile's Telegram state dir is the default `~/.claude/channels/telegram`, warn:

```text
Danger: finance uses the default Telegram state dir. This can steal or corrupt another profile's bot binding.
Expected: ~/.claude/claw/profiles/finance/channels/telegram
```

### Shared bot token

If later we can compare token fingerprints, warn when two profiles use the same Telegram token:

```text
Danger: profiles main and finance appear to use the same Telegram bot token.
Telegram allows only one long-polling consumer per token. Use a separate BotFather bot.
```

Do not print token values. If comparing, compare salted fingerprints.

### Missing channel flag

If runtime is running but command does not include Telegram channel flag:

```text
finance is running, but Telegram channel is not attached.
Expected flag: --channels plugin:telegram@claude-plugins-official
```

### Scheduler missing

If runtime lacks scheduler dev channel flag:

```text
finance is running, but scheduler is not attached.
Expected flag: --dangerously-load-development-channels plugin:scheduler@claw-cron
```

## Later extensions

After the happy path is stable:

- `claw profile import main --from-tmux aoe_Telegram_345a329e`
- token setup command with secure prompt
- profile templates (`finance`, `diet`, `main`)
- profile cloning from `main`
- Discord binding experiment
- status/control tower integration
- scheduler job list/status under `claw profile show`
- profile export/import
- optional shared global memory plus profile-local memory namespaces

## Open questions

1. Does Claude Code load `CLAUDE.md` from `CLAUDE_CONFIG_DIR`, or do we need to launch from the profile config directory / use `--settings` and explicit prompt files? Verify during implementation.
2. Do official plugin slash commands correctly resolve profile-specific `TELEGRAM_STATE_DIR` when launched with env vars? Expected yes, because the server uses `process.env.TELEGRAM_STATE_DIR`; verify end-to-end.
3. Should profile-local skills be implemented as copied files under `config/skills`, symlinks to global skills, or Claude Code plugin settings? V1 can start with `CLAUDE.md` plus existing installed skills and defer deeper skill isolation.
4. Should `profile create` require token immediately, or allow token-missing profiles? Recommendation: allow token-missing and show next step clearly.
