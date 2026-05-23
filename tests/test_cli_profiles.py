import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest import mock

from claw.cli import main
from claw.registry import ClawPaths, create_profile, load_registry


PS_FIXTURE = """
123 ?? Ss 0:00.01 tmux new-session -d -s aoe_Telegram_345a329e -c /Users/davide -x 120 -y 40 'exec env TELEGRAM_STATE_DIR=/Users/davide/.claude/channels/telegram SCHEDULER_STATE_DIR=/Users/davide/.claude/channels/scheduler claude --settings /Users/davide/Infra/Claude Code/settings-telegram.json --channels plugin:telegram@claude-plugins-official --dangerously-load-development-channels plugin:scheduler@claw-cron --session-id ebb1415a-48dd-43bd-bcfa-a5959e5328a0'
"""


class CliProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_env = os.environ.copy()
        os.environ["CLAW_HOME"] = self.tmp.name
        os.environ["CLAW_TEST_PS_OUTPUT"] = PS_FIXTURE
        os.environ["CLAW_TEST_TMUX_OUTPUT"] = "aoe_Telegram_345a329e: 1 windows"

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.old_env)
        self.tmp.cleanup()

    def run_cli(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_profile_list_includes_registry_profiles(self):
        create_profile(ClawPaths.from_env(), "finance", telegram=True)
        code, out, err = self.run_cli("profile", "list")
        self.assertEqual(code, 0, err)
        self.assertIn("finance", out)
        self.assertIn("token-missing", out)

    def test_sessions_list_includes_discovered_main(self):
        code, out, err = self.run_cli("sessions", "list")
        self.assertEqual(code, 0, err)
        self.assertIn("main", out)
        self.assertIn("aoe_Telegram_345a329e", out)
        self.assertIn("running", out)

    def test_profile_show_prints_paths_and_never_token_values(self):
        profile = create_profile(ClawPaths.from_env(), "finance", telegram=True)
        env_file = Path(profile["bindings"]["telegram"]["envFile"])
        env_file.write_text("TELEGRAM_BOT_TOKEN=123456:SECRET\n")
        code, out, err = self.run_cli("profile", "show", "finance")
        self.assertEqual(code, 0, err)
        self.assertIn("Profile: finance", out)
        self.assertIn("Telegram state:", out)
        self.assertIn("Scheduler state:", out)
        self.assertIn("Token configured: yes", out)
        self.assertNotIn("123456:SECRET", out)

    def test_profile_attach_main_print_command(self):
        code, out, err = self.run_cli("profile", "attach", "main", "--print-command")
        self.assertEqual(code, 0, err)
        self.assertEqual(out.strip(), "tmux attach -t aoe_Telegram_345a329e")

    def test_status_includes_summary(self):
        code, out, err = self.run_cli("status")
        self.assertEqual(code, 0, err)
        self.assertIn("Registry:", out)
        self.assertIn("Runtime profiles:", out)
        self.assertIn("main", out)

    def test_profile_create_creates_tree_and_instructions(self):
        code, out, err = self.run_cli("profile", "create", "finance", "--telegram")
        self.assertEqual(code, 0, err)
        profile_dir = Path(self.tmp.name) / "profiles" / "finance"
        self.assertTrue((profile_dir / "config" / "CLAUDE.md").is_file())
        self.assertTrue((profile_dir / "channels" / "telegram").is_dir())
        self.assertIn("Created profile: finance", out)
        self.assertIn("BotFather", out)
        self.assertIn("claw profile launch finance", out)
        self.assertIn("--dangerously-skip-permissions", out)
        self.assertIn("cwd", out.lower())
        self.assertIn(str(Path.home()), out)

    def test_profile_launch_dry_run_prints_isolated_command(self):
        create_profile(ClawPaths.from_env(), "finance", telegram=True)
        code, out, err = self.run_cli("profile", "launch", "finance", "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("tmux new-session", out)
        self.assertIn("CLAUDE_CONFIG_DIR=", out)
        self.assertIn("TELEGRAM_STATE_DIR=", out)
        self.assertIn("SCHEDULER_STATE_DIR=", out)
        self.assertIn("plugin:telegram@claude-plugins-official", out)
        self.assertIn("plugin:scheduler@claw-cron", out)
        self.assertIn("--dangerously-skip-permissions", out)
        self.assertIn("cwd", out.lower())
        self.assertIn(str(Path.home()), out)

    def test_profile_launch_without_token_refuses_before_subprocess_run(self):
        create_profile(ClawPaths.from_env(), "finance", telegram=True)
        with mock.patch("claw.cli.subprocess.run") as run:
            code, out, err = self.run_cli("profile", "launch", "finance")
        self.assertEqual(code, 1)
        self.assertIn("no TELEGRAM_BOT_TOKEN", err)
        run.assert_not_called()

    def test_profile_launch_success_prints_permission_note(self):
        profile = create_profile(ClawPaths.from_env(), "finance", telegram=True)
        env_file = Path(profile["bindings"]["telegram"]["envFile"])
        env_file.write_text("TELEGRAM_BOT_TOKEN=123456:SECRET\n")
        with mock.patch("claw.cli.subprocess.run") as run:
            code, out, err = self.run_cli("profile", "launch", "finance")
        self.assertEqual(code, 0, err)
        run.assert_called_once()
        self.assertIn("Started profile: finance", out)
        self.assertIn("--dangerously-skip-permissions", out)
        self.assertIn("cwd", out.lower())
        self.assertIn(str(Path.home()), out)

    def test_profile_delete_requires_yes(self):
        create_profile(ClawPaths.from_env(), "finance", telegram=True)
        code, out, err = self.run_cli("profile", "delete", "finance")
        self.assertNotEqual(code, 0)
        self.assertIn("--yes", err)

    def test_profile_delete_yes_moves_to_trash(self):
        create_profile(ClawPaths.from_env(), "finance", telegram=True)
        code, out, err = self.run_cli("profile", "delete", "finance", "--yes")
        self.assertEqual(code, 0, err)
        self.assertIn("Deleted profile: finance", out)
        self.assertFalse((Path(self.tmp.name) / "profiles" / "finance").exists())
        self.assertTrue((Path(self.tmp.name) / "trash").exists())
        self.assertNotIn("finance", load_registry(ClawPaths.from_env())["profiles"])


if __name__ == "__main__":
    unittest.main()
