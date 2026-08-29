import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai import detail_promote as dp
from houdini_ai.study_card import card_from_records, load_study_card, overlay_fields, validate_study_card


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "design-overlay-generator" / "web"


def sample_card() -> dict:
    return {
        "schema_version": 1,
        "study_id": "study-003-nonlocal-affinity-dance",
        "variation_id": "variation-001-primary-treatment",
        "variation_number": 1,
        "variation_title": "Primary Treatment",
        "variation_slug": "primary-treatment",
        "variation_file_stem": "var_001_primary-treatment",
        "number": 3,
        "title": "NONLOCAL AFFINITY",
        "subtitle": "agent fields with distance-defying attraction",
        "summary": "Agents form transient alliances with distant partners.",
        "bullets": ["attraction follows the alliance graph"],
        "params": [["AGENTS", "100 000"]],
        "source": "study-003",
        "date": "2026-08-21",
        "credits": "bzor computational studio",
    }


class StudyCardTests(unittest.TestCase):
    def test_valid_card_round_trips(self) -> None:
        card = sample_card()
        self.assertEqual(validate_study_card(card), [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study-card.json"
            path.write_text(json.dumps(card), encoding="utf-8")
            self.assertEqual(load_study_card(path), card)

    def test_invalid_cards_are_rejected(self) -> None:
        missing = sample_card()
        del missing["title"]
        self.assertEqual(validate_study_card(missing), ["study card is missing 'title'"])

        card = sample_card()
        card["number"] = 0
        card["bullets"] = ["fine", ""]
        card["params"] = [["only-label"]]
        errors = validate_study_card(card)
        self.assertEqual(len(errors), 3)
        card["number"] = 3
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study-card.json"
            path.write_text(json.dumps(card), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_study_card(path)

    def test_study_card_requires_variation_identity(self) -> None:
        card = sample_card()
        del card["variation_id"]
        self.assertEqual(
            validate_study_card(card),
            ["study card is missing 'variation_id'"],
        )

    def test_study_card_rejects_em_dash_in_display_text(self) -> None:
        card = sample_card()
        card["summary"] = "The update is deterministic — every run uses the same seed."

        self.assertEqual(
            validate_study_card(card),
            ["summary contains an em dash; use a period, colon, comma, or parentheses"],
        )

    def test_study_card_rejects_negative_parallelism(self) -> None:
        card = sample_card()
        card["summary"] = "It is not decoration, it is instrumentation."

        self.assertEqual(
            validate_study_card(card),
            ["summary uses an AI-style 'not X, it is Y' contrast; state the technical claim directly"],
        )

    def test_study_card_rejects_em_dash_in_bullets_and_parameters(self) -> None:
        card = sample_card()
        card["bullets"] = ["Measured density — normalized by cell count"]
        card["params"] = [["UPDATE — ORDER", "SYNCHRONOUS"]]

        self.assertEqual(
            validate_study_card(card),
            [
                "bullets[0] contains an em dash; use a period, colon, comma, or parentheses",
                "params[0][0] contains an em dash; use a period, colon, comma, or parentheses",
            ],
        )

    def test_overlay_fields_mapping(self) -> None:
        fields = overlay_fields(sample_card())
        self.assertEqual(fields["id"], "STUDY-003")
        self.assertEqual(fields["number"], 3)
        self.assertEqual(
            fields["variation"],
            {
                "id": "variation-001-primary-treatment",
                "number": 1,
                "title": "Primary Treatment",
                "slug": "primary-treatment",
                "file_stem": "var_001_primary-treatment",
            },
        )
        self.assertEqual(fields["summary"], "Agents form transient alliances with distant partners.")
        self.assertEqual(fields["params"], [["AGENTS", "100 000"]])
        card = sample_card()
        card["overlay_id"] = "STUDY-3B"
        self.assertEqual(overlay_fields(card)["id"], "STUDY-3B")

    def test_card_from_records_seeds_summaries(self) -> None:
        card = card_from_records(
            {"id": "study-007-test-thing", "title": "Test Thing"},
            {"title": "seed title", "short_summary": "short", "long_summary": "long"},
        )
        self.assertEqual(card["study_id"], "study-007-test-thing")
        self.assertEqual(card["number"], 7)
        self.assertEqual(card["title"], "Test Thing")
        self.assertEqual(card["subtitle"], "short")
        self.assertEqual(card["summary"], "long")
        self.assertEqual(validate_study_card(card), [])

    def test_sidecar_validation_covers_tracks_and_bullets(self) -> None:
        study = {
            "id": "STUDY-003", "title": "T", "fps": 24, "frames": 3,
            "variation": {
                "id": "variation-001-primary-treatment",
                "number": 1,
                "title": "Primary Treatment",
                "slug": "primary-treatment",
                "file_stem": "var_001_primary-treatment",
            },
            "bullets": ["ok"],
            "tracks": {
                "leader": {
                    "screen": [[0.5, 0.5], None, [0.6, 0.4]],
                    "depth": [5.0, None, 5.2],
                    "values": {"speed": [0.1, None, 0.9]},
                },
            },
        }
        self.assertEqual(dp.validate_study_sidecar(study), [])
        study["tracks"]["leader"]["screen"] = [[0.5, 0.5]]
        study["tracks"]["leader"]["values"]["speed"] = [0.1, 0.2]
        study["bullets"] = ["ok", 3]
        errors = dp.validate_study_sidecar(study)
        self.assertEqual(len(errors), 3)

    def test_overlay_display_defaults_do_not_use_em_dash(self) -> None:
        app = (WEB / "app.js").read_text(encoding="utf-8")
        capture = (WEB / "capture.js").read_text(encoding="utf-8")
        components = (WEB / "components.js").read_text(encoding="utf-8")

        self.assertNotIn('"9:16 — 1080×1920"', app)
        self.assertNotIn('"9:16 — 1080×1920"', capture)
        self.assertNotIn('tick: "—"', components)
        self.assertNotIn(' + " — " + ', app)

    def test_overlay_web_supports_tracks_and_text(self) -> None:
        components = (WEB / "components.js").read_text(encoding="utf-8")
        for component in ('id: "trackCallout"', 'id: "summaryBlock"', 'id: "bulletBlock"'):
            self.assertIn(component, components)
        self.assertIn('type: "track"', components)
        app = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn('s.type === "track"', app)
        self.assertIn("study.tracks", app)
        self.assertIn("loadRenderSpec", app)
        self.assertIn("CONFIG.render", app)
        self.assertIn("dog.activeStudy", app)
        self.assertIn("importJsonFile", app)
        self.assertIn('id="sampleStudyBtn"', (WEB / "index.html").read_text(encoding="utf-8"))
        sample = (WEB / "sample-study.js").read_text(encoding="utf-8")
        for key in ("tracks:", "summary:", "bullets:"):
            self.assertIn(key, sample)
        self.assertIn("wrapMini", (WEB / "overlay.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
