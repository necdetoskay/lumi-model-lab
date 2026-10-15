#!/usr/bin/env python3
"""v0.10 offline structurals and negative/fail-closed narrative-agency checks."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_bioshock as builder
import validate_bioshock as v
import sqlite_bioshock as sql

class BioShockResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res=v.validate()
        cls.data={k:v.rows(k) for k in v.EXPECTED}
    def test_01_structural_pass(self):
        self.assertEqual(self.res['status'],'PASS',self.res.get('errors'))
    def test_02_one_original_game(self):
        self.assertEqual(self.data['works'][0]['original_release_year'],2007)
        self.assertEqual(self.data['works'][0]['work_id'],'BS2007')
    def test_03_fourteen_sources(self):
        self.assertEqual(len(self.data['sources']),14)
        self.assertEqual(len({x['source_id'] for x in self.data['sources']}),14)
    def test_04_event_count(self):
        self.assertEqual([x['event_id'] for x in self.data['story_events']],
            [f'BS-E{i:02d}' for i in range(1,24)])
    def test_05_sixteen_mechanics(self):
        self.assertEqual([x['mechanic_id'] for x in self.data['mechanics']],
            [f'BSM-{i:03d}' for i in range(1,17)])
    def test_06_fortyeight_mechanic_events(self):
        self.assertEqual(len(self.data['mechanic_evidence']),48)
        self.assertEqual(len({x['evidence_id'] for x in self.data['mechanic_evidence']}),48)
    def test_07_thirtyfour_previous_mechanic_links(self):
        self.assertEqual(len(self.data['prior_mechanic_references']),34)
    def test_08_speaker_truth_separation(self):
        k={x['state_id']:x for x in self.data['knowledge_states']}
        self.assertEqual(k['BS-K01']['reveal_event_id'],'BS-E16')
        self.assertEqual(k['BS-K04']['knowledge_status'],'source_claim_not_automatically_real_event')
    def test_09_mental_control_different_from_choice(self):
        events={x['event_id']:x for x in self.data['story_events']}
        self.assertEqual(events['BS-E05']['event_kind'],'player_branch')
        self.assertEqual(events['BS-E15']['event_kind'],'mandatory_story')
        self.assertEqual(events['BS-E11']['event_kind'],'optional_evidence')
    def test_10_two_mutually_exclusive_endings(self):
        ends=self.data['ending_variants']
        self.assertEqual(len(ends),2)
        self.assertTrue(all(x['specific_numeric_threshold'] is None for x in ends))
    def test_11_13_typed_causal_links(self):
        self.assertEqual(len(self.data['narrative_links']),13)
        self.assertEqual(sum(x['relation_kind']=='exclusive_epilogue' for x in self.data['narrative_links']),2)
    def test_12_six_pending_claim_boundaries(self):
        self.assertEqual(len(self.data['editorial_boundaries']),6)
    def test_13_work_not_remaster(self):
        self.assertFalse(self.data['works'][0]['remaster_is_distinct_story'])
    def test_14_zero_paid_and_quality(self):
        self.assertFalse(v.rows('quality_evaluations'))
        self.assertFalse(v.rows('lumi_usage_history'))
        self.assertEqual(self.res['story_quality_trials'],0)
        self.assertEqual(self.res['paid_calls'],0)
    def test_15_source_sha(self):
        m=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(m['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_16_deterministic_outputs(self):
        files=[builder.BASE/(k+'.jsonl') for k in v.TABLES]
        before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in files]
        builder.build()
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in files])
    def test_17_sqlite_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            r=sql.build(Path(d)/'bioshock.sqlite')
            self.assertEqual(r['status'],'PASS')
            self.assertEqual(r['foreign_key_violations'],0)
            self.assertEqual(r['counts']['previous_mechanics'],115)
    def test_18_all_old_validators_still_pass(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        import validate_prototype as v04
        import validate_tomb_raider as v05
        import validate_tomb_raider_classic as v06
        import validate_tomb_raider_lau as v07
        import validate_prototype2 as v08
        import validate_prototype_comics as v09
        self.assertEqual(v01.validate()['status'],'PASS')
        self.assertEqual(v02.check()['status'],'PASS')
        self.assertEqual(v03.validate()['status'],'PASS')
        self.assertEqual(v04.check()['status'],'PASS')
        self.assertEqual(v05.validate()['status'],'PASS')
        self.assertEqual(v06.validate()['status'],'PASS')
        self.assertEqual(v07.validate()['status'],'PASS')
        self.assertEqual(v08.validate()['status'],'PASS')
        self.assertEqual(v09.validate()['status'],'PASS')
    def mutate(self,table,change):
        orig=v.rows
        def patched(key):
            ret=copy.deepcopy(orig(key))
            if table==key:change(ret)
            return ret
        with mock.patch.object(v,'rows',side_effect=patched):
            return v.validate()
    def test_19_bad_source_fails(self):
        self.assertEqual(self.mutate('story_events',lambda rows:rows[0].update(source_ids=['OTHER']))['status'],'FAIL')
    def test_20_mandatory_event_as_choice_fails(self):
        self.assertEqual(self.mutate('story_events',lambda rows:rows[14].update(event_kind='player_branch',player_choice=True))['status'],'FAIL')
    def test_21_actual_choice_as_script_fails(self):
        self.assertEqual(self.mutate('story_events',lambda rows:rows[4].update(event_kind='mandatory_story',player_choice=False))['status'],'FAIL')
    def test_22_ending_false_exact_threshold_fails(self):
        self.assertEqual(self.mutate('ending_variants',lambda rows:rows[0].update(specific_numeric_threshold=1,threshold_verified=True))['status'],'FAIL')
    def test_23_merging_ending_history_fails(self):
        self.assertEqual(self.mutate('ending_variants',lambda rows:rows[1].update(canon_status='simultaneously_happened'))['status'],'FAIL')
    def test_24_false_family_fact_fails(self):
        self.assertEqual(self.mutate('knowledge_states',lambda rows:rows[3].update(knowledge_status='confirmed_family_exists'))['status'],'FAIL')
    def test_25_atlas_allegiance_false_fails(self):
        self.assertEqual(self.mutate('knowledge_states',lambda rows:rows[0].update(world_truth='two different people'))['status'],'FAIL')
    def test_26_missing_lazarus_vector_cause_fails(self):
        self.assertEqual(self.mutate('narrative_links',
          lambda rows:next(x for x in rows if x['from_event_id']=='BS-E08').update(to_event_id='BS-E12'))['status'],'FAIL')
    def test_27_wrong_prior_mechanic_fails(self):
        self.assertEqual(self.mutate('prior_mechanic_references',lambda rows:rows[0].update(prior_mechanic_id='FAKE'))['status'],'FAIL')
    def test_28_synthetic_story_quality_false_fails(self):
        self.assertEqual(self.mutate('quality_evaluations',lambda rows:rows.append({'fake':'PASS'}))['status'],'FAIL')
    def test_29_wrong_evidence_kind_fails(self):
        self.assertEqual(self.mutate('mechanic_evidence',lambda rows:rows[0].update(event_kind='ending_variant'))['status'],'FAIL')
    def test_30_invented_primary_gameplay_audit_fails(self):
        self.assertEqual(self.mutate('story_events',
          lambda rows:rows[0].update(evidence_strength='directly_gameplay_verified'))['status'],'FAIL')
    def test_31_ending_sources_are_lower_confidence(self):
        events={x['event_id']:x for x in self.data['story_events']}
        self.assertEqual(events['BS-E22']['evidence_strength'],'walkthrough_and_conflicting_community_rule')
    def test_32_mechanisms_never_proven(self):
        self.assertTrue(all(x['quality_effect']=='not_evaluated' for x in self.data['mechanics']))
if __name__=='__main__':unittest.main(verbosity=2)
