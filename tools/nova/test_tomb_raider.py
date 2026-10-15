#!/usr/bin/env python3
"""NOVA v0.5 Survivor trilogy offline regression and negative validation cases."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_tomb_raider as builder
import validate_tomb_raider as validator
import sqlite_tomb_raider as sqlite_builder

class TombRaiderDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=validator.validate()
        cls.data={k:validator.read(k) for k in validator.EXPECTED}
    def test_01_green_contract(self):
        self.assertEqual(self.result['status'],'PASS',self.result['errors'])
    def test_02_three_separate_works(self):
        self.assertEqual([x['work_id'] for x in self.data['works']],list(validator.EXPECTED_WORKS))
    def test_03_18_publisher_sources(self):
        self.assertEqual(len(self.data['sources']),18)
        self.assertEqual(len({x['source_id'] for x in self.data['sources']}),18)
    def test_04_source_events_per_game(self):
        self.assertEqual({id:sum(e['work_id']==id for e in self.data['story_events'])
                          for id in validator.EXPECTED_WORKS},validator.EXPECTED_EVENTS)
    def test_05_stages_not_collapsed(self):
        self.assertEqual(len(self.data['character_states']),9)
        self.assertEqual([x['state_id'] for x in self.data['character_states']],
                         [f'TR-ARC-{n:02d}' for n in range(1,10)])
    def test_06_links_cross_game_not_same_game(self):
        events={e['event_id']:e for e in self.data['story_events']}
        self.assertEqual(len(self.data['cross_work_links']),10)
        self.assertTrue(all(events[x['from_event_id']]['work_id']!=events[x['to_event_id']]['work_id']
                            for x in self.data['cross_work_links']))
    def test_07_independent_timeline_firewall(self):
        self.assertEqual({w['continuity'] for w in self.data['works']},{'SURVIVOR_TRILOGY'})
    def test_08_definitive_not_duplicate(self):
        self.assertEqual(len(self.data['supplementary_releases']),3)
        self.assertTrue(all(x['work_id'] in validator.EXPECTED_WORKS for x in self.data['supplementary_releases']))
    def test_09_18_distinct_mechanics(self):
        self.assertEqual([x['mechanic_id'] for x in self.data['mechanics']],
                         [f'TRS-{i:03d}' for i in range(1,19)])
    def test_10_59_evidence_links(self):
        self.assertEqual(len(self.data['mechanic_evidence']),59)
        self.assertEqual(len({e['evidence_id'] for e in self.data['mechanic_evidence']}),59)
    def test_11_46_cross_corpus_links(self):
        self.assertEqual(len(self.data['prior_links']),46)
        self.assertEqual({x['prior_version'] for x in self.data['prior_links']},{'0.3','0.4'})
    def test_12_quality_and_payment_zero(self):
        self.assertEqual(self.result['story_quality_trials'],0)
        self.assertEqual(self.result['new_paid_api_calls'],0)
        self.assertFalse(validator.read('quality_evaluations'))
        self.assertFalse(validator.read('lumi_usage_history'))
    def test_13_canonical_hash(self):
        meta=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(meta['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_14_deterministic_compilation(self):
        paths=[builder.BASE/(k+'.jsonl') for k in validator.EXPECTED]
        hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        builder.build()
        self.assertEqual(hashes,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
    def test_15_foreign_keys(self):
        with tempfile.TemporaryDirectory() as d:
            report=sqlite_builder.build(Path(d)/'tr_survivor.sqlite')
            self.assertEqual(report['status'],'PASS')
            self.assertEqual(report['foreign_key_violations'],0)
            self.assertEqual(report['counts']['events'],37)
    def _mutate(self,table,mutation):
        orig=validator.read
        def changed(name):
            value=copy.deepcopy(orig(name))
            if name==table:mutation(value)
            return value
        with mock.patch.object(validator,'read',side_effect=changed):
            return validator.validate()
    def test_16_missing_event_source_fails(self):
        report=self._mutate('story_events',lambda x:x[0].update(source_ids=['FAKE-SRC']))
        self.assertEqual(report['status'],'FAIL')
    def test_17_wrong_source_work_fails(self):
        report=self._mutate('story_events',lambda x:x[0].update(work_id='SHADOW2018'))
        self.assertEqual(report['status'],'FAIL')
    def test_18_cross_game_backwards_fails(self):
        report=self._mutate('cross_work_links',lambda x:x[0].update(from_event_id='S18-13',to_event_id='T13-01'))
        self.assertEqual(report['status'],'FAIL')
    def test_19_false_certainty_fails(self):
        report=self._mutate('story_events',lambda x:x[0].update(confidence='independently_gameplay_verified'))
        self.assertEqual(report['status'],'FAIL')
    def test_20_false_mechanic_quality_fails(self):
        report=self._mutate('mechanics',lambda x:x[0].update(quality_effect='proven'))
        self.assertEqual(report['status'],'FAIL')
    def test_21_bad_evidence_work_fails(self):
        report=self._mutate('mechanic_evidence',lambda x:x[0].update(work_id='RISE2015' if x[0]['work_id']!='RISE2015' else 'TR2013'))
        self.assertEqual(report['status'],'FAIL')
    def test_22_bad_character_arc_fails(self):
        report=self._mutate('character_states',lambda x:x[0].update(anchor_event_id='S18-13'))
        self.assertEqual(report['status'],'FAIL')
    def test_23_wrong_previous_version_fails(self):
        report=self._mutate('prior_links',lambda x:x[0].update(prior_version='0.1'))
        self.assertEqual(report['status'],'FAIL')
    def test_24_canonical_sources_unchanged_prior(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        import validate_prototype as v04
        self.assertEqual(v01.validate()['status'],'PASS')
        self.assertEqual(v02.check()['status'],'PASS')
        self.assertEqual(v03.validate()['status'],'PASS')
        self.assertEqual(v04.check()['status'],'PASS')
    def test_25_no_story_quality_evaluation(self):
        report=self._mutate('quality_evaluations',lambda x:x.append({'fabricated':'pass'}))
        self.assertEqual(report['status'],'FAIL')
    def test_26_specific_known_source_examples(self):
        ev={x['event_id']:x for x in self.data['story_events']}
        self.assertIn('TR-SHADOW-MOMENTS',ev['S18-02']['source_ids'])
        self.assertIn('TR-RISE-DIVINE',ev['R15-12']['source_ids'])
        self.assertIn('TR-2013-ROTH',ev['T13-08']['source_ids'])
if __name__=='__main__':unittest.main(verbosity=2)
