import os
import re
import shlex
import subprocess

TELEGRAM_FLAG = "plugin:telegram@claude-plugins-official"
SCHEDULER_FLAG = "plugin:scheduler@claw-cron"


def run_command(args):
    try:
        return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_ps_output():
    if "CLAW_TEST_PS_OUTPUT" in os.environ:
        return os.environ["CLAW_TEST_PS_OUTPUT"]
    return run_command(["ps", "axo", "pid,command"])


def get_tmux_sessions():
    if "CLAW_TEST_TMUX_OUTPUT" in os.environ:
        return os.environ["CLAW_TEST_TMUX_OUTPUT"]
    return run_command(["tmux", "list-sessions"])


def _redact_command(command):
    return re.sub(r"([A-Za-z0-9_]*(?:TOKEN|SECRET|KEY)[A-Za-z0-9_]*)=[^\s'\"]+", r"\1=***", command)


def _regex_after(flag, command):
    if flag == "--settings":
        m = re.search(r"(?:^|\s)--settings\s+(.+?)(?=\s+--[A-Za-z-]+|$)", command)
    else:
        m = re.search(r"(?:^|\s)" + re.escape(flag) + r"\s+([^\s'\"]+|'[^']+'|\"[^\"]+\")", command)
    if not m:
        return None
    return m.group(1).strip("'\"")


def _safe_runtime(command, pid=None):
    # Never preserve the full process command; it can contain environment secrets.
    runtime = {"pid": pid}
    parts = shlex.split(command)
    for i, part in enumerate(parts):
        if part == "-s" and i + 1 < len(parts):
            runtime["tmuxSession"] = parts[i + 1]
        elif part.startswith("-s") and len(part) > 2:
            runtime["tmuxSession"] = part[2:]
    session_id = _regex_after("--session-id", command)
    settings = _regex_after("--settings", command)
    if session_id:
        runtime["sessionId"] = session_id
    if settings:
        runtime["settings"] = settings
    runtime["telegram"] = TELEGRAM_FLAG in command
    runtime["scheduler"] = SCHEDULER_FLAG in command
    return runtime


def parse_processes(ps_output):
    found = []
    for raw in ps_output.splitlines():
        line = raw.strip()
        if not line or TELEGRAM_FLAG not in line or "tmux" not in line or "claude" not in line:
            continue
        pid = None
        command = line
        first = line.split(maxsplit=1)
        if first and first[0].isdigit():
            pid = first[0]
            command = first[1] if len(first) > 1 else ""
        try:
            runtime = _safe_runtime(command, pid=pid)
        except ValueError:
            continue
        if runtime.get("tmuxSession"):
            found.append(runtime)
    return found


def discover_main_profile(ps_output=None, tmux_output=None):
    if ps_output is None:
        ps_output = get_ps_output()
    runtimes = parse_processes(ps_output)
    if not runtimes:
        return None
    runtime = None
    for candidate in runtimes:
        if candidate.get("tmuxSession") == "aoe_Telegram_345a329e":
            runtime = candidate
            break
    if runtime is None:
        runtime = runtimes[0]
    runtime = dict(runtime)
    runtime["status"] = "running"
    return {
        "name": "main",
        "description": "Discovered current Telegram assistant",
        "runtime": runtime,
        "tmux": {"sessionName": runtime.get("tmuxSession")},
        "bindings": {
            "telegram": {"enabled": True, "botTokenConfigured": True},
            "scheduler": {"enabled": bool(runtime.get("scheduler"))},
        },
        "discovered": True,
    }
