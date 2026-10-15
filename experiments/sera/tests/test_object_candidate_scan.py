"""SERA additional deterministic open-world object-candidate controls.

These tests do not claim that a noun lexicon can exhaustively understand prose.
"""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from experiments.sera.coverage import (
    CoverageError, EXTRACTION_SCHEMA, prose_hash, reconcile,
)
from experiments.sera.jev_verifier import build_atomic_questions

ROOT = Path(__file__).resolve().parents[1]
LEXICON = json.loads((ROOT / "fixtures/object_candidate_lexicon_v0.1.json")
                     .read_text(encoding="utf-8"))["candidates"]


def report(role, prose, mentions):
    payload = []
    for ref, kind, quote in mentions:
        start = prose.index(quote)
        payload.append({
            "entity_ref": ref, "role": kind,
            "start": start, "end": start + len(quote),
        })
    return {
        "schema": EXTRACTION_SCHEMA, "source_role": role,
        "scene_key": "hook_empty_platform",
        "entry_revision": 0, "prose_sha256": prose_hash(prose),
        "mentions": payload, "events": [],
    }


class ObjectCandidateTests(unittest.TestCase):
    def test_two_models_miss_bench_and_pencil_but_lexicon_finds_both(self):
        prose = "Teodor Vane stood beside the bench. Mara watched the pencil move."
        registry = {"vane": ["Teodor Vane"], "mara": ["Mara"]}
        mentions = [("vane", "PRESENT", "Teodor Vane"),
                    ("mara", "PRESENT", "Mara")]
        writer = report("WRITER", prose, mentions)
        independent = report("INDEPENDENT", prose, mentions)

        baseline = reconcile(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0, registry=registry,
            writer=writer, independent=independent,
        )
        self.assertEqual(baseline["status"], "RECONCILED_PENDING_SEMANTIC")
        improved = reconcile(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0, registry=registry,
            writer=writer, independent=independent,
            candidate_lexicon=LEXICON,
        )
        candidates = {
            finding["candidate_ref"]
            for finding in improved["findings"]
            if finding["code"] == "UNREPORTED_OBJECT_CANDIDATE"
        }
        self.assertEqual(candidates, {"candidate:bench", "candidate:pencil"})
        self.assertEqual(improved["status"], "HOLD")
        self.assertFalse(improved["commit_authorized"])

        bundle = build_atomic_questions(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0, registry=registry,
            writer=writer, independent=independent,
            coverage=improved, candidate_lexicon=LEXICON,
        )
        jev_targets = {
            claim["claim"]["entity_ref"]
            for claim in bundle["candidate_claims"].values()
        }
        self.assertIn("new:bench", jev_targets)
        self.assertIn("new:pencil", jev_targets)

    def test_known_compound_alias_blocks_spurious_new_clock_candidate(self):
        prose = "Mara studied the platform clock."
        registry = {"mara": ["Mara"],
                    "platform_clock": ["platform clock"]}
        mentions = [("mara", "PRESENT", "Mara"),
                    ("platform_clock", "INTERACTED", "platform clock")]
        out = reconcile(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0, registry=registry,
            writer=report("WRITER", prose, mentions),
            independent=report("INDEPENDENT", prose, mentions),
            candidate_lexicon=LEXICON,
        )
        self.assertNotIn("UNREPORTED_OBJECT_CANDIDATE",
                         {f["code"] for f in out["findings"]})
        self.assertEqual(out["status"], "RECONCILED_PENDING_SEMANTIC")

    def test_recognized_new_entity_keeps_explicit_authority_gate(self):
        prose = "Mara found a pencil."
        registry = {"mara": ["Mara"]}
        mentions = [("mara", "PRESENT", "Mara"),
                    ("new:pencil", "INTERACTED", "pencil")]
        out = reconcile(
            prose=prose, scene_key="hook_empty_platform",
            entry_revision=0, registry=registry,
            writer=report("WRITER", prose, mentions),
            independent=report("INDEPENDENT", prose, mentions),
            candidate_lexicon=LEXICON,
        )
        codes = {f["code"] for f in out["findings"]}
        self.assertIn("NEW_ENTITY_REQUIRES_AUTHORITY", codes)
        self.assertNotIn("UNREPORTED_OBJECT_CANDIDATE", codes)

    def test_invalid_candidate_identifier_fails_closed(self):
        prose = "Mara sat on the bench."
        registry = {"mara": ["Mara"]}
        mentions = [("mara", "PRESENT", "Mara")]
        with self.assertRaisesRegex(
            CoverageError, "OBJECT_CANDIDATE_ID_INVALID"
        ):
            reconcile(
                prose=prose, scene_key="hook_empty_platform",
                entry_revision=0, registry=registry,
                writer=report("WRITER", prose, mentions),
                independent=report("INDEPENDENT", prose, mentions),
                candidate_lexicon={"bench": ["bench"]},
            )


if __name__ == "__main__":
    unittest.main()
