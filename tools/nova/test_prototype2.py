#!/usr/bin/env python3
"""NOVA v0.8 Prototype 2 local structural and negative test suite."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_prototype2 as builder
import validate_prototype2 as v
import sqlite_prototype2 as sql

class Prototype2CorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.check=v.validate()
        cls.data={key:v.rows(key) for key in v.EXPECTED}
    def test_01_valid(self):
        self.assertEqual(self.check['status'],'PASS',self.check.get('errors'))
    def test_02_one_2012_game(self):
        self.assertEqual([(w['work_id'],w['release_year']) for w in self.data['works']],[('PROTOTYPE2-2012',2012)])
    def test_03_11_sources(self):
        self.assertEqual(len(self.data['sources']),11)
        self.assertEqual(len({x['source_id'] for x in self.data['sources']}),11)
    def test_04_20_events(self):
        self.assertEqual([e['event_id'] for e in self.data['story_events']],
            [f'P2-E{i:02d}' for i in range(1,21)])
    def test_05_14_distinct_mechanisms(self):
        self.assertEqual([m['mechanic_id'] for m in self.data['mechanics']],
            [f'P2M-{i:03d}' for i in range(1,15)])
    def test_06_42_provenance_links(self):
        self.assertEqual(len(self.data['mechanic_evidence']),42)
        self.assertEqual(len({x['evidence_id'] for x in self.data['mechanic_evidence']}),42)
    def test_07_38_prior_mechanic_links(self):
        self.assertEqual(len(self.data['prior_links']),38)
        self.assertEqual({x['source_version'] for x in self.data['prior_links']},{'0.4','other'})
    def test_08_8_prior_event_links(self):
        self.assertEqual(len(self.data['cross_game_links']),8)
        self.assertTrue(all(x['from_prior_event_id'].startswith('PRT-E') for x in self.data['cross_game_links']))
    def test_09_7_belief_states(self):
        self.assertEqual(len(self.data['belief_states']),7)
    def test_10_daughter_alive_not_resurrected(self):
        x=next(x for x in self.data['belief_states'] if x['subject']=='maya_alive')
        self.assertEqual(x['world_state_rule'],'always_alive_not_retroactively_resurrected')
        self.assertEqual(x['reveal_event_id'],'P2-E15')
    def test_11_final_has_lower_source_certainty(self):
        e={x['event_id']:x for x in self.data['story_events']}
        for id in v.LOW_CONFIDENCE:
            self.assertEqual(e[id]['confidence'],'tertiary_and_community_nonindependent')
    def test_12_zero_quality_trials_and_paid_calls(self):
        self.assertFalse(v.rows('quality_evaluations'))
        self.assertFalse(v.rows('lumi_usage_history'))
        self.assertEqual(self.check['story_quality_trials'],0)
        self.assertEqual(self.check['paid_calls'],0)
    def test_13_canonical_manifest_sha(self):
        m=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(m['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_14_rebuild_is_deterministic(self):
        paths=[builder.BASE/(k+'.jsonl') for k in v.EXPECTED]
        initial=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        builder.build()
        self.assertEqual(initial,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
    def test_15_sqlite_fk(self):
        with tempfile.TemporaryDirectory() as d:
            r=sql.build(Path(d)/'p2.sqlite')
            self.assertEqual(r['foreign_key_violations'],0)
            self.assertEqual(r['counts']['prior_links'],38)
    def test_16_previous_corpora_pass(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        import validate_prototype as v04
        import validate_tomb_raider as v05
        import validate_tomb_raider_classic as v06
        import validate_tomb_raider_lau as v07
        self.assertEqual(v01.validate()['status'],'PASS')
        self.assertEqual(v02.check()['status'],'PASS')
        self.assertEqual(v03.validate()['status'],'PASS')
        self.assertEqual(v04.check()['status'],'PASS')
        self.assertEqual(v05.validate()['status'],'PASS')
        self.assertEqual(v06.validate()['status'],'PASS')
        self.assertEqual(v07.validate()['status'],'PASS')
    def mutate(self,table,callback):
        source=v.rows
        def changed(key):
            current=copy.deepcopy(source(key))
            if key==table:callback(current)
            return current
        with mock.patch.object(v,'rows',side_effect=changed):
            return v.validate()
    def test_17_unregistered_source_fails(self):
        self.assertEqual(self.mutate('story_events',lambda r:r[0].update(source_ids=['FAKE']))['status'],'FAIL')
    def test_18_wrong_maya_resurrection_fails(self):
        self.assertEqual(self.mutate('belief_states',lambda r:r[0].update(world_state_rule='resurrected'))['status'],'FAIL')
    def test_19_false_high_confidence_end_fails(self):
        self.assertEqual(self.mutate('story_events',lambda r:r[-1].update(confidence='primary_gameplay_audit'))['status'],'FAIL')
    def test_20_wrong_prior_event_fails(self):
        self.assertEqual(self.mutate('cross_game_links',lambda r:r[0].update(from_prior_event_id='OTHER-EVENT'))['status'],'FAIL')
    def test_21_false_mechanism_quality_fails(self):
        self.assertEqual(self.mutate('mechanics',lambda r:r[0].update(quality_effect='proven'))['status'],'FAIL')
    def test_22_wrong_source_for_evidence_fails(self):
        self.assertEqual(self.mutate('mechanic_evidence',lambda r:r[0].update(source_ids=['P2-ACTIVISION']))['status'],'FAIL')
    def test_23_wrong_prior_mechanic_fails(self):
        self.assertEqual(self.mutate('prior_links',lambda r:r[0].update(prior_mechanic_id='FAKE'))['status'],'FAIL')
    def test_24_comic_artifact_not_in_game_fails(self):
        self.assertEqual(self.mutate('works',lambda r:r.append({**copy.deepcopy(r[0]),'work_id':'THE-ANCHOR-COMIC'}))['status'],'FAIL')
    def test_25_fake_trial_fails(self):
        self.assertEqual(self.mutate('quality_evaluations',lambda r:r.append({'trial':'fabricated'}))['status'],'FAIL')
    def test_26_changed_knowledge_source_fails(self):
        self.assertEqual(self.mutate('belief_states',lambda r:r[0].update(reveal_event_id='P2-E02'))['status'],'FAIL')
    def test_27_provenance_count_nonduplicated(self):
        self.assertEqual(len({(r['mechanic_id'],r['event_id']) for r in self.data['mechanic_evidence']}),42)
    def test_28_no_runtime_usage(self):
        self.assertTrue(all(m['lumi_canon'] is False for m in self.data['mechanics']))
    def test_29_developer_interview_not_game_fact(self):
        s=next(s for s in self.data['sources'] if s['source_id']=='P2-DEV')
        self.assertEqual(s['evidence_tier'],'developer_interview')
    def test_30_allegiance_not_frozen(self):
        self.assertIn('alliance_changes',[b['world_state_rule'] for b in self.data['belief_states']])
if __name__=='__main__':unittest.main(verbosity=2)
