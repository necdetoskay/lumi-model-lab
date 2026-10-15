#!/usr/bin/env python3
"""v0.9 research-only integrity / negative injection suite (no model or story trials)."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_prototype_comics as builder
import validate_prototype_comics as v
import sqlite_prototype_comics as sqlite

class ComicResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={k:v.rows(k) for k in v.TABLES}
        cls.result=v.validate()
    def test_01_valid(self):
        self.assertEqual(self.result['status'],'PASS',self.result.get('errors'))
    def test_02_three_stories_not_six(self):
        self.assertEqual([x['work_id'] for x in self.data['works']],list(v.ARC_IDS))
    def test_03_six_issues(self):
        self.assertEqual([x['issue_id'] for x in self.data['issues']],[f'PC-ISS-{i:02d}' for i in range(1,7)])
    def test_04_two_parts_per_arc(self):
        for arc in v.ARC_IDS:
            self.assertEqual([x['part_number'] for x in self.data['issues'] if x['arc_id']==arc],[1,2])
    def test_05_issue_dates_unknown(self):
        self.assertTrue(all(x['exact_on_sale_date'] is None for x in self.data['issues']))
    def test_06_bibliographic_edition_not_new_story(self):
        canonical=json.loads(builder.SRC.read_text(encoding='utf8'))
        self.assertEqual(canonical['collection']['page_count'],80)
        self.assertFalse(canonical['collection']['is_independent_story'])
        self.assertEqual(canonical['collection']['isbn13'],'9781595829184')
    def test_07_source_types_are_distinct(self):
        s={x['source_id']:x for x in self.data['sources']}
        self.assertEqual(s['PC-PUBLISHER']['evidence_tier'],'primary_publisher')
        self.assertEqual(s['PC-STEAM-REPOST']['evidence_tier'],'community_republication')
    def test_08_twelve_observations(self):
        self.assertEqual(len(self.data['story_observations']),12)
    def test_09_observations_not_publisher_verified_panels(self):
        self.assertTrue(all(not x['is_publisher_confirmed_story_detail'] for x in self.data['story_observations']))
    def test_10_four_unverified_claims_quarantined(self):
        self.assertEqual(len(self.data['unverified_candidate_claims']),4)
        self.assertTrue(all(x['exclude_from_mechanic_evidence'] for x in self.data['unverified_candidate_claims']))
    def test_11_twelve_mechanic_hypotheses(self):
        self.assertEqual([m['mechanic_id'] for m in self.data['mechanics']],
                         [f'PCM-{i:03d}' for i in range(1,13)])
    def test_12_33_evidences(self):
        self.assertEqual(len(self.data['mechanic_evidence']),33)
        self.assertEqual(len({x['evidence_id'] for x in self.data['mechanic_evidence']}),33)
    def test_13_25_prior_links(self):
        self.assertEqual(len(self.data['mechanic_prior_links']),25)
    def test_14_5_prior_game_links(self):
        self.assertEqual(len(self.data['prior_game_links']),5)
    def test_15_zero_paid_and_story(self):
        self.assertEqual(self.result['paid_model_calls'],0)
        self.assertEqual(self.result['story_quality_trials'],0)
        self.assertEqual(self.result['primary_comic_panels_examined'],0)
        self.assertFalse(v.rows('quality_evaluations'))
        self.assertFalse(v.rows('lumi_usage_history'))
    def test_16_source_sha256(self):
        meta=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(meta['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_17_deterministic_rebuild(self):
        paths=[builder.BASE/(k+'.jsonl') for k in v.TABLES]
        before=[hashlib.sha256(x.read_bytes()).hexdigest() for x in paths]
        builder.build()
        self.assertEqual(before,[hashlib.sha256(x.read_bytes()).hexdigest() for x in paths])
    def test_18_sqlite_foreign_keys(self):
        with tempfile.TemporaryDirectory() as d:
            result=sqlite.build(Path(d)/'comic.sqlite')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['foreign_key_violations'],0)
            self.assertEqual(result['counts']['collection_issues'],6)
    def test_19_prior_corpora_pass(self):
        import validate as sg
        import validate_cross_media as cross
        import validate_prince_of_persia as pop
        import validate_prototype as pt
        import validate_tomb_raider as survivor
        import validate_tomb_raider_classic as classic
        import validate_tomb_raider_lau as lau
        import validate_prototype2 as pt2
        self.assertEqual(sg.validate()['status'],'PASS')
        self.assertEqual(cross.check()['status'],'PASS')
        self.assertEqual(pop.validate()['status'],'PASS')
        self.assertEqual(pt.check()['status'],'PASS')
        self.assertEqual(survivor.validate()['status'],'PASS')
        self.assertEqual(classic.validate()['status'],'PASS')
        self.assertEqual(lau.validate()['status'],'PASS')
        self.assertEqual(pt2.validate()['status'],'PASS')
    def mutate(self,table,change):
        original=v.rows
        def swapped(name):
            data=copy.deepcopy(original(name))
            if name==table:change(data)
            return data
        with mock.patch.object(v,'rows',side_effect=swapped):
            return v.validate()
    def test_20_fabricated_issue_date_fails(self):
        self.assertEqual(self.mutate('issues',lambda a:a[0].update(exact_on_sale_date='2012-02-15'))['status'],'FAIL')
    def test_21_promotional_claim_as_panel_audit_fails(self):
        self.assertEqual(self.mutate('story_observations',lambda a:a[0].update(is_publisher_confirmed_story_detail=True))['status'],'FAIL')
    def test_22_fan_claim_promoted_fails(self):
        self.assertEqual(self.mutate('unverified_candidate_claims',lambda a:a[0].update(exclude_from_mechanic_evidence=False))['status'],'FAIL')
    def test_23_community_source_promoted_fails(self):
        self.assertEqual(self.mutate('sources',lambda a:next(s for s in a if s['source_id']=='PC-STEAM-REPOST').update(evidence_tier='primary_publisher'))['status'],'FAIL')
    def test_24_seventh_independent_story_fails(self):
        self.assertEqual(self.mutate('works',lambda a:a.append({**copy.deepcopy(a[0]),'work_id':'COMIC-COLLECTOR'}))['status'],'FAIL')
    def test_25_bad_issue_arc_fails(self):
        self.assertEqual(self.mutate('issues',lambda a:a[0].update(arc_id='OTHER-WORLD'))['status'],'FAIL')
    def test_26_bad_source_observation_fails(self):
        self.assertEqual(self.mutate('story_observations',lambda a:a[0].update(source_ids=['PC-COMICS-WIKI']))['status'],'FAIL')
    def test_27_wrong_episode_mechanic_link_fails(self):
        self.assertEqual(self.mutate('mechanic_evidence',lambda a:a[0].update(issue_id='PC-ISS-06'))['status'],'FAIL')
    def test_28_fake_story_quality_fails(self):
        self.assertEqual(self.mutate('mechanics',lambda a:a[0].update(quality_effect='proven'))['status'],'FAIL')
    def test_29_bad_prior_mechanic_fails(self):
        self.assertEqual(self.mutate('mechanic_prior_links',lambda a:a[0].update(prior_mechanic_id='FAKE-000'))['status'],'FAIL')
    def test_30_fake_quality_evaluation_fails(self):
        self.assertEqual(self.mutate('quality_evaluations',lambda a:a.append({'fake':'pass'}))['status'],'FAIL')
    def test_31_faked_cross_game_causality_fails(self):
        self.assertEqual(self.mutate('prior_game_links',
           lambda a:next(x for x in a if x['kind']=='research_question_not_proven_causality').update(inference=False))['status'],'FAIL')
    def test_32_absent_primary_pages_not_reported_as_read(self):
        self.assertTrue(all(not x['actual_panels_examined'] for x in self.data['issues']))
if __name__=='__main__':unittest.main(verbosity=2)
