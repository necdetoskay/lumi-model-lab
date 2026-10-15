#!/usr/bin/env python3
"""NOVA v0.11 negative and regression coverage, no live stories or paid API calls."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_bioshock2 as builder
import validate_bioshock2 as v
import sqlite_bioshock2 as sql

class BioShock2ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={key:v.rows(key) for key in v.EXPECTED}
        cls.status=v.validate()
    def test_01_pass(self):
        self.assertEqual(self.status['status'],'PASS',self.status.get('errors'))
    def test_02_two_separate_works(self):
        self.assertEqual([w['work_id'] for w in self.data['works']],list(v.WIDS))
    def test_03_dlc_release(self):
        self.assertEqual(self.data['works'][1]['original_release_date'],'2010-08-31')
    def test_04_base_release(self):
        self.assertEqual(self.data['works'][0]['original_release_date'],'2010-02-09')
    def test_05_nineteen_source_records(self):
        self.assertEqual(len({x['source_id'] for x in self.data['sources']}),19)
    def test_06_30_events(self):
        self.assertEqual(len(self.data['story_events']),30)
        self.assertEqual(len({x['event_id'] for x in self.data['story_events']}),30)
    def test_07_per_work_event_counts(self):
        self.assertEqual([sum(x['work_id']==w for x in self.data['story_events']) for w in v.WIDS],[18,12])
    def test_08_prologue_vs_main_era(self):
        e={x['event_id']:x for x in self.data['story_events']}
        self.assertEqual(e['B2-E01']['narrative_time_type'],'historical_1958')
        self.assertEqual(e['B2-E02']['narrative_time_type'],'main_1968')
    def test_09_eighteen_new_mechanics(self):
        self.assertEqual([m['mechanic_id'] for m in self.data['mechanics']],
                         [f'B2M-{i:03d}' for i in range(1,19)])
    def test_10_47_evidence_links(self):
        self.assertEqual(len(self.data['mechanic_evidence']),47)
        self.assertEqual(len({e['evidence_id'] for e in self.data['mechanic_evidence']}),47)
    def test_11_36_prior_concept_links(self):
        self.assertEqual(len(self.data['mechanic_prior_links']),36)
    def test_12_6_bioshock2007_links(self):
        self.assertEqual(len(self.data['prior_bioshock_links']),6)
    def test_13_four_independent_choice_axes(self):
        self.assertEqual(len(self.data['choice_axes']),4)
        self.assertEqual({x['axis_id'] for x in self.data['choice_axes']},
                         {'B2-C-LITTLE','B2-C-GRACE','B2-C-STAN','B2-C-GIL'})
    def test_14_three_exclusive_epilogue_categories(self):
        out=self.data['ending_outcomes']
        self.assertEqual(len(out),3)
        self.assertTrue(all(len(x['exclusive_with'])==2 for x in out))
    def test_15_eleanor_example_not_mind_control(self):
        k=next(x for x in self.data['knowledge_states'] if x['knowledge_id']=='B2-K04')
        self.assertEqual(k['actual_world_rule'],'observes_and_imitates_delta_actions')
        self.assertFalse(k['subjective_claim_is_objective_fact'])
    def test_16_subject_sigma_and_thinker_identity(self):
        k={x['knowledge_id']:x for x in self.data['knowledge_states']}
        self.assertEqual(k['MD-K01']['actual_world_rule'],'thinker_simulates_porter_voice')
        self.assertEqual(k['MD-K02']['actual_world_rule'],'sigma_is_transformed_physical_porter')
    def test_17_simulation_not_resurrection(self):
        k=next(x for x in self.data['knowledge_states'] if x['knowledge_id']=='MD-K03')
        self.assertEqual(k['actual_world_rule'],'voice_personality_emulation_is_not_original_person_resurrection')
    def test_18_six_stateful_objects(self):
        self.assertEqual(len(self.data['object_states']),6)
    def test_19_zero_paid_calls(self):
        self.assertEqual(self.status['paid_calls'],0)
        self.assertEqual(self.status['story_quality_trials'],0)
        self.assertFalse(v.rows('quality_evaluations'))
        self.assertFalse(v.rows('lumi_usage_history'))
    def test_20_source_sha_matches_manifest(self):
        m=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(m['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_21_deterministic_build(self):
        files=[builder.BASE/(k+'.jsonl') for k in v.EXPECTED]
        before=[hashlib.sha256(x.read_bytes()).hexdigest() for x in files]
        builder.build()
        self.assertEqual(before,[hashlib.sha256(x.read_bytes()).hexdigest() for x in files])
    def test_22_sqlite_foreign_keys(self):
        with tempfile.TemporaryDirectory() as d:
            x=sql.build(Path(d)/'bioshock2-minerva.sqlite')
            self.assertEqual(x['status'],'PASS')
            self.assertEqual(x['foreign_key_violations'],0)
            self.assertEqual(x['counts']['previous_mechanics'],131)
    def test_23_all_older_corpus_validators(self):
        import validate as a
        import validate_cross_media as b
        import validate_prince_of_persia as c
        import validate_prototype as d
        import validate_tomb_raider as e
        import validate_tomb_raider_classic as f
        import validate_tomb_raider_lau as g
        import validate_prototype2 as h
        import validate_prototype_comics as i
        import validate_bioshock as j
        self.assertEqual(a.validate()['status'],'PASS')
        self.assertEqual(b.check()['status'],'PASS')
        self.assertEqual(c.validate()['status'],'PASS')
        self.assertEqual(d.check()['status'],'PASS')
        self.assertEqual(e.validate()['status'],'PASS')
        self.assertEqual(f.validate()['status'],'PASS')
        self.assertEqual(g.validate()['status'],'PASS')
        self.assertEqual(h.validate()['status'],'PASS')
        self.assertEqual(i.validate()['status'],'PASS')
        self.assertEqual(j.validate()['status'],'PASS')
    def mutate(self,table,change):
        original=v.rows
        def patched(key):
            data=copy.deepcopy(original(key))
            if key==table:change(data)
            return data
        with mock.patch.object(v,'rows',side_effect=patched):
            return v.validate()
    def test_24_dlc_merged_into_main_fails(self):
        self.assertEqual(self.mutate('works',lambda a:a[1].update(work_id='B2-BASE-2010'))['status'],'FAIL')
    def test_25_false_dlc_time_alignment_fails(self):
        self.assertEqual(self.mutate('works',lambda a:a[1].update(narrative_time_scope='same_hour_as_delta'))['status'],'FAIL')
    def test_26_comics_style_tier_fails(self):
        self.assertEqual(self.mutate('sources',lambda a:a[0].update(evidence_tier='gameplay_independently_audited'))['status'],'FAIL')
    def test_27_missing_event_source_fails(self):
        self.assertEqual(self.mutate('story_events',lambda a:a[0].update(source_ids=['UNKNOWN']))['status'],'FAIL')
    def test_28_temporary_eleanor_dead_fails(self):
        self.assertEqual(self.mutate('knowledge_states',lambda a:next(x for x in a if x['knowledge_id']=='B2-K02').update(actual_world_rule='permanently_dead'))['status'],'FAIL')
    def test_29_thinker_voice_as_second_person_fails(self):
        self.assertEqual(self.mutate('knowledge_states',lambda a:next(x for x in a if x['knowledge_id']=='MD-K01').update(actual_world_rule='physically_present_porter'))['status'],'FAIL')
    def test_30_sigma_identity_wrong_fails(self):
        self.assertEqual(self.mutate('knowledge_states',lambda a:next(x for x in a if x['knowledge_id']=='MD-K02').update(actual_world_rule='different_independent_person'))['status'],'FAIL')
    def test_31_pearl_simulation_as_alive_fails(self):
        self.assertEqual(self.mutate('object_states',lambda a:next(x for x in a if x['object_id']=='OBJ-MD-PEARL').update(state_rule='actually_alive'))['status'],'FAIL')
    def test_32_punchcard_teleport_fails(self):
        self.assertEqual(self.mutate('object_states',lambda a:next(x for x in a if x['object_id']=='OBJ-MD-PUNCHCARD').update(state_rule='both_hold_simultaneously'))['status'],'FAIL')
    def test_33_wrong_little_sister_choice_fails(self):
        self.assertEqual(self.mutate('choice_axes',lambda a:a[0].update(options=['kill','spare']))['status'],'FAIL')
    def test_34_numeric_ending_count_fails(self):
        self.assertEqual(self.mutate('ending_outcomes',lambda a:a[0].update(exact_numeric_threshold=1))['status'],'FAIL')
    def test_35_invented_variant_merge_fails(self):
        self.assertEqual(self.mutate('ending_outcomes',lambda a:a[0].update(exclusive_with=[]))['status'],'FAIL')
    def test_36_cross_dlc_physical_jump_fails(self):
        self.assertEqual(self.mutate('narrative_links',lambda a:a[0].update(to_event_id='MD-E01'))['status'],'FAIL')
    def test_37_bad_prior_mechanic_fails(self):
        self.assertEqual(self.mutate('mechanic_prior_links',lambda a:a[0].update(prior_mechanic_id='NONEXISTENT'))['status'],'FAIL')
    def test_38_mechanic_as_proven_fails(self):
        self.assertEqual(self.mutate('mechanics',lambda a:a[0].update(quality_effect='proven'))['status'],'FAIL')
    def test_39_wrong_evidence_source_fails(self):
        self.assertEqual(self.mutate('mechanic_evidence',lambda a:a[0].update(source_ids=['B2-XBOX-MD']))['status'],'FAIL')
    def test_40_fake_quality_experiment_fails(self):
        self.assertEqual(self.mutate('quality_evaluations',lambda a:a.append({'fake':'PASS'}))['status'],'FAIL')
if __name__=='__main__':
    unittest.main(verbosity=2)
