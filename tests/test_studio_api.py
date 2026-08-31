import tempfile
import unittest
from pathlib import Path

from houdini_ai.studio_api import StudioAPI


class StudioAPITests(unittest.TestCase):
    def test_direction_operations_require_dedicated_decisions_and_derive_only_proposed_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            idea = api.capture_idea({"title": "Pilot", "raw_text": "Explore reciprocal traces.", "track": "behavior"})
            value = {
                "idea_id": idea["id"],
                "title": "Reciprocal Scar Field",
                "premise": "Local memory can turn attraction into later repulsion.",
                "mechanism": "Agents deposit a signed memory field and invert their response after repeated exposure.",
                "expected_emergent_behavior": "Migrating fronts should scar and repel later populations.",
                "cheapest_informative_probe": "Run 120 low-resolution steps and inspect fronts.",
                "risks": ["The field may settle into a static attractor."],
                "conceptual_distinction": "This changes the causal interaction rule rather than numerical tuning.",
                "sibling_relations": [],
            }
            direction = api.create_direction(value)
            with self.assertRaises(ValueError):
                api.update_status("directions", direction["id"], "selected")
            selected = api.decide_direction(direction["id"], "select")
            self.assertEqual(selected["state"], "selected")
            proposal = api.derive_direction_proposal(direction["id"], {
                "outputs": ["motion-check.mp4"], "stop_conditions": ["120 steps"],
                "runner": "behavior.probe", "cost_tier": "probe",
            })
            self.assertEqual(proposal["state"], "proposed")
            self.assertEqual(proposal["direction_ids"], [direction["id"]])
            self.assertEqual(api.list_records("directions")["items"][0]["id"], direction["id"])

    def test_capture_idea_is_private_local_inert_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api = StudioAPI(root)
            raw_text = '<script>alert("network")</script> $(touch escaped)'

            idea = api.capture_idea({"title": "Scar paths", "raw_text": raw_text, "track": "behavior"})

            self.assertEqual(idea["raw_text"], raw_text)
            self.assertEqual(idea["visibility"], "private")
            self.assertEqual(idea["state"], "inbox")
            self.assertTrue(idea["id"].startswith("idea-"))
            self.assertEqual(api.list_records("ideas")["items"], [idea])
            self.assertTrue((root / "studio" / "ideas" / f'{idea["id"]}.json').is_file())
            self.assertFalse((root / "escaped").exists())

    def test_create_proposal_lists_details_and_enforces_status_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            proposal = api.create_record(
                "proposals",
                {
                    "schema_version": 1,
                    "id": "proposal-scar-probe",
                    "idea_id": "idea-scar-paths",
                    "track": "behavior",
                    "state": "proposed",
                    "question": "Does saturation create turnover?",
                    "mechanism": "Deposit, saturate, repel, decay.",
                    "outputs": ["field-slice", "preview-loop"],
                    "stop_conditions": ["No turnover after 300 steps"],
                    "runner": "behavior.scar_probe",
                    "cost_tier": "probe",
                    "visibility": "private",
                },
            )

            self.assertEqual(api.list_records("proposals")["items"], [proposal])
            approved = api.update_status("proposals", proposal["id"], "approved")
            self.assertEqual(approved["state"], "approved")
            with self.assertRaisesRegex(ValueError, "cannot transition"):
                api.update_status("proposals", proposal["id"], "rejected")

    def test_dedicated_proposal_decisions_only_approve_or_hold_proposed_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            proposal = api.create_record(
                "proposals",
                {
                    "schema_version": 1, "id": "proposal-decision", "idea_id": "idea-source",
                    "track": "behavior", "state": "proposed", "question": "Q", "mechanism": "M",
                    "outputs": ["preview"], "stop_conditions": ["stop"], "runner": "behavior.probe",
                    "cost_tier": "probe", "visibility": "private",
                },
            )
            held = api.hold_proposal(proposal["id"])
            self.assertEqual(held["state"], "held")
            with self.assertRaisesRegex(ValueError, "only proposed"):
                api.approve_proposal(proposal["id"])

    def test_generic_creation_requires_safe_initial_lifecycle_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            with self.assertRaisesRegex(ValueError, "initial state"):
                api.create_record(
                    "proposals",
                    {
                        "schema_version": 1,
                        "id": "proposal-bypass",
                        "idea_id": "idea-source",
                        "track": "behavior",
                        "state": "approved",
                        "question": "Bypass?",
                        "mechanism": "No.",
                        "outputs": ["none"],
                        "stop_conditions": ["immediately"],
                        "runner": "behavior.probe",
                        "cost_tier": "probe",
                        "visibility": "private",
                    },
                )

    def test_unverified_free_text_component_promotion_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            value = {
                "schema_version": 1, "id": "experiment-safe", "proposal_id": "proposal-missing",
                "track": "behavior", "state": "draft", "runner": "arbitrary.command",
                "parameters": {}, "visibility": "private",
            }
            with self.assertRaisesRegex(ValueError, "proposal"):
                api.create_record("experiments", value)
            api.store.create(
                "proposals", "proposal-approved",
                {"schema_version": 1, "id": "proposal-approved", "idea_id": "idea-source", "track": "behavior", "state": "approved", "question": "Q", "mechanism": "M", "outputs": ["preview"], "stop_conditions": ["stop"], "runner": "behavior.probe", "cost_tier": "probe", "visibility": "private"},
            )
            value.update({"proposal_id": "proposal-approved", "runner": "behavior.probe", "parameters": {"command": "touch escaped"}})
            with self.assertRaisesRegex(ValueError, "parameters"):
                api.create_record("experiments", value)

        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            with self.assertRaisesRegex(ValueError, "verified artifact"):
                api.promote_component({"source_artifact_ref": "work/jobs/made-up.mp4"})

    def test_generic_status_api_cannot_manufacture_completed_experiments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            api.store.create(
                "proposals", "proposal-approved",
                {"schema_version": 1, "id": "proposal-approved", "idea_id": "idea-source", "track": "behavior", "state": "approved", "question": "Q", "mechanism": "M", "outputs": ["preview"], "stop_conditions": ["stop"], "runner": "behavior.probe", "cost_tier": "probe", "visibility": "private"},
            )
            experiment = api.create_record("experiments", {
                "schema_version": 1, "id": "experiment-safe", "proposal_id": "proposal-approved",
                "track": "behavior", "state": "draft", "runner": "behavior.probe",
                "parameters": {}, "visibility": "private",
            })
            self.assertEqual(experiment["state"], "draft")
            with self.assertRaisesRegex(ValueError, "dedicated execution"):
                api.update_status("experiments", experiment["id"], "approved")

    def test_api_proposal_creation_uses_runner_allowlist_and_existing_idea(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            idea = api.capture_idea({"title": "Path memory", "raw_text": "Seed", "track": "behavior"})
            value = {
                "idea_id": idea["id"], "question": "Q", "mechanism": "M",
                "outputs": ["preview"], "stop_conditions": ["stop"],
                "runner": "arbitrary.command", "cost_tier": "probe",
            }
            with self.assertRaisesRegex(ValueError, "unregistered runner"):
                api.create_proposal(value)
            value["runner"] = "behavior.probe"
            proposal = api.create_proposal(value)
            self.assertEqual(proposal["idea_id"], idea["id"])
            value["idea_id"] = "idea-missing"
            with self.assertRaises(FileNotFoundError):
                api.create_proposal(value)

    def test_lookdev_proposal_can_reference_promoted_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            idea = api.capture_idea({"title": "Scar Tissue looks", "raw_text": "Develop visual language", "track": "look"})
            value = {
                "idea_id": idea["id"], "question": "Which visual grammar reveals the behavior?",
                "mechanism": "Render fixed behavior through independent visual treatments.",
                "outputs": ["look-comparison"], "stop_conditions": ["behavior becomes illegible"],
                "runner": "look.scar_tissue_probe", "cost_tier": "probe",
                "extensions": {"studio/source-component": "component-behavior-source"},
            }
            proposal = api.create_proposal(value)
            self.assertEqual(proposal["track"], "look")
            self.assertEqual(proposal["extensions"]["studio/source-component"], "component-behavior-source")

    def test_generic_record_creation_cannot_bypass_component_promotion_verification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            with self.assertRaisesRegex(ValueError, "verified artifact"):
                api.create_record("components", {"id": "component-made-up", "visibility": "private"})

    def test_editorial_tags_and_summary_remain_private(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            editorial = api.create_record(
                "editorial",
                {
                    "schema_version": 1,
                    "id": "editorial-scar-note",
                    "state": "draft",
                    "artifact_refs": ["work/jobs/scar/review/preview.mp4"],
                    "destinations": [],
                    "roles": [],
                    "tags": ["visibility:private"],
                    "visibility": "private",
                    "approved": False,
                },
            )
            tagged = api.update_editorial_tags(
                editorial["id"], ["publish:web", "role:field-observation", "visibility:private"]
            )

            self.assertIn("publish:web", tagged["tags"])
            self.assertEqual(tagged["visibility"], "private")
            summary = api.summary()
            self.assertEqual(summary["visibility"], "private")
            self.assertEqual(summary["counts"]["components"], 0)
            self.assertEqual(summary["counts"]["editorial"], 1)

    def test_editorial_tag_update_rejects_non_list_payload(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api = StudioAPI(Path(directory))
            api.create_record(
                "editorial",
                {
                    "schema_version": 1,
                    "id": "editorial-safe",
                    "state": "draft",
                    "artifact_refs": ["work/jobs/a.mp4"],
                    "destinations": [],
                    "roles": [],
                    "tags": [],
                    "visibility": "private",
                    "approved": False,
                },
            )
            with self.assertRaisesRegex(ValueError, "list"):
                api.update_editorial_tags("editorial-safe", "publish:web")

    def test_promotion_verifies_artifact_lineage_instead_of_trusting_free_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            api = StudioAPI(root)
            artifact_path = root / "work" / "jobs" / "scar" / "review" / "preview.mp4"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"verified preview")
            import hashlib

            api.store.create("ideas", "idea-scar", {"id": "idea-scar", "track": "behavior", "state": "proposed"})
            api.store.create("proposals", "proposal-scar", {"id": "proposal-scar", "idea_id": "idea-scar", "track": "behavior", "state": "approved"})
            api.store.create("experiments", "experiment-scar-001", {"id": "experiment-scar-001", "proposal_id": "proposal-scar", "track": "behavior", "state": "completed"})
            api.store.create(
                "artifacts",
                "artifact-scar-preview",
                {
                    "schema_version": 1,
                    "id": "artifact-scar-preview",
                    "experiment_id": "experiment-scar-001",
                    "track": "behavior",
                    "state": "verified",
                    "path": "work/jobs/scar/review/preview.mp4",
                    "sha256": "sha256:" + hashlib.sha256(b"verified preview").hexdigest(),
                    "verified": True,
                    "visibility": "private",
                },
            )

            component = api.promote_artifact("artifact-scar-preview", "behavior", "Legible turnover.")

            self.assertEqual(component["source_experiment_id"], "experiment-scar-001")
            self.assertEqual(component["source_artifact_ref"], "work/jobs/scar/review/preview.mp4")
            with self.assertRaisesRegex(ValueError, "does not exist"):
                api.promote_artifact("artifact-made-up", "behavior", "Trust this path.")

    def test_browser_shell_exposes_milestone_navigation_and_safe_rendering(self) -> None:
        website = Path(__file__).resolve().parents[1] / "website"
        html = (website / "index.html").read_text(encoding="utf-8")
        script = (website / "app.js").read_text(encoding="utf-8")
        styles = (website / "styles.css").read_text(encoding="utf-8")
        for label in ("Cockpit / Inbox", "Seeds", "Directions", "Proposals", "Artifacts", "Runs / Reviews", "Components", "Specimens", "Editorial"):
            self.assertIn(label, html)
        self.assertIn('id="ideaForm"', html)
        self.assertIn('id="processNoteForm"', html)
        self.assertIn('id="directionForm"', html)
        self.assertIn('id="directionMerge"', html)
        self.assertIn('id="studioContent"', html)
        self.assertIn('id="promotionForm"', html)
        self.assertIn("['approve','hold']", script)
        self.assertIn("/proposals/${encodeURIComponent(item.id)}/${action}", script)
        self.assertIn("/api/studio/artifacts/${encodeURIComponent(id)}/promote", script)
        self.assertIn("/api/studio/catalog", script)
        self.assertIn("renderCatalog", script)
        self.assertIn("renderCatalogProjects", script)
        self.assertIn("renderCatalogPlayer", script)
        self.assertIn("video.controls=true", script)
        self.assertIn("video.preload='metadata'", script)
        self.assertIn("catalogProjectId", script)
        self.assertIn("catalog-project-bar", styles)
        self.assertIn(".catalog-player", styles)
        self.assertIn(".studio-card>.button{display:inline-block;margin-top:12px}", styles)
        self.assertIn("PROJECTS", script)
        self.assertIn("showStartupError", script)
        self.assertIn("Unable to load the private Studio", script)
        self.assertIn("/api/studio/review-inbox", script)
        self.assertIn("/api/studio/notes", script)
        self.assertIn("renderCockpit", script)
        self.assertIn("renderDirectionBoard", script)
        self.assertIn("/api/studio/directions", script)
        for operation in ("select", "hold", "mutate", "merge", "archive", "reject", "propose"):
            self.assertIn(operation, script)
        self.assertIn(".idea-form.hidden{display:none}", styles)
        self.assertIn("method:'POST'", script)
        self.assertIn("X-Studio-Mutation-Token", script)
        self.assertIn("textContent", script)
        self.assertNotIn("raw_text}</", script)
        self.assertNotIn('data-job="${j.id}"', script)
        self.assertNotIn("<dd>${state.job.seed}</dd>", script)
        self.assertNotIn("innerHTML", script)


if __name__ == "__main__":
    unittest.main()
