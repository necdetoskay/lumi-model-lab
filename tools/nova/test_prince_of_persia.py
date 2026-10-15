#!/usr/bin/env python3
"""NOVA v0.3 PoP offline research tests. No story generation, no API."""
import copy
import hashlib
import json
import unittest
from collections import Counter
from unittest import mock

import validate_prince_of_persia as validator
from build_prince_of_persia import BASE, DOCS, ROOT, compile_data
from sqlite_prince_of_persia import build as build_sql

class PoPResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate=validator.validate()
        cls.data={name:validator.jsonl(name) for name in validator.EXPECTED}
    def test_01_green_data_contract(self):
        self.assertEqual(self.gate["status"],"PASS",self.gate["errors"])
    def test_02_19_stories(self):
        self.assertEqual(len(self.data["works"]),19)
    def test_03_8_distinct_supplemental_releases(self):
        self.assertEqual(len(self.data["supplementary_releases"]),8)
    def test_04_every_work_has_story_and_source(self):
        self.assertTrue(all(len(w["story_overview_tr"])>=240 and len(w["source_ids"])>=2 for w in self.data["works"]))
    def test_05_four_distinct_forgotten_sands(self):
        x=[w for w in self.data["works"] if w["work_id"].startswith("FORGOTTEN-")]
        self.assertEqual({w["work_id"] for w in x},
        {"FORGOTTEN-MAIN-2010","FORGOTTEN-WII-2010","FORGOTTEN-PSP-2010","FORGOTTEN-DS-2010"})
    def test_06_current_released_vs_cancelled_remake(self):
        c=[w for w in self.data["supplementary_releases"] if w["class"]=="cancelled_not_released"]
        self.assertEqual(len(c),1)
        self.assertNotIn(c[0]["release_id"],{w["work_id"] for w in self.data["works"]})
    def test_07_84_story_beats(self):
        self.assertEqual(len(self.data["story_beats"]),84)
    def test_08_29_warrior_events(self):
        self.assertEqual(len(self.data["temporal_events"]),29)
    def test_09_reveal_order_contiguous(self):
        self.assertEqual([e["player_reveal_order"] for e in self.data["temporal_events"]],list(range(1,30)))
    def test_10_distinct_actor_versions(self):
        versions={x["actor_version"] for x in self.data["temporal_events"]}
        self.assertTrue({"PRINCE","SAND_WRAITH","PRINCE_AFTER_MASK"}<=versions)
    def test_11_both_histories_of_dahaka_interception(self):
        xs=[e for e in self.data["temporal_events"] if e["time_slot_id"]=="SLOT_DAHAKA_INTERCEPTION"]
        self.assertEqual(len(xs),3)
        self.assertEqual({x["worldline_variant"] for x in xs},{"FIRST_HISTORY","REVISED_HISTORY"})
    def test_12_era_time_of_two_deaths(self):
        ev={x["event_id"]:x for x in self.data["temporal_events"]}
        self.assertEqual(ev["W12"]["epoch"],"ISLAND_PAST")
        self.assertEqual(ev["W25"]["epoch"],"ISLAND_PRESENT")
    def test_13_exactly_two_endings_and_single_canon(self):
        ending=self.data["ending_branches"]
        self.assertEqual(len(ending),2)
        self.assertEqual(sum(x["canonical_for_next_game"] for x in ending),1)
    def test_14_water_sword_condition(self):
        canon=next(x for x in self.data["ending_branches"] if x["canonical_for_next_game"])
        self.assertIn("life_upgrades == 9",canon["condition"])
        self.assertIn("water_sword_obtained == true",canon["condition"])
    def test_15_two_thrones_only_canon(self):
        ev={x["event_id"]:x for x in self.data["temporal_events"]}
        self.assertEqual(ev["W28"]["worldline_variant"],"CANON_TRANSFER")
        self.assertIn("vizier_alive_in_altered_history",ev["W28"]["state_delta_tr"])
    def test_16_7_past_present_locations(self):
        self.assertEqual(len(self.data["temporal_locations"]),7)
        self.assertTrue(all(x["past_state_tr"] and x["present_state_tr"]
            for x in self.data["temporal_locations"]))
    def test_17_34_causal_links_and_inference_marker(self):
        edges=self.data["temporal_edges"]
        self.assertEqual(len(edges),34)
        conjectures=[x for x in edges if x["is_temporal_loop"]]
        self.assertEqual(len(conjectures),1)
        self.assertTrue(conjectures[0]["inference"])
    def test_17b_graph_causal_join_requires_kaileena_and_sword(self):
        edges=self.data["temporal_edges"]
        pairs={(x["from_event_id"],x["to_event_id"]) for x in edges}
        self.assertIn(("W23","W26"),pairs)
        self.assertIn(("W24","W26"),pairs)
        self.assertEqual(validator.causal_graph_errors(self.data["temporal_events"],edges,self.data["ending_branches"]),[])
        without_transfer=[x for x in edges if (x["from_event_id"],x["to_event_id"])!=("W23","W26")]
        issues=validator.causal_graph_errors(self.data["temporal_events"],without_transfer,self.data["ending_branches"])
        self.assertTrue(any("prerequisite missing" in issue for issue in issues),issues)
    def test_17c_no_forward_causal_cycle(self):
        edges=copy.deepcopy(self.data["temporal_edges"])
        edges.append({"from_event_id":"W27","to_event_id":"W23","relation":"bad_causal_backedge",
                      "is_temporal_loop":False,"inference":False})
        issues=validator.causal_graph_errors(self.data["temporal_events"],edges,self.data["ending_branches"])
        self.assertTrue(any("directed cycle" in issue for issue in issues),issues)
    def test_17d_mirror_time_slot_mismatch_fails(self):
        events=copy.deepcopy(self.data["temporal_events"])
        next(x for x in events if x["event_id"]=="W16")["time_slot_id"]="OTHER_SLOT"
        issues=validator.causal_graph_errors(events,self.data["temporal_edges"],self.data["ending_branches"])
        self.assertTrue(any("same time/era" in issue for issue in issues),issues)
    def test_17e_noncanonical_sequel_leak_fails(self):
        edges=copy.deepcopy(self.data["temporal_edges"])
        edges.append({"from_event_id":"W25","to_event_id":"W28","relation":"invalid_sequel",
                      "is_temporal_loop":False,"inference":False})
        issues=validator.causal_graph_errors(self.data["temporal_events"],edges,self.data["ending_branches"])
        self.assertTrue(any("leaks into canonical sequel" in issue for issue in issues),issues)
    def test_18_22_unique_mechanics(self):
        self.assertEqual(len(self.data["mechanics"]),22)
        self.assertEqual(len({x["mechanic_id"] for x in self.data["mechanics"]}),22)
    def test_19_72_traceable_evidences(self):
        self.assertEqual(len(self.data["mechanic_evidence"]),72)
        self.assertTrue(all(x["source_ids"] for x in self.data["mechanic_evidence"]))
    def test_20_old_mechanics_cross_references(self):
        self.assertEqual(len(self.data["cross_corpus_links"]),27)
        self.assertEqual(self.gate["old_cm_mechanisms_unchanged"],35)
    def test_21_2010_wii_psp_ds_alternate_plot(self):
        d={x["work_id"]:x["story_overview_tr"] for x in self.data["works"]}
        self.assertIn("Zahra",d["FORGOTTEN-WII-2010"])
        self.assertIn("Ahihud",d["FORGOTTEN-PSP-2010"])
        self.assertIn("Razia",d["FORGOTTEN-DS-2010"])
        self.assertIn("Malik",d["FORGOTTEN-MAIN-2010"])
    def test_22_lost_crown_and_dlc_not_duplicated(self):
        works={x["work_id"] for x in self.data["works"]}
        self.assertTrue({"LOST-2024","MASK-2024","ROGUE-2025"}<=works)
    def test_23_all_story_docs(self):
        self.assertEqual(len(list((DOCS/"works").glob("*.md"))),19)
    def test_24_zero_paid_and_no_real_evals(self):
        self.assertEqual(validator.jsonl("quality_evaluations"),[])
        self.assertEqual(validator.jsonl("lumi_usage_history"),[])
        self.assertEqual(self.gate["independent_quality_ab_trials"],0)
    def test_25_sandbox_sqlite_fks(self):
        report=build_sql()
        self.assertEqual(report["status"],"PASS")
        self.assertEqual(report["foreign_key_violations"],0)
        self.assertEqual(report["counts"]["anchors"],113)
    def test_25b_water_sword_is_optional_in_past(self):
        event=next(x for x in self.data["temporal_events"] if x["event_id"]=="W24")
        self.assertEqual(event["epoch"],"ISLAND_PAST")
        self.assertTrue(event["analysis_order_not_required_gameplay_order"])
        self.assertTrue(event["earliest_documented_acquisition_before_mask"])
    def test_25c_harem_independent_mobile_story(self):
        game=next(x for x in self.data["works"] if x["work_id"]=="HAREM-2002")
        self.assertEqual(game["kind"],"original_mobile_side_game")
        self.assertEqual(game["status"],"short_source_grounded_plot_only")
        self.assertEqual(len(game["beats_tr"]),4)
    def test_26_source_integrity(self):
        man=json.loads((BASE/"manifest.json").read_text(encoding="utf8"))
        for name,sha in man["hashes"].items():
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),sha)
    def test_27_deterministic_compilation(self):
        paths=[BASE/(n+".jsonl") for n in validator.EXPECTED]
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        compile_data()
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        self.assertEqual(before,after)
    def test_28_fail_closed_on_changed_history(self):
        real=validator.jsonl
        def fake(name):
            rows=copy.deepcopy(real(name))
            if name=="temporal_events":rows[19]["worldline_variant"]="FIRST_HISTORY"
            return rows
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")
    def test_29_fail_closed_on_noncanonical_promotion(self):
        real=validator.jsonl
        def fake(name):
            rows=copy.deepcopy(real(name))
            if name=="ending_branches":
                rows[0]["canonical_for_next_game"]=True
            return rows
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")
    def test_30_fail_closed_on_orphan_evidence(self):
        real=validator.jsonl
        def fake(name):
            rows=copy.deepcopy(real(name))
            if name=="mechanic_evidence":
                rows[0]["source_ids"]=["FAKE-SOURCE"]
            return rows
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")
    def test_31_fail_closed_on_fake_evaluation(self):
        real=validator.jsonl
        def fake(name):
            if name=="quality_evaluations":return [{"fabricated":"PASS"}]
            return real(name)
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")
    def test_31b_fail_closed_on_water_sword_misplaced(self):
        real=validator.jsonl
        def fake(name):
            rows=copy.deepcopy(real(name))
            if name=="temporal_events":
                rows[23]["epoch"]="ISLAND_PRESENT"
            return rows
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")
    def test_32_fail_closed_on_changed_mechanism(self):
        real=validator.jsonl
        def fake(name):
            rows=copy.deepcopy(real(name))
            if name=="mechanics":
                rows[0]["quality_effect"]="proven"
            return rows
        with mock.patch.object(validator,"jsonl",side_effect=fake):
            report=validator.validate()
        self.assertEqual(report["status"],"FAIL")

if __name__=="__main__":
    unittest.main(verbosity=2)
