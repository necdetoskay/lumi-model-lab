#!/usr/bin/env python3
"""Offline NOVA cross-media unit/smoke tests. Not the 12 story-quality A/B trials."""
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from validate_cross_media import ROOT, BASE, DOCS, check, read_jsonl
from match_cross_media import search
from sqlite_cross_media import build

class CrossMediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=check()
        cls.works=read_jsonl("works")
        cls.beats=read_jsonl("story_beats")
        cls.mechanics=read_jsonl("mechanisms")
        cls.edges=read_jsonl("decisions")
        cls.evidence=read_jsonl("mechanic_evidence")
        cls.sources=read_jsonl("sources")

    def test_01_validator_green(self):
        self.assertEqual(self.report["status"],"PASS",self.report.get("errors"))
    def test_02_exact_five_works(self):
        self.assertEqual(len(self.works),5)
    def test_03_all_ordered(self):
        self.assertEqual([x["work_id"] for x in self.works],
                         ["HADES-2020","OUTER-WILDS-2019","WITCHER3-2015","ARRIVAL-2016","12-ANGRY-MEN-1957"])
    def test_04_source_count(self):
        self.assertEqual(len(self.sources),25)
    def test_05_story_beat_count(self):
        self.assertEqual(len(self.beats),47)
    def test_06_mechanism_count(self):
        self.assertEqual(len(self.mechanics),35)
    def test_07_provenance_evidence_count(self):
        self.assertEqual(len(self.evidence),85)
    def test_08_decision_count(self):
        self.assertEqual(len(self.edges),22)
    def test_09_medium_choice_firewall(self):
        medium={x["work_id"]:x["medium"] for x in self.works}
        for edge in self.edges:
            if medium[edge["work_id"]]=="linear_feature_film":
                self.assertTrue(edge["decision_kind"].startswith("diegetic_"))
            else:
                self.assertFalse(edge["decision_kind"].startswith("diegetic_"))
    def test_10_no_quality_claim(self):
        self.assertEqual({x["quality_effect"] for x in self.mechanics},{"not_evaluated"})
    def test_11_no_lumi_canon(self):
        self.assertEqual({x["lumi_canon"] for x in self.works},{False})
    def test_12_full_story_files(self):
        pages=list(DOCS.glob("*/STORY.md"))
        self.assertEqual(len(pages),5)
        self.assertTrue(all(p.stat().st_size>3000 for p in pages))
    def test_13_branched_witcher(self):
        ids={x["decision_id"] for x in self.edges if x["work_id"]=="WITCHER3-2015"}
        self.assertTrue({"W-D02","W-D03","W-D04","W-D05","W-D06"}<=ids)
    def test_14_movies_not_player_games(self):
        self.assertFalse(next(x for x in self.works if x["work_id"]=="ARRIVAL-2016")["nonlinear"])
        self.assertFalse(next(x for x in self.works if x["work_id"]=="12-ANGRY-MEN-1957")["nonlinear"])
    def test_15_smoke_hades(self):
        self.assertEqual(search("Başarısızlıkla kalıcı ilerleme")[0]["mechanic_id"],"CM01")
    def test_16_smoke_outer(self):
        self.assertEqual(search("Bilgiye bağlı erişim")[0]["mechanic_id"],"CM08")
    def test_17_smoke_witcher(self):
        self.assertEqual(search("Gecikmeli kararın çoklu alıcıları")[0]["mechanic_id"],"CM16")
    def test_18_smoke_arrival(self):
        self.assertEqual(search("Finalin açılışı yeniden anlamlandırması")[0]["mechanic_id"],"CM23")
    def test_19_smoke_jury(self):
        self.assertEqual(search("Makul şüphe üzerine ilerleyen kanıt dizisi")[0]["mechanic_id"],"CM30")
    def test_20_sqlite_foreign_keys(self):
        with tempfile.TemporaryDirectory() as d:
            results=build(Path(d)/"vault.sqlite")
            self.assertEqual(results["status"],"PASS")
            self.assertEqual(results["tables"]["evidence"],85)
    def test_21_prior_sgu_unchanged_in_contract(self):
        from validate import validate
        self.assertEqual(validate()["status"],"PASS")
    def test_22_no_real_evaluation(self):
        m=json.loads((BASE/"manifest.json").read_text(encoding="utf8"))
        self.assertEqual(m["actual_story_trials"],0)
    def test_24_seven_cross_media_comparisons(self):
        links=read_jsonl("cross_media_links")
        self.assertEqual(len(links),7)
        by_id={x["mechanic_id"]:x["work_id"] for x in self.mechanics}
        for link in links:
            self.assertNotEqual(by_id[link["left"]],by_id[link["right"]])

    def test_25_http_coverage_no_false_claims(self):
        data=json.loads((BASE/"SOURCE_HTTP_CHECK.json").read_text(encoding="utf8"))
        counts={str(c):sum(str(x["status"])==str(c) for x in data["results"]) for c in (200,403,202)}
        self.assertEqual(counts,{"200":16,"403":8,"202":1})

    def test_23_idempotent_compiler(self):
        from build_cross_media import compile_corpus
        before=hashlib.sha256((BASE/"mechanic_evidence.jsonl").read_bytes()).hexdigest()
        compile_corpus()
        after=hashlib.sha256((BASE/"mechanic_evidence.jsonl").read_bytes()).hexdigest()
        self.assertEqual(before,after)

if __name__=="__main__":
    unittest.main(verbosity=2)
