import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli


class SeedBankCliTests(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> dict[str, object]:
        output = StringIO()
        with patch.object(cli, "ROOT", root), redirect_stdout(output):
            self.assertEqual(cli.main(["studio", *args]), 0)
        return json.loads(output.getvalue())

    def test_seed_lifecycle_is_available_as_machine_readable_local_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = self.run_cli(
                root,
                "seed-create",
                json.dumps(
                    {
                        "title": "Reciprocal Weather",
                        "short_summary": "Agents create weather that changes their relationships.",
                        "long_summary": "A field-driven system where collective motion leaves an atmosphere that feeds back into nonlocal affinities.",
                        "reference_links": [],
                        "tags": ["agents", "weather"],
                    }
                ),
                "--json",
            )
            seed = self.run_cli(
                root,
                "seed-update",
                str(seed["id"]),
                json.dumps({"short_summary": "Agents leave weather that alters later affinities."}),
                "--json",
            )
            self.assertIn("later affinities", str(seed["short_summary"]))
            self.run_cli(root, "seed-transition", str(seed["id"]), "incubating", "--json")
            self.run_cli(root, "seed-transition", str(seed["id"]), "ready", "--json")
            promotion = self.run_cli(
                root,
                "seed-promote",
                str(seed["id"]),
                json.dumps(
                    {
                        "study_id": "study-004-reciprocal-weather",
                        "study_title": "Study 004 — Reciprocal Weather",
                        "primary_track": "behavior",
                        "recommended_next_action": "Define a realtime Behavior probe.",
                    }
                ),
                json.dumps(
                    {
                        "actor": "kc",
                        "origin": "discord",
                        "source_ref": "discord:seed-thread:message-promote",
                        "idempotency_key": "discord:message-promote:seed.promote",
                    }
                ),
                "--json",
            )
            study = promotion["result"]
            self.assertEqual(study["idea_id"], seed["id"])
            self.assertEqual(promotion["activity"]["seed_id"], seed["id"])
            self.assertFalse(promotion["replayed"])
            inclusion = self.run_cli(
                root,
                "seed-site-draft",
                str(seed["id"]),
                "discord:seed-thread:message-1",
                "--json",
            )
            self.run_cli(
                root,
                "seed-site-rights",
                str(inclusion["id"]),
                "cleared",
                "Original Studio-authored summary.",
                "--json",
            )
            self.run_cli(
                root,
                "seed-site-transition",
                str(inclusion["id"]),
                "site-live",
                "kc",
                "discord:seed-thread:message-2",
                "--json",
            )
            output = root / "work" / "public-site" / "seeds"
            receipt = self.run_cli(root, "seed-bank-preview", str(output), "--json")
            self.assertEqual(receipt["seed_count"], 1)
            self.assertTrue((output / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
