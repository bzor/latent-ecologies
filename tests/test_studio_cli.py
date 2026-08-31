import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class StudioCliTests(unittest.TestCase):
    def run_cli(self, root: Path, *args: str) -> tuple[int, str]:
        output = StringIO()
        with patch.object(cli, "ROOT", root), redirect_stdout(output):
            result = cli.main(["studio", *args])
        return result, output.getvalue()

    def test_seed_preserves_raw_text_is_private_and_prints_id_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = "  Keep  spacing; $(never execute)\nsecond line  "
            code, output = self.run_cli(root, "seed", raw, "--track", "behavior", "--source", "https://example.com/a")
            self.assertEqual(code, 0)
            record_id = output.splitlines()[0].split(": ", 1)[1]
            record = StudioStore(root).read("ideas", record_id)
            self.assertEqual(record["raw_text"], raw)
            self.assertEqual(record["visibility"], "private")
            self.assertEqual(record["source_urls"], ["https://example.com/a"])
            self.assertIn(str(root / "studio" / "ideas" / f"{record_id}.json"), output)

    def test_ideas_show_propose_list_and_approve_do_not_execute(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, seeded = self.run_cli(root, "seed", "idea")
            idea_id = seeded.splitlines()[0].split(": ", 1)[1]
            payload = json.dumps({"question": "Q", "mechanism": "M", "outputs": ["o"], "stop_conditions": ["s"], "runner": "behavior.probe", "cost_tier": "study"})
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                code, proposed = self.run_cli(root, "propose", idea_id, payload)
                proposal_id = proposed.splitlines()[0].split(": ", 1)[1]
                self.assertEqual(code, 0)
                self.assertEqual(self.run_cli(root, "approve", proposal_id)[0], 0)
                dispatch.assert_not_called()
            self.assertEqual(StudioStore(root).read("ideas", idea_id)["state"], "proposed")
            self.assertIn(idea_id, self.run_cli(root, "ideas")[1])
            self.assertIn(proposal_id, self.run_cli(root, "proposals", "--state", "approved")[1])
            self.assertIn('"raw_text": "idea"', self.run_cli(root, "show", idea_id)[1])

    def test_decide_promote_tag_untag_editorial_and_separate_approval(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            artifact_path = root / "work" / "jobs" / "run" / "review" / "artifact.bin"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"ok")
            store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior", "state": "proposed"})
            store.create("proposals", "proposal-a", {"id": "proposal-a", "idea_id": "idea-a", "track": "behavior", "state": "approved"})
            store.create("experiments", "experiment-a", {"id": "experiment-a", "proposal_id": "proposal-a", "track": "behavior", "state": "completed"})
            store.create("artifacts", "artifact-a", {"schema_version": 1, "id": "artifact-a", "experiment_id": "experiment-a", "track": "behavior", "state": "verified", "path": "work/jobs/run/review/artifact.bin", "sha256": "sha256:" + hashlib.sha256(b"ok").hexdigest(), "verified": True, "visibility": "private"})
            self.assertEqual(self.run_cli(root, "decide", "artifact-a", "promote", "--note", "KC selected it")[0], 0)
            self.assertEqual(validate_record("artifact", store.read("artifacts", "artifact-a")), [])
            self.assertEqual(self.run_cli(root, "promote", "artifact-a", "--kind", "behavior", "--rationale", "KC rationale")[0], 0)
            self.assertEqual(self.run_cli(root, "tag", "artifact-a", "publish:x", "role:field-observation", "readiness:ready-for-approval")[0], 0)
            editorial_id = "editorial-a"
            self.assertFalse(store.read("editorial", editorial_id)["approved"])
            self.assertEqual(self.run_cli(root, "approve", editorial_id)[0], 0)
            self.assertTrue(store.read("editorial", editorial_id)["approved"])
            self.assertEqual(self.run_cli(root, "untag", "artifact-a", "publish:x")[0], 0)
            self.assertIn(editorial_id, self.run_cli(root, "editorial")[1])

    def test_process_notes_capture_filter_and_generate_digest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            text = "  The browser should let me capture friction while it is fresh.  "
            code, output = self.run_cli(
                root, "note", text, "--category", "missing-functionality",
                "--stage", "look", "--track", "look", "--reference", "component-look-a",
            )
            self.assertEqual(code, 0)
            note_id = output.splitlines()[0].split(": ", 1)[1]
            note = StudioStore(root).read("notes", note_id)
            self.assertEqual(note["text"], text)
            self.assertEqual(note["reference_id"], "component-look-a")
            listed = self.run_cli(root, "notes", "--category", "missing-functionality")[1]
            self.assertIn(note_id, listed)
            self.assertNotIn(text.strip(), self.run_cli(root, "notes", "--category", "working")[1])
            code, digest_output = self.run_cli(root, "notes", "--digest")
            self.assertEqual(code, 0)
            digest = root / "studio" / "PROCESS_NOTES.md"
            self.assertIn(str(digest), digest_output)
            content = digest.read_text(encoding="utf-8")
            self.assertIn("## Missing functionality", content)
            self.assertIn(text.strip(), content)
            self.assertIn("component-look-a", content)

    def test_direction_cli_selects_a_thesis_and_derives_proposed_probe_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            store.create("ideas", "idea-pilot", {"id": "idea-pilot", "track": "behavior", "state": "scoped"})
            value = {
                "title": "Contact Exchange",
                "premise": "Contact can reorganize affinity without a global controller.",
                "mechanism": "Agents exchange discrete internal states only at contact, changing later affinity.",
                "expected_emergent_behavior": "Transient coalitions should form, split, and recombine.",
                "cheapest_informative_probe": "Run 120 low-resolution steps and inspect contact networks.",
                "risks": ["One state may dominate too quickly."],
                "conceptual_distinction": "This tests contact-mediated contagion rather than parameter variation.",
                "sibling_relations": [],
            }
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                code, output = self.run_cli(root, "direction-create", "idea-pilot", json.dumps(value))
                self.assertEqual(code, 0)
                direction_id = output.splitlines()[0].split(": ", 1)[1]
                self.assertEqual(self.run_cli(root, "direction-decide", direction_id, "select")[0], 0)
                probe = json.dumps({
                    "outputs": ["motion-check.mp4"], "stop_conditions": ["120 steps"],
                    "runner": "behavior.probe", "cost_tier": "probe",
                })
                code, proposal_output = self.run_cli(root, "direction-propose", direction_id, probe)
                self.assertEqual(code, 0)
                proposal_id = proposal_output.splitlines()[0].split(": ", 1)[1]
                self.assertEqual(store.read("proposals", proposal_id)["direction_ids"], [direction_id])
                self.assertIn(direction_id, self.run_cli(root, "directions")[1])
                dispatch.assert_not_called()

    def test_note_capture_refreshes_digest_automatically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, _ = self.run_cli(
                root, "note", "the packet flow feels fast", "--category", "working",
                "--stage", "behavior", "--track", "behavior",
            )
            self.assertEqual(code, 0)
            digest = root / "studio" / "PROCESS_NOTES.md"
            self.assertTrue(digest.is_file())
            self.assertIn("the packet flow feels fast", digest.read_text(encoding="utf-8"))

    def test_retro_records_both_answers_as_notes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, output = self.run_cli(
                root, "retro", "--stage", "look", "--track", "look",
                "--dragged", "waiting on the starter build", "--fun", "the one-frame probes",
                "--reference", "component-look-a",
            )
            self.assertEqual(code, 0)
            store = StudioStore(root)
            ids = [line.split(": ", 1)[1] for line in output.splitlines() if line.startswith("id: ")]
            self.assertEqual(len(ids), 2)
            categories = {store.read("notes", note_id)["category"] for note_id in ids}
            self.assertEqual(categories, {"pain-point", "working"})
            for note_id in ids:
                self.assertEqual(store.read("notes", note_id)["reference_id"], "component-look-a")

    def test_retro_accepts_a_single_answer_but_not_none(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            code, output = self.run_cli(root, "retro", "--stage", "look", "--track", "look", "--fun", "clean handoff")
            self.assertEqual(code, 0)
            self.assertEqual(output.count("id: "), 1)
            with self.assertRaisesRegex(ValueError, "at least one answer"):
                self.run_cli(root, "retro", "--stage", "look", "--track", "look")

    def test_gate_decisions_print_the_micro_retro_nudge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            artifact_path = root / "work" / "jobs" / "run" / "review" / "artifact.bin"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"ok")
            store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior", "state": "proposed"})
            store.create("proposals", "proposal-a", {"id": "proposal-a", "idea_id": "idea-a", "track": "behavior", "state": "approved"})
            store.create("experiments", "experiment-a", {"id": "experiment-a", "proposal_id": "proposal-a", "track": "behavior", "state": "completed"})
            store.create("artifacts", "artifact-a", {"schema_version": 1, "id": "artifact-a", "experiment_id": "experiment-a", "track": "behavior", "state": "verified", "path": "work/jobs/run/review/artifact.bin", "sha256": "sha256:" + hashlib.sha256(b"ok").hexdigest(), "verified": True, "visibility": "private"})
            _, decide_output = self.run_cli(root, "decide", "artifact-a", "promote", "--note", "selected")
            self.assertIn("micro-retro", decide_output)
            _, promote_output = self.run_cli(root, "promote", "artifact-a", "--kind", "behavior", "--rationale", "KC rationale")
            self.assertIn("micro-retro", promote_output)


if __name__ == "__main__":
    unittest.main()
