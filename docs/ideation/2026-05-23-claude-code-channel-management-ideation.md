---
title: Claude Code Channel Management Ideation
date: 2026-05-23
topic: Claude Code personal-assistant channel/session management
source_skill: dstack-ideation
status: draft
---

# Claude Code Channel Management Ideation

## Summary

Davide wants Claude Code channels to behave like a manageable personal-assistant substrate rather than a set of manually launched, persistent, plugin-owned terminal sessions. The core pain is not that Telegram/Discord channels are impossible; it is that adding a new assistant context requires remembering low-level session/process/plugin/state-dir details.

The strongest recommendation is to build a layered management surface:

1. A read-only Assistant Control Tower first: session inventory, channel attachment matrix, scheduler/job status, state files, launch commands, logs, and failure hints.
2. A Channel Profile Registry on top: named profiles like `main`, `diet`, `work`, mapping to platform, plugin, state dir, bot token location, access config, aliases, and intended Claude launch recipe.
3. Then an Add Channel Wizard / command flow that writes safe config and produces or launches the right Claude session.

Do not start with a full router daemon. It is the interesting long-term architecture, but it is the highest-risk path because official Telegram/Discord channels are currently owned by one Claude Code session/process and the channel feature is still research-preview.

## Grounding context

- Strategy anchor: `STRATEGY.md` defines claw-tools as thin assistant glue around Claude Code, not a replacement. Success signals are understandable state, low-friction context creation, and recoverable operation.
- Repo/product context: `scheduler/README.md` already implements one missing assistant primitive: cron events into a running Claude Code session plus `claude -p` subprocesses for scheduled work. It stores state under `~/.claude/channels/scheduler/`, with `jobs.json`, logs, locks, and slash commands for configure/add/list/remove/run.
- User/request context: Davide has a personal upload assistant on Telegram and wants to add new contexts like a diet channel, Telegram topic, or Discord channel without manually managing persistent Claude Code sessions.
- External context: Claude Code channels push external events into a running session via MCP server capability `experimental['claude/channel']`; events arrive as `<channel source="...">` blocks with metadata. Reply tools route back using identifiers like `chat_id`.
- External context: Official Telegram and Discord plugins are channel plugins installed into a Claude Code session and relaunched with `--channels plugin:<name>@claude-plugins-official`.
- External context: Telegram state is under `~/.claude/channels/telegram/`, token in `.env`, access in `access.json`; multiple bot instances can use different `TELEGRAM_STATE_DIR`. Telegram groups are opt-in by supergroup ID, require mention by default, and Telegram Bot API has no history/search.
- External context: Discord state is under `~/.claude/channels/discord/`, token in `.env`, access in `access.json`; multiple bot instances can use different `DISCORD_STATE_DIR`. Discord guild channels are opt-in by channel snowflake; threads inherit parent opt-in; Discord plugin exposes recent-history and attachment download tools.
- External context: Channel reference supports custom channel servers, reply tools, inbound sender gating, and optional permission relay via `experimental['claude/channel/permission']`.
- Uncertainties: Telegram topic metadata needs empirical probing in the actual official plugin. The docs clearly describe groups but not enough about forum topic/thread routing. Also, `claude --print` not surfacing channel events appears to be an observed limitation in this repo’s README, so interactive/supervised sessions remain the realistic path.

## Topic axes

- Session/process ownership: which running Claude Code session owns which channel plugin and state dir.
- Channel/profile onboarding: how a user adds `main`, `diet`, a Telegram group/topic, or a Discord channel/thread safely.
- Routing and identity: how named assistant contexts map to raw platform IDs, state dirs, and reply targets.
- Observability/control: how to inspect sessions, attached plugins, cron jobs, logs, failures, locks, and launch commands.
- Recovery and safety: how to avoid dropped messages, accidental broad access, stale locks, wrong-session launches, and cross-posting.

## Candidate generation overview

Three parallel ideation passes generated roughly 45 raw candidates:

- Routing/session model: channel registry, identity profiles, router daemon, topic-aware bindings, route-on-first-message, alias book, ownership claims, unrouted inbox.
- Onboarding/config UX: `claw channel add`, first-run wizard, profile clone, access presets, state-dir registry, doctor command, launch generator, safe remove/disable.
- Operations/control: Assistant Control Tower, process/session inventory, channel attachment matrix, scheduler health panel, cron timeline, run history explorer, failure inbox, stale lock recovery, black-box recorder.

