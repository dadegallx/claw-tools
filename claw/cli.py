#!/usr/bin/env python3
import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claw.discovery import discover_main_profile
from claw.registry import ClawPaths, create_profile, delete_profile, load_registry, token_configured
from claw.render import render_profile_show, render_profile_table

TELEGRAM_PLUGIN = "plugin:telegram@claude-plugins-official"
SCHEDULER_PLUGIN = "plugin:scheduler@claw-cron"


def registry_profiles(paths):
    registry = load_registry(paths)
    return registry["profiles"]


def discovered_profiles():
    main_profile = discover_main_profile()
    return {"main": main_profile} if main_profile else {}


def combined_profiles(paths):
    profiles = dict(registry_profiles(paths))
    for name, profile in discovered_profiles().items():
        profiles.setdefault(name, profile)
    return profiles


def build_launch_command(profile):
    tmux = profile["tmux"]
    claude = profile["claude"]
    config_dir = profile["claudeConfigDir"]
    telegram_dir = profile["bindings"]["telegram"]["stateDir"]
    scheduler_dir = profile["bindings"]["scheduler"]["stateDir"]
    settings = claude["settings"]
    inner = [
        "exec", "env",
        f"CLAUDE_CONFIG_DIR={config_dir}",
        f"TELEGRAM_STATE_DIR={telegram_dir}",
        f"SCHEDULER_STATE_DIR={scheduler_dir}",
        "claude",
        "--settings", settings,
    ] + list(claude.get("args", [])) + ["--session-id", claude["sessionId"]]
    inner_s = " ".join(shlex.quote(x) for x in inner)
    return [
        "tmux", "new-session", "-d",
        "-s", tmux["sessionName"],
        "-c", profile.get("cwd", str(Path.home())),
        "-x", str(tmux.get("width", 128)),
        "-y", str(tmux.get("height", 48)),
        inner_s,
    ]


def command_to_string(cmd):
    return " ".join(shlex.quote(str(part)) for part in cmd)


def print_permission_note(profile):
    print("Permission note: created profiles launch Claude with --dangerously-skip-permissions.")
    print(f"Working directory (cwd): {profile.get('cwd', str(Path.home()))}")
    print("This matches the current main assistant behavior and grants broad file/tool permission in that cwd.")


def cmd_status(args):
    paths = ClawPaths.from_env()
    profiles = combined_profiles(paths)
    registry = load_registry(paths)
    print(f"Registry: {paths.registry_file} ({len(registry['profiles'])} configured)")
    print(f"Runtime profiles: {len([p for p in profiles.values() if p.get('runtime', {}).get('status') == 'running'])}")
    print(render_profile_table(list(profiles.values())), end="")
    return 0


def cmd_list(args):
    paths = ClawPaths.from_env()
    profiles = combined_profiles(paths)
    print(render_profile_table(list(profiles.values())), end="")
    return 0


def cmd_show(args):
    paths = ClawPaths.from_env()
    profiles = combined_profiles(paths)
    profile = profiles.get(args.name)
    if not profile:
        print(f"profile not found: {args.name}", file=sys.stderr)
        return 1
    print(render_profile_show(profile), end="")
    return 0


def cmd_create(args):
    paths = ClawPaths.from_env()
    if not args.telegram:
        print("only --telegram profiles are supported in V1", file=sys.stderr)
        return 2
    try:
        profile = create_profile(paths, args.name, telegram=True)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    telegram = profile["bindings"]["telegram"]
    scheduler = profile["bindings"]["scheduler"]
    print(f"Created profile: {args.name}")
    print(f"Profile dir: {profile['profileDir']}")
    print(f"Telegram state: {telegram['stateDir']}")
    print(f"Scheduler state: {scheduler['stateDir']}")
    print()
    print_permission_note(profile)
    print()
    print("Telegram requires a dedicated BotFather bot per independent Claude profile.")
    print("Create a bot with @BotFather, then save your token to:")
    print()
    print(f"  {telegram['envFile']}")
    print()
    print("Format:")
    print("  TELEGRAM_BOT_TOKEN=<PASTE_TOKEN_HERE>")
    print()
    print("Then run:")
    print(f"  claw profile launch {args.name}")
    return 0


