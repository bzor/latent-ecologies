import json
import tempfile
import unittest
from pathlib import Path

from houdini_ai.public_seed_bank import build_public_seed_bank
from houdini_ai.seed_bank import create_seed
from houdini_ai.seed_publication import create_seed_site_draft, set_seed_rights, transition_seed_publication
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore


class PublicSeedBankTests(unittest.TestCase):
    def test_public_projection_revalidates_legacy_display_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            seed = self.seed(store, "Refractory field")
            store.update(
                "ideas",
                seed["id"],
                {**seed, "short_summary": "The field stores history — later agents sample it."},
            )
            inclusion = create_seed_site_draft(store, seed["id"], source_ref="discord:message-1")
            set_seed_rights(store, inclusion["id"], "cleared", "Summary rights cleared.")
            transition_seed_publication(
                store, inclusion["id"], "site-live", actor="kc", source_ref="discord:message-2"
            )

            with self.assertRaisesRegex(ValueError, "short_summary contains an em dash"):
                build_public_seed_bank(store, root, root / "work" / "public-site" / "seeds")

    def test_public_manifest_rejects_local_or_credential_bearing_reference_urls(self) -> None:
        for unsafe_url in (
            "file:///C:/private/notes.txt",
            "https://user:secret@example.com/paper",
            "http://127.0.0.1/private",
        ):
            with self.subTest(url=unsafe_url), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                store = StudioStore(root)
                seed = create_seed(
                    store,
                    {
                        "title": "Unsafe Reference",
                        "short_summary": "A complete summary.",
                        "long_summary": "A complete long summary.",
                        "reference_links": [{"title": "Unsafe", "url": unsafe_url, "kind": "other"}],
                        "tags": [],
                    },
                )
                inclusion = create_seed_site_draft(store, seed["id"], source_ref="discord:message-1")
                set_seed_rights(store, inclusion["id"], "cleared", "Summary rights cleared.")
                transition_seed_publication(
                    store, inclusion["id"], "site-live", actor="kc", source_ref="discord:message-2"
                )
                with self.assertRaisesRegex(ValueError, "unsafe public Seed reference URL"):
                    build_public_seed_bank(store, root, root / "work" / "public-site" / "seeds")

    def seed(self, store: StudioStore, title: str) -> dict[str, object]:
        return create_seed(
            store,
            {
                "title": title,
                "short_summary": f"Short public summary for {title}.",
                "long_summary": f"Long public summary for {title}, with enough context to restart the investigation.",
                "raw_text": f"PRIVATE SCRATCH NOTES FOR {title}",
                "reference_links": [
                    {"title": "Reference paper", "url": "https://example.com/paper", "kind": "paper"}
                ],
                "tags": ["feedback", "agents"],
            },
        )

    def test_only_explicitly_live_seed_enters_read_only_public_bank(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            store = StudioStore(root)
            public_seed = self.seed(store, "Reciprocal Weather")
            private_seed = self.seed(store, "Private Organism")
            inclusion = create_seed_site_draft(
                store,
                public_seed["id"],
                source_ref="discord:seed-thread:message-1",
            )
            set_seed_rights(
                store,
                inclusion["id"],
                "cleared",
                "Original Studio-authored summary with external links only.",
            )
            transition_seed_publication(
                store,
                inclusion["id"],
                "site-live",
                actor="kc",
                source_ref="discord:seed-thread:message-2",
            )
            output = root / "work" / "public-site" / "seeds"

            receipt = build_public_seed_bank(store, root, output)

            self.assertEqual(receipt["seed_count"], 1)
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(validate_record("seed-publication-manifest", manifest), [])
            self.assertEqual(manifest["seeds"][0]["id"], public_seed["id"])
            encoded = json.dumps(manifest)
            self.assertNotIn(str(private_seed["id"]), encoded)
            self.assertNotIn("PRIVATE SCRATCH NOTES", encoded)
            self.assertNotIn(str(root), encoded)
            index = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn("Seed Bank", index)
            self.assertIn("Reciprocal Weather", index)
            self.assertNotIn("Private Organism", index)
            self.assertNotIn("<form", index.lower())
            self.assertNotIn("<input", index.lower())
            detail = output / manifest["seeds"][0]["public_path"]
            self.assertTrue(detail.is_file())
            self.assertIn("Long public summary", detail.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
