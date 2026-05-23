import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROFILE_RE = re.compile(r"^[a-z][a-z0-9_-]*$")
TELEGRAM_PLUGIN = "plugin:telegram@claude-plugins-official"
SCHEDULER_PLUGIN = "plugin:scheduler@claw-cron"


@dataclass(frozen=True)
class ClawPaths:
    home: Path

    @classmethod
    def from_env(cls):
        value = os.environ.get("CLAW_HOME")
        return cls(Path(value).expanduser() if value else Path.home() / ".claude" / "claw")

    @property
    def registry_file(self):
        return self.home / "profiles.json"

    @property
    def profiles_dir(self):
        return self.home / "profiles"

    @property
    def trash_dir(self):
        return self.home / "trash"


def validate_profile_name(name):
    if not name or not PROFILE_RE.match(name):
        raise ValueError("invalid profile name: use /^[a-z][a-z0-9_-]*$/")


def default_registry():
    return {"version": 1, "profiles": {}}


def load_registry(paths):
    if not paths.registry_file.exists():
        return default_registry()
    with paths.registry_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("version", 1)
    data.setdefault("profiles", {})
    return data


def save_registry(paths, registry):
    paths.home.mkdir(parents=True, exist_ok=True)
    tmp = paths.registry_file.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, sort_keys=True)
        f.write("\n")
    tmp.replace(paths.registry_file)


def token_configured(env_file):
    p = Path(env_file)
    if not p.exists():
        return False
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("TELEGRAM_BOT_TOKEN=") and line.split("=", 1)[1].strip():
                return True
    except OSError:
        return False
    return False


def _claude_md(name):
    title = name.replace("-", " ").replace("_", " ").title()
    return f"""# {title} Profile

You are Davide's {name}-focused personal assistant.

## Scope
Help Davide with tasks related to this profile. Keep profile-specific context and channel state isolated.

## Operating principles
- Be precise with numbers and dates.
- Use tools to calculate; do not do arithmetic mentally.
- Treat private data as sensitive.
- Ask before sending, deleting, or modifying external records.

## Telegram behavior
Davide may be chatting with you through this profile's dedicated Telegram bot. Reply through the Telegram reply tool when a Telegram channel message arrives.
"""


def make_profile_entry(paths, name, telegram=True):
    profile_dir = paths.profiles_dir / name
    config_dir = profile_dir / "config"
    telegram_dir = profile_dir / "channels" / "telegram"
    scheduler_dir = profile_dir / "channels" / "scheduler"
    session_id = str(uuid.uuid4())
    args = []
    bindings = {}
    if telegram:
        args.extend(["--channels", TELEGRAM_PLUGIN])
        bindings["telegram"] = {
            "enabled": True,
            "plugin": "telegram@claude-plugins-official",
            "stateDir": str(telegram_dir),
            "envFile": str(telegram_dir / ".env"),
            "accessFile": str(telegram_dir / "access.json"),
            "botUsername": None,
            "botTokenConfigured": False,
        }
    args.extend(["--dangerously-load-development-channels", SCHEDULER_PLUGIN, "--dangerously-skip-permissions"])
    bindings["scheduler"] = {
        "enabled": True,
        "plugin": "scheduler@claw-cron",
        "stateDir": str(scheduler_dir),
        "jobsFile": str(scheduler_dir / "jobs.json"),
    }
    return {
        "name": name,
        "description": f"{name.title()} assistant",
        "profileDir": str(profile_dir),
        "claudeConfigDir": str(config_dir),
        "cwd": str(Path.home()),
        "tmux": {"sessionName": f"claw_{name}", "width": 128, "height": 48},
        "claude": {"sessionId": session_id, "settings": str(config_dir / "settings.json"), "args": args},
        "bindings": bindings,
    }


def create_profile(paths, name, telegram=True):
    validate_profile_name(name)
    registry = load_registry(paths)
    if name in registry["profiles"]:
        raise ValueError(f"profile already exists: {name}")
    entry = make_profile_entry(paths, name, telegram=telegram)
    profile_dir = Path(entry["profileDir"])
    config_dir = Path(entry["claudeConfigDir"])
    telegram_dir = Path(entry["bindings"]["telegram"]["stateDir"])
    scheduler_dir = Path(entry["bindings"]["scheduler"]["stateDir"])
    (config_dir / "skills").mkdir(parents=True, exist_ok=True)
    telegram_dir.mkdir(parents=True, exist_ok=True)
    (scheduler_dir / "logs").mkdir(parents=True, exist_ok=True)
    (scheduler_dir / "locks").mkdir(parents=True, exist_ok=True)
    (profile_dir / "logs").mkdir(parents=True, exist_ok=True)
    (profile_dir / "runtime").mkdir(parents=True, exist_ok=True)
    (config_dir / "CLAUDE.md").write_text(_claude_md(name), encoding="utf-8")
    (config_dir / "settings.json").write_text(json.dumps({"permissions": {"allow": [], "deny": []}}, indent=2) + "\n", encoding="utf-8")
    (scheduler_dir / "jobs.json").write_text(json.dumps({"jobs": []}, indent=2) + "\n", encoding="utf-8")
    registry["profiles"][name] = entry
    save_registry(paths, registry)
    (profile_dir / "profile.json").write_text(json.dumps(entry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return entry


def _resolve_for_safety(path):
    return Path(path).expanduser().resolve(strict=False)


def _validate_profile_dir_for_delete(paths, name, profile_dir):
    expected = _resolve_for_safety(paths.profiles_dir / name)
    actual = _resolve_for_safety(profile_dir)
    if actual == expected or expected in actual.parents:
        return actual
    raise ValueError(f"refusing to delete unsafe profileDir outside profiles dir: {profile_dir}")


def delete_profile(paths, name):
    validate_profile_name(name)
    registry = load_registry(paths)
    if name not in registry["profiles"]:
        raise ValueError(f"profile not found: {name}")
    entry = registry["profiles"][name]
    profile_dir = _validate_profile_dir_for_delete(paths, name, entry["profileDir"])
    paths.trash_dir.mkdir(parents=True, exist_ok=True)
    trashed = None
    if profile_dir.exists():
        stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        dest = paths.trash_dir / f"{name}-{stamp}"
        i = 1
        while dest.exists():
            dest = paths.trash_dir / f"{name}-{stamp}-{i}"
            i += 1
        shutil.move(str(profile_dir), str(dest))
        trashed = str(dest)
    registry["profiles"].pop(name)
    save_registry(paths, registry)
    return trashed
