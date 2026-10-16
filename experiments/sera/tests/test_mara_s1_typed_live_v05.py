"""SERA one-call Mara S1 typed extractor: offline mocks, zero real provider calls."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from experiments.sera.mara_s1_typed_live_v05 import (
    prepare_request, entry_state, one_provider_call,
    EXPECTED_SHA, MODEL, SCENE,
)
from experiments.sera.coverage import prose_hash


class MaraS1TypedLiveTests(unittest.TestCase):
    def test_exact_source_bound_to_registry_and_unknown_new_objects(self):
        p = prepare_request()
        self.assertEqual(prose_hash(p["prose"]), EXPECTED_SHA)
        self.assertEqual(p["entry"]["revision"], 0)
        self.assertEqual(p["entry"]["minute"], 135)
        self.assertIn("vane_watch", p["entry"]["entities"])
        self.assertNotIn("bench", p["entry"]["entities"])
        self.assertNotIn("pencil", p["entry"]["entities"])
        self.assertNotIn("train_41", p["entry"]["entities"])
        self.assertEqual(p["entry"]["entities"]["vane_watch"]
                         ["condition"]["functional"], "STOPPED")
        self.assertFalse(p["request"]["commit_authorized"])
        self.assertEqual(p["request"]["prose_sha256"], EXPECTED_SHA)

    def test_request_never_includes_writer_report_or_jev_gold(self):
        request = prepare_request()["request"]
        user_json = json.loads(request["messages"][1]["content"])
        self.assertEqual(user_json["scene_key"], SCENE)
        self.assertEqual(user_json["prose"], prepare_request()["prose"])
        self.assertNotIn("writer_report", user_json)
        self.assertNotIn("jev_verdict", user_json)
        self.assertIn("claim:vane_watch_stopped_0207",
                      user_json["declared_claim_ids"])
        self.assertEqual(
            request["response_format"]["json_schema"]["strict"], True
        )

    def test_transport_exactly_one_request_and_no_fallback(self):
        prepared = prepare_request()
        requests = []
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({
                    "id": "mock",
                    "model": MODEL,
                    "choices": [{"finish_reason": "stop",
                                 "message": {"content": '{"mentions":[],"events":[]}'}}],
                    "usage": {"cost": 0.001},
                }).encode()

        def once(request, timeout):
            data = json.loads(request.data.decode())
            requests.append(data)
            return FakeResponse()
        with patch("experiments.sera.mara_s1_typed_live_v05.urlopen",
                   side_effect=once):
            result = one_provider_call(key="not-real-key", prepared=prepared)
        self.assertIsNone(result["error"])
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]["model"], MODEL)
        self.assertEqual(requests[0]["response_format"]["type"], "json_schema")
        self.assertFalse(requests[0]["stream"])
        self.assertEqual(requests[0]["max_tokens"], 4096)
        self.assertNotIn("reasoning", requests[0])

    def test_missing_key_fail_closed(self):
        with self.assertRaisesRegex(Exception, "V05_LIVE_KEY_MISSING"):
            one_provider_call(key="", prepared=prepare_request())


if __name__ == "__main__":
    unittest.main()
