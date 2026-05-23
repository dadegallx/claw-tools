---
name: claw-tools
last_updated: 2026-05-23
---

# claw-tools Strategy

## Target problem

Claude Code has many of the primitives for a capable local assistant, but its session and interaction model is built for coding workflows, not a chat-native personal assistant. Simple personal-assistant actions, like adding the bot to a new Telegram channel or maintaining multiple contexts, become cumbersome instead of natural.

## Our approach

Use Claude Code as the execution engine and source of agent capabilities, then build the thin personal-assistant layer around it. This repo owns the glue Claude Code is missing for assistant use: session/channel management, scheduling, visibility, and operational control, without rebuilding Claude Code itself or cloning all of OpenClaw.

OpenClaw is the reference shape: a local, persistent personal AI assistant that can be reached from chat apps, remember context, run tools, browse, use the shell, and perform background work. claw-tools aims for the useful subset of that experience that can be unlocked by enhancing Claude Code instead of replacing it.

## Who it's for

**Primary:** Davide - use Claude Code as a persistent personal assistant from Telegram and other lightweight contexts, with recurring tasks and multiple assistant sessions managed without ceremony.

**Secondary:** Developers interested in using their Claude/Anthropic subscription and Claude Code's existing tool stack as the basis for a hackable personal assistant.

## Key success signals

- **Time saved** - maintaining and operating personal assistants takes less time than doing the same work manually or wiring it repeatedly by hand.
- **Understandable state** - it is easy to see what is running, where it is running, which session or channel owns it, and why it exists.
- **Low-friction context creation** - adding a new assistant session or Telegram context feels like a normal assistant action, not a debugging project.
- **Recoverable operation** - sessions, scheduled jobs, and assistant runs can be inspected, resumed, or fixed without guessing.

## Tracks

### Claude Code integration glue

Make Claude Code usable as the assistant execution substrate without forking or replacing its core agent, model, and tool runtime.

_Why it serves the approach:_ The whole bet is that Claude Code already contains most of the hard execution machinery; this repo should add the assistant layer around it.

### Session and channel management

Create, route, name, and maintain assistant contexts across Telegram-style channels and other lightweight entry points.

_Why it serves the approach:_ A personal assistant needs to follow the user's contexts naturally; Claude Code's default session model makes that too cumbersome.

### Scheduling and background work

Support cron-like and recurring assistant work that can run proactively without the user manually starting every task.

_Why it serves the approach:_ OpenClaw-style usefulness comes from background assistance, not only interactive coding sessions.

### Observability and control

Expose dashboards, logs, status, and control surfaces that make assistant state obvious and recoverable.

_Why it serves the approach:_ The most important success signal is understanding what is going on; without visibility, the assistant becomes harder to maintain than it is worth.
