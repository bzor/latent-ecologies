import tempfile
import unittest
from pathlib import Path

from houdini_ai.lineage import LineageError, assert_acyclic, stable_content_hash, validate_edge
from houdini_ai.studio_store import StudioStore


class LineageTests(unittest.TestCase):
    def test_allowed_edge_requires_existing_typed_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-a", {"id": "idea-a"})
            store.create("proposals", "proposal-a", {"id": "proposal-a"})
            validate_edge(store, "idea-a", "proposal-a")
            with self.assertRaises(LineageError):
                validate_edge(store, "proposal-a", "idea-a")
            with self.assertRaises(LineageError):
                validate_edge(store, "idea-missing", "proposal-a")

    def test_content_hash_is_stable_and_ignores_mapping_order(self) -> None:
        self.assertEqual(stable_content_hash({"b": 2, "a": 1}), stable_content_hash({"a": 1, "b": 2}))
        self.assertTrue(stable_content_hash({"a": 1}).startswith("sha256:"))

    def test_cycles_are_rejected(self) -> None:
        with self.assertRaises(LineageError):
            assert_acyclic([("idea-a", "proposal-a"), ("proposal-a", "idea-a")])


if __name__ == "__main__":
    unittest.main()
