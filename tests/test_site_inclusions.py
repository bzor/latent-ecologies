import hashlib
import tempfile
import unittest
from pathlib import Path

from houdini_ai.site_inclusions import create_site_draft, set_site_rights, transition_site_inclusion
from houdini_ai.studies import create_study
from houdini_ai.studio_commands import CommandContext
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class SiteInclusionTests(unittest.TestCase):
    def test_verified_artifact_can_be_drafted_for_site_without_creative_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            create_study(
                store,
                {
                    "id": "study-003-nonlocal-affinity-dance",
                    "title": "Study 003",
                    "intent": "Preserve exact behavior identity.",
                    "recommended_next_action": "Review the comparison.",
                },
            )
            media = root / "work" / "studio" / "handoffs" / "study-003-affinity-test" / "comparison.mp4"
            media.parent.mkdir(parents=True)
            media.write_bytes(b"verified comparison")
            artifact = {
                "schema_version": 1,
                "id": "artifact-study-003-comparison",
                "experiment_id": "experiment-study-003-comparison",
                "track": "behavior",
                "state": "verified",
                "path": media.relative_to(root).as_posix(),
                "sha256": "sha256:" + hashlib.sha256(media.read_bytes()).hexdigest(),
                "verified": True,
                "visibility": "private",
            }
            store.create("artifacts", artifact["id"], artifact)
            context = CommandContext(
                study_id="study-003-nonlocal-affinity-dance",
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:423456789012345678",
                idempotency_key="discord:423456789012345678:site.include:artifact-study-003-comparison",
            )

            first = create_site_draft(
                store,
                root,
                context,
                artifact_id=artifact["id"],
                public_title="Cohort routing comparison",
                public_caption="Three structure-preserving lifts compared at equal simulation time.",
                role="comparison",
                section="behavior",
                order=30,
                alt_text="Three particle simulations showing nested loops with different internal density.",
            )
            replay = create_site_draft(
                store,
                root,
                context,
                artifact_id=artifact["id"],
                public_title="Cohort routing comparison",
                public_caption="Three structure-preserving lifts compared at equal simulation time.",
                role="comparison",
                section="behavior",
                order=30,
                alt_text="Three particle simulations showing nested loops with different internal density.",
            )

            inclusion = first["result"]
            self.assertEqual(inclusion["state"], "site-draft")
            self.assertEqual(inclusion["artifact_id"], artifact["id"])
            self.assertEqual(validate_record("site-inclusion", inclusion), [])
            self.assertTrue(replay["replayed"])
            self.assertEqual(len(store.list("site-inclusions")[0]), 1)
            self.assertEqual(store.read("artifacts", artifact["id"]), artifact)
            self.assertEqual(store.list("components")[0], [])

            live_context = CommandContext(
                study_id=context.study_id,
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:523456789012345678",
                idempotency_key=f"discord:523456789012345678:site.live:{inclusion['id']}",
            )
            with self.assertRaisesRegex(ValueError, "rights clearance"):
                transition_site_inclusion(store, live_context, inclusion["id"], "site-live")
            rights_context = CommandContext(
                study_id=context.study_id,
                actor="hermes",
                origin="local",
                source_ref="local:rights-review:artifact-study-003-comparison",
                idempotency_key=f"local:rights-review:{inclusion['id']}",
            )
            set_site_rights(
                store,
                rights_context,
                inclusion["id"],
                "cleared",
                "Original Studio output; publication rights confirmed.",
            )
            hermes_live_context = CommandContext(
                study_id=context.study_id,
                actor="hermes",
                origin="local",
                source_ref="local:publication-preflight",
                idempotency_key=f"local:publication-preflight:site.live:{inclusion['id']}",
            )
            with self.assertRaisesRegex(ValueError, "KC confirmation"):
                transition_site_inclusion(store, hermes_live_context, inclusion["id"], "site-live")
            live_context = CommandContext(
                study_id=context.study_id,
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:723456789012345678",
                idempotency_key=f"discord:723456789012345678:site.live:{inclusion['id']}",
            )
            live = transition_site_inclusion(store, live_context, inclusion["id"], "site-live")["result"]
            first_published_at = live["first_published_at"]
            self.assertTrue(live["ever_public"])

            retire_context = CommandContext(
                study_id=context.study_id,
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:823456789012345678",
                idempotency_key=f"discord:823456789012345678:site.retire:{inclusion['id']}",
            )
            retired = transition_site_inclusion(store, retire_context, inclusion["id"], "retired")["result"]
            self.assertTrue(retired["ever_public"])
            self.assertEqual(retired["first_published_at"], first_published_at)
            self.assertEqual(validate_record("site-inclusion", retired), [])

            invalid_context = CommandContext(
                study_id=context.study_id,
                actor="kc",
                origin="discord",
                source_ref="discord:123456789012345678:323456789012345678:923456789012345678",
                idempotency_key=f"discord:923456789012345678:site.live:{inclusion['id']}",
            )
            with self.assertRaisesRegex(ValueError, "cannot transition"):
                transition_site_inclusion(store, invalid_context, inclusion["id"], "site-live")


if __name__ == "__main__":
    unittest.main()
