---
name: claw-dash
last_updated: 2026-05-24
---

# claw-dash Strategy

## What this is

claw-dash is the management and control surface for Davide's "claws" — Claude-Code-based personal assistants. The always-on Telegram-connected session (main) is one claw. The budget assistant is another. Future channel-specific or topic-specific assistants will be claws too.

The dash is the thin layer that lets you see what claws exist, what they're doing, refresh them, schedule prompts into them, and recover when things drift — all without rebuilding Claude Code itself.

## Target problem

Claude Code has many of the primitives for a capable local assistant, but its session and interaction model is built for coding workflows, not chat-native personal assistant use. Simple personal-assistant actions — adding a bot to a new Telegram channel, maintaining multiple parallel claws, knowing whether your morning refresh actually ran — become cumbersome or invisible instead of natural.

## Our approach

Use Claude Code as the execution engine and source of agent capabilities, then build the thin dash plus glue layer around it. claw-dash owns:

- Session and channel management — create, route, name, maintain claw contexts across Telegram and other entry points
- Scheduling and background work — cron-like recurring work that runs proactively, eventually injected as prompts into live claws rather than headless subprocesses
- Observability and control — surfaces (CLI today, dashboard tomorrow) that make claw state obvious and recoverable

OpenClaw is the reference shape: a local, persistent personal AI assistant reachable from chat apps, with memory, tools, browsing, shell, and background work. claw-dash aims for the useful subset of that experience that can be unlocked by enhancing Claude Code instead of replacing it.

## Who it's for

**Primary:** Davide — use Claude Code as a persistent personal assistant from Telegram and other lightweight contexts, with multiple parallel claws managed without ceremony.

**Secondary:** Developers interested in using their Claude/Anthropic subscription and Claude Code's existing tool stack as the basis for a hackable personal assistant.

## Key success signals

- **Time saved** — running multiple claws takes less time than wiring them by hand each time.
- **Understandable state** — it is easy to see what is running, where it is running, which claw owns it, and why it exists.
- **Low-friction context creation** — adding a new claw or Telegram context feels like a normal assistant action, not a debugging project.
- **Recoverable operation** — claws, scheduled jobs, and assistant runs can be inspected, resumed, or fixed without guessing.

## Tracks

### Claude Code integration glue

Make Claude Code usable as the substrate for managed claws without forking or replacing its core agent, model, and tool runtime.

_Why it serves the approach:_ The whole bet is that Claude Code already contains most of the hard execution machinery; claw-dash should add the management layer around it.

### Session and channel management

Create, route, name, and maintain claws across Telegram-style channels and other lightweight entry points.

_Why it serves the approach:_ A personal assistant needs to follow the user's contexts naturally; Claude Code's default session model makes that too cumbersome.

### Scheduling and background work

Support cron-like recurring assistant work — initially as headless subprocesses, eventually as prompts injected into the live claw — so claws can run proactively without the user manually starting every task.

_Why it serves the approach:_ OpenClaw-style usefulness comes from background assistance, not only interactive coding sessions.

### Observability and control

Expose the dash itself: dashboards, logs, status, and control surfaces that make claw state obvious and recoverable.

_Why it serves the approach:_ The most important success signal is understanding what is going on; without visibility, claws become harder to maintain than they are worth. This is the namesake track — the "dash" in claw-dash.
