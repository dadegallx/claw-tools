from pathlib import Path

from .registry import token_configured


def _token_state(profile):
    telegram = profile.get("bindings", {}).get("telegram")
    if not telegram or not telegram.get("enabled"):
        return "disabled"
    env_file = telegram.get("envFile")
    if env_file:
        return "configured" if token_configured(env_file) else "token-missing"
    return "configured" if telegram.get("botTokenConfigured") else "unknown"


def _scheduler_state(profile):
    scheduler = profile.get("bindings", {}).get("scheduler")
    return "configured" if scheduler and scheduler.get("enabled") else "disabled"


def render_profile_table(profiles, runtimes=None):
    runtimes = runtimes or {}
    rows = [["NAME", "TELEGRAM", "SCHEDULER", "RUNTIME", "TMUX"]]
    for profile in profiles:
        name = profile["name"]
        runtime = runtimes.get(name) or profile.get("runtime") or {}
        status = runtime.get("status") or "stopped"
        tmux = runtime.get("tmuxSession") or profile.get("tmux", {}).get("sessionName") or "-"
        rows.append([name, _token_state(profile), _scheduler_state(profile), status, tmux])
    widths = [max(len(str(row[i])) for row in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)).rstrip() for row in rows) + "\n"


def render_profile_show(profile, runtime=None):
    runtime = runtime or profile.get("runtime") or {}
    telegram = profile.get("bindings", {}).get("telegram", {})
    scheduler = profile.get("bindings", {}).get("scheduler", {})
    env_file = telegram.get("envFile")
    access_file = telegram.get("accessFile")
    token_yes = telegram.get("botTokenConfigured") if not env_file else token_configured(env_file)
    lines = [
        f"Profile: {profile.get('name')}",
        f"Runtime: {runtime.get('status', 'stopped')}",
        f"Profile dir: {profile.get('profileDir', '-')}",
        f"Claude config: {profile.get('claudeConfigDir', '-')}",
        f"Telegram state: {telegram.get('stateDir', '-')}",
        f"Scheduler state: {scheduler.get('stateDir', '-')}",
        f"Token configured: {'yes' if token_yes else 'no'}",
        f"Access file exists: {'yes' if access_file and Path(access_file).exists() else 'no'}",
        f"tmux: {runtime.get('tmuxSession') or profile.get('tmux', {}).get('sessionName', '-')}",
    ]
    if runtime.get("pid"):
        lines.append(f"Observed runtime PID: {runtime['pid']}")
    return "\n".join(lines) + "\n"
