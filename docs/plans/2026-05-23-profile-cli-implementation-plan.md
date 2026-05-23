# Profile CLI Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build and install a working `claw` CLI that manages Claude Code Telegram assistant profiles without changing the current running Telegram assistant.

**Architecture:** Use a small Python stdlib CLI at the claw-tools root. Store intended profile state in `~/.claude/claw/profiles.json` and per-profile directories under `~/.claude/claw/profiles/<name>/`. Detect live Claude/tmux runtimes read-only via `ps` and `tmux`; auto-surface the current Telegram assistant as `main` even before registry migration. Tests run against a temporary `CLAW_HOME` so real Claude data is never touched.

**Tech Stack:** Python 3 stdlib (`argparse`, `json`, `pathlib`, `subprocess`, `uuid`, `shutil`), pytest-compatible unittest tests, tmux/ps for runtime discovery, shell wrapper installed to `~/.local/bin/claw`.

---

## Safety invariants

1. Do not kill, restart, relaunch, mutate, or reconfigure the current running Telegram assistant.
2. `claw sessions list` must show the existing Telegram assistant as `main` by observing the current tmux/Claude process.
3. `claw profile attach main` must attach to the existing tmux session `aoe_Telegram_345a329e`.
4. No command may print Telegram bot tokens.
5. Tests must use `CLAW_HOME=<tempdir>` and must not write to `~/.claude/claw`.
6. Profile deletion must be reversible: move profile directories under a claw trash folder instead of permanent deletion.
7. Profile creation must be allowed without a Telegram token; this supports BotFather-first or CLI-first setup.
8. Official Telegram plugin commands remain the authority for pairing/access: `/telegram:access pair <code>` and `/telegram:access policy allowlist`.

## Target command surface

V1 commands:

```sh
claw --help
claw status
claw sessions list
claw profile list
claw profile show <name>
claw profile create <name> --telegram
claw profile launch <name> [--dry-run]
claw profile attach <name>
claw profile delete <name> --yes
```

Aliases/compatibility:

- `claw sessions list` and `claw profile list` may render the same table.
- `main` is a reserved discovered profile name if not already present in the registry.

## File layout to create

```text
/Users/davide/Tools/claw-tools/
  claw/
    __init__.py
    __main__.py
    cli.py
    discovery.py
    registry.py
    render.py
  tests/
    test_registry.py
    test_cli_profiles.py
    test_discovery.py
  docs/plans/2026-05-23-profile-cli-implementation-plan.md
  install.sh
```

## Task 1: Registry and path model

**Objective:** Implement profile storage using a configurable claw home.

**Files:**
- Create: `claw/__init__.py`
- Create: `claw/registry.py`
- Create: `tests/test_registry.py`

**Step 1: Write failing tests**

Test behaviors:

- `ClawPaths.from_env()` uses `CLAW_HOME` when set.
- default claw home is `~/.claude/claw`.
- `create_profile("finance", telegram=True)` creates:
  - `profiles/finance/config/CLAUDE.md`
  - `profiles/finance/config/settings.json`
  - `profiles/finance/channels/telegram/`
  - `profiles/finance/channels/scheduler/jobs.json`
  - registry entry in `profiles.json`
- created profile has `TELEGRAM_STATE_DIR` and `SCHEDULER_STATE_DIR` paths under its own profile dir.
- invalid profile names are rejected.
- duplicate profile creation is rejected.
- deleting a profile moves its directory under `trash/` and removes the registry entry.

Run:

```sh
python -m unittest tests.test_registry -v
```

Expected: FAIL because modules do not exist.

**Step 2: Implement minimal registry**

Implement:

- `ClawPaths`
- `load_registry(paths)`
- `save_registry(paths, registry)`
- `create_profile(paths, name, telegram=True)`
- `delete_profile(paths, name)`
- profile name validation
- generated `CLAUDE.md` and `settings.json`
- generated scheduler `jobs.json` as `{ "jobs": [] }`

**Step 3: Verify**

Run:

```sh
python -m unittest tests.test_registry -v
```

Expected: PASS.

## Task 2: Runtime discovery for current main assistant

**Objective:** Detect the current Telegram Claude assistant without mutating it.

**Files:**
- Create: `claw/discovery.py`
- Create: `tests/test_discovery.py`

**Step 1: Write failing tests**

Use pure parsing functions with fixture strings; do not depend on live system in unit tests.

Test behaviors:

- parse `ps` output containing current command:
  - tmux session `aoe_Telegram_345a329e`
  - Claude process with `--channels plugin:telegram@claude-plugins-official`
  - scheduler flag `--dangerously-load-development-channels plugin:scheduler@claw-cron`
  - `--session-id ebb1415a-48dd-43bd-bcfa-a5959e5328a0`
  - `--settings /Users/davide/Infra/Claude Code/settings-telegram.json`
- discovery returns a `main` profile candidate when it finds a Telegram Claude process attached to a tmux session.
- discovery does not require or read bot tokens.

Run:

```sh
python -m unittest tests.test_discovery -v
```

Expected: FAIL.

**Step 2: Implement discovery**

Implement:

- `run_command(args)` helper
- `get_ps_output()`
- `get_tmux_sessions()`
- `parse_processes(ps_output)`
- `discover_main_profile(ps_output=None, tmux_output=None)`

Parsing can be pragmatic and macOS-focused for V1:

