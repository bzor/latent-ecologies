import json
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from houdini_ai.studio_store import StudioStore


class StudioStoreTests(unittest.TestCase):
    def test_create_read_and_list_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            idea = {"id": "idea-001", "kind": "idea", "text": "Folded smoke"}

            created = store.create("ideas", "idea-001", idea)

            self.assertEqual(created, idea)
            self.assertEqual(store.read("ideas", "idea-001"), idea)
            records, errors = store.list("ideas")
            self.assertEqual(records, [idea])
            self.assertEqual(errors, [])
            self.assertTrue((root / "studio" / "ideas" / "idea-001.json").is_file())

    def test_duplicate_create_fails_and_explicit_update_replaces_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-001", {"id": "idea-001", "revision": 1})

            with self.assertRaises(FileExistsError):
                store.create("ideas", "idea-001", {"id": "idea-001", "revision": 2})

            updated = store.update("ideas", "idea-001", {"id": "idea-001", "revision": 2})
            self.assertEqual(updated["revision"], 2)
            self.assertEqual(store.read("ideas", "idea-001")["revision"], 2)

    def test_rejects_malformed_and_traversal_identifiers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            invalid = ("", ".", "..", "../escape", "a/b", "A", "under_score", "-leading", "x" * 81)
            for value in invalid:
                with self.subTest(value=value):
                    with self.assertRaises(ValueError):
                        store.create("ideas", value, {"id": value})
            with self.assertRaises(ValueError):
                store.create("../outside", "safe-id", {"id": "safe-id"})

    def test_symlinked_collection_cannot_escape_supplied_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside_directory:
            root = Path(directory)
            studio = root / "studio"
            studio.mkdir(parents=True)
            try:
                (studio / "ideas").symlink_to(Path(outside_directory), target_is_directory=True)
            except OSError as error:
                self.skipTest(f"directory symlinks unavailable: {error}")

            with self.assertRaises(ValueError):
                StudioStore(root).create("ideas", "idea-001", {"id": "idea-001"})
            self.assertFalse((Path(outside_directory) / "idea-001.json").exists())

    def test_root_must_be_explicit_and_records_stay_beneath_it(self) -> None:
        with self.assertRaises(TypeError):
            StudioStore(None)  # type: ignore[arg-type]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            store.create("ideas", "idea-001", {"id": "idea-001"})
            self.assertTrue((root / "studio" / "ideas" / "idea-001.json").is_file())

    def test_malformed_and_interrupted_siblings_are_reported_without_hiding_valid_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            valid = {"id": "idea-valid", "text": "safe"}
            store.create("ideas", "idea-valid", valid)
            records_dir = root / "studio" / "ideas"
            (records_dir / "idea-broken.json").write_text("{not json", encoding="utf-8")
            (records_dir / "BAD.json").write_text('{"id": "bad-name"}', encoding="utf-8")
            (records_dir / "idea-interrupted.tmp").write_text('{"id": "partial"', encoding="utf-8")

            records, errors = store.list("ideas")

            self.assertEqual(records, [valid])
            self.assertEqual(
                {Path(error["path"]).name for error in errors},
                {"BAD.json", "idea-broken.json", "idea-interrupted.tmp"},
            )
            self.assertEqual(store.read("ideas", "idea-valid"), valid)

    def test_writes_use_atomic_replacement_and_leave_no_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            path = root / "studio" / "ideas" / "idea-001.json"

            with patch("houdini_ai.studio_store.os.replace", wraps=os.replace) as replace:
                store.create("ideas", "idea-001", {"id": "idea-001"})

            replace.assert_called_once()
            temporary, destination = map(Path, replace.call_args.args)
            self.assertEqual(destination, path)
            self.assertEqual(temporary.parent, path.parent)
            self.assertFalse(temporary.exists())

    def test_concurrent_writes_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = StudioStore(Path(directory))
            store.create("ideas", "idea-001", {"id": "idea-001", "revision": 0})
            active = 0
            maximum_active = 0
            activity_lock = threading.Lock()
            original_write = store._write

            def observed_write(path: Path, value: dict[str, object]) -> None:
                nonlocal active, maximum_active
                with activity_lock:
                    active += 1
                    maximum_active = max(maximum_active, active)
                time.sleep(0.02)
                original_write(path, value)
                with activity_lock:
                    active -= 1

            errors: list[Exception] = []

            def update(revision: int) -> None:
                try:
                    store.update("ideas", "idea-001", {"id": "idea-001", "revision": revision})
                except Exception as error:  # pragma: no cover - asserted below
                    errors.append(error)

            with patch.object(store, "_write", side_effect=observed_write):
                threads = [threading.Thread(target=update, args=(revision,)) for revision in range(8)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join()

            self.assertEqual(errors, [])
            self.assertEqual(maximum_active, 1)
            self.assertIn(store.read("ideas", "idea-001")["revision"], range(8))


if __name__ == "__main__":
    unittest.main()
