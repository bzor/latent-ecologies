import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from houdini_ai.review_studio import ReviewStore, discover_jobs, make_handler
from http.server import ThreadingHTTPServer


class ReviewStudioTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[Path, Path]:
        job = root / "work" / "jobs" / "002-mass-flow-test"
        review = job / "review"
        review.mkdir(parents=True)
        (job / "effective-config.json").write_text(
            json.dumps(
                {
                    "source_state": "abc123",
                    "study": {
                        "id": "002-mass-flow",
                        "title": "Mass Flow",
                        "seed": 7,
                        "presentation": {"quality": "probe"},
                        "simulation": {"rule_genome": {"system": {"agent_count": 4000}}},
                    },
                }
            ),
            encoding="utf-8",
        )
        media = review / "preview.mp4"
        media.write_bytes(b"0123456789")
        (review / "still.png").write_bytes(b"png")
        frames = review / "motion-frames"
        frames.mkdir()
        (frames / "motion.0001.jpg").write_bytes(b"ignored")
        return job, media

    def test_discovery_indexes_review_media_without_frame_spam(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            jobs = discover_jobs(root)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["parameters"]["agent_count"], 4000)
            self.assertEqual({item["path"] for item in jobs[0]["artifacts"]}, {"review/preview.mp4", "review/still.png"})

    def test_review_store_validates_artifacts_and_updates_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            store = ReviewStore(root)
            item = store.add(
                {
                    "study_id": "002-mass-flow",
                    "job_id": "002-mass-flow-test",
                    "artifact_path": "review/preview.mp4",
                    "kind": "decision",
                    "decision": "iterate",
                    "timecode": 4.25,
                    "text": "Open the middle crossing.",
                }
            )
            self.assertEqual(item["status"], "open")
            updated = store.update_status("002-mass-flow", item["id"], "resolved")
            self.assertEqual(updated["status"], "resolved")
            with self.assertRaisesRegex(ValueError, "artifact does not exist"):
                store.add(
                    {
                        "study_id": "002-mass-flow",
                        "job_id": "002-mass-flow-test",
                        "artifact_path": "../../outside.txt",
                        "text": "invalid",
                    }
                )

    def test_http_api_range_and_feedback_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _, media = self.fixture(root)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("review", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                jobs = json.load(urllib.request.urlopen(f"{base}/api/jobs"))
                self.assertEqual(jobs["jobs"][0]["id"], "002-mass-flow-test")
                request = urllib.request.Request(
                    f"{base}/media/002-mass-flow-test/review/preview.mp4", headers={"Range": "bytes=2-5"}
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), media.read_bytes()[2:6])
                payload = json.dumps(
                    {
                        "study_id": "002-mass-flow",
                        "job_id": "002-mass-flow-test",
                        "artifact_path": "review/preview.mp4",
                        "kind": "comment",
                        "text": "Good movement.",
                    }
                ).encode()
                request = urllib.request.Request(
                    f"{base}/api/reviews", data=payload, headers={"Content-Type": "application/json"}, method="POST"
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 201)
                reviews = json.load(urllib.request.urlopen(f"{base}/api/reviews/002-mass-flow"))
                self.assertEqual(reviews["items"][0]["text"], "Good movement.")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/002-mass-flow-test/../../effective-config.json")
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