The surviving ideas below are intentionally layered so the first version can ship without betting on private Claude Code internals.

## Rejected ideas and themes

| Rejected direction | Reason |
| --- | --- |
| Full session router daemon as V1 | Architecturally attractive, but too much surface area too early: process supervision, forwarding, reply-tool mediation, permission relay, failure recovery, and compatibility risk with research-preview channel semantics. Better as a later scaling path after registry/control surfaces exist. |
| Route-on-first-message as core UX | Nice assistant-native feel, but official plugin access gates may drop unknown/unconfigured sources before the manager can see them. It also creates spam and authorization complexity. Keep as later enhancement or intake mode. |
| Multi-session same-channel concurrency | Davide called this out as likely problematic. Two sessions handling the same Telegram/Discord channel invites duplicate replies, state races, and confused memory. Prefer explicit single-owner bindings and make conflict detection visible. |
| Hide all implementation details behind a friendly wizard | Too opaque for this problem. Davide explicitly wants to see what is going on behind the hood. The product should expose raw state paths, launch args, IDs, and logs, not abstract them away completely. |
| Build a new Telegram/Discord bridge from scratch immediately | Would dodge official plugin limitations but violates the thin-glue strategy and duplicates maintained integrations. First reuse official plugins and add management around them. |
| Make cron management a separate product surface | Cron/job state is part of assistant operations. Splitting it away would preserve the current problem: users still cannot see sessions, channels, and background work together. |
| Use only Claude slash commands for setup | Useful inside a session, but channel setup often requires relaunching sessions and inspecting local files/processes. A CLI/control surface outside the Claude session is needed. |
| Treat channel IDs as the primary interface | Raw Telegram IDs and Discord snowflakes are unavoidable internally, but user-facing management should use stable aliases/profiles like `main`, `diet`, `telegram-family`, `discord-lab`. |
| Let every profile freely share state dirs | Sharing plugin state across assistant identities risks cross-talk, allowlist confusion, and hard-to-debug ownership. State dirs should be explicit and usually per profile. |

## Ranked survivors

### 1. Assistant Control Tower

- What it is: A read-only local status surface that shows running Claude Code sessions, attached channel plugins, scheduler state, configured profiles/state dirs, cron jobs, recent runs, locks, launch commands, and failure hints. Start as CLI/TUI; web UI can come later.
- Basis: direct. `STRATEGY.md` says understandable state and recoverable operation are core success signals. The scheduler already has state and logs, but they are not joined with session/channel ownership.
- Why it matters: It answers the first design question immediately: “How can we see all sessions in one place?” It also gives Davide confidence before adding more automation.
- Carrying cost: medium. Process inspection, filesystem aggregation, JSON validation, and rendering are tractable. Live Claude session internals may be incomplete, so the first version should label inferred/unknown state honestly.
- Why now / why not now: Now, because it de-risks every later feature and requires minimal mutation. Not now only if the goal is a pure proof-of-concept of channel creation; but operational clarity is the repo’s main strategic gap.
- Handoff recommendation: brainstorm the exact CLI/TUI shape and data model: `claw status`, `claw sessions`, `claw channels`, `claw scheduler`.

### 2. Channel Profile Registry

- What it is: A durable registry mapping friendly names like `main`, `diet`, `work`, or `discord-lab` to platform, plugin, bot token location, state dir, access file, aliases, expected launch flags, and intended owning session.
- Basis: direct. Official plugins support multiple instances via `TELEGRAM_STATE_DIR`/`DISCORD_STATE_DIR`, but this is currently manual. Davide thinks in assistant contexts, not directories.
- Why it matters: This creates the missing product primitive. Adding a channel becomes “create or modify a profile” instead of “remember how Claude Code channel plugins, access.json, .env, and persistent sessions work.”
- Carrying cost: medium. Needs schema, migration/import from existing `~/.claude/channels/*`, drift detection, and clear conventions for state-dir naming.
- Why now / why not now: Now, because registry + control tower creates an inspectable source of truth without taking over message routing. Avoid over-designing profile semantics until actual Telegram topic behavior is probed.
- Handoff recommendation: brainstorm schema and import behavior. Prefer a small `profiles.json` plus derived facts from existing plugin state, not a database.

### 3. Channel Attachment Matrix

