import json
import hashlib
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli
from houdini_ai.seed_bank import create_seed
from houdini_ai.studies import create_study
from houdini_ai.studio_store import StudioStore


class DiscordPublicStudioCliTests(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> tuple[int, str]:
        output = StringIO()
        with patch.object(cli, "ROOT", root), redirect_stdout(output):
            result = cli.main(["studio", *args])
        return result, output.getvalue()

    def test_discord_binding_commands_emit_private_machine_readable_routing_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003",
                    "intent": "Develop the study.",
                    "recommended_next_action": "Review evidence.",
                },
            )

            code, output = self.run_cli(
                root,
                "conversation-bind",
                "study-003-nonlocal-affinity-dance",
                "--guild-id",
                "123456789012345678",
                "--parent-channel-id",
                "223456789012345678",
                "--thread-id",
                "323456789012345678",
                "--json",
            )

            self.assertEqual(code, 0)
            binding = json.loads(output)
            self.assertEqual(binding["visibility"], "private")
            code, output = self.run_cli(root, "conversation-resolve", binding["thread_id"], "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["study_id"], "study-003-nonlocal-affinity-dance")

    def test_seed_conversation_bind_emits_private_machine_readable_routing_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = create_seed(
                StudioStore(root),
                {
                    "title": "Lineage Machines",
                    "short_summary": "Graphs split into descendants.",
                    "long_summary": "Rewrite events produce a verifiable branching lineage.",
                },
            )

            code, output = self.run_cli(
                root,
                "seed-conversation-bind",
                seed["id"],
                "--guild-id",
                "123456789012345678",
                "--parent-channel-id",
                "223456789012345678",
                "--thread-id",
                "323456789012345678",
                "--json",
            )

            self.assertEqual(code, 0)
            binding = json.loads(output)
            self.assertEqual(binding["seed_id"], seed["id"])
            self.assertEqual(binding["visibility"], "private")
            code, output = self.run_cli(root, "conversation-resolve", binding["thread_id"], "--json")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["seed_id"], seed["id"])
            code, output = self.run_cli(root, "conversation-resolve", binding["thread_id"])
            self.assertEqual(code, 0)
            self.assertIn(f"seed: {seed['id']}", output)

    def test_site_commands_create_receipted_inclusion_and_local_read_only_preview(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003",
                    "intent": "Develop the study.",
                    "recommended_next_action": "Review evidence.",
                },
            )
            media = root / "work" / "studio" / "handoffs" / "study-003-affinity-cli-test" / "comparison.mp4"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"cli comparison")
            artifact = {
                "schema_version": 1,
                "id": "artifact-cli-comparison",
                "experiment_id": "experiment-cli-comparison",
                "track": "behavior",
                "state": "verified",
                "path": media.relative_to(root).as_posix(),
                "sha256": "sha256:" + hashlib.sha256(media.read_bytes()).hexdigest(),
                "verified": True,
                "visibility": "private",
            }
            store.create("artifacts", artifact["id"], artifact)
            details = json.dumps(
                {
                    "public_title": "CLI comparison",
                    "public_caption": "A selected behavior milestone.",
                    "role": "comparison",
                    "section": "behavior",
                    "order": 10,
                    "alt_text": "A comparison of looping particle structures.",
                }
            )
            context = json.dumps(
                {
                    "actor": "kc",
                    "origin": "discord",
                    "source_ref": "discord:123456789012345678:323456789012345678:423456789012345678",
                    "idempotency_key": "discord:423456789012345678:site.include:artifact-cli-comparison",
                }
            )

            code, output = self.run_cli(
                root,
                "site-include",
                "study-003-nonlocal-affinity-dance",
                artifact["id"],
                details,
                context,
                "--json",
            )
            self.assertEqual(code, 0)
            inclusion = json.loads(output)["result"]
            rights_context = json.dumps(
                {
                    "actor": "hermes",
                    "origin": "local",
                    "source_ref": "local:rights-review:artifact-cli-comparison",
                    "idempotency_key": f"local:rights-review:{inclusion['id']}",
                }
            )
            code, _ = self.run_cli(
                root,
                "site-rights",
                "study-003-nonlocal-affinity-dance",
                inclusion["id"],
                "cleared",
                "Original Studio output.",
                rights_context,
                "--json",
            )
            self.assertEqual(code, 0)
            transition_context = json.dumps(
                {
                    "actor": "kc",
                    "origin": "discord",
                    "source_ref": "discord:123456789012345678:323456789012345678:523456789012345678",
                    "idempotency_key": f"discord:523456789012345678:site.live:{inclusion['id']}",
                }
            )
            code, _ = self.run_cli(
                root,
                "site-transition",
                "study-003-nonlocal-affinity-dance",
                inclusion["id"],
                "site-live",
                transition_context,
                "--json",
            )
            self.assertEqual(code, 0)
            destination = root / "work" / "public-site" / "study-003-nonlocal-affinity-dance"
            code, output = self.run_cli(
                root,
                "public-preview",
                "study-003-nonlocal-affinity-dance",
                str(destination),
                "--json",
            )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["network_actions"], 0)
            self.assertTrue((destination / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
