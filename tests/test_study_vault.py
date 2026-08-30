import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from houdini_ai import cli
from houdini_ai.study_vault import (
    PHASE_DIRECTORIES,
    PHASE_SECTIONS,
    SECTIONED_PHASE_DIRECTORIES,
    add_study_variation,
    initialize_study_vault,
    study_directory_name,
    variation_file_stem,
)
from houdini_ai.studio_store import StudioStore


class StudyVaultTests(unittest.TestCase):
    def test_variation_file_stem_separates_variation_identity_from_revision(self) -> None:
        self.assertEqual(variation_file_stem(1, 2, "Fibrous Remodeling"), "bhvr_001_var_002_fibrous-remodeling")
        with self.assertRaises(ValueError):
            variation_file_stem(1, 0, "Invalid")

    def test_add_study_variation_records_stable_identity_and_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = initialize_study_vault(
                Path(directory),
                {"id": "study-002-scar-tissue", "title": "Study 002 — Scar Tissue"},
            )

            variation = add_study_variation(
                vault,
                number=2,
                title="Fibrous Remodeling",
                behavior_selection_id="selection_001",
                derived_from="variation-bhvr001-001-primary-treatment",
            )

            self.assertEqual(variation["id"], "variation-bhvr001-002-fibrous-remodeling")
            self.assertEqual(variation["file_stem"], "bhvr_001_var_002_fibrous-remodeling")
            registry = json.loads((vault / "00_study" / "variations.json").read_text(encoding="utf-8"))
            self.assertEqual(registry["current_variation_id"], variation["id"])
            self.assertEqual(registry["variations"][-1], variation)

    def test_current_variation_updates_existing_study_card_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            vault = initialize_study_vault(
                Path(directory),
                {"id": "study-002-scar-tissue", "title": "Scar Tissue"},
            )
            card_path = vault / "00_study" / "study-card.json"
            card_path.write_text(
                json.dumps(
                    {
                        "variation_id": "variation-bhvr001-001-primary-treatment",
                        "variation_number": 1,
                        "variation_title": "Primary Treatment",
                        "variation_slug": "primary-treatment",
                        "variation_file_stem": "bhvr_001_var_001_primary-treatment",
                    }
                ),
                encoding="utf-8",
            )

            add_study_variation(vault, number=2, title="Fibrous Remodeling")

            card = json.loads(card_path.read_text(encoding="utf-8"))
            self.assertEqual(card["variation_id"], "variation-bhvr001-002-fibrous-remodeling")
            self.assertEqual(card["variation_number"], 2)
            self.assertEqual(card["variation_title"], "Fibrous Remodeling")
            self.assertEqual(card["variation_slug"], "fibrous-remodeling")
            self.assertEqual(card["variation_file_stem"], "bhvr_001_var_002_fibrous-remodeling")

    def test_initialize_creates_the_complete_numbered_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = {
                "schema_version": 1,
                "id": "study-003-nonlocal-affinity-dance",
                "title": "Study 003 — Non-Local Affinity",
                "state": "active",
                "current_phase": "look",
                "visibility": "private",
            }

            vault = initialize_study_vault(root, study)

            self.assertEqual(vault, root / "studies" / "study_003_nonlocal-affinity-dance")
            self.assertEqual(study_directory_name(study["id"]), "study_003_nonlocal-affinity-dance")
            self.assertEqual(
                tuple(path.name for path in vault.iterdir() if path.is_dir()),
                PHASE_DIRECTORIES,
            )
            self.assertEqual(PHASE_DIRECTORIES, (
                "00_study", "01_behavior", "02_look", "03_specimen", "04_delivery",
                "90_shared", "99_archive",
            ))
            self.assertEqual(PHASE_SECTIONS, ("00_brief", "01_work", "02_review", "03_selected"))
            self.assertEqual(SECTIONED_PHASE_DIRECTORIES, ("01_behavior",))
            for phase in SECTIONED_PHASE_DIRECTORIES:
                self.assertEqual(
                    tuple(path.name for path in (vault / phase).iterdir() if path.is_dir()),
                    PHASE_SECTIONS,
                )
            for phase in ("02_look", "03_specimen", "04_delivery"):
                self.assertEqual(tuple((vault / phase).iterdir()), ())
            self.assertEqual(json.loads((vault / "00_study" / "study.json").read_text(encoding="utf-8")), study)
            self.assertIn("Study 003 — Non-Local Affinity", (vault / "00_study" / "README.md").read_text(encoding="utf-8"))
            self.assertEqual(
                json.loads((vault / "00_study" / "status.json").read_text(encoding="utf-8")),
                {"current_phase": "look", "state": "active", "study_id": study["id"]},
            )
            self.assertEqual(json.loads((vault / "00_study" / "lineage.json").read_text(encoding="utf-8")), {"edges": [], "study_id": study["id"]})
            self.assertEqual(json.loads((vault / "00_study" / "artifact-index.json").read_text(encoding="utf-8")), {"artifacts": [], "study_id": study["id"]})
            self.assertEqual(
                json.loads((vault / "00_study" / "variations.json").read_text(encoding="utf-8")),
                {
                    "current_variation_id": "variation-bhvr001-001-primary-treatment",
                    "schema_version": 2,
                    "study_id": study["id"],
                    "variations": [{
                        "behavior_selection_id": None,
                        "derived_from": None,
                        "behavior_number": 1,
                        "file_stem": "bhvr_001_var_001_primary-treatment",
                        "id": "variation-bhvr001-001-primary-treatment",
                        "number": 1,
                        "slug": "primary-treatment",
                        "state": "active",
                        "title": "Primary Treatment",
                    }],
                },
            )
            self.assertIn("# Decisions", (vault / "00_study" / "decisions.md").read_text(encoding="utf-8"))

    def test_initialize_is_idempotent_and_does_not_replace_authored_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = {"id": "study-003-nonlocal-affinity-dance", "title": "Study 003"}
            vault = initialize_study_vault(root, study)
            readme = vault / "00_study" / "README.md"
            readme.write_text("authored\n", encoding="utf-8")

            second = initialize_study_vault(root, study)

            self.assertEqual(second, vault)
            self.assertEqual(readme.read_text(encoding="utf-8"), "authored\n")

    def test_directory_name_rejects_noncanonical_study_ids(self) -> None:
        for invalid in ("003-affinity", "study-3-affinity", "study-003", "study-003-Affinity", "../study-003-affinity"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                study_directory_name(invalid)

    def test_study_init_cli_scaffolds_an_existing_canonical_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = {
                "id": "study-003-nonlocal-affinity-dance",
                "title": "Study 003 — Non-Local Affinity",
            }
            StudioStore(root).create("studies", study["id"], study)
            output = StringIO()

            with patch.object(cli, "ROOT", root), redirect_stdout(output):
                code = cli.main(["studio", "study-init", study["id"]])

            expected = root / "studies" / "study_003_nonlocal-affinity-dance"
            self.assertEqual(code, 0)
            self.assertEqual(output.getvalue(), f"vault: {expected}\n")
            self.assertTrue((expected / "01_behavior" / "03_selected").is_dir())
            for phase in ("02_look", "03_specimen", "04_delivery"):
                self.assertEqual(tuple((expected / phase).iterdir()), ())

    def test_study_variation_add_cli_registers_filename_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            study = {"id": "study-002-scar-tissue", "title": "Study 002 — Scar Tissue"}
            StudioStore(root).create("studies", study["id"], study)
            initialize_study_vault(root, study)
            output = StringIO()

            with patch.object(cli, "ROOT", root), redirect_stdout(output):
                code = cli.main([
                    "studio", "study-variation-add", study["id"], "2", "Fibrous Remodeling",
                    "--behavior-selection-id", "selection_001",
                    "--derived-from", "variation-bhvr001-001-primary-treatment",
                ])

            self.assertEqual(code, 0)
            self.assertIn("variation: variation-bhvr001-002-fibrous-remodeling", output.getvalue())
            self.assertIn("file-stem: bhvr_001_var_002_fibrous-remodeling", output.getvalue())


if __name__ == "__main__":
    unittest.main()