def cmd_launch(args):
    paths = ClawPaths.from_env()
    profiles = registry_profiles(paths)
    profile = profiles.get(args.name)
    if not profile:
        print(f"profile not found: {args.name}", file=sys.stderr)
        return 1
    env_file = profile["bindings"]["telegram"].get("envFile")
    if not args.dry_run and not args.allow_missing_token and not token_configured(env_file):
        print(f"Profile {args.name} has Telegram enabled but no TELEGRAM_BOT_TOKEN in:", file=sys.stderr)
        print(env_file, file=sys.stderr)
        print("Use --allow-missing-token to launch anyway.", file=sys.stderr)
        return 1
    cmd = build_launch_command(profile)
    if args.dry_run:
        print(command_to_string(cmd))
        print()
        print_permission_note(profile)
        return 0
    try:
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"launch failed: {e}", file=sys.stderr)
        return 1
    print(f"Started profile: {args.name}")
    print(f"tmux: {profile['tmux']['sessionName']}")
    print(f"Attach with: claw profile attach {args.name}")
    print()
    print_permission_note(profile)
    print()
    print("Next:")
    print("1. Open your new Telegram bot and send a DM, for example: hello")
    print("2. Attach to Claude and run /telegram:access pair <code>")
    print("3. Run /telegram:access policy allowlist")
    return 0


def cmd_attach(args):
    paths = ClawPaths.from_env()
    profile = combined_profiles(paths).get(args.name)
    if not profile:
        print(f"profile not found: {args.name}", file=sys.stderr)
        return 1
    tmux_name = profile.get("runtime", {}).get("tmuxSession") or profile.get("tmux", {}).get("sessionName")
    if not tmux_name:
        print(f"no tmux session known for profile: {args.name}", file=sys.stderr)
        return 1
    cmd = ["tmux", "attach", "-t", tmux_name]
    if args.print_command:
        print(command_to_string(cmd))
        return 0
    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("tmux not found", file=sys.stderr)
        return 1
    return 0


def cmd_delete(args):
    if not args.yes:
        print("refusing to delete without --yes", file=sys.stderr)
        return 2
    paths = ClawPaths.from_env()
    try:
        trashed = delete_profile(paths, args.name)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    print(f"Deleted profile: {args.name}")
    if trashed:
        print(f"Moved to trash: {trashed}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="claw", description="Manage claw Claude Code profiles")
    sub = parser.add_subparsers(dest="command")

    status = sub.add_parser("status")
    status.set_defaults(func=cmd_status)

    sessions = sub.add_parser("sessions")
    sessions_sub = sessions.add_subparsers(dest="sessions_command")
    sessions_list = sessions_sub.add_parser("list")
    sessions_list.set_defaults(func=cmd_list)

    profile = sub.add_parser("profile")
    profile_sub = profile.add_subparsers(dest="profile_command")

    profile_list = profile_sub.add_parser("list")
    profile_list.set_defaults(func=cmd_list)

    show = profile_sub.add_parser("show")
    show.add_argument("name")
    show.set_defaults(func=cmd_show)

    create = profile_sub.add_parser("create")
    create.add_argument("name")
    create.add_argument("--telegram", action="store_true")
    create.set_defaults(func=cmd_create)

    launch = profile_sub.add_parser("launch")
    launch.add_argument("name")
    launch.add_argument("--dry-run", action="store_true")
    launch.add_argument("--allow-missing-token", action="store_true")
    launch.set_defaults(func=cmd_launch)

    attach = profile_sub.add_parser("attach")
    attach.add_argument("name")
    attach.add_argument("--print-command", action="store_true")
    attach.set_defaults(func=cmd_attach)

    delete = profile_sub.add_parser("delete")
    delete.add_argument("name")
    delete.add_argument("--yes", action="store_true")
    delete.set_defaults(func=cmd_delete)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
