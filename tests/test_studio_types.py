import unittest

from houdini_ai.studio_types import (
    COST_TIERS,
    DECISIONS,
    EDITORIAL_ROLES,
    EDITORIAL_TAGS,
    LIFECYCLE_TRANSITIONS,
    TRACKS,
    VISIBILITIES,
    can_transition,
    cost_tier_rank,
    effective_visibility,
    validate_editorial_tags,
    validate_track,
)


class StudioTypesTests(unittest.TestCase):
    def test_track_vocabulary_accepts_six_studio_tracks(self) -> None:
        self.assertEqual(
            TRACKS,
            ("behavior", "look", "chromatic", "cinematography", "specimen", "field-station"),
        )
        for track in TRACKS:
            with self.subTest(track=track):
                self.assertTrue(validate_track(track))

    def test_track_vocabulary_rejects_unknown_or_malformed_values(self) -> None:
        for track in ("", "Behavior", "field_station", "render", None, 1):
            with self.subTest(track=track):
                self.assertFalse(validate_track(track))

    def test_lifecycle_transition_tables_are_explicit_and_terminal_states_are_closed(self) -> None:
        self.assertTrue(can_transition("idea", "inbox", "scoped"))
        self.assertTrue(can_transition("proposal", "proposed", "approved"))
        self.assertTrue(can_transition("experiment", "approved", "running"))
        self.assertFalse(can_transition("proposal", "proposed", "running"))
        self.assertFalse(can_transition("idea", "archived", "inbox"))
        self.assertEqual(LIFECYCLE_TRANSITIONS["idea"]["archived"], frozenset())

    def test_decision_vocabulary_is_complete(self) -> None:
        self.assertEqual(
            DECISIONS,
            ("keep", "iterate", "mutate", "hold", "archive", "reject", "promote"),
        )

    def test_private_visibility_dominates_public_candidate_tags(self) -> None:
        self.assertEqual(VISIBILITIES, ("private", "public-candidate"))
        self.assertEqual(
            effective_visibility("public-candidate", ["publish:x", "visibility:private"]),
            "private",
        )
        self.assertEqual(effective_visibility("private", ["publish:web"]), "private")
        self.assertEqual(
            effective_visibility("public-candidate", ["publish:web"]),
            "public-candidate",
        )

    def test_editorial_tags_and_roles_have_a_checked_vocabulary(self) -> None:
        self.assertIn("field-observation", EDITORIAL_ROLES)
        self.assertIn("role:field-observation", EDITORIAL_TAGS)
        self.assertEqual(validate_editorial_tags(["publish:web", "role:failure"]), [])
        self.assertEqual(validate_editorial_tags(["publish:web", "publish:web"]), ["duplicate tag: publish:web"])
        self.assertEqual(validate_editorial_tags(["role:unknown"]), ["unknown editorial tag: role:unknown"])

    def test_cost_tiers_have_strict_total_order(self) -> None:
        self.assertEqual(COST_TIERS, ("tiny", "probe", "study", "specimen", "external"))
        ranks = [cost_tier_rank(tier) for tier in COST_TIERS]
        self.assertEqual(ranks, sorted(set(ranks)))
        with self.assertRaises(ValueError):
            cost_tier_rank("large")


if __name__ == "__main__":
    unittest.main()
