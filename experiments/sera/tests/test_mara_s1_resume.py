"""SERA resumed Mara scene pilot: offline contract checks, zero provider calls."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.sera.mara_s1_resume import (
    SOURCE_RESULT_SHA256, SOURCE_PROSE_SHA256, SOURCE_ARTIFACT_RUN,
    EXTRACTOR_MODEL, EXTRACT_SCHEMA, SPEND_STOP_USD,
    load_source, call_structured_gemini,
)


class MaraResumeTests(unittest.TestCase):
    def test_immutable_previous_run_identity(self):
        self.assertEqual(SOURCE_ARTIFACT_RUN, 38808450095)
        self.assertEqual(len(SOURCE_RESULT_SHA256), 64)
        self.assertEqual(len(SOURCE_PROSE_SHA256), 64)
        self.assertEqual(EXTRACTOR_MODEL, "google/gemini-3.7-flash")
        self.assertLessEqual(SPEND_STOP_USD, 0.20)

    def test_extraction_schema_requires_both_collections(self):
        self.assertEqual(set(EXTRACT_SCHEMA["required"]),
                         {"mentions", "events"})
        self.assertFalse(EXTRACT_SCHEMA["additionalProperties"])
        for dimension in ("mentions", "events"):
            item = EXTRACT_SCHEMA["properties"][dimension]["items"]
            self.assertFalse(item["additionalProperties"])

    def test_unverified_prior_artifact_is_rejected_offline(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "result.json"
            path.write_text(json.dumps({
                "source_spine_sha": "untrusted", "prose": "hello"
            }))
            with self.assertRaisesRegex(
                ValueError, "SOURCE_EVIDENCE_SHA_MISMATCH"
            ):
                load_source(path)

    def test_gemini_transport_is_one_post_and_requests_json_schema(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
            def __enter__(self):
                return self
            def __exit__(self, *unused):
                return False
            def read(self):
                return json.dumps(self.payload).encode("utf-8")

        captured = []
        fake = {
            "id": "fake-resume",
            "model": EXTRACTOR_MODEL,
            "usage": {"prompt_tokens": 200, "completion_tokens": 100,
                      "cost": 0.001},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": '{"mentions":[],"events":[]}'}
            }]
        }
        def urlopen(request, timeout):
            payload = json.loads(request.data.decode("utf-8"))
            captured.append(payload)
            return FakeResponse(fake)

        with patch("experiments.sera.mara_s1_resume.urlopen",
                   side_effect=urlopen):
            out = call_structured_gemini(
                key="fake-key-for-tests",
                messages=[{"role": "user", "content": "scene"}],
            )
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["response_format"]["type"], "json_schema")
        self.assertEqual(captured[0]["model"], EXTRACTOR_MODEL)
        self.assertEqual(out["finish_reason"], "stop")
        self.assertEqual(out["usage"]["cost"], 0.001)


if __name__ == "__main__":
    unittest.main()
