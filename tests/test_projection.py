import hashlib
import tempfile
import unittest
from pathlib import Path

from houdini_ai.projection import project_canonical_editorial, project_editorial_record
from houdini_ai.studio_store import StudioStore


class ProjectionTests(unittest.TestCase):
    def approved_record(self):
        return {
            "id": "scar-tissue-field-note",
            "visibility": "public-candidate",
            "readiness": "approved",
            "license": "CC-BY-NC-SA-4.0",
            "title": "Scar Tissue",
            "summary": "Paths attract traffic until saturation makes them repellent.",
            "artifacts": [
                {
                    "id": "scar-loop",
                    "path": "package/scar-loop.mp4",
                    "sha256": "a" * 64,
                    "role": "field-observation",
                    "download": False,
                }
            ],
            "claims": [{"status": "observed", "text": "Saturated paths are abandoned."}],
            "private_notes": "Do not publish this sentence.",
        }

    def test_private_record_does_not_project(self) -> None:
        record = self.approved_record()
        record["visibility"] = "private"
        with self.assertRaisesRegex(ValueError, "private"):
            project_editorial_record(record)

    def test_projection_keeps_public_fields_and_removes_private_notes(self) -> None:
        projected = project_editorial_record(self.approved_record())
        self.assertEqual(projected["id"], "scar-tissue-field-note")
        self.assertEqual(projected["artifacts"][0]["sha256"], "a" * 64)
        self.assertNotIn("private_notes", projected)

    def test_projection_fails_closed_on_unapproved_or_unknown_claim_status(self) -> None:
        record = self.approved_record()
        record["readiness"] = "ready-for-approval"
        with self.assertRaisesRegex(ValueError, "approved"):
            project_editorial_record(record)
        record = self.approved_record()
        record["claims"][0]["status"] = "factish"
        with self.assertRaisesRegex(ValueError, "claim status"):
            project_editorial_record(record)

    def test_projection_rejects_local_absolute_paths(self) -> None:
        record = self.approved_record()
        record["artifacts"][0]["path"] = "C:/Users/Owner/private.mp4"
        with self.assertRaisesRegex(ValueError, "relative"):
            project_editorial_record(record)

    def test_projection_rejects_uri_schemes_and_unsafe_record_ids(self) -> None:
        record = self.approved_record()
        record["artifacts"][0]["path"] = "javascript:alert(1)"
        with self.assertRaisesRegex(ValueError, "relative"):
            project_editorial_record(record)
        record = self.approved_record()
        record["id"] = "../escaped"
        with self.assertRaisesRegex(ValueError, "relative"):
            project_editorial_record(record)

    def test_canonical_editorial_and_verified_artifacts_convert_to_public_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            artifact_path = Path(directory) / "work/jobs/scar/package/scar-loop.mp4"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"verified")
            store.create("artifacts", "artifact-scar-loop", {
                "schema_version": 1, "id": "artifact-scar-loop", "experiment_id": "experiment-scar",
                "track": "behavior", "state": "verified", "path": "work/jobs/scar/package/scar-loop.mp4",
                "sha256": "sha256:" + hashlib.sha256(b"verified").hexdigest(), "verified": True, "visibility": "private",
            })
            store.create("editorial", "editorial-scar-note", {
                "schema_version": 1, "id": "editorial-scar-note", "state": "approved",
                "artifact_refs": ["work/jobs/scar/package/scar-loop.mp4"], "destinations": ["web"],
                "roles": ["field-observation"], "tags": ["publish:web", "role:field-observation", "visibility:public-candidate", "readiness:approved"],
                "visibility": "public-candidate", "approved": True, "title": "Scar Tissue",
                "summary": "Saturated paths become repellent.", "license": "CC-BY-NC-SA-4.0",
                "claims": [{"status": "observed", "text": "Paths turned over."}],
            })

            projected = project_canonical_editorial(store, "editorial-scar-note")

            self.assertEqual(projected["id"], "scar-note")
            self.assertEqual(projected["artifacts"], [{"id": "artifact-scar-loop", "path": "work/jobs/scar/package/scar-loop.mp4", "sha256": hashlib.sha256(b"verified").hexdigest(), "role": "field-observation", "download": False}])
            self.assertNotIn("tags", projected)
            artifact_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                project_canonical_editorial(store, "editorial-scar-note")

    def test_canonical_conversion_fails_closed_for_unverified_or_unapproved_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("artifacts", "artifact-a", {"id": "artifact-a", "path": "work/jobs/a/file.mp4", "verified": False})
            store.create("editorial", "editorial-a", {
                "schema_version": 1, "id": "editorial-a", "state": "approved", "approved": True,
                "visibility": "public-candidate", "artifact_refs": ["work/jobs/a/file.mp4"],
                "destinations": ["web"], "roles": ["field-observation"],
                "tags": ["publish:web", "role:field-observation", "visibility:public-candidate", "readiness:approved"],
            })
            with self.assertRaisesRegex(ValueError, "artifact"):
                project_canonical_editorial(store, "editorial-a")
            store.update("editorial", "editorial-a", {**store.read("editorial", "editorial-a"), "state": "draft", "approved": False})
            with self.assertRaisesRegex(ValueError, "approved"):
                project_canonical_editorial(store, "editorial-a")


if __name__ == "__main__":
    unittest.main()
