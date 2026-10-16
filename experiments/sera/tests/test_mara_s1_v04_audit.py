"""Audit real Mara source without automatically promoting claims to canon."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.mara_s1_v04_audit import (
    PATH, audit_real_mara,
)


class MaraV04AuditTests(unittest.TestCase):
    def test_real_243_word_scene_is_held_with_nine_candidates(self):
        report = audit_real_mara()
        self.assertEqual(report["candidate_count"], 9)
        self.assertEqual(report["candidate_statuses"], {"HOLD": 9})
        self.assertEqual(report["unregistered_physical_candidates"],
                         ["new:bench", "new:pencil"])
        self.assertEqual(report["unregistered_reported_topics"], ["train_41"])
        self.assertFalse(report["commit_authorized"])
        self.assertEqual(report["eventgraph_committed_count"], 0)
        self.assertEqual(report["prior_live_coverage"], "HOLD")
        self.assertEqual(report["prior_live_jev"], "ESCALATE")
        self.assertTrue(all("V04_UNRESOLVED_TIME_AND_EVENT_SCHEMA" in row["blockers"]
                            for row in report["rows"]))

    def _bad(self, mutate, code):
        obj = json.loads(PATH.read_text(encoding="utf-8"))
        mutate(obj)
        with TemporaryDirectory() as folder:
            path = Path(folder) / "altered.json"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, code):
                audit_real_mara(path)

    def test_forged_source_text_fails_fingerprint(self):
        self._bad(lambda obj: obj.__setitem__("prose", obj["prose"] + " !"),
                  "MARA_PROSE_HASH_MISMATCH")

    def test_promoted_candidate_fails(self):
        self._bad(lambda obj: obj["candidates"][0].__setitem__("status", "COMMITTED"),
                  "MARA_UNAUTHORIZED_PROMOTION")

    def test_invented_action_clock_fails(self):
        self._bad(lambda obj: obj["candidates"][0]["time"].__setitem__(
            "exact_minute", 135,
        ), "MARA_UNGROUNDED_ACTION_CLOCK")

    def test_corrupted_quote_span_fails(self):
        self._bad(lambda obj: obj["candidates"][0]["evidence"].__setitem__(
            "quote", "this does not occur in prose",
        ), "MARA_EVIDENCE_SPAN_MISMATCH")


if __name__ == "__main__":
    unittest.main()
