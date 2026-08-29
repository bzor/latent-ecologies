import json
import unittest
from pathlib import Path

from houdini_ai.look_execution import _validate_source
from houdini_ai.studio_schema import validate_record

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_001"
NEW = ROOT / "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_002"


class AffinityContinuousRewireCacheTests(unittest.TestCase):
    def test_corrected_behavior_rewires_through_visible_end(self) -> None:
        self.assertTrue((OLD / "cache_sequence/receipt.json").is_file(), "historical selection_001 must remain preserved")
        self.assertTrue((NEW / "cache_sequence/receipt.json").is_file(), "corrected selection_002 is missing")
        self.assertTrue((NEW / "look-source.json").is_file())
        self.assertTrue((NEW / "component.json").is_file())
        receipt = json.loads((NEW / "cache_sequence/receipt.json").read_text(encoding="utf-8"))
        audit = json.loads((NEW / "cache_sequence/fresh-hython-audit.json").read_text(encoding="utf-8"))
        source = json.loads((NEW / "look-source.json").read_text(encoding="utf-8"))
        component = json.loads((NEW / "component.json").read_text(encoding="utf-8"))
        old_component = json.loads((OLD / "component.json").read_text(encoding="utf-8"))

        self.assertEqual(receipt["frame_range"], [201, 650])
        self.assertEqual(receipt["frame_count"], 450)
        self.assertEqual(receipt["simulation_step_range"], [200, 649])
        self.assertEqual(receipt["extended_event_schedule_steps"], 960)
        self.assertEqual(receipt["extended_event_max_step"], 960)
        self.assertTrue(receipt["original_240_step_schedule_is_exact_prefix"])
        self.assertEqual(receipt["original_event_count"], 4400)
        self.assertEqual(receipt["extended_event_count"], 16520)
        self.assertEqual(receipt["last_visible_scheduled_rewire_frame"], 650)
        self.assertGreater(receipt["active_rewire_frames_in_visible_range"], 180)
        self.assertEqual(audit["checked_frame_count"], 450)
        self.assertEqual(audit["last_relationship_change_frame"], 650)
        self.assertGreater(audit["total_friend_changes"], 8000)
        self.assertGreater(audit["total_enemy_changes"], 8000)
        self.assertEqual(audit["errors"], [])
        self.assertNotEqual(receipt["final_state_sha256"], receipt["superseded_final_state_sha256"])

        self.assertEqual(component["state"], "promoted")
        self.assertEqual(component["component_kind"], "behavior")
        self.assertEqual(component["supersedes_id"], old_component["id"])
        self.assertFalse(validate_record("component", component))
        self.assertEqual(source["id"], component["id"])
        self.assertEqual(source["content_hash"], component["content_hash"])
        records = _validate_source(ROOT, "study-003-nonlocal-affinity-dance", source)
        self.assertEqual(len(records), 450)


if __name__ == "__main__":
    unittest.main()
