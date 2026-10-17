"""SERA offline source chronology proof; no network, gold or world writes."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json
import unittest

from experiments.sera.coverage import CoverageError,prose_hash
from experiments.sera.mara_s1_typed_live_v05 import entry_state,REGISTRY
from experiments.sera.real_blind_benchmark_v040 import prepare,EXPECTED_SHA,LEXICON
from experiments.sera.sentence_sweep_v010 import REPORT_SCHEMA
from experiments.sera.source_chronology_v052 import build_source_chronology
from experiments.sera.world_state_v02 import canonical
from experiments.sera.artifact_scene_checker_v021 import digest

SCENE="v052-frozen-mara-source-timeline"


class SourceChronologyTests(unittest.TestCase):
    def setUp(self):
        self.prose=prepare()["prose"]
        self.world=entry_state()
        self.world_sha=digest(self.world)
        self.registry={key:value for key,value in REGISTRY.items()
                       if key in self.world["entities"]}
        self.lexicon=json.loads(LEXICON.read_text(
            encoding="utf-8"))["candidates"]

    def build(self,**kwargs):
        params=dict(prose=self.prose,scene_key=SCENE,
                    world_sha256=self.world_sha,
                    registry=self.registry,candidate_lexicon=self.lexicon)
        params.update(kwargs)
        return build_source_chronology(**params)

    def simple_report(self):
        doc=self.build()
        source=doc["source_sentences"]
        rows=[{"sentence_id":s["sentence_id"],
               "disposition":"NO_TRACKED_CHANGE",
               "event_ids":[],"candidate_refs":[],"reason":"mock incomplete"}
              for s in source]
        # An intentionally adversarial event is only a model candidate; its
        # presence is NOT a physical event or source time certification.
        first=source[0]
        pos=first["exact_source_quote"].find("Mara")
        self.assertGreaterEqual(pos,0)
        event={
            "event_id":"model-claim-001",
            "sentence_id":first["sentence_id"],
            "start":first["source_start"]+pos,
            "end":first["source_start"]+pos+len("Mara"),
            "quote":"Mara",
            "kind":"MOVE","effect":"WORLD",
            "epistemic":"NARRATOR_ASSERTION",
        }
        rows[0]["event_ids"]=[event["event_id"]]
        rows[0]["disposition"]="STATE_EVENT"
        return {"schema":REPORT_SCHEMA,
                "source_prose_sha256":prose_hash(self.prose),
                "scene_key":SCENE,
                "sentences_accounted_for":len(source),
                "canonical_commit_authorized":False,
                "world_state_writes":0,
                "semantic_recall_proven":False,
                "model_ledger":{"prose_sha256":prose_hash(self.prose),
                                "rows":rows},
                "candidate_events":[event],
                "findings":["SWEEP_FAKE_MODEL_EVENT_UNVERIFIED"]}

    def test_mara_28_original_sentences_source_bound_replay_stable(self):
        actual=self.build()
        replay=self.build()
        self.assertEqual(actual,replay)
        self.assertEqual(actual["source_prose_sha256"],EXPECTED_SHA)
        self.assertEqual(actual["source_sentence_count"],28)
        self.assertEqual(actual["sentences_accounted_for"],28)
        self.assertEqual([s["source_ordinal"] for s in actual["source_sentences"]],
                         list(range(1,29)))
        self.assertEqual("".join(
            self.prose[s["source_start"]:s["source_end"]]
            for s in actual["source_sentences"]).replace(" ","").replace("\n",""),
            "".join(s["exact_source_quote"] for s in actual["source_sentences"]).replace(" ","").replace("\n",""))
        self.assertEqual(actual["candidate_event_count"],0)
        self.assertFalse(actual["canonical_commit_authorized"])
        self.assertFalse(actual["model_report_available"])
        self.assertFalse(actual["wall_clock_action_time_proven"])

    def test_clock_text_is_not_assigned_as_action_minute(self):
        actual=self.build()
        mentioned=[t["quote"] for s in actual["source_sentences"]
                   for t in s["quoted_clock_expressions"]]
        self.assertIn("02:10",mentioned)
        self.assertIn("02:07",mentioned)
        for row in actual["source_sentences"]:
            self.assertIsNone(row["action_minute"])
            self.assertEqual(row["action_time_status"],"NOT_PROVEN")
            self.assertTrue(all(not t["is_action_time"]
                                for t in row["quoted_clock_expressions"]))
        self.assertEqual(actual["time_order_semantics"],"SOURCE_ORDINAL_ONLY")

    def test_report_event_exact_span_binds_but_world_truth_remains_hold(self):
        report=self.simple_report()
        out=self.build(model_report=report)
        self.assertEqual(out["candidate_event_count"],1)
        self.assertTrue(out["model_report_available"])
        ev=out["model_candidate_events"][0]
        self.assertEqual(ev["exact_evidence_quote"],"Mara")
        self.assertIsNone(ev["event_action_minute"])
        self.assertEqual(ev["event_truth"],"MODEL_CANDIDATE_UNVERIFIED")
        self.assertEqual(out["source_graph_status"],"HOLD_NONCANONICAL")
        self.assertEqual(out["world_db_writes"],0)

    def test_forged_source_excerpt_cannot_be_recorded(self):
        report=self.simple_report()
        report["candidate_events"][0]["quote"]="An invented train appeared"
        with self.assertRaisesRegex(CoverageError,"EVENT_SPAN_INVALID"):
            self.build(model_report=report)

    def test_forged_sentence_link_and_missing_rows_denied(self):
        report=self.simple_report()
        report["candidate_events"][0]["sentence_id"]="invented-sentence"
        with self.assertRaisesRegex(CoverageError,"EVENT_UNLINKED"):
            self.build(model_report=report)
        report=self.simple_report()
        report["model_ledger"]["rows"].pop()
        with self.assertRaisesRegex(CoverageError,"MODEL_LEDGER_INCOMPLETE"):
            self.build(model_report=report)

    def test_source_world_and_model_count_drift_denied(self):
        report=self.simple_report()
        report["source_prose_sha256"]="f"*64
        with self.assertRaisesRegex(CoverageError,"NOT_SOURCE_BOUND"):
            self.build(model_report=report)
        with self.assertRaisesRegex(CoverageError,"SCOPE_INVALID"):
            self.build(world_sha256="a")
        self.assertNotEqual(self.build(prose=self.prose+" Another line.")[
            "chronology_sha256"],self.build()["chronology_sha256"])


if __name__=="__main__":
    unittest.main()
