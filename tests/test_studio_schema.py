import copy
import unittest

from houdini_ai.studio_schema import validate_record


VALID_RECORDS = {
    "idea": {
        "schema_version": 1,
        "id": "idea-scar-tissue",
        "title": "Scar tissue paths",
        "raw_text": "Agents reinforce paths until saturation makes them repellent.",
        "track": "behavior",
        "state": "inbox",
        "visibility": "private",
    },
    "proposal": {
        "schema_version": 1,
        "id": "proposal-scar-probe",
        "idea_id": "idea-scar-tissue",
        "track": "behavior",
        "state": "proposed",
        "question": "Does saturation produce path turnover?",
        "mechanism": "Deposit, saturate, repel, and decay a scalar field.",
        "outputs": ["field-slice"],
        "stop_conditions": ["No turnover after 300 steps"],
        "runner": "behavior.scar_tissue_probe",
        "cost_tier": "probe",
        "visibility": "private",
    },
    "experiment": {
        "schema_version": 1,
        "id": "experiment-scar-001",
        "proposal_id": "proposal-scar-probe",
        "track": "behavior",
        "state": "approved",
        "runner": "behavior.scar_tissue_probe",
        "parameters": {"seed": 7},
        "visibility": "private",
    },
    "artifact": {
        "schema_version": 1,
        "id": "artifact-scar-preview",
        "experiment_id": "experiment-scar-001",
        "track": "behavior",
        "state": "verified",
        "path": "work/jobs/scar-001/review/preview.mp4",
        "sha256": "sha256:" + "a" * 64,
        "verified": True,
        "visibility": "private",
    },
    "component": {
        "schema_version": 1,
        "id": "component-behavior-scar-v1",
        "track": "behavior",
        "state": "promoted",
        "component_kind": "behavior",
        "source_experiment_id": "experiment-scar-001",
        "source_artifact_ref": "work/jobs/scar/preview.mp4",
        "rationale": "The turnover is legible and structurally useful.",
        "content_hash": "sha256:" + "a" * 64,
        "visibility": "private",
    },
    "specimen": {
        "schema_version": 1,
        "id": "specimen-scar-glass-v1",
        "state": "draft",
        "component_ids": ["component-behavior-scar-v1"],
        "creative_reason": "Pair path memory with a transparent material study.",
        "deliverables": ["ten-second-loop"],
        "cost_tier": "specimen",
        "approved": False,
        "visibility": "private",
    },
    "editorial": {
        "schema_version": 1,
        "id": "editorial-scar-field-note",
        "state": "draft",
        "artifact_refs": ["work/jobs/scar/preview.mp4"],
        "destinations": ["web"],
        "roles": ["field-observation"],
        "tags": ["publish:web", "role:field-observation", "visibility:public-candidate"],
        "visibility": "public-candidate",
        "approved": False,
    },
    "look-direction-brief": {
        "schema_version": 1,
        "id": "look-direction-weave",
        "study_id": "study-003-test",
        "round_id": "look-round-001",
        "sequence_index": 1,
        "state": "selected",
        "visibility": "private",
        "source_behavior_component_id": "component-behavior-a",
        "source_behavior_content_hash": "sha256:" + "a" * 64,
        "source_cache_receipt": [{
            "path": "studies/study_003_test/01_behavior/03_selected/selection_001/cache.0001.bgeo.sc",
            "bytes": 12,
            "sha256": "a" * 64,
        }],
        "direction": {
            "id": "look-direction-weave",
            "title": "Affinity Weave",
            "thesis": "Affinity becomes physical weave.",
            "visual_target": {
                "references": ["reference A", "reference B"],
                "final_image_thesis": "A resolved material weave whose density makes affinity visible.",
                "required_reads": ["weave density"],
                "prohibited_reads": ["raw point diagnostic"],
                "material_intent": "Editable fibrous MaterialX response.",
                "framing_intent": "Neutral coverage and hero detail.",
                "lighting_intent": "Locked neutral rig plus hero grazing light.",
                "temporal_signature": "Strands remain coherent as they relax.",
            },
            "state_to_form_mappings": [{
                "source_attribute": "affinity",
                "visible_response": "strand density",
                "houdini_mechanism": "Copy strands from affinity.",
                "acceptance_observable": "High affinity produces more strands.",
            }],
            "primary_hierarchy": ["field", "agents"],
            "representation_system": "SOP curves",
            "lighting_assumptions": "Neutral technical rig",
            "cost_tier": "probe",
            "motion_proposition": "Strands relax over time.",
            "exclusions": ["Behavior changes"],
            "risks": ["Decorative noise"],
            "cheapest_decisive_probe": "Three technical frames",
            "stop_conditions": ["Missing affinity"],
            "implementation_stages": [
                {
                    "id": stage_id,
                    "title": title,
                    "intent": "Build and verify one meaningful part of the direction.",
                    "data_inputs": ["affinity"],
                    "houdini_strategy": "Use a labelled, independently cookable SOP branch.",
                    "output": "A cooked and inspectable stage output.",
                    "acceptance_observable": f"{title} is visible in the verified probe.",
                }
                for stage_id, title in (
                    ("inspect-source", "Source inspection"),
                    ("build-primary", "Primary form"),
                    ("build-hierarchy", "Supporting hierarchy"),
                    ("package-handoff", "Temporal proof and handoff"),
                )
            ],
        },
    },
    "note": {
        "schema_version": 1,
        "id": "note-process-capture",
        "created_at": "2026-08-12T22:30:00Z",
        "category": "missing-functionality",
        "stage": "look",
        "track": "look",
        "text": "Capture process observations while they are fresh.",
        "reference_id": "component-look-6013004ba32c",
        "visibility": "private",
    },
}


