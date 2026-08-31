import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.overlay_parameter_manifest import (
    HEADLESS_BINDING,
    bind_headless_overlay_manifest,
    load_overlay_parameter_manifest,
    overlay_manifest_fields,
)


ROOT = Path(__file__).resolve().parents[1]


class OverlayParameterManifestTests(unittest.TestCase):
    def sample_manifest(self) -> dict:
        return {
            "schema_version": 1,
            "variation": {
                "number": 4,
                "title": "High Attraction",
                "file_stem": "bhvr_001_var_004_high-attraction",
            },
            "source": {
                "hip_path": "E:/study/02_look/look-v004.hiplc",
                "hip_sha256": "sha256:" + "a" * 64,
                "hip_dirty": False,
                "node_path": "/obj/PLAYGROUND_SIM/PROMOTED_BEHAVIOR",
                "asset_type": "bzor::nonlocal_affinity_parallel::1.3",
                "frame": 120,
            },
            "parameters": [
                {
                    "key": "behavior.attraction",
                    "label": "Attraction",
                    "parameter": "attraction",
                    "type": "float",
                    "value": 0.035,
                    "units": "coefficient",
                    "comparison_range": [0.0, 0.08],
                    "animated": False,
                },
                {
                    "key": "behavior.apply_rewires",
                    "label": "Apply Ordered Rewires",
                    "parameter": "apply_rewires",
                    "type": "toggle",
                    "value": True,
                    "units": "boolean",
                    "animated": False,
                },
            ],
        }

    def test_loads_and_maps_structured_overlay_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(self.sample_manifest()), encoding="utf-8")

            manifest = load_overlay_parameter_manifest(path)
            fields = overlay_manifest_fields(manifest)

            self.assertEqual(fields["parameter_manifest"]["variation"]["number"], 4)
            self.assertEqual(fields["overlay_parameters"][0]["key"], "behavior.attraction")
            self.assertEqual(fields["params"], [["Attraction", "0.035"], ["Apply Ordered Rewires", "on"]])

    def test_rejects_duplicate_keys_and_invalid_comparison_ranges(self) -> None:
        manifest = self.sample_manifest()
        manifest["parameters"][1]["key"] = "behavior.attraction"
        manifest["parameters"][0]["comparison_range"] = [1.0, 0.0]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError) as raised:
                load_overlay_parameter_manifest(path)
            message = str(raised.exception)
            self.assertIn("duplicate parameter key", message)
            self.assertIn("comparison_range", message)

    def test_houdini_overlay_exporter_consumes_parameter_manifest(self) -> None:
        source = (ROOT / "houdini" / "export_overlay_study.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--parameter-manifest"', source)
        self.assertIn("load_overlay_parameter_manifest", source)
        self.assertIn("overlay_manifest_fields", source)


if __name__ == "__main__":
    unittest.main()


class HeadlessBindingTests(unittest.TestCase):
    def unbound_manifest(self, hip_path: Path) -> dict:
        manifest = OverlayParameterManifestTests().sample_manifest()
        manifest["source"]["hip_path"] = str(hip_path)
        manifest["source"]["hip_sha256"] = None
        manifest["source"]["hip_dirty"] = True
        return manifest

    def write_scene(self, directory: Path) -> tuple[Path, Path, str]:
        hip = directory / "look_r001.hiplc"
        hip.write_bytes(b"locked scene bytes")
        digest = "sha256:" + hashlib.sha256(hip.read_bytes()).hexdigest()
        manifest_path = directory / "manifest.json"
        manifest_path.write_text(json.dumps(self.unbound_manifest(hip)), encoding="utf-8")
        return hip, manifest_path, digest

    def test_binds_unbound_headless_export(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            hip, manifest_path, digest = self.write_scene(Path(raw))
            bound = bind_headless_overlay_manifest(manifest_path, hip, digest)
            self.assertEqual(bound["source"]["hip_sha256"], digest)
            self.assertFalse(bound["source"]["hip_dirty"])
            self.assertEqual(bound["source"]["checksum_binding"], HEADLESS_BINDING)
            reread = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(reread["source"]["hip_sha256"], digest)

    def test_refuses_when_hip_changed_after_load(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            hip, manifest_path, _ = self.write_scene(Path(raw))
            stale = "sha256:" + "b" * 64
            with self.assertRaisesRegex(ValueError, "changed on disk"):
                bind_headless_overlay_manifest(manifest_path, hip, stale)

    def test_refuses_manifest_from_another_hip(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            hip, manifest_path, digest = self.write_scene(directory)
            other = directory / "other.hiplc"
            other.write_bytes(hip.read_bytes())
            with self.assertRaisesRegex(ValueError, "not the HIP being bound"):
                bind_headless_overlay_manifest(manifest_path, other, digest)

    def test_already_bound_matching_manifest_is_left_alone(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            hip, manifest_path, digest = self.write_scene(directory)
            manifest = self.unbound_manifest(hip)
            manifest["source"]["hip_sha256"] = digest
            manifest["source"]["hip_dirty"] = False
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            bound = bind_headless_overlay_manifest(manifest_path, hip, digest)
            self.assertNotIn("checksum_binding", bound["source"])

    def test_already_bound_mismatching_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            hip, manifest_path, digest = self.write_scene(Path(raw))
            manifest = self.unbound_manifest(hip)
            manifest["source"]["hip_sha256"] = "sha256:" + "c" * 64
            manifest["source"]["hip_dirty"] = False
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not match the on-disk HIP"):
                bind_headless_overlay_manifest(manifest_path, hip, digest)
