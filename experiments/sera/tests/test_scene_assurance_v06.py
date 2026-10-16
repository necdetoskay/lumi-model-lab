"""SERA v0.6 acceptance: sentence ledger, T2 recall, plan-diff and epistemic safety.

Live Mara data remains analyst-curated HOLD, NOT human-adjudicated gold. Every
test is offline and may NOT authorize story state or make model calls.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.sentence_ledger_v06 import (
    build_pending_ledger, scanner, sentences, validate_ledger,
)
from experiments.sera.scene_contract_v06 import make_contract, align_intents
from experiments.sera.scene_assurance_v06 import (
    audit_scene, repair_routes,
)
from experiments.sera.observation_archive_v06 import ObservationArchive
from experiments.sera.aspect_epistemic_v06 import (
    proposition, character_stance, review_aspect_change,
)

ROOT = Path(__file__).resolve().parents[1]
LEXICON = json.loads((ROOT/"fixtures/object_candidate_lexicon_v0.1.json")
                     .read_text(encoding="utf-8"))["candidates"]
REAL = json.loads((ROOT/"fixtures/mara_s1_real_eventgraph_candidates_v03.json")
                  .read_text(encoding="utf-8"))
REAL_REGISTRY = {
    "mara": ["Mara"], "vane": ["Vane", "Teodor Vane"],
    "vane_watch": ["pocket watch", "watch"],
    "mara_notebook": ["notebook"], "platform_clock": ["platform clock"],
    "archive_telegram": ["archive telegram", "telegram"],
}
PROSE = "Mara opened her notebook. Vane said the watch stopped at 02:07."
REGISTRY = {
    "mara": ["Mara"], "vane": ["Vane"],
    "mara_notebook": ["notebook"],
    "vane_watch": ["watch"],
}


def scan(p=PROSE, registry=REGISTRY):
    return scanner(prose=p, registry=registry,
                   candidate_lexicon=LEXICON)


def ledger_ok(p=PROSE):
    found = scan(p)
    rows = build_pending_ledger(found)
    rows["status"] = "EXTERNALLY_REVIEWED_NOT_AUTHORIZED"
    rows["rows"][0]["disposition"] = "STATE_EVENT"
    rows["rows"][0]["event_ids"] = ["open_notebook"]
    rows["rows"][0]["reason"] = "Reviewer identified explicit opening"
    rows["rows"][1]["disposition"] = "CLAIM_ONLY"
    rows["rows"][1]["reason"] = "Attributed witness utterance, not objective fact"
    start = p.index("opened her notebook")
    evidence = [{
        "event_id": "open_notebook", "sentence_id": "s001",
        "start": start, "end": start+len("opened her notebook"),
        "quote": "opened her notebook",
    }]
    return found, rows, evidence


class SentenceLedgerV06Tests(unittest.TestCase):
    def test_sentence_partition_does_not_drop_any_nonwhitespace_prose(self):
        source = REAL["prose"]
        spans = sentences(source)
        self.assertGreater(len(spans), 10)
        self.assertEqual([x["id"] for x in spans],
                         [f"s{i:03d}" for i in range(1, len(spans)+1)])
        rebuilt = []
        for s in spans:
            self.assertEqual(source[s["start"]:s["end"]], s["quote"])
            rebuilt.append(s["quote"])
        self.assertIn("Vane watched the pencil move.", rebuilt)
        self.assertTrue(any("02:07" in s for s in rebuilt))
        self.assertTrue(any("02:10" in s for s in rebuilt))

    def test_bench_and_pencil_found_even_if_both_models_miss_them(self):
        s = scan(REAL["prose"], REAL_REGISTRY)
        refs = {hint["ref"] for hint in s["hints"] if hint["tier"] == "T2"}
        self.assertTrue({"candidate:bench", "candidate:pencil"} <= refs)
        for hint in s["hints"]:
            if hint["tier"] == "T2":
                self.assertFalse(hint["canonical_entity_created"])
                self.assertEqual(hint["physical_presence"], "UNDETERMINED")
        self.assertFalse(s["semantic_completeness_proven"])

    def test_compound_platform_clock_does_not_become_two_entities(self):
        s = scan("Mara read the platform clock.",
                 {"mara": ["Mara"], "platform_clock": ["platform clock"]})
        refs = {h["ref"] for h in s["hints"]}
        self.assertIn("platform_clock", refs)
        self.assertNotIn("candidate:clock", refs)

    def test_quoted_time_is_not_action_timestamp(self):
        s = scan("Vane said the clock showed 02:07.")
        hints = [t for row in s["sentence_cues"]
                 for t in row["time_expressions"]]
        self.assertEqual([h["quote"] for h in hints], ["02:07"])
        self.assertEqual(hints[0]["narrative_action_time"], "NOT_PROVEN")

    def test_watch_case_and_notebook_writing_are_cues_not_state_writes(self):
        s = scan(REAL["prose"], REAL_REGISTRY)
        physical = {x["quote"].lower() for v in s["sentence_cues"]
                    for x in v["cues"] if x["family"] == "PHYSICAL_CHANGE"}
        docs = {x["quote"].lower() for v in s["sentence_cues"]
                for x in v["cues"] if x["family"] == "DOCUMENT_CHANGE"}
        self.assertIn("closed", physical)
        self.assertIn("wrote", docs)
        self.assertIn("added", docs)

    def test_pending_ledger_covers_every_sentence_but_remains_hold(self):
        s = scan(REAL["prose"], REAL_REGISTRY)
        ledger = build_pending_ledger(s)
        report = validate_ledger(prose=REAL["prose"], scan=s,
                                 ledger=ledger, evidence_events=[])
        self.assertEqual(report["total_sentences"],
                         report["accounted_sentences"])
        self.assertEqual(report["status"], "HOLD")
        self.assertFalse(report["semantic_completeness_proven"])
        self.assertFalse(report["canonical_commit_authorized"])

    def test_reviewed_ledger_with_exact_spans_structurally_passes_not_semantically(self):
        s, ledger, ev = ledger_ok()
        result = validate_ledger(prose=PROSE, scan=s, ledger=ledger,
                                 evidence_events=ev)
        self.assertEqual(result["status"],
                         "STRUCTURAL_PASS_SEMANTIC_UNVERIFIED")
        self.assertFalse(result["canonical_commit_authorized"])

    def test_single_narrative_event_can_span_two_sentences(self):
        source = "Vane said he waited. He saw no train."
        s = scan(source, {"vane": ["Vane"]})
        ledger = build_pending_ledger(s)
        for row in ledger["rows"]:
            row["disposition"] = "KNOWLEDGE_EVENT"
            row["reason"] = "One witness statement continues across sentences"
            row["event_ids"] = ["vane_testimony"]
        evidence = []
        for row, sentence in zip(ledger["rows"], s["sentences"]):
            evidence.append({
                "event_id": "vane_testimony",
                "sentence_id": row["sentence_id"],
                "start": sentence["start"], "end": sentence["end"],
                "quote": sentence["quote"],
            })
        out = validate_ledger(
            prose=source, scan=s, ledger=ledger, evidence_events=evidence,
        )
        self.assertEqual(out["event_evidence_count"], 2)
        self.assertEqual(out["distinct_narrative_events"], 1)
        self.assertEqual(out["status"],
                         "STRUCTURAL_PASS_SEMANTIC_UNVERIFIED")

    def test_missing_sentence_row_is_rejected(self):
        s, ledger, ev = ledger_ok()
        ledger["rows"].pop()
        with self.assertRaisesRegex(
                CoverageError,"LEDGER_SENTENCE_COVERAGE_GAP_OR_DUPLICATE"):
            validate_ledger(prose=PROSE,scan=s,ledger=ledger,
                            evidence_events=ev)

    def test_duplicate_sentence_row_is_rejected(self):
        s, ledger, ev = ledger_ok()
        ledger["rows"].append(deepcopy(ledger["rows"][0]))
        with self.assertRaisesRegex(
                CoverageError,"LEDGER_SENTENCE_COVERAGE_GAP_OR_DUPLICATE"):
            validate_ledger(prose=PROSE,scan=s,ledger=ledger,
                            evidence_events=ev)

    def test_missed_object_cannot_be_unaccounted(self):
        s, ledger, ev = ledger_ok()
        ledger["rows"][0]["candidate_refs"] = []
        with self.assertRaisesRegex(
                CoverageError,"LEDGER_ENTITY_HINT_UNACCOUNTED"):
            validate_ledger(prose=PROSE,scan=s,ledger=ledger,
                            evidence_events=ev)

    def test_cued_sentence_mislabeled_texture_emits_finding(self):
        s, ledger, ev = ledger_ok()
        ledger["rows"][0]["event_ids"] = []
        ledger["rows"][0]["disposition"] = "TEXTURE"
        result = validate_ledger(prose=PROSE,scan=s,ledger=ledger,
                                 evidence_events=[])
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("LEDGER_NO_CHANGE_WITH_SIGNIFICANT_CUE:s001",
                      result["findings"])

    def test_forged_evidence_does_not_pass_python(self):
        s, ledger, ev = ledger_ok()
        ev[0]["quote"] = "not actually in prose"
        with self.assertRaisesRegex(CoverageError,"LEDGER_EVENT_EVIDENCE_INVALID"):
            validate_ledger(prose=PROSE,scan=s,ledger=ledger,
                            evidence_events=ev)


class SceneContractV06Tests(unittest.TestCase):
    def contract(self):
        return make_contract(
            scene_key="scene_01",entry_revision=0,
            tracked_refs=["mara", "vane", "mara_notebook", "vane_watch"],
            texture_freedom="Writer may add atmospheric detail",
            intents=[{
                "intent_id":"witness_claim","kind":"COMMUNICATE",
                "actor_ids":["vane","mara"],"object_refs":["vane_watch"],
                "required_in_prose":True,"epistemic":"REPORTED_CLAIM",
                "notes":"Vane reports what his watch showed; not objective train arrival",
            }],
        )

    def test_verified_span_is_still_only_structural_review(self):
        contract = self.contract()
        quote = "Vane said the watch stopped at 02:07."
        start = PROSE.index(quote)
        r = align_intents(prose=PROSE,contract=contract,
                          alignments=[{
                              "intent_id":"witness_claim","status":"MATCHED",
                              "evidence":[{"start":start,"end":start+len(quote),
                                           "quote":quote}],
                              "reason":"Independent reviewer proposed evidence",
                          }],unplanned_changes=[])
        self.assertEqual(r["status"],
                         "STRUCTURAL_PASS_SEMANTIC_UNVERIFIED")
        self.assertFalse(r["canonical_commit_authorized"])
        self.assertEqual(r["planned_events_committed"],0)

    def test_unrealized_required_intent_never_committed(self):
        contract = self.contract()
        out=align_intents(prose=PROSE,contract=contract,
                          alignments=[{
                              "intent_id":"witness_claim","status":"MISSING",
                              "evidence":[],"reason":"No evidence",
                          }],unplanned_changes=[])
        self.assertIn("REQUIRED_INTENT_NOT_IN_PROSE:witness_claim",
                      out["findings"])
        self.assertEqual(out["status"],"HOLD")

    def test_plan_outside_change_must_be_reviewed(self):
        out=align_intents(prose=PROSE,contract=self.contract(),
                          alignments=[{
                              "intent_id":"witness_claim","status":"MISSING",
                              "evidence":[],"reason":"unverified",
                          }],unplanned_changes=[{
                              "event_candidate_id":"case_change",
                              "start":PROSE.index("opened her notebook"),
                              "end":PROSE.index("opened her notebook")+
                                    len("opened her notebook"),
                              "quote":"opened her notebook",
                              "reason":"Writer added object change",
                          }])
        self.assertIn("UNPLANNED_STATE_CHANGE:case_change",out["findings"])
        self.assertFalse(out["canonical_commit_authorized"])

    def test_fabricated_plan_evidence_is_rejected(self):
        with self.assertRaisesRegex(CoverageError,"ALIGNMENT_EVIDENCE_NOT_IN_PROSE"):
            align_intents(prose=PROSE,contract=self.contract(),
                          alignments=[{
                              "intent_id":"witness_claim","status":"MATCHED",
                              "evidence":[{"start":0,"end":5,"quote":"false"}],
                              "reason":"invented",
                          }],unplanned_changes=[])


class AspectEpistemicV06Tests(unittest.TestCase):
    def test_watch_case_can_be_proposed_without_unregistered_mutation(self):
        p=review_aspect_change(
            entity_id="vane_watch",entity_kind="OBJECT",
            aspect_id="openable.case_open",before=True,after=False,
            evidence_ref="scene_01:Vane closed the case",
        )
        self.assertFalse(p["canonical_commit_authorized"])
        self.assertFalse(p["existing_world_reducer_updated"])
        self.assertEqual(p["proposed"], False)

    def test_notebook_append_requires_exact_one_new_record(self):
        p=review_aspect_change(
            entity_id="mara_notebook",entity_kind="OBJECT",
            aspect_id="writable.entries",before=[],
            after=["claim:vane_watch_stopped_0207"],
            evidence_ref="scene_01:wrote",
        )
        self.assertFalse(p["canonical_commit_authorized"])
        with self.assertRaisesRegex(CoverageError,"ASPECT_APPEND_CONTRACT_INVALID"):
            review_aspect_change(
                entity_id="mara_notebook",entity_kind="OBJECT",
                aspect_id="writable.entries",before=[],
                after=["p1","p2"],evidence_ref="source:99",
            )

    def test_model_cannot_invent_dynamic_property(self):
        with self.assertRaisesRegex(CoverageError,"ASPECT_NOT_REGISTERED"):
            review_aspect_change(
                entity_id="vane_watch",entity_kind="OBJECT",
                aspect_id="magical_color_without_registry",
                before=None,after="PURPLE",evidence_ref="source:99",
            )

    def test_witness_claim_and_character_stance_not_objective_fact(self):
        claim=proposition(
            proposition_id="claim:train_41_arrival",text="Train 41 arrived at 02:10",
            origin="DOCUMENT",source_entity_id="archive_telegram",
            evidence_ref="scene1:arrival-recorded",
        )
        self.assertFalse(claim["canonical_objective_fact"])
        stance=character_stance(
            character_id="mara",proposition_record=claim,
            stance="DOUBTS",evidence_ref="scene1:record-contrast",
        )
        self.assertFalse(stance["heard_or_believed_is_objective_fact"])
        self.assertFalse(stance["canonical_commit_authorized"])

    def test_narrator_cannot_self_authorize_objective_truth(self):
        with self.assertRaisesRegex(
                CoverageError,"PROPOSITION_TRUSTED_VERIFICATION_NOT_IMPLEMENTED"):
            proposition(proposition_id="fact:station",
                        text="The clock objectively proved the train arrived",
                        origin="NARRATOR",source_entity_id="narrator",
                        evidence_ref="scene:1",truth="VERIFIED")

    def test_document_cannot_self_assert_verified_truth(self):
        with self.assertRaisesRegex(
                CoverageError,"PROPOSITION_CLAIM_NOT_OBJECTIVE_FACT"):
            proposition(proposition_id="claim:train",text="Train arrived",
                        origin="DOCUMENT",source_entity_id="telegram",
                        evidence_ref="scene:1",truth="VERIFIED")


class AssuranceIntegrationV06Tests(unittest.TestCase):
    def test_real_mara_offline_holds_and_preserves_t2_sightings(self):
        r=audit_scene(
            prose=REAL["prose"],scene_key=REAL["scene_id"],
            entry_revision=0,registry=REAL_REGISTRY,
            candidate_lexicon=LEXICON,
        )
        self.assertEqual(r["status"],"HOLD")
        self.assertTrue(
            {"candidate:bench","candidate:pencil"} <=
            {v["ref"] for v in r["t2_sightings"]}
        )
        self.assertEqual(r["model_calls"],0)
        self.assertEqual(r["world_db_writes"],0)
        self.assertFalse(r["canonical_commit_authorized"])
        self.assertIn("LEDGER_ALL_SENTENCES_UNREVIEWED",r["findings"])
        self.assertIn("INDEPENDENT_EXTRACTION_NOT_PERFORMED",r["findings"])

    def test_t2_sightings_persist_without_creating_world_entities(self):
        audit = audit_scene(
            prose=REAL["prose"], scene_key=REAL["scene_id"],
            entry_revision=0, registry=REAL_REGISTRY,
            candidate_lexicon=LEXICON,
        )
        with TemporaryDirectory() as directory:
            path=Path(directory)/"t2-archive.sqlite"
            with ObservationArchive(path) as archive:
                receipt=archive.save(
                    inspection_id="mara-s1-scanner-v06",stream_id="mara",
                    inspection=audit,
                )
                self.assertFalse(receipt["idempotent"])
                self.assertEqual(receipt["canonical_db_writes"], 0)
                self.assertTrue(archive.save(
                    inspection_id="mara-s1-scanner-v06",stream_id="mara",
                    inspection=audit,
                )["idempotent"])
                for entity in ("candidate:bench", "candidate:pencil"):
                    sightings=archive.sightings(
                        stream_id="mara",candidate_ref=entity,
                    )
                    self.assertTrue(sightings)
                    self.assertTrue(all(
                        s["tier"]=="T2" and not s["canonical_entity_created"]
                        for s in sightings
                    ))
                with self.assertRaises(sqlite3.DatabaseError):
                    archive.db.execute("DELETE FROM candidate_sightings")
                with self.assertRaises(sqlite3.DatabaseError):
                    archive.db.execute("UPDATE inspection_archive "
                                       "SET result_status='COMMITTED'")
            with ObservationArchive(path) as opened:
                previous=opened.inspection("mara-s1-scanner-v06")
                self.assertEqual(previous["status"], "HOLD")
                self.assertFalse(previous["canonical_commit_authorized"])
                self.assertEqual(previous["world_db_writes"],0)

    def test_archive_rejects_any_canonical_claim_or_recycled_id(self):
        inspection=audit_scene(
            prose=REAL["prose"],scene_key=REAL["scene_id"],
            entry_revision=0,registry=REAL_REGISTRY,
            candidate_lexicon=LEXICON,
        )
        with ObservationArchive() as archive:
            archive.save(inspection_id="one",stream_id="mara",
                         inspection=inspection)
            changed=deepcopy(inspection)
            changed["findings"]=[]
            with self.assertRaisesRegex(
                    CoverageError,"OBSERVATION_ID_REUSE_CONFLICT"):
                archive.save(inspection_id="one",stream_id="mara",
                             inspection=changed)
            changed=deepcopy(inspection)
            changed["canonical_commit_authorized"]=True
            with self.assertRaisesRegex(
                    CoverageError,"OBSERVATION_CANONICAL_WRITE_NOT_ALLOWED"):
                archive.save(inspection_id="other",stream_id="mara",
                             inspection=changed)

    def test_contract_without_aligner_held_not_assumed_matched(self):
        contract=make_contract(
            scene_key="scene_01",entry_revision=0,
            tracked_refs=["mara"],
            texture_freedom="Natural dialogue",
            intents=[{
                "intent_id":"find_clue","kind":"DISCOVER",
                "actor_ids":["mara"],"object_refs":[],
                "required_in_prose":True,"epistemic":"OBSERVED_ACTION",
                "notes":"Find clue",
            }],
        )
        result=audit_scene(
            prose="Mara stood quietly.",scene_key="scene_01",
            entry_revision=0,registry={"mara":["Mara"]},
            candidate_lexicon=LEXICON,contract=contract,
        )
        self.assertIn("SCENE_CONTRACT_NOT_ALIGNED",result["findings"])

    def test_repair_router_no_auto_commit_no_infinite_loop(self):
        findings=["REQUIRED_INTENT_NOT_IN_PROSE:find_clue",
                  "UNREPORTED_OBJECT_CANDIDATE"]
        first=repair_routes(findings)
        self.assertEqual(first[0]["suggested_action"],
                         "VERIFY_THEN_WRITER_PATCH")
        self.assertTrue(all(not x["automatic_state_commit"] and
                            not x["may_invent_new_story_event"] for x in first))
        final=repair_routes(findings,prior_rounds=2)
        self.assertTrue(all(
            x["suggested_action"]=="HUMAN_REVIEW_REPAIR_BUDGET_EXHAUSTED"
            for x in final
        ))


if __name__ == "__main__":
    unittest.main()