- What it is: A table that joins desired profiles to actual running sessions: session PID/cwd/argv, attached `--channels` plugins, env/state dirs, and gaps like “profile `diet` exists but no running session owns it” or “scheduler attached, Telegram missing.”
- Basis: direct. Claude Code channels attach at launch via `--channels plugin:...`; existing scheduler docs require exact relaunch commands.
- Why it matters: Most failures are likely “wrong session launched with wrong flags” rather than deep code bugs. This makes ownership and mismatch obvious.
- Carrying cost: low-medium. Process argv parsing is feasible on macOS; env discovery may be limited for other users’ processes, so registry/launch manifests should fill gaps.
- Why now / why not now: Now as part of Control Tower. It is the bridge between friendly profiles and actual Claude sessions.
- Handoff recommendation: implement as read-only first; avoid auto-restarts until status reporting is trusted.

### 4. Add Channel Wizard / `claw channel add`

- What it is: A guided flow to add a Telegram/Discord channel profile. It creates state dirs, writes/redacts env/token pointers, initializes `access.json` with safe defaults, assigns aliases, prints the exact launch command, and gives pairing/access instructions.
- Basis: direct. Official setup requires plugin install, token config, relaunch with `--channels`, pair, then switch to allowlist. The user explicitly wants adding a new channel to be easy.
- Why it matters: It answers the second design question: “How can the user add a new channel?” It turns setup into a repeatable workflow.
- Carrying cost: medium. Secret handling, idempotent writes, plugin-specific branches, and interruption recovery matter. But it can be shipped incrementally after the registry exists.
- Why now / why not now: Do not build before the registry/control tower, because otherwise the wizard will create more hidden state. Build second.
- Handoff recommendation: brainstorm a small happy path first: Telegram DM profile and Discord channel profile. Add Telegram group/topic only after empirical plugin probing.

### 5. Safe Defaults and Access Presets

- What it is: Named policy templates for `access.json`: `dm-only`, `mentioned-groups`, `discord-channel-only`, `noisy-group-safe`, `private-main`, etc. Defaults should prefer allowlist/pairing, require mention in groups/channels, conservative chunking, and visible caveats.
- Basis: direct. Telegram/Discord access schemas have many knobs; Telegram `--no-mention` requires disabling BotFather privacy; Discord threads inherit parent channel opt-in.
- Why it matters: Onboarding cannot become easier by making bots listen everywhere. Presets encode safe product decisions and reduce accidental exposure.
- Carrying cost: low-medium. Mostly templates plus schema validation, but must track upstream plugin schema changes.
- Why now / why not now: Build into `channel add`; do not expose every access field in the first wizard.
- Handoff recommendation: define 3 presets only for V1: `private-dm`, `mentioned-group`, `discord-channel-mentioned`.

### 6. Alias Book and Human-Readable IDs

- What it is: Stable aliases for raw Telegram user IDs, supergroup IDs, topic/thread IDs, Discord channel snowflakes, and Discord thread IDs. Examples: `me`, `diet`, `family`, `discord-ai`, `telegram-main-topic`.
- Basis: direct/reasoned. Official tools route by raw IDs like `chat_id`; Discord and Telegram IDs are permanent but human-hostile.
- Why it matters: Scheduler prompts, logs, channel profiles, and status screens become readable. It also lowers risk of sending a message to the wrong place.
- Carrying cost: low-medium. Needs uniqueness rules, stale target warnings, and maybe reverse lookup from observed inbound events.
- Why now / why not now: Add early because it makes every other surface legible.
- Handoff recommendation: keep aliases in the profile registry; do not create a separate subsystem yet.

### 7. Scheduler + Channel Operations Panel

- What it is: Fold existing scheduler data into the control surface: next fires, last runs, cost, status, logs, corrupt jobs file warnings, stale locks, run-now/remove/disable commands, and failure inbox.
- Basis: direct. `scheduler/README.md` already defines jobs, logs, locks, configure/list/remove/run. The user explicitly asks to manage cron jobs and see what is going on.
- Why it matters: Cron jobs are part of the assistant’s behavior. If they are not visible alongside sessions/channels, the system remains operationally fragmented.
- Carrying cost: low-medium. Most data already exists. Mutating controls require confirmations and atomic writes, but read-only visibility can ship first.
- Why now / why not now: Now, because the repo already has scheduler state; it is the quickest way to make the dashboard feel real.
- Handoff recommendation: start read-only: `claw scheduler status`, `claw scheduler logs <job>`, `claw scheduler timeline`.

