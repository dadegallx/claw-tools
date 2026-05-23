import unittest

from claw.discovery import discover_main_profile, parse_processes


PS_FIXTURE = """
123 ?? Ss 0:00.01 tmux new-session -d -s aoe_Telegram_345a329e -c /Users/davide -x 120 -y 40 'exec env TELEGRAM_STATE_DIR=/Users/davide/.claude/channels/telegram SCHEDULER_STATE_DIR=/Users/davide/.claude/channels/scheduler claude --settings /Users/davide/Infra/Claude Code/settings-telegram.json --channels plugin:telegram@claude-plugins-official --dangerously-load-development-channels plugin:scheduler@claw-cron --session-id ebb1415a-48dd-43bd-bcfa-a5959e5328a0'
456 ?? S 0:00.01 other process TELEGRAM_BOT_TOKEN=secret
"""


class DiscoveryTests(unittest.TestCase):
    def test_parse_processes_extracts_current_telegram_tmux_command(self):
        found = parse_processes(PS_FIXTURE)
        self.assertEqual(len(found), 1)
        runtime = found[0]
        self.assertEqual(runtime["tmuxSession"], "aoe_Telegram_345a329e")
        self.assertEqual(runtime["sessionId"], "ebb1415a-48dd-43bd-bcfa-a5959e5328a0")
        self.assertEqual(runtime["settings"], "/Users/davide/Infra/Claude Code/settings-telegram.json")
        self.assertTrue(runtime["telegram"])
        self.assertTrue(runtime["scheduler"])
        self.assertNotIn("secret", str(runtime))

    def test_discover_main_profile_from_fixture(self):
        main = discover_main_profile(ps_output=PS_FIXTURE, tmux_output="aoe_Telegram_345a329e: 1 windows")
        self.assertIsNotNone(main)
        self.assertEqual(main["name"], "main")
        self.assertEqual(main["runtime"]["tmuxSession"], "aoe_Telegram_345a329e")
        self.assertEqual(main["runtime"]["status"], "running")

    def test_discovery_returns_none_without_telegram_channel(self):
        self.assertIsNone(discover_main_profile(ps_output="tmux new-session -s other claude", tmux_output=""))

    def test_parse_processes_does_not_store_full_command_or_secret_values(self):
        ps_output = """
789 ?? Ss 0:00.01 tmux new-session -d -s secret_session -c /Users/davide 'exec env TELEGRAM_BOT_TOKEN=telegram-secret ANTHROPIC_API_KEY=anthropic-secret OTHER_SECRET=other-secret claude --settings /tmp/settings.json --channels plugin:telegram@claude-plugins-official --dangerously-load-development-channels plugin:scheduler@claw-cron --session-id session-123'
"""
        found = parse_processes(ps_output)
        self.assertEqual(len(found), 1)
        runtime = found[0]
        self.assertNotIn("command", runtime)
        rendered = str(runtime)
        self.assertNotIn("telegram-secret", rendered)
        self.assertNotIn("anthropic-secret", rendered)
        self.assertNotIn("other-secret", rendered)
        self.assertNotIn("TELEGRAM_BOT_TOKEN", rendered)
        self.assertNotIn("ANTHROPIC_API_KEY", rendered)
        self.assertNotIn("OTHER_SECRET", rendered)


if __name__ == "__main__":
    unittest.main()
