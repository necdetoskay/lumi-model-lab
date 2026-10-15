"""SERA M2 structural coverage tests with explicitly labeled synthetic gold.

Test reports stand in for model outputs; not evidence that any live extractor works.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from experiments.sera.coverage import (
    EXTRACTION_SCHEMA, CoverageError, extraction_metrics, prose_hash,
    reconcile, report_signatures, validate_report,
)

ROOT = Path(__file__).resolve().parents[1]
GOLD = json.loads((ROOT / "fixtures/gold_mara_m2_v0.1.json").read_text(
    encoding="utf-8"
))
SCENE_KEY = "hook_empty_platform"
ENTRY_REVISION = 0


def mk_report(case: dict, role: str) -> dict:
    prose = case["prose"]
    source = case[role.lower()]
    mentions = []
    for entity_ref, presence, quote in source["mentions"]:
        pos = prose.index(quote)
        mentions.append({
            "entity_ref": entity_ref, "role": presence,
            "start": pos, "end": pos + len(quote),
        })
    events = []
    for idx, (event_type, args, at, modality, quote) in enumerate(source["events"]):
        pos = prose.index(quote)
        events.append({
            "local_id": f"{role.lower()}-{idx}",
            "type": event_type, "arguments": args,
            "at": at, "modality": modality,
            "start": pos, "end": pos + len(quote),
        })
    return {
        "schema": EXTRACTION_SCHEMA, "source_role": role,
        "scene_key": SCENE_KEY, "entry_revision": ENTRY_REVISION,
        "prose_sha256": prose_hash(prose),
        "mentions": mentions, "events": events,
    }


def expected_signatures(case: dict) -> dict:
    mentions = {(eid, role) for eid, role in case["gold"]["mentions"]}
    events = {
        (etype, tuple(sorted(args.items())), at, modality)
        for etype, args, at, modality in case["gold"]["events"]
    }
    return {"mentions": mentions, "events": events}


def check_case(case: dict) -> tuple[dict, dict, dict]:
    writer = mk_report(case, "WRITER")
    independent = mk_report(case, "INDEPENDENT")
    coverage = reconcile(
        prose=case["prose"], scene_key=SCENE_KEY,
        entry_revision=ENTRY_REVISION, registry=case["registry"],
        writer=writer, independent=independent,
    )
    return coverage, writer, independent


class CoverageGoldTests(unittest.TestCase):
    def test_corpus_is_explicitly_synthetic_and_has_six_cases(self):
        self.assertEqual(GOLD["source_type"], "MANUALLY_ADJUDICATED_SYNTHETIC")
        self.assertEqual(len(GOLD["cases"]), 6)
        self.assertEqual(len({c["id"] for c in GOLD["cases"]}), 6)

    def test_every_gold_case_matches_expected_findings(self):
        for case in GOLD["cases"]:
            with self.subTest(case=case["id"]):
                coverage, _, _ = check_case(case)
                codes = {x["code"] for x in coverage["findings"]}
                self.assertEqual(coverage["status"], case["expected_status"])
                self.assertEqual(codes, set(case["expected_findings"]))
                self.assertFalse(coverage["commit_authorized"])
                self.assertEqual(coverage["semantic_verification"], "NOT_RUN")
                self.assertEqual(coverage["prose_sha256"], prose_hash(case["prose"]))

    def test_writer_misses_clock_but_independent_catches(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "independent_catches_clock")
        coverage, writer, independent = check_case(case)
        gold = expected_signatures(case)
        w = report_signatures(writer)
        i = report_signatures(independent)
        wm = extraction_metrics(
            expected_mentions=gold["mentions"], found_mentions=w["mentions"],
            expected_events=gold["events"], found_events=w["events"],
        )
        im = extraction_metrics(
            expected_mentions=gold["mentions"], found_mentions=i["mentions"],
            expected_events=gold["events"], found_events=i["events"],
        )
        self.assertEqual(wm["entity_role_mentions"]["recall"], 2 / 3)
        self.assertEqual(im["entity_role_mentions"]["recall"], 1.0)
        self.assertEqual(coverage["status"], "HOLD")

    def test_two_wrong_reports_cannot_prove_completeness(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "two_extractors_miss_new_item")
        coverage, writer, independent = check_case(case)
        gold = expected_signatures(case)
        for report in (writer, independent):
            extracted = report_signatures(report)
            metrics = extraction_metrics(
                expected_mentions=gold["mentions"],
                found_mentions=extracted["mentions"],
                expected_events=gold["events"],
                found_events=extracted["events"],
            )
            self.assertEqual(metrics["entity_role_mentions"]["recall"], 0.0)
            self.assertIsNone(metrics["entity_role_mentions"]["precision"])
        self.assertEqual(coverage["status"], "RECONCILED_PENDING_SEMANTIC")
        self.assertFalse(coverage["commit_authorized"])

    def test_manifest_mention_never_upgrades_to_physical_arrival(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "manifest_is_not_physical_arrival")
        coverage, writer, independent = check_case(case)
        self.assertIn(("train_41", "PRESENT"), report_signatures(writer)["mentions"])
        self.assertIn(
            ("train_41", "REPORTED_ONLY"),
            report_signatures(independent)["mentions"],
        )
        self.assertEqual(coverage["status"], "HOLD")

    def test_grounded_event_both_agree_still_requires_jev(self):
        case = GOLD["cases"][0]
        coverage, writer, independent = check_case(case)
        self.assertEqual(coverage["matched_event_count"], 1)
        self.assertEqual(coverage["status"], "RECONCILED_PENDING_SEMANTIC")
        self.assertFalse(coverage["commit_authorized"])

    def test_event_reported_without_time_is_held(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "missing_clock_time_for_knowledge")
        coverage, _, _ = check_case(case)
        self.assertIn(
            "EVENT_TIME_NOT_GROUNDED",
            [f["code"] for f in coverage["findings"]],
        )

    def test_unknown_new_entity_requires_authority(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "new_key_requires_authority")
        coverage, _, _ = check_case(case)
        self.assertIn(
            "NEW_ENTITY_REQUIRES_AUTHORITY",
            [f["code"] for f in coverage["findings"]],
        )

    def test_gold_metric_false_positive_and_false_negative(self):
        case = next(x for x in GOLD["cases"]
                    if x["id"] == "manifest_is_not_physical_arrival")
        gold = expected_signatures(case)
        writer = report_signatures(mk_report(case, "WRITER"))
        result = extraction_metrics(
            expected_mentions=gold["mentions"],
            found_mentions=writer["mentions"],
            expected_events=gold["events"], found_events=writer["events"],
        )["entity_role_mentions"]
        self.assertEqual((result["tp"], result["fp"], result["fn"]), (2, 1, 1))

    def test_stale_fingerprint_rejected_before_reconciliation(self):
        case = GOLD["cases"][0]
        writer = mk_report(case, "WRITER")
        writer["prose_sha256"] = "0" * 64
        with self.assertRaisesRegex(CoverageError, "PROSE_FINGERPRINT_MISMATCH"):
            reconcile(
                prose=case["prose"], scene_key=SCENE_KEY,
                entry_revision=ENTRY_REVISION, registry=case["registry"],
                writer=writer, independent=mk_report(case, "INDEPENDENT"),
            )

    def test_wrong_revision_and_forged_role_rejected(self):
        case = GOLD["cases"][0]
        writer = mk_report(case, "WRITER")
        writer["entry_revision"] = 8
        with self.assertRaisesRegex(CoverageError, "ENTRY_REVISION_MISMATCH"):
            validate_report(writer, role="WRITER", prose=case["prose"],
                            scene_key=SCENE_KEY, entry_revision=0)
        writer["entry_revision"] = 0
        writer["source_role"] = "INDEPENDENT"
        with self.assertRaisesRegex(CoverageError, "SOURCE_ROLE_INVALID"):
            validate_report(writer, role="WRITER", prose=case["prose"],
                            scene_key=SCENE_KEY, entry_revision=0)

    def test_invalid_evidence_span_rejected(self):
        case = GOLD["cases"][0]
        writer = mk_report(case, "WRITER")
        writer["mentions"][0]["end"] = len(case["prose"]) + 50
        with self.assertRaisesRegex(CoverageError, "MENTION_OFFSET_INVALID"):
            validate_report(writer, role="WRITER", prose=case["prose"],
                            scene_key=SCENE_KEY, entry_revision=0)

    def test_unsupported_object_movement_is_held(self):
        case = GOLD["cases"][0]
        writer, independent = mk_report(case, "WRITER"), mk_report(case, "INDEPENDENT")
        for report in (writer, independent):
            report["events"][0]["type"] = "MOVE_OBJECT"
        coverage = reconcile(
            prose=case["prose"], scene_key=SCENE_KEY,
            entry_revision=ENTRY_REVISION, registry=case["registry"],
            writer=writer, independent=independent,
        )
        self.assertIn("UNSUPPORTED_REDUCER_EVENT",
                      [f["code"] for f in coverage["findings"]])
        self.assertEqual(coverage["status"], "HOLD")

    def test_reported_claim_never_committed_as_asserted_fact(self):
        case = GOLD["cases"][0]
        writer, independent = mk_report(case, "WRITER"), mk_report(case, "INDEPENDENT")
        for report in (writer, independent):
            report["events"][0]["modality"] = "REPORTED"
        coverage = reconcile(
            prose=case["prose"], scene_key=SCENE_KEY,
            entry_revision=ENTRY_REVISION, registry=case["registry"],
            writer=writer, independent=independent,
        )
        self.assertEqual(coverage["status"], "HOLD")
        self.assertIn("EVENT_NOT_ASSERTED_AS_FACT",
                      [f["code"] for f in coverage["findings"]])

    def test_duplicate_local_id_and_schema_extra_field_rejected(self):
        case = GOLD["cases"][0]
        report = mk_report(case, "WRITER")
        report["events"].append(deepcopy(report["events"][0]))
        with self.assertRaisesRegex(CoverageError, "DUPLICATE_EVENT_LOCAL_ID"):
            validate_report(report, role="WRITER", prose=case["prose"],
                            scene_key=SCENE_KEY, entry_revision=0)
        report["events"].pop()
        report["unexpected_model_field"] = "surprise"
        with self.assertRaisesRegex(CoverageError, "REPORT_SCHEMA_INVALID"):
            validate_report(report, role="WRITER", prose=case["prose"],
                            scene_key=SCENE_KEY, entry_revision=0)


if __name__ == "__main__":
    unittest.main()
