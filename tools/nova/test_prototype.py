#!/usr/bin/env python3
"""Offline source-only regression tests for Prototype 2009 first pass."""
import copy
import hashlib
import json
import unittest
from unittest import mock
import build_prototype as compiler
import validate_prototype as v

class PrototypeResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=v.check()
        cls.data={n:v.rows(n) for n in v.EXPECTED}
    def test_01_validator(self):
        self.assertEqual(self.report["status"],"PASS",self.report.get("errors"))
    def test_02_one_distinct_work(self):
        self.assertEqual([x["work_id"] for x in self.data["works"]],["PROTOTYPE-2009"])
    def test_03_nine_provenance_sources(self):
        self.assertEqual(len(self.data["sources"]),9)
        self.assertEqual(len({x["source_id"] for x in self.data["sources"]}),9)
    def test_04_sixteen_ordered_events(self):
        self.assertEqual([x["event_id"] for x in self.data["story_events"]],
                         [f"PRT-E{i:02d}" for i in range(1,17)])
    def test_05_twelve_distinct_candidate_mechanisms(self):
        self.assertEqual(len(self.data["mechanics"]),12)
        self.assertEqual(len({x["mechanic_id"] for x in self.data["mechanics"]}),12)
    def test_06_thirty_source_linked_evidences(self):
        self.assertEqual(len(self.data["mechanic_evidence"]),30)
        self.assertEqual(len({x["evidence_id"] for x in self.data["mechanic_evidence"]}),30)
    def test_07_twenty_prior_links(self):
        self.assertEqual(len(self.data["prior_links"]),20)
        self.assertTrue(all(x["prior_mechanic_id"].startswith("POP-") for x in self.data["prior_links"]))
    def test_08_source_hash(self):
        manifest=json.loads((compiler.BASE/"manifest.json").read_text(encoding="utf8"))
        self.assertEqual(manifest["source_sha256"],hashlib.sha256(compiler.SRC.read_bytes()).hexdigest())
    def test_09_zero_evaluation_history(self):
        self.assertFalse(v.rows("quality_evaluations"))
        self.assertFalse(v.rows("lumi_usage_history"))
        self.assertEqual(self.report["story_quality_trials"],0)
        self.assertEqual(self.report["new_paid_calls"],0)
    def test_10_both_endings_and_other_games_not_falsely_merged(self):
        self.assertEqual(len(self.data["works"]),1)
        self.assertNotIn("PROTOTYPE-2012",{x["work_id"] for x in self.data["works"]})
    def test_11_weak_claims_not_promoted(self):
        for e in self.data["story_events"]:
            if e["event_id"] in v.REFERENCE_LOWER_CONFIDENCE:
                self.assertEqual(e["evidence_strength"],"secondary_or_community_not_independently_audited")
    def test_12_deterministic_compilation(self):
        before={t:hashlib.sha256((compiler.BASE/(t+".jsonl")).read_bytes()).hexdigest()
                for t in v.EXPECTED}
        compiler.compile_data()
        after={t:hashlib.sha256((compiler.BASE/(t+".jsonl")).read_bytes()).hexdigest()
               for t in v.EXPECTED}
        self.assertEqual(before,after)
    def _simulate(self,table,mutator):
        original=v.rows
        def broken(name):
            data=copy.deepcopy(original(name))
            if name==table:mutator(data)
            return data
        with mock.patch.object(v,"rows",side_effect=broken):
            return v.check()
    def test_13_fail_closed_on_deleted_provenance(self):
        result=self._simulate("story_events",lambda x:x[0].update(source_ids=["NO_SOURCE"]))
        self.assertEqual(result["status"],"FAIL")
    def test_14_fail_closed_on_fabricated_mechanic_quality(self):
        result=self._simulate("mechanics",lambda x:x[0].update(quality_effect="proven"))
        self.assertEqual(result["status"],"FAIL")
    def test_15_fail_closed_on_identity_claim_promotion(self):
        result=self._simulate("story_events",lambda x:x[12].update(evidence_strength="official_gameplay_verified"))
        self.assertEqual(result["status"],"FAIL")
    def test_16_fail_closed_on_orphan_mechanic_evidence(self):
        result=self._simulate("mechanic_evidence",lambda x:x[0].update(event_id="BAD-EVENT"))
        self.assertEqual(result["status"],"FAIL")
    def test_17_fail_closed_on_false_quality_evaluation(self):
        result=self._simulate("quality_evaluations",lambda x:x.append({"made_up":"PASS"}))
        self.assertEqual(result["status"],"FAIL")
    def test_18_fail_closed_on_missing_cross_version_link(self):
        result=self._simulate("prior_links",lambda x:x.pop())
        self.assertEqual(result["status"],"FAIL")
    def test_19_prior_versions_still_validate(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        self.assertEqual(v01.validate()["status"],"PASS")
        self.assertEqual(v02.check()["status"],"PASS")
        self.assertEqual(v03.validate()["status"],"PASS")
    def test_20_source_records_hold_no_lumi_canon(self):
        self.assertTrue(all(x["lumi_canon"] is False for x in self.data["mechanics"]))
        self.assertTrue(all(x["quality_effect"]=="not_evaluated" for x in self.data["mechanics"]))
    def test_21_independent_source_corpus_present(self):
        self.assertTrue(all((compiler.DOCS/n).is_file() for n in v.DOCUMENTS))
    def test_22_gameplay_and_editorial_candidates_distinguished(self):
        m=next(x for x in self.data["mechanics"] if x["mechanic_id"]=="PRT-009")
        self.assertTrue(m["mechanism_inference"])
        self.assertIn("oyun mekaniğinde bulunmayan",m["guardrail_tr"].lower())
if __name__=="__main__":
    unittest.main(verbosity=2)
