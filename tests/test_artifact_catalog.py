import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from houdini_ai.artifact_catalog import build_artifact_catalog, resolve_catalog_media
from houdini_ai.studio_store import StudioStore


class ArtifactCatalogTests(unittest.TestCase):
    def fixture(self, root: Path) -> None:
        job = root / "work" / "jobs" / "legacy-job"
        review = job / "review"
        review.mkdir(parents=True)
        (job / "effective-config.json").write_text(
            json.dumps({"study": {"id": "legacy-study", "title": "Legacy Study", "seed": 7}}),
            encoding="utf-8",
        )
        (review / "preview.mp4").write_bytes(b"video")
        (review / "preview.mp4.tmp").write_bytes(b"partial")
        flood = review / "motion-frames"
        flood.mkdir()
        (flood / "frame-0001.png").write_bytes(b"frame")
        hips = review / "hips"
        hips.mkdir()
        (hips / "scene.0001.hip").write_bytes(b"per-frame scene")
        cache = review / "cache"
        cache.mkdir()
        (cache / "metrics.json").write_text("{}", encoding="utf-8")

        handoff = root / "work" / "studio" / "handoffs" / "scar-tissue-v1"
        handoff.mkdir(parents=True)
        selected = handoff / "selected.hiplc"
        selected.write_bytes(b"hip")
        (handoff / "unregistered-working.hiplc").write_bytes(b"working scene")
        (handoff / "receipt.json").write_text("{}", encoding="utf-8")
        (handoff / "motion-check.mp4").write_bytes(b"motion")
        (handoff / ".env").write_text("SECRET=x", encoding="utf-8")
        (handoff / "scratch.tmp").write_bytes(b"partial")
        frames = handoff / "portrait-frames"
        frames.mkdir()
        (frames / "scar-tissue-portrait-0001.png").write_bytes(b"png1")
        (frames / "scar-tissue-portrait-0002.png").write_bytes(b"png2")

        affinity = root / "work" / "studio" / "handoffs" / "study-003-affinity-3d-100k-v1"
        affinity.mkdir(parents=True)
        (affinity / "neutral-comparison.mp4").write_bytes(b"affinity")

        outside = root / "secret.mp4"
        outside.write_bytes(b"outside")
        store = StudioStore(root)
        store.create(
            "artifacts",
            "artifact-shot-selected",
            {
                "schema_version": 1,
                "id": "artifact-shot-selected",
                "experiment_id": "experiment-shot-selected",
                "track": "cinematography",
                "state": "verified",
                "path": "work/studio/handoffs/scar-tissue-v1/selected.hiplc",
                "sha256": "sha256:" + hashlib.sha256(b"hip").hexdigest(),
                "verified": True,
                "visibility": "private",
            },
        )
        store.create(
            "components",
            "component-shot-selected",
            {
                "schema_version": 1,
                "id": "component-shot-selected",
                "track": "cinematography",
                "state": "promoted",
                "component_kind": "shot",
                "source_experiment_id": "experiment-shot-selected",
                "source_artifact_ref": "work/studio/handoffs/scar-tissue-v1/selected.hiplc",
                "rationale": "Selected coverage.",
                "content_hash": "sha256:" + "a" * 64,
                "visibility": "private",
            },
        )
        store.create(
            "specimens",
            "specimen-scar-tissue-v1",
            {
                "schema_version": 1,
                "id": "specimen-scar-tissue-v1",
                "state": "rendering",
                "component_ids": ["component-shot-selected"],
                "creative_reason": "Golden run.",
                "deliverables": ["portrait-sequence"],
                "cost_tier": "specimen",
                "approved": False,
                "visibility": "private",
            },
        )

    def test_catalog_unifies_deduplicates_and_enriches_safe_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)

            first = build_artifact_catalog(root)
            second = build_artifact_catalog(root)

            self.assertEqual([item["id"] for item in first], [item["id"] for item in second])
            paths = [item["path"] for item in first]
            self.assertEqual(len(paths), len(set(paths)))
            self.assertIn("work/jobs/legacy-job/review/preview.mp4", paths)
            self.assertIn("work/studio/handoffs/scar-tissue-v1/selected.hiplc", paths)
            self.assertIn("work/studio/handoffs/scar-tissue-v1/motion-check.mp4", paths)
            self.assertIn("work/studio/handoffs/scar-tissue-v1/portrait-frames", paths)
            self.assertNotIn("work/studio/handoffs/scar-tissue-v1/unregistered-working.hiplc", paths)
            self.assertNotIn("work/studio/handoffs/scar-tissue-v1/receipt.json", paths)
            self.assertNotIn("work/studio/handoffs/scar-tissue-v1/portrait-frames/scar-tissue-portrait-0001.png", paths)
            self.assertFalse(any(
                ".env" in path or ".tmp" in path or any(part in {"motion-frames", "hips", "cache"} for part in Path(path).parts)
                for path in paths
            ))
            self.assertFalse(any(path == "secret.mp4" for path in paths))

            selected = next(item for item in first if item["path"].endswith("selected.hiplc"))
            legacy_preview = next(item for item in first if item["path"].endswith("preview.mp4"))
            affinity_preview = next(item for item in first if item["path"].endswith("neutral-comparison.mp4"))
            self.assertEqual(legacy_preview["project_id"], "legacy-study")
            self.assertEqual(legacy_preview["project_title"], "Legacy Study")
            self.assertEqual(affinity_preview["project_id"], "study-003-nonlocal-affinity-dance")
            self.assertEqual(affinity_preview["project_title"], "Study 003 | Nonlocal affinity graph dynamics")
            self.assertEqual(selected["project_id"], "study-002-scar-tissue")
            self.assertEqual(selected["project_title"], "Study 002 | Directional refractory path memory")
            self.assertEqual(selected["artifact_id"], "artifact-shot-selected")
            self.assertEqual(selected["experiment_id"], "experiment-shot-selected")
            self.assertEqual(selected["track"], "cinematography")
            self.assertEqual(selected["component_ids"], ["component-shot-selected"])
            self.assertEqual(selected["specimen_ids"], ["specimen-scar-tissue-v1"])
            self.assertEqual(selected["validation"], "verified")
            self.assertEqual(selected["stage"], "handoff")
            self.assertEqual(selected["media"]["kind"], "scene")
            self.assertEqual(selected["url"], f"/catalog-media/{selected['id']}")
            with mock.patch("houdini_ai.artifact_catalog._catalog_entries", side_effect=AssertionError("catalog rescanned")):
                self.assertEqual(resolve_catalog_media(root, selected["id"]), root / selected["path"])

            sequence = next(item for item in first if item["media"]["kind"] == "sequence")
            self.assertEqual(sequence["media"]["frame_count"], 2)
            self.assertEqual(sequence["media"]["first_frame"], 1)
            self.assertEqual(sequence["media"]["last_frame"], 2)
            self.assertTrue(resolve_catalog_media(root, sequence["id"]).name.endswith("0001.png"))

    def test_catalog_media_resolution_rejects_unknown_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            with self.assertRaisesRegex(FileNotFoundError, "catalog artifact"):
                resolve_catalog_media(root, "catalog-not-authority")

    def test_catalog_excludes_work_roots_retired_by_study_reset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            retired = root / "work" / "jobs" / "scar-tissue-look-old" / "review"
            retired.mkdir(parents=True)
            (retired / "preview.mp4").write_bytes(b"archived look")
            current = root / "work" / "jobs" / "scar-tissue-behavior-current" / "review"
            current.mkdir(parents=True)
            (current / "preview.mp4").write_bytes(b"current behavior")
            manifest = root / "studies" / "study_002_scar-tissue" / "99_archive" / "reset" / "archive-manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({
                "archived_work_roots": ["work/jobs/scar-tissue-look-old"]
            }), encoding="utf-8")

            paths = [item["path"] for item in build_artifact_catalog(root)]

            self.assertNotIn("work/jobs/scar-tissue-look-old/review/preview.mp4", paths)
            self.assertIn("work/jobs/scar-tissue-behavior-current/review/preview.mp4", paths)

    def test_catalog_discovers_and_verifies_canonical_study_vault_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_001/behavior-review.mp4"
            artifact = root / relative
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"selected-behavior")
            StudioStore(root).create(
                "artifacts",
                "artifact-study-003-selected-behavior",
                {
                    "id": "artifact-study-003-selected-behavior",
                    "experiment_id": "experiment-affinity",
                    "track": "behavior",
                    "path": relative,
                    "sha256": "sha256:" + hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "verified": True,
                },
            )

            item = next(entry for entry in build_artifact_catalog(root) if entry["path"] == relative)

            self.assertEqual(item["project_id"], "study-003-nonlocal-affinity-dance")
            self.assertEqual(item["project_title"], "Study 003 | Nonlocal affinity graph dynamics")
            self.assertEqual(item["track"], "behavior")
            self.assertEqual(item["stage"], "selected")
            self.assertEqual(item["validation"], "verified")
            self.assertEqual(resolve_catalog_media(root, item["id"]), artifact)

    def test_catalog_discovers_flat_specimen_and_delivery_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = root / "studies" / "study_003_nonlocal-affinity-dance"
            manifest = study / "00_study" / "study.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({
                "id": "study-003-nonlocal-affinity-dance",
                "title": "Study 003 — Non-Local Affinity",
            }), encoding="utf-8")
            specimen = study / "03_specimen" / "specimen-preview.mp4"
            delivery = study / "04_delivery" / "study-003-final.mp4"
            specimen.parent.mkdir(parents=True)
            delivery.parent.mkdir(parents=True)
            specimen.write_bytes(b"specimen")
            delivery.write_bytes(b"delivery")

            by_path = {item["path"]: item for item in build_artifact_catalog(root)}

            specimen_item = by_path[specimen.relative_to(root).as_posix()]
            delivery_item = by_path[delivery.relative_to(root).as_posix()]
            self.assertEqual(specimen_item["stage"], "specimen")
            self.assertEqual(delivery_item["stage"], "delivery")


if __name__ == "__main__":
    unittest.main()
