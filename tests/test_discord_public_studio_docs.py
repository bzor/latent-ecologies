import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DiscordPublicStudioDocumentationTests(unittest.TestCase):
    def test_architecture_defines_discord_only_control_and_allowlisted_public_projection(self) -> None:
        architecture = (ROOT / "docs" / "DISCORD_PUBLIC_STUDIO_ARCHITECTURE.md").read_text(encoding="utf-8")

        for required in (
            "Discord is the sole human interaction surface",
            "private local Studio",
            "read-only public Study",
            "explicit allowlist",
            "site-draft",
            "site-live",
            "archive-keep",
            "retired",
            "no login",
            "no public mutation",
            "public exposure is effectively irreversible",
        ):
            with self.subTest(required=required):
                self.assertIn(required, architecture)

    def test_protocol_forbids_automatic_workspace_publication(self) -> None:
        protocol = (ROOT / "docs" / "STUDIO_PROTOCOL.md").read_text(encoding="utf-8")

        self.assertIn("never scans the working tree for publication candidates", protocol)
        self.assertIn("Site inclusion is independent of production promotion", protocol)


    def test_technical_voice_forbids_ai_style_output(self) -> None:
        voice = (ROOT / "docs" / "TECHNICAL_VOICE.md").read_text(encoding="utf-8")

        for required in (
            "Display text must not contain em dashes",
            "negative parallelism",
            "stock AI-style phrasing",
            "mechanical validator",
        ):
            with self.subTest(required=required):
                self.assertIn(required, voice)


if __name__ == "__main__":
    unittest.main()
