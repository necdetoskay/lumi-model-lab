#!/usr/bin/env python3
"""Classic v0.6 source-only regression and mutation tests: no paid calls."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_tomb_raider_classic as b
import validate_tomb_raider_classic as v
import sqlite_tomb_raider_classic as sql

class ClassicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={k:v.records(k) for k in v.TABLES}
        cls.report=v.validate()
    def test_01_validator(self):
        self.assertEqual(self.report['status'],'PASS',self.report['errors'])
    def test_02_six_work_eras(self):
        self.assertEqual(tuple(x['work_id'] for x in self.data['works']),v.IDS)
        self.assertEqual([x['year'] for x in self.data['works']],[1996,1997,1998,1999,2000,2003])
    def test_03_21_official_sources(self):
        self.assertEqual(len(self.data['sources']),21)
        self.assertTrue(all(s['url'].startswith('https://www.tombraider.com/') for s in self.data['sources']))
    def test_04_36_beats(self):
        self.assertEqual(len(self.data['story_events']),36)
        self.assertEqual(len({x['event_id'] for x in self.data['story_events']}),36)
    def test_05_19_distinct_mechanics(self):
        self.assertEqual([x['mechanic_id'] for x in self.data['mechanics']],
             [f'TRC-{i:03d}' for i in range(1,20)])
    def test_06_evidence_count(self):
        self.assertEqual(len(self.data['mechanic_evidence']),54)
        self.assertEqual(len({x['evidence_id'] for x in self.data['mechanic_evidence']}),54)
    def test_07_prior_link_count(self):
        self.assertEqual(len(self.data['prior_links']),38)
        self.assertEqual({x['prior_version'] for x in self.data['prior_links']},{'0.5','prior'})
    def test_08_memorial_not_original_chronology(self):
        events={x['event_id']:x for x in self.data['story_events']}
        self.assertEqual(events['C00-01']['narrated_time_type'],'memorial_present')
        self.assertEqual(events['C00-03']['narrated_time_type'],'recalled_childhood')
        self.assertEqual(events['C99-01']['narrated_time_type'],'flashback_young_lara')
    def test_09_cut_content_not_canon(self):
        e=next(x for x in self.data['story_events'] if x['event_id']=='C03-06')
        self.assertEqual(e['claim_kind'],'development_plan_not_game_canon')
        self.assertEqual(e['narrated_time_type'],'development_history')
    def test_10_remasters_not_main_works(self):
        self.assertEqual(len(self.data['supplementary_releases']),3)
        self.assertTrue(all('REMASTERED' in x['release_id'] or 'BONUS' in x['release_id']
             for x in self.data['supplementary_releases']))
    def test_11_10_typed_narrative_links(self):
        self.assertEqual(len(self.data['narrative_links']),10)
        self.assertTrue(all(x['claim_scope']=='compare_narration_and_history_not_directed_game_chronology'
            for x in self.data['narrative_links']))
    def test_12_canonical_manifest_sha(self):
        m=json.loads((b.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(m['source_sha256'],hashlib.sha256(b.SRC.read_bytes()).hexdigest())
    def test_13_compiler_deterministic(self):
        files=[b.BASE/(x+'.jsonl') for x in v.TABLES]
        original=[hashlib.sha256(x.read_bytes()).hexdigest() for x in files]
        b.build()
        self.assertEqual(original,[hashlib.sha256(x.read_bytes()).hexdigest() for x in files])
    def test_14_zero_paid_calls_and_evaluations(self):
        self.assertFalse(v.records('quality_evaluations'))
        self.assertFalse(v.records('lumi_usage_history'))
        self.assertEqual(self.report['paid_calls'],0)
        self.assertEqual(self.report['story_quality_trials'],0)
    def test_15_sqlite_foreign_keys(self):
        with tempfile.TemporaryDirectory() as d:
            report=sql.build(Path(d)/'classic.sqlite')
            self.assertEqual(report['status'],'PASS')
            self.assertEqual(report['foreign_key_violations'],0)
            self.assertEqual(report['counts']['evidence'],54)
    def change(self,table,mutation):
        r=v.records
        def read(name):
            current=copy.deepcopy(r(name))
            if name==table:mutation(current)
            return current
        with mock.patch.object(v,'records',side_effect=read):
            return v.validate()
    def test_16_bad_source_fails(self):
        self.assertEqual(self.change('story_events',lambda rows:rows[0].update(source_ids=['UNKNOWN']))['status'],'FAIL')
    def test_17_cross_continuity_work_fails(self):
        self.assertEqual(self.change('works',lambda rows:rows[0].update(continuity='SURVIVOR_TRILOGY'))['status'],'FAIL')
    def test_18_false_gameplay_verified_fails(self):
        self.assertEqual(self.change('story_events',lambda rows:rows[0].update(evidence_strength='independently_verified'))['status'],'FAIL')
    def test_19_wrong_childhood_time_fails(self):
        self.assertEqual(self.change('story_events',lambda rows:rows[26].update(narrated_time_type='memorial_present'))['status'],'FAIL')
    def test_20_cut_plan_as_game_event_fails(self):
        self.assertEqual(self.change('story_events',lambda rows:rows[-1].update(claim_kind='observed_game_story'))['status'],'FAIL')
    def test_21_false_causal_inference_fails(self):
        self.assertEqual(self.change('narrative_links',lambda rows:rows[2].update(inference=False))['status'],'FAIL')
    def test_22_wrong_evidence_work_fails(self):
        self.assertEqual(self.change('mechanic_evidence',lambda rows:rows[0].update(work_id='TR03'))['status'],'FAIL')
    def test_23_false_quality_proof_fails(self):
        self.assertEqual(self.change('mechanics',lambda rows:rows[0].update(quality_effect='proven'))['status'],'FAIL')
    def test_24_orphan_prior_fails(self):
        self.assertEqual(self.change('prior_links',lambda rows:rows.pop())['status'],'FAIL')
    def test_25_fabricated_quality_run_fails(self):
        self.assertEqual(self.change('quality_evaluations',lambda rows:rows.append({'fake':'pass'}))['status'],'FAIL')
    def test_26_previous_all_regression_pass(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        import validate_prototype as v04
        import validate_tomb_raider as v05
        self.assertEqual(v01.validate()['status'],'PASS')
        self.assertEqual(v02.check()['status'],'PASS')
        self.assertEqual(v03.validate()['status'],'PASS')
        self.assertEqual(v04.check()['status'],'PASS')
        self.assertEqual(v05.validate()['status'],'PASS')
if __name__=='__main__':unittest.main(verbosity=2)