### 8. Session Launch Recipes / Manifests

- What it is: Generated launch recipes for named assistant modes, such as `main = telegram + scheduler`, `diet = telegram-state-dir-diet + scheduler`, `debug = scheduler shell mode`. Recipes print exact `claude` commands and env vars; later a supervisor can execute them.
- Basis: direct. Existing docs have fragile launch commands including hidden development-channel flags. Official plugins require relaunch with `--channels`.
- Why it matters: This reduces session startup cognitive load without prematurely building a daemon.
- Carrying cost: low-medium. Templating is simple; the main work is keeping flags aligned with Claude Code and profile state.
- Why now / why not now: Build with registry/control tower. Launching is where profile intent meets actual session process.
- Handoff recommendation: output commands first; execute/supervise later.

### 9. Failure Inbox and Recovery Playbooks

- What it is: A focused view of things requiring attention: failed job runs, max-budget exits, timeouts, stale locks, corrupt `jobs.json`, missing token/env, missing channel attachment, and “session not receiving channel events” diagnostics.
- Basis: direct. README already lists troubleshooting cases; strategy says recoverable operation matters.
- Why it matters: Raw dashboards are useful, but the assistant should also tell Davide what needs fixing and how.
- Carrying cost: medium. Needs heuristics and careful confidence labeling. Avoid auto-fixing until signals are reliable.
- Why now / why not now: After the read-only control tower; it adds opinionated diagnosis on top of aggregated state.
- Handoff recommendation: encode only known failure modes first; never pretend to infer hidden Claude internals.

### 10. Router Daemon / Broker, later

- What it is: A long-term daemon that owns Telegram/Discord bridge processes and forwards normalized events to selected Claude sessions/workers by routing table. It could also mediate replies and permission relay.
- Basis: reasoned. It directly addresses plugin-owned-by-single-session limitations, but requires building around research-preview channel semantics.
- Why it matters: This is the clean architecture if the product grows: channels become durable inputs, Claude sessions become workers, routing becomes explicit.
- Carrying cost: high. Process supervision, event replay, reply mediation, permission relay, routing conflicts, duplicate prevention, and compatibility risk.
- Why now / why not now: Not V1. Keep the design path open, but do not start here. Build registry and observability first so a router has real requirements.
- Handoff recommendation: revisit after Control Tower + Profile Registry + Add Channel Wizard have exposed the actual operational constraints.

## Recommended next step

Run `dstack-brainstorming` on the top survivor: Assistant Control Tower + Channel Profile Registry as the first product slice.

Recommended V1 scope:

- `claw status`: one screen with sessions, channels/profiles, scheduler health, and failures.
- `claw channel list --behind-the-hood`: profiles, state dirs, access files, launch flags, raw IDs, safe/default warnings.
- `claw scheduler status`: jobs, next fires, recent failures, stale locks.
- Profile registry import from existing `~/.claude/channels/telegram`, `discord`, and `scheduler` state.
- Launch recipe generation, not automatic supervision yet.

This slice solves visibility first and sets up the add-channel workflow without creating more hidden state.

## Handoff notes for brainstorming

Selected direction: Assistant Control Tower + Channel Profile Registry.

Why it won:

- It directly matches the repo strategy and Davide’s design questions.
- It is the lowest-risk first step because it can be mostly read-only.
- It improves the existing scheduler immediately.
- It creates the data model needed for `channel add` without prematurely building a router daemon.

Known constraints:

- Official Telegram/Discord plugins are session-attached and own their state under `~/.claude/channels/<plugin>` unless state-dir env vars override it.
- Telegram has no history/search through the Bot API, so status/recovery cannot promise replay of old Telegram messages unless we store them ourselves on arrival.
- Discord can fetch recent messages and attachments, so Discord recovery can be richer.
- Telegram group topics need empirical validation against actual plugin event metadata before making them first-class.
- `claude --print` not surfacing channel events means a practical assistant session is still interactive/supervised, not print-mode-only.
- Avoid managing two sessions on one channel until conflict detection and ownership semantics are explicit.

Do not reopen without new evidence:

- Full router daemon as V1.
- Replacing official Telegram/Discord plugins before exhausting management around them.
- Opaque wizard-only UX that hides state paths and launch commands.
- Shared state dirs across profiles by default.