class StudioSchemaTests(unittest.TestCase):
    def test_minimal_record_of_each_kind_is_valid(self) -> None:
        for kind, record in VALID_RECORDS.items():
            with self.subTest(kind=kind):
                self.assertEqual(validate_record(kind, record), [])

    def test_validation_does_not_mutate_input(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["editorial"])
        before = copy.deepcopy(record)
        validate_record("editorial", record)
        self.assertEqual(record, before)

    def test_invalid_ids_unknown_tracks_and_visibility_return_paths(self) -> None:
        cases = (("id", "bad id"), ("track", "rendering"), ("visibility", "public"))
        for field, value in cases:
            record = copy.deepcopy(VALID_RECORDS["proposal"])
            record[field] = value
            with self.subTest(field=field):
                errors = validate_record("proposal", record)
                self.assertTrue(any(error.startswith(f"{field}:") for error in errors), errors)

    def test_missing_lineage_is_rejected_at_its_path(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["proposal"])
        del record["idea_id"]
        self.assertTrue(any(error.startswith("idea_id:") for error in validate_record("proposal", record)))

    def test_proposal_runner_must_be_identifier_not_command(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["proposal"])
        record["runner"] = "python probe.py --seed 7"
        self.assertTrue(any(error.startswith("runner:") for error in validate_record("proposal", record)))

    def test_public_candidate_requires_artifacts_and_is_not_approved(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["editorial"])
        record["artifact_refs"] = []
        self.assertTrue(any(error.startswith("artifact_refs:") for error in validate_record("editorial", record)))
        record = copy.deepcopy(VALID_RECORDS["editorial"])
        record["approved"] = True
        self.assertTrue(any(error.startswith("approved:") for error in validate_record("editorial", record)))

    def test_malformed_tags_are_rejected_at_item_path(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["editorial"])
        record["tags"] = ["publish:web", "role:made-up"]
        self.assertTrue(any(error.startswith("tags.1:") for error in validate_record("editorial", record)))

    def test_unknown_properties_are_rejected_but_extension_data_is_allowed(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["experiment"])
        record["surprise"] = True
        self.assertTrue(any("surprise" in error for error in validate_record("experiment", record)))
        record.pop("surprise")
        record["extensions"] = {"lab.example/diagnostic": {"threshold": 0.2}}
        self.assertEqual(validate_record("experiment", record), [])

    def test_artifacts_are_verified_records_under_canonical_generated_roots(self) -> None:
        record = copy.deepcopy(VALID_RECORDS["artifact"])
        self.assertEqual(validate_record("artifact", record), [])
        record["path"] = "work/studio/handoffs/scar-tissue-v1/selected.hiplc"
        self.assertEqual(validate_record("artifact", record), [])
        record["path"] = "studies/study_003_nonlocal-affinity-dance/01_behavior/03_selected/selection_001/review.mp4"
        self.assertEqual(validate_record("artifact", record), [])
        record["path"] = "studies/study_003_nonlocal-affinity-dance/03_specimen/specimen-preview.mp4"
        self.assertEqual(validate_record("artifact", record), [])
        record["path"] = "studies/study_003_nonlocal-affinity-dance/04_delivery/study-003-final.mp4"
        self.assertEqual(validate_record("artifact", record), [])
        record["path"] = "work/studio/handoffs/scar-tissue-v1/../../secret.bin"
        self.assertTrue(any(error.startswith("path:") for error in validate_record("artifact", record)))
        record["path"] = "package/preview.mp4"
        self.assertTrue(any(error.startswith("path:") for error in validate_record("artifact", record)))
        record = copy.deepcopy(VALID_RECORDS["artifact"])
        record["verified"] = False
        self.assertTrue(any(error.startswith("verified:") for error in validate_record("artifact", record)))

    def test_unknown_kind_returns_a_useful_error(self) -> None:
        self.assertEqual(validate_record("publication", {}), ["kind: unknown studio record kind 'publication'"])


if __name__ == "__main__":
    unittest.main()
