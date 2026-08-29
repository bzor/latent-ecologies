import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.publication_manifest import build_publication_manifest
from houdini_ai.site_inclusions import create_site_draft, set_site_rights, transition_site_inclusion
from houdini_ai.studies import create_study
from houdini_ai.studio_commands import CommandContext
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class PublicationManifestTests(unittest.TestCase):
    def context(self, message: int, action: str) -> CommandContext:
        return CommandContext(
            study_id="study-003-nonlocal-affinity-dance",
            actor="kc",
            origin="discord",
            source_ref=f"discord:123456789012345678:323456789012345678:{message}",
            idempotency_key=f"discord:{message}:{action}",
        )

    def artifact(self, root: Path, store: StudioStore, name: str, content: bytes) -> dict[str, object]:
        path = root / "work" / "studio" / "handoffs" / "study-003-affinity-publication-test" / f"{name}.mp4"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        record = {
            "schema_version": 1,
            "id": f"artifact-{name}",
            "experiment_id": f"experiment-{name}",
            "track": "behavior",
            "state": "verified",
            "path": path.relative_to(root).as_posix(),
            "sha256": "sha256:" + hashlib.sha256(content).hexdigest(),
            "verified": True,
            "visibility": "private",
        }
        store.create("artifacts", str(record["id"]), record)
        return record

    def draft(self, root: Path, store: StudioStore, artifact_id: str, message: int) -> dict[str, object]:
        return create_site_draft(
            store,
            root,
            self.context(message, f"site.include:{artifact_id}"),
            artifact_id=artifact_id,
            public_title=artifact_id.replace("artifact-", "").replace("-", " ").title(),
            public_caption="A selected milestone in the behavior study.",
            role="comparison",
            section="behavior",
            order=message % 1000,
            alt_text="A particle-system comparison with looping filament structures.",
        )["result"]

    def test_manifest_includes_only_explicitly_live_items_and_leaks_no_private_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003 — Nonlocal Affinity Dance",
                    "intent": "Private working intent must not be projected.",
                    "recommended_next_action": "Private next action must not be projected.",
                },
            )
            live_artifact = self.artifact(root, store, "live-comparison", b"live video")
            draft_artifact = self.artifact(root, store, "draft-comparison", b"draft video")
            live_draft = self.draft(root, store, str(live_artifact["id"]), 423456789012345678)
            self.draft(root, store, str(draft_artifact["id"]), 523456789012345678)
            set_site_rights(
                store,
                self.context(623456789012345678, f"site.rights:{live_draft['id']}"),
                str(live_draft["id"]),
                "cleared",
                "Original test output.",
            )
            transition_site_inclusion(
                store,
                self.context(723456789012345678, f"site.live:{live_draft['id']}"),
                str(live_draft["id"]),
                "site-live",
            )

            manifest = build_publication_manifest(store, root, "study-003-nonlocal-affinity-dance")

            self.assertEqual(validate_record("publication-manifest", manifest), [])
            self.assertEqual([item["artifact_id"] for item in manifest["items"]], [live_artifact["id"]])
            self.assertEqual(manifest["mode"], "living")
            self.assertTrue(manifest["items"][0]["media"]["public_path"].startswith("media/"))
            encoded = json.dumps(manifest, sort_keys=True)
            self.assertNotIn(str(root), encoded)
            self.assertNotIn("work/", encoded)
            self.assertNotIn("Private working intent", encoded)
            self.assertNotIn("discord:", encoded)
            self.assertNotIn("activity-", encoded)
            self.assertNotIn(str(draft_artifact["id"]), encoded)

            stored_inclusion = store.read("site-inclusions", str(live_draft["id"]))
            store.update(
                "site-inclusions",
                str(live_draft["id"]),
                {**stored_inclusion, "rights_status": "pending", "rights_rationale": "Tampered fixture."},
            )
            with self.assertRaisesRegex(ValueError, "rights clearance"):
                build_publication_manifest(store, root, "study-003-nonlocal-affinity-dance")
            store.update("site-inclusions", str(live_draft["id"]), stored_inclusion)

            source = root / str(live_artifact["path"])
            source.write_bytes(b"changed after verification")
            with self.assertRaisesRegex(ValueError, "verified artifact|checksum"):
                build_publication_manifest(store, root, "study-003-nonlocal-affinity-dance")


if __name__ == "__main__":
    unittest.main()