- find tmux command lines with `tmux new-session ... -s <name> ... claude ... --channels plugin:telegram@claude-plugins-official`
- extract session name after `-s`
- extract session ID/settings/channel flags from the command line
- return `None` if not found

**Step 3: Verify**

Run:

```sh
python -m unittest tests.test_discovery -v
```

Expected: PASS.

## Task 3: CLI read/list/show/status commands

**Objective:** Provide installed CLI-facing read-only views and main attach target.

**Files:**
- Create: `claw/cli.py`
- Create: `claw/__main__.py`
- Create: `claw/render.py`
- Create: `tests/test_cli_profiles.py`

**Step 1: Write failing tests**

Test with temp `CLAW_HOME` and injected fixture discovery through env vars or dependency injection.

Test behaviors:

- `claw profile list` includes registry profiles.
- `claw sessions list` includes discovered `main` even with empty registry.
- `claw profile show finance` prints paths and token configured state without token values.
- `claw profile attach main --print-command` prints `tmux attach -t aoe_Telegram_345a329e`.
- `claw status` exits 0 and includes profile/runtime summary.

Run:

```sh
python -m unittest tests.test_cli_profiles -v
```

Expected: FAIL.

**Step 2: Implement CLI**

Implement argparse command tree:

- `status`
- `sessions list`
- `profile list`
- `profile show`
- `profile attach`

Add `--print-command` to `profile attach` for safe testing.

Default behavior of `profile attach <name>`:

- resolve profile runtime/tmux session
- run `tmux attach -t <session>` with `subprocess.run`

For `main`, if registry lacks a profile entry, use live discovery result.

**Step 3: Verify**

Run:

```sh
python -m unittest tests.test_cli_profiles -v
```

Expected: PASS.

## Task 4: CLI create/delete/launch commands

**Objective:** Add mutating profile lifecycle commands, but keep launch safe and explicit.

**Files:**
- Modify: `claw/cli.py`
- Modify: `claw/registry.py`
- Modify: `tests/test_cli_profiles.py`

**Step 1: Write failing tests**

Test behaviors:

- `claw profile create finance --telegram` creates the expected folder tree under temp `CLAW_HOME`.
- create output includes BotFather/token instructions and next launch command.
- `claw profile launch finance --dry-run` prints tmux launch command with:
  - `CLAUDE_CONFIG_DIR`
  - `TELEGRAM_STATE_DIR`
  - `SCHEDULER_STATE_DIR`
  - Telegram channel flag
  - scheduler channel flag
- `claw profile delete finance --yes` removes profile from registry and moves dir to trash.
- delete refuses without `--yes`.

Run:

```sh
python -m unittest tests.test_cli_profiles -v
```

Expected: FAIL.

**Step 2: Implement lifecycle commands**

Implement:

- `profile create <name> --telegram`
- `profile launch <name> --dry-run`
- `profile delete <name> --yes`

Actual `profile launch <name>` may start tmux. It must refuse if token is missing unless `--allow-missing-token` is explicitly provided. `--dry-run` should work without token.

**Step 3: Verify**

Run:

```sh
python -m unittest tests.test_cli_profiles -v
```

Expected: PASS.

## Task 5: Install wrapper and integration verification

**Objective:** Install `claw` into Davide's PATH and verify against real current assistant plus a throwaway test profile.

**Files:**
- Create: `install.sh`
- Optional create: `bin/claw` if preferred

**Step 1: Write install script**

`install.sh` should:

- create `~/.local/bin`
- write executable `~/.local/bin/claw`
- wrapper runs:

```sh
#!/usr/bin/env bash
exec python3 /Users/davide/Tools/claw-tools/claw/cli.py "$@"
```

**Step 2: Run all tests**

```sh
python -m unittest discover -s tests -v
```

Expected: PASS.

**Step 3: Install**

```sh
bash /Users/davide/Tools/claw-tools/install.sh
command -v claw
claw --help
```

Expected:

- `command -v claw` prints `/Users/davide/.local/bin/claw`
- help renders

**Step 4: Verify current main assistant read-only**

```sh
claw sessions list
claw profile attach main --print-command
```

Expected:

- list includes `main`
- attach print command is `tmux attach -t aoe_Telegram_345a329e`
- current Telegram assistant remains running; do not attach interactively unless needed

**Step 5: Verify create/cleanup with throwaway profile**

```sh
claw profile create hermes-test-finance --telegram
claw profile show hermes-test-finance
claw profile launch hermes-test-finance --dry-run
claw profile delete hermes-test-finance --yes
claw profile list
```

Expected:

- folder is created
- dry-run launch command contains isolated env vars
- deletion moves folder to claw trash and removes profile from list

## Final acceptance checklist

- [ ] Plan saved at `docs/plans/2026-05-23-profile-cli-implementation-plan.md`.
- [ ] `python -m unittest discover -s tests -v` passes.
- [ ] `claw` installed at `~/.local/bin/claw`.
- [ ] `claw sessions list` shows `main` for current running Telegram assistant.
- [ ] `claw profile attach main --print-command` points to `aoe_Telegram_345a329e`.
- [ ] No command altered or restarted the current assistant.
- [ ] Throwaway profile creation works.
- [ ] Throwaway profile cleanup works through CLI.
- [ ] Final response includes exact steps to create a real finance assistant with BotFather.
