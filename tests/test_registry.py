import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from claw.registry import ClawPaths, create_profile, delete_profile, load_registry, save_registry


class RegistryTests(unittest.TestCase):
    def test_paths_from_env_uses_claw_home(self):
        with tempfile.TemporaryDirectory() as td:
            old = os.environ.get("CLAW_HOME")
            os.environ["CLAW_HOME"] = td
            try:
                paths = ClawPaths.from_env()
            finally:
                if old is None:
                    os.environ.pop("CLAW_HOME", None)
                else:
                    os.environ["CLAW_HOME"] = old
            self.assertEqual(paths.home, Path(td))
            self.assertEqual(paths.registry_file, Path(td) / "profiles.json")

    def test_default_claw_home(self):
        old = os.environ.pop("CLAW_HOME", None)
        try:
            paths = ClawPaths.from_env()
        finally:
            if old is not None:
                os.environ["CLAW_HOME"] = old
        self.assertEqual(paths.home, Path.home() / ".claude" / "claw")

    def test_create_profile_creates_tree_and_registry(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            profile = create_profile(paths, "finance", telegram=True)
            profile_dir = Path(profile["profileDir"])
            self.assertTrue((profile_dir / "config" / "CLAUDE.md").is_file())
            self.assertTrue((profile_dir / "config" / "settings.json").is_file())
            self.assertTrue((profile_dir / "channels" / "telegram").is_dir())
            self.assertTrue((profile_dir / "channels" / "scheduler" / "jobs.json").is_file())
            jobs = json.loads((profile_dir / "channels" / "scheduler" / "jobs.json").read_text())
            self.assertEqual(jobs, {"jobs": []})

            registry = load_registry(paths)
            self.assertIn("finance", registry["profiles"])
            entry = registry["profiles"]["finance"]
            self.assertEqual(entry["bindings"]["telegram"]["stateDir"], str(profile_dir / "channels" / "telegram"))
            self.assertEqual(entry["bindings"]["scheduler"]["stateDir"], str(profile_dir / "channels" / "scheduler"))
            self.assertIn(str(profile_dir), entry["bindings"]["telegram"]["stateDir"])
            self.assertIn(str(profile_dir), entry["bindings"]["scheduler"]["stateDir"])

    def test_invalid_profile_names_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            for name in ["Finance", "1finance", "finance team", "finance/ops", "", "-bad"]:
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        create_profile(paths, name, telegram=True)

    def test_duplicate_profile_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            create_profile(paths, "finance", telegram=True)
            with self.assertRaises(ValueError):
                create_profile(paths, "finance", telegram=True)

    def test_delete_profile_moves_to_trash_and_removes_registry(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            profile = create_profile(paths, "finance", telegram=True)
            old_dir = Path(profile["profileDir"])
            trashed = delete_profile(paths, "finance")
            self.assertFalse(old_dir.exists())
            self.assertTrue(Path(trashed).exists())
            self.assertIn(Path(td) / "trash", Path(trashed).parents)
            registry = load_registry(paths)
            self.assertNotIn("finance", registry["profiles"])

    def test_delete_profile_rejects_invalid_profile_name(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            with self.assertRaises(ValueError):
                delete_profile(paths, "../finance")

    def test_delete_profile_refuses_registry_profile_dir_outside_profiles_dir(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            outside = Path(td) / "outside-finance"
            outside.mkdir()
            registry = {
                "version": 1,
                "profiles": {
                    "finance": {
                        "name": "finance",
                        "profileDir": str(outside),
                    }
                },
            }
            save_registry(paths, registry)

            with self.assertRaises(ValueError):
                delete_profile(paths, "finance")

            self.assertTrue(outside.exists())
            self.assertIn("finance", load_registry(paths)["profiles"])

    def test_delete_profile_move_failure_preserves_registry(self):
        with tempfile.TemporaryDirectory() as td:
            paths = ClawPaths(Path(td))
            create_profile(paths, "finance", telegram=True)

            with mock.patch("claw.registry.shutil.move", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    delete_profile(paths, "finance")

            self.assertIn("finance", load_registry(paths)["profiles"])


if __name__ == "__main__":
    unittest.main()
