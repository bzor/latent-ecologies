import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli
from houdini_ai.golden_specimens import GoldenSpecimenError, register_scar_tissue
from houdini_ai.studio_sessions import ensure_scar_tissue_session
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
            self.assertIn(str(root / "work" / "studio" / "ideas" / f"{record_id}.json"), output)

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
            digest = root / "work" / "studio" / "PROCESS_NOTES.md"
            self.assertIn(str(digest), digest_output)
            content = digest.read_text(encoding="utf-8")
            self.assertIn("## Missing functionality", content)
            self.assertIn(text.strip(), content)
            self.assertIn("component-look-a", content)

    def test_register_scar_tissue_golden_lineage_is_private_truthful_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            existing_components = (
                ("component-behavior-b3bcc837c3e2", "behavior", "behavior"),
                ("component-look-6013004ba32c", "look", "look"),
                ("component-palette-a52433fdb147", "chromatic", "palette"),
            )
            for component_id, track, kind in existing_components:
                store.create(
                    "components",
                    component_id,
                    {
                        "schema_version": 1,
                        "id": component_id,
                        "track": track,
                        "state": "promoted",
                        "component_kind": kind,
                        "source_experiment_id": f"experiment-scar-tissue-{track}",
                        "source_artifact_ref": f"work/jobs/scar-tissue-{track}/review/evidence.bin",
                        "rationale": f"KC selected the {track} component.",
                        "content_hash": "sha256:" + hashlib.sha256(component_id.encode()).hexdigest(),
                        "visibility": "private",
                    },
                )

            handoff = root / "work" / "studio" / "handoffs" / "scar-tissue-abc-a-v1"
            handoff.mkdir(parents=True)
            (handoff / "scar-tissue-abc-a-handoff.hiplc").write_bytes(b"hip")
            frames = handoff / "portrait-frames"
            frames.mkdir()
            for frame in range(1, 219):
                (frames / f"scar-tissue-portrait-{frame:04d}.png").write_bytes(b"png")

            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                code, output = self.run_cli(root, "register-golden", "scar-tissue")
                self.assertEqual(code, 0, output)
                self.assertEqual(self.run_cli(root, "register-golden", "scar-tissue")[0], 0)
                dispatch.assert_not_called()

            specimen = store.read("specimens", "specimen-scar-tissue-v1")
            self.assertEqual(validate_record("specimen", specimen), [])
            self.assertEqual(specimen["state"], "rendering")
            self.assertFalse(specimen["approved"])
            self.assertEqual(specimen["visibility"], "private")
            self.assertEqual(len(specimen["component_ids"]), 4)
            self.assertEqual(
                {store.read("components", component_id)["component_kind"] for component_id in specimen["component_ids"]},
                {"behavior", "look", "palette", "shot"},
            )
            progress = specimen["extensions"]["studio/render-progress"]
            self.assertEqual(progress["completed_frames"], 218)
            self.assertEqual(progress["contiguous_frames"], 218)
            self.assertEqual(progress["expected_frames"], 1260)
            self.assertEqual(progress["next_frame"], 219)
            self.assertEqual(specimen["extensions"]["studio/sound-decision"], "undecided")
            self.assertEqual(len(store.list("specimens")[0]), 1)
            self.assertEqual(len(store.list("components")[0]), 4)
            session = store.read("sessions", "session-scar-tissue-golden-run")
            self.assertEqual(session["current_phase"], "delivery")
            self.assertEqual(session["specimen_id"], "specimen-scar-tissue-v1")
            self.assertEqual(session["approved_selection_ids"], specimen["component_ids"])
            self.assertIn("sound", " ".join(session["unresolved_questions"]).lower())
            self.assertIn("219", session["recommended_next_action"])
            self.assertEqual(store.read("session-state", "active")["session_id"], session["id"])
            self.assertEqual(len(store.list("sessions")[0]), 1)

    def test_scar_tissue_behavior_reset_blocks_legacy_golden_reactivation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            store.create("studies", "study-002-scar-tissue", {
                "id": "study-002-scar-tissue",
                "state": "active",
                "current_phase": "behavior",
                "extensions": {"studio/reset-from-study-id": "scar-tissue"},
            })
            specimen = {"id": "specimen-scar-tissue-v1", "component_ids": []}

            with self.assertRaisesRegex(GoldenSpecimenError, "reset to Behavior"):
                register_scar_tissue(root)
            with self.assertRaisesRegex(ValueError, "reset to Behavior"):
                ensure_scar_tissue_session(store, specimen)

            self.assertEqual(store.list("sessions")[0], [])
            self.assertEqual(store.list("specimens")[0], [])

    def test_session_cli_creates_updates_activates_and_lists_inbox_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                code, output = self.run_cli(
                    root,
                    "session-create",
                    "Pilot Study",
                    "--project",
                    "pilot-study",
                    "--intent",
                    "Explore safely.",
                    "--next-action",
                    "Draft three directions.",
                    "--activate",
                )
                self.assertEqual(code, 0)
                session_id = output.splitlines()[0].split(": ", 1)[1]
                code, _ = self.run_cli(
                    root,
                    "session-update",
                    session_id,
                    json.dumps({"current_phase": "directions", "unresolved_questions": ["Which direction?"]}),
                )
                self.assertEqual(code, 0)
                self.assertIn(session_id, self.run_cli(root, "sessions")[1])
                inbox = self.run_cli(root, "inbox")[1]
                self.assertIn("session-question", inbox)
                self.assertIn("Which direction?", inbox)
                dispatch.assert_not_called()

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

    def test_pilot_study_003_bootstrap_cli_is_idempotent_and_non_executing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch("houdini_ai.runners.RunnerRegistry.dispatch") as dispatch:
                first_code, first_output = self.run_cli(root, "bootstrap-pilot-003")
                second_code, second_output = self.run_cli(root, "bootstrap-pilot-003")
            self.assertEqual((first_code, second_code), (0, 0))
            self.assertEqual(first_output, second_output)
            self.assertIn("idea: idea-nonlocal-affinity-dance-", first_output)
            self.assertIn("direction: selected Faithful Nonlocal Signed Graph", first_output)
            self.assertIn("direction: held Graph Choreography", first_output)
            self.assertIn("direction: held Encounter Memory", first_output)
            self.assertIn("proposal: proposed proposal-", first_output)
            self.assertIn("session: active Pilot Study 003", first_output)
            dispatch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
