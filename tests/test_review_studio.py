import hashlib
import http.client
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from houdini_ai.review_studio import DECISIONS, ReviewStore, discover_jobs, make_handler
from http.server import ThreadingHTTPServer


class ReviewStudioTests(unittest.TestCase):
    def test_static_review_shell_disables_browser_caching_during_local_development(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("<script src='/app.js'></script>", encoding="utf-8")
            (website / "app.js").write_text("document.body.dataset.loaded='yes'", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"
                for path in ("/", "/app.js"):
                    with urllib.request.urlopen(base + path) as response:
                        self.assertEqual(response.headers["Cache-Control"], "no-store")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_review_decisions_cover_branch_and_promotion_workflow(self) -> None:
        self.assertEqual(
            DECISIONS,
            {"keep", "iterate", "mutate", "hold", "archive", "reject", "promote"},
        )

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
            acknowledged = store.respond(
                "002-mass-flow", item["id"], {"text": "I will widen the separation field.", "status": "acknowledged"}
            )
            self.assertEqual(acknowledged["status"], "acknowledged")
            self.assertEqual(acknowledged["responses"][0]["author"], "assistant")
            implemented = store.respond(
                "002-mass-flow",
                item["id"],
                {
                    "text": "The replacement preview is ready.",
                    "status": "implemented",
                    "result": {
                        "commit": "abcdef1",
                        "job_id": "002-mass-flow-test",
                        "artifact_paths": ["review/preview.mp4"],
                    },
                },
            )
            self.assertEqual(implemented["result"]["commit"], "abcdef1")
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
            other = root / "work" / "jobs" / "other-job" / "review" / "private.mp4"
            other.parent.mkdir(parents=True)
            other.write_bytes(b"private")
            with self.assertRaisesRegex(ValueError, "selected job"):
                store.add(
                    {
                        "study_id": "002-mass-flow",
                        "job_id": "002-mass-flow-test",
                        "artifact_path": "../other-job/review/private.mp4",
                        "text": "invalid sibling",
                    }
                )
            with self.assertRaisesRegex(ValueError, "job does not exist"):
                store.respond(
                    "002-mass-flow", item["id"],
                    {"text": "No traversal", "status": "resolved", "result": {"job_id": "../../", "artifact_paths": ["secret.mp4"]}},
                )
            with self.assertRaisesRegex(ValueError, "decision is required"):
                store.add(
                    {
                        "study_id": "002-mass-flow",
                        "job_id": "002-mass-flow-test",
                        "artifact_path": "review/preview.mp4",
                        "kind": "decision",
                        "text": "missing decision",
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
                catalog = json.load(urllib.request.urlopen(f"{base}/api/studio/catalog"))
                catalog_media = next(
                    item for item in catalog["items"]
                    if item["path"] == "work/jobs/002-mass-flow-test/review/preview.mp4"
                )
                catalog_request = urllib.request.Request(
                    base + catalog_media["url"], headers={"Range": "bytes=2-5"}
                )
                with urllib.request.urlopen(catalog_request) as response:
                    self.assertEqual(response.status, 206)
                    self.assertEqual(response.read(), media.read_bytes()[2:6])
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/catalog-media/catalog-00000000000000000000")
                self.assertEqual(error.exception.code, 404)
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
                item_id = reviews["items"][0]["id"]
                payload = json.dumps({"text": "Acknowledged for the next branch.", "status": "acknowledged"}).encode()
                request = urllib.request.Request(
                    f"{base}/api/reviews/002-mass-flow/{item_id}/responses",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.status, 201)
                    acknowledged = json.load(response)
                self.assertEqual(acknowledged["responses"][0]["author"], "assistant")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/002-mass-flow-test/../../effective-config.json")
                self.assertEqual(error.exception.code, 404)
                sibling = root / "work" / "jobs" / "private-job" / "secret.txt"
                sibling.parent.mkdir(parents=True)
                sibling.write_text("private", encoding="utf-8")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/002-mass-flow-test/../private-job/secret.txt")
                self.assertEqual(error.exception.code, 404)
                prefix_sibling = root / "work" / "jobs" / "002-mass-flow-test-secret" / "private.mp4"
                prefix_sibling.parent.mkdir(parents=True)
                prefix_sibling.write_bytes(b"private")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/002-mass-flow-test/../002-mass-flow-test-secret/private.mp4")
                self.assertEqual(error.exception.code, 404)
                active = root / "work" / "jobs" / "002-mass-flow-test" / "review" / "active.html"
                active.write_text("<script>alert(1)</script>", encoding="utf-8")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/002-mass-flow-test/review/active.html")
                self.assertEqual(error.exception.code, 404)
                secret = root / "secret.mp4"
                secret.write_bytes(b"SECRET")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(f"{base}/media/..%2F../secret.mp4")
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
    def test_studio_http_api_captures_lists_updates_and_summarizes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("studio", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def request(path: str, method: str = "GET", value: dict | None = None) -> tuple[int, dict]:
                data = json.dumps(value).encode() if value is not None else None
                req = urllib.request.Request(
                    base + path,
                    data=data,
                    headers={"Content-Type": "application/json"} if data else {},
                    method=method,
                )
                with urllib.request.urlopen(req) as response:
                    return response.status, json.load(response)

            try:
                status, idea = request(
                    "/api/studio/ideas", "POST", {"title": "Scar paths", "raw_text": "<b>inert</b>", "track": "behavior"}
                )
                self.assertEqual(status, 201)
                self.assertEqual(idea["visibility"], "private")
                _, inbox = request("/api/studio/ideas")
                self.assertEqual(inbox["items"][0]["raw_text"], "<b>inert</b>")
                _, summary = request("/api/studio/summary")
                self.assertEqual(summary["counts"]["ideas"], 1)
                self.assertEqual(summary["visibility"], "private")
                _, proposal = request(
                    "/api/studio/proposals",
                    "POST",
                    {
                        "schema_version": 1,
                        "id": "proposal-scar-probe",
                        "idea_id": idea["id"],
                        "track": "behavior",
                        "state": "proposed",
                        "question": "Does saturation create turnover?",
                        "mechanism": "Deposit, saturate, repel, decay.",
                        "outputs": ["preview-loop"],
                        "stop_conditions": ["No turnover after 300 steps"],
                        "runner": "behavior.scar_probe",
                        "cost_tier": "probe",
                        "visibility": "private",
                    },
                )
                _, approved = request(
                    f'/api/studio/proposals/{proposal["id"]}', "PATCH", {"state": "approved"}
                )
                self.assertEqual(approved["state"], "approved")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    request("/api/studio/not-a-collection")
                self.assertEqual(error.exception.code, 404)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_mutations_require_json_loopback_origin_and_launch_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("studio", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, mutation_token="launch-secret"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"

            def post(headers: dict[str, str]) -> int:
                request = urllib.request.Request(base + "/api/studio/ideas", data=b'{}', headers=headers, method="POST")
                try:
                    urllib.request.urlopen(request)
                except urllib.error.HTTPError as error:
                    return error.code
                return 200

            try:
                session = json.load(urllib.request.urlopen(base + "/api/studio/session"))
                self.assertEqual(session["mutation_token"], "launch-secret")
                with urllib.request.urlopen(base + "/api/studio/session") as response:
                    self.assertEqual(response.headers["Access-Control-Allow-Origin"], base)
                    self.assertEqual(response.headers["Content-Security-Policy"], "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(
                        urllib.request.Request(
                            base + "/api/studio/session",
                            headers={"Origin": "https://evil.example"},
                        )
                    )
                self.assertEqual(error.exception.code, 403)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(
                        urllib.request.Request(base + "/api/studio/session", headers={"Host": "evil.example"})
                    )
                self.assertEqual(error.exception.code, 403)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base + "/api/jobs", headers={"Host": "evil.example"}))
                self.assertEqual(error.exception.code, 403)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base + "/api/studio/session", headers={"Host": f"evil@localhost:{server.server_port}"}))
                self.assertEqual(error.exception.code, 403)
                connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
                connection.putrequest("GET", "/api/studio/session", skip_host=True)
                connection.putheader("Host", "[::1")
                connection.endheaders()
                malformed = connection.getresponse()
                self.assertEqual(malformed.status, 403)
                malformed.read()
                connection.close()
                self.assertEqual(post({"X-Studio-Mutation-Token": "launch-secret"}), 415)
                self.assertEqual(post({"Content-Type": "application/json"}), 403)
                self.assertEqual(post({"Content-Type": "application/json", "X-Studio-Mutation-Token": "launch-secret", "Origin": "https://evil.example"}), 403)
                self.assertEqual(post({"Content-Type": "application/json", "X-Studio-Mutation-Token": "launch-secret", "Origin": "http://127.0.0.1:9"}), 403)
                self.assertEqual(post({"Content-Type": "application/json", "X-Studio-Mutation-Token": "launch-secret", "Host": "evil.example"}), 403)
                self.assertEqual(post({"Content-Type": "application/json; charset=utf-8", "X-Studio-Mutation-Token": "launch-secret", "Origin": base}), 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_creative_session_and_review_inbox_http_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("studio", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, mutation_token="token"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            headers = {"Content-Type": "application/json", "X-Studio-Mutation-Token": "token"}

            def mutate(path: str, value: dict, method: str = "POST") -> tuple[int, dict]:
                request = urllib.request.Request(
                    base + path, data=json.dumps(value).encode(), headers=headers, method=method
                )
                with urllib.request.urlopen(request) as response:
                    return response.status, json.load(response)

            payload = {
                "title": "Pilot Study",
                "project_slug": "pilot-study",
                "current_phase": "seed",
                "intent": "Explore $(touch escaped) as inert prose.",
                "approved_selection_ids": [],
                "unresolved_questions": ["Which direction?"],
                "blockers": [],
                "recommended_next_action": "Draft behavior directions.",
                "activate": True,
            }
            try:
                bootstrap = json.load(urllib.request.urlopen(base + "/api/studio/session"))
                self.assertIsNone(bootstrap["active_session"])
                self.assertIn("directions", bootstrap["phases"])

                status, created = mutate("/api/studio/sessions", payload)
                self.assertEqual(status, 201)
                self.assertTrue(created["is_active"])
                session_id = created["id"]

                status, updated = mutate(
                    f"/api/studio/sessions/{session_id}",
                    {"current_phase": "directions", "recommended_next_action": "Compare three mechanisms."},
                    method="PATCH",
                )
                self.assertEqual(status, 200)
                self.assertEqual(updated["current_phase"], "directions")
                self.assertEqual(updated["recommended_next_action"], "Compare three mechanisms.")

                sessions = json.load(urllib.request.urlopen(base + "/api/studio/sessions"))
                self.assertEqual(sessions["items"][0]["id"], session_id)
                self.assertTrue(sessions["items"][0]["is_active"])
                status, note = mutate(
                    "/api/studio/notes",
                    {
                        "text": "Should this question remain visible?",
                        "category": "question",
                        "stage": "behavior",
                        "track": "behavior",
                        "reference_id": session_id,
                    },
                )
                self.assertEqual(status, 201)
                self.assertEqual(note["reference_id"], session_id)
                inbox = json.load(urllib.request.urlopen(base + "/api/studio/review-inbox"))
                self.assertEqual(inbox["session_id"], session_id)
                self.assertEqual(inbox["counts"]["session-question"], 1)
                self.assertEqual(inbox["counts"]["process-question"], 1)
                self.assertFalse((root / "escaped").exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_dedicated_proposal_and_verified_promotion_http_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("studio", encoding="utf-8")
            artifact_path = root / "work" / "jobs" / "run" / "review" / "preview.mp4"
            artifact_path.parent.mkdir(parents=True)
            artifact_path.write_bytes(b"verified")
            from houdini_ai.studio_api import StudioAPI
            studio = StudioAPI(root)
            studio.store.create("ideas", "idea-a", {"id": "idea-a", "track": "behavior", "state": "proposed"})
            studio.store.create("proposals", "proposal-a", {"id": "proposal-a", "idea_id": "idea-a", "track": "behavior", "state": "approved"})
            studio.store.create("experiments", "experiment-a", {"id": "experiment-a", "proposal_id": "proposal-a", "track": "behavior", "state": "completed"})
            studio.store.create("artifacts", "artifact-a", {"schema_version": 1, "id": "artifact-a", "experiment_id": "experiment-a", "track": "behavior", "state": "verified", "path": "work/jobs/run/review/preview.mp4", "sha256": "sha256:" + hashlib.sha256(b"verified").hexdigest(), "verified": True, "visibility": "private"})
            proposal = studio.create_record("proposals", {"schema_version": 1, "id": "proposal-safe", "idea_id": "idea-a", "track": "behavior", "state": "proposed", "question": "Q", "mechanism": "M", "outputs": ["preview"], "stop_conditions": ["stop"], "runner": "behavior.probe", "cost_tier": "probe", "visibility": "private"})
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, mutation_token="token"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            headers = {"Content-Type": "application/json", "X-Studio-Mutation-Token": "token"}

            def mutate(path: str, value: dict) -> tuple[int, dict]:
                request = urllib.request.Request(base + path, data=json.dumps(value).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(request) as response:
                    return response.status, json.load(response)

            try:
                artifacts = json.load(urllib.request.urlopen(base + "/api/studio/artifacts/verified"))
                self.assertEqual([item["id"] for item in artifacts["items"]], ["artifact-a"])
                status, held = mutate(f'/api/studio/proposals/{proposal["id"]}/hold', {})
                self.assertEqual((status, held["state"]), (200, "held"))
                status, component = mutate("/api/studio/artifacts/artifact-a/promote", {"component_kind": "behavior", "rationale": "KC approved."})
                self.assertEqual(status, 201)
                self.assertEqual(component["source_artifact_ref"], "work/jobs/run/review/preview.mp4")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    def test_direction_board_http_operations_preserve_lineage_and_only_propose_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            website = root / "website"
            website.mkdir()
            (website / "index.html").write_text("studio", encoding="utf-8")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(root, mutation_token="token"))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            headers = {"Content-Type": "application/json", "X-Studio-Mutation-Token": "token"}

            def mutate(path: str, value: dict) -> tuple[int, dict]:
                request = urllib.request.Request(base + path, data=json.dumps(value).encode(), headers=headers, method="POST")
                with urllib.request.urlopen(request) as response:
                    return response.status, json.load(response)

            def value(title: str, mechanism: str) -> dict:
                return {
                    "title": title,
                    "premise": f"{title} tests a distinct local causal rule.",
                    "mechanism": mechanism,
                    "expected_emergent_behavior": "Structured fronts should form and reorganize.",
                    "cheapest_informative_probe": "Run 120 low-resolution steps.",
                    "risks": ["The rule may collapse."],
                    "conceptual_distinction": "This changes causal interaction rather than tuning parameter values.",
                    "sibling_relations": [],
                }

            try:
                _, idea = mutate("/api/studio/ideas", {"title": "Pilot", "raw_text": "A fresh field study.", "track": "behavior"})
                first_value = value("Reciprocal Field", "Agents deposit memory and later invert their response to it.")
                first_value["idea_id"] = idea["id"]
                status, first = mutate("/api/studio/directions", first_value)
                self.assertEqual(status, 201)
                _, first = mutate(f"/api/studio/directions/{first['id']}/select", {})
                self.assertEqual(first["state"], "selected")
                _, proposal = mutate(f"/api/studio/directions/{first['id']}/propose", {
                    "outputs": ["motion-check.mp4"], "stop_conditions": ["120 steps"],
                    "runner": "behavior.probe", "cost_tier": "probe",
                })
                self.assertEqual(proposal["state"], "proposed")
                status, mutant = mutate(f"/api/studio/directions/{first['id']}/mutate", value(
                    "Delayed Field", "Agents read an earlier field state, creating delayed feedback."
                ))
                self.assertEqual(status, 201)
                second_value = value("Contact Exchange", "Agents exchange discrete state only at direct contact.")
                second_value["idea_id"] = idea["id"]
                _, second = mutate("/api/studio/directions", second_value)
                status, merged = mutate("/api/studio/directions/merge", {
                    "source_ids": [first["id"], second["id"]],
                    "direction": value("Field Exchange", "Contact changes state while a persistent field stores the exchange."),
                })
                self.assertEqual(status, 201)
                self.assertEqual(merged["relation_kind"], "conceptual-merge")
                self.assertEqual(mutant["relation_kind"], "mutation")
                listed = json.load(urllib.request.urlopen(base + "/api/studio/directions"))
                self.assertEqual(len(listed["items"]), 4)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
