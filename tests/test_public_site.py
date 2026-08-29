import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from houdini_ai.public_site import build_public_site
from houdini_ai.site_inclusions import create_site_draft, set_site_rights, transition_site_inclusion
from houdini_ai.studies import create_study
from houdini_ai.studio_commands import CommandContext
from houdini_ai.studio_store import StudioStore


class PublicSiteTests(unittest.TestCase):
    def context(self, message: str, action: str) -> CommandContext:
        return CommandContext(
            study_id="study-003-nonlocal-affinity-dance",
            actor="kc",
            origin="discord",
            source_ref=f"discord:123456789012345678:323456789012345678:{message}",
            idempotency_key=f"discord:{message}:{action}",
        )

    def test_builds_read_only_local_site_with_content_addressed_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003 — Nonlocal Affinity Dance",
                    "intent": "Private intent.",
                    "recommended_next_action": "Private action.",
                },
            )
            source = root / "work" / "studio" / "handoffs" / "study-003-affinity-site-test" / "loops.png"
            source.parent.mkdir(parents=True)
            Image.new("RGB", (16, 12), (20, 40, 90)).save(source)
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            artifact = {
                "schema_version": 1,
                "id": "artifact-public-loops",
                "experiment_id": "experiment-public-loops",
                "track": "behavior",
                "state": "verified",
                "path": source.relative_to(root).as_posix(),
                "sha256": f"sha256:{digest}",
                "verified": True,
                "visibility": "private",
            }
            store.create("artifacts", artifact["id"], artifact)
            inclusion = create_site_draft(
                store,
                root,
                self.context("423456789012345678", "site.include:artifact-public-loops"),
                artifact_id=artifact["id"],
                public_title="Nested loop emergence",
                public_caption="The exact graph identity restores the nested loop vocabulary.",
                role="experiment",
                section="behavior",
                order=10,
                alt_text="Dark blue image representing a nested-loop particle study.",
            )["result"]
            set_site_rights(
                store,
                self.context("523456789012345678", f"site.rights:{inclusion['id']}"),
                inclusion["id"],
                "cleared",
                "Original test output.",
            )
            transition_site_inclusion(
                store,
                self.context("623456789012345678", f"site.live:{inclusion['id']}"),
                inclusion["id"],
                "site-live",
            )
            output = root / "work" / "public-site" / "study-003-nonlocal-affinity-dance"

            receipt = build_public_site(store, root, "study-003-nonlocal-affinity-dance", output)

            expected_media = output / "media" / f"{digest}.png"
            self.assertTrue((output / "index.html").is_file())
            self.assertTrue((output / "styles.css").is_file())
            self.assertTrue((output / "manifest.json").is_file())
            self.assertTrue(expected_media.is_file())
            self.assertEqual(hashlib.sha256(expected_media.read_bytes()).hexdigest(), digest)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["content_sha256"], receipt["manifest_sha256"])
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Study 003 — Nonlocal Affinity Dance", html)
            self.assertIn("Nested loop emergence", html)
            self.assertIn(f"media/{digest}.png", html)
            self.assertNotIn(str(root), html)
            self.assertNotIn("Private intent", html)
            self.assertNotIn("<form", html.lower())
            self.assertNotIn("<input", html.lower())
            self.assertNotIn("login", html.lower())
            self.assertEqual(receipt["item_count"], 1)
            self.assertEqual(receipt["network_actions"], 0)


if __name__ == "__main__":
    unittest.main()
