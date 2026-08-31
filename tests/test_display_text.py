import ast
import json
import re
import unittest
from pathlib import Path

from houdini_ai.display_text import validate_display_text


ROOT = Path(__file__).resolve().parents[1]


class DisplayTextTests(unittest.TestCase):
    def test_rejects_stock_ai_style_phrasing(self) -> None:
        examples = (
            "Let's dive into the simulation results.",
            "Here is what you need to know about the model.",
            "The result serves as a testament to the power of emergence.",
            "In today's rapidly evolving technical landscape, models change quickly.",
            "At its core, this system integrates a scalar field.",
            "It is not just a simulation; it is a window into complexity.",
            "I hope this helps explain the update rule.",
        )

        for text in examples:
            with self.subTest(text=text):
                errors = validate_display_text(text, "summary")
                self.assertTrue(errors)
                self.assertIn("AI-style", errors[0])

    def test_display_sources_do_not_embed_em_dash(self) -> None:
        python_sources = (
            "artifact_catalog.py",
            "nonlocal_affinity_review.py",
            "pipeline.py",
            "public_seed_bank.py",
        )
        for name in python_sources:
            path = ROOT / "src" / "houdini_ai" / name
            tree = ast.parse(path.read_text(encoding="utf-8"))
            values = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)]
            with self.subTest(path=path):
                self.assertFalse([value for value in values if "—" in value])

        for name in ("app.js", "capture.js", "components.js", "sample-study.js"):
            path = ROOT / "design-overlay-generator" / "web" / name
            quoted = re.findall(r'''["']([^"'\n]*—[^"'\n]*)["']''', path.read_text(encoding="utf-8"))
            with self.subTest(path=path):
                self.assertEqual(quoted, [])

        for path in (
            ROOT / "studies" / "study_003_nonlocal-affinity-dance" / "settings-export.json",
            ROOT / "studies" / "study_003_nonlocal-affinity-dance" / "03_specimen" / "overlay-config.json",
        ):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("—", json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
