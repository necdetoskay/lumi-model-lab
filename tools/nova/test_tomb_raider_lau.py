#!/usr/bin/env python3
"""v0.7 LAU offline structural regressions with negative/mutation cases."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_tomb_raider_lau as builder
import validate_tomb_raider_lau as v
import sqlite_tomb_raider_lau as sql
class LAUTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data={k:v.rows(k) for k in v.TABLES}
        cls.report=v.validate()
    def test_01_validator_green(self):
        self.assertEqual(self.report['status'],'PASS',self.report.get('errors'))
    def test_02_three_works(self):
        self.assertEqual(tuple(x['work_id'] for x in self.data['works']),v.WORK_IDS)
    def test_03_17_official_sources(self):
        self.assertEqual(len(self.data['sources']),17)
        self.assertEqual(len({x['source_id'] for x in self.data['sources']}),17)
    def test_04_correct_release_order(self):
        self.assertEqual([x['release_year'] for x in self.data['works']],[2006,2007,2008])
    def test_05_story_order_is_different(self):
        x={r['work_id']:r for r in self.data['narrative_chronology']}
        self.assertEqual([x[k]['story_rank'] for k in ('ANN2007','LEG2006','UND2008')],[1,2,3])
    def test_06_36_events_per_work(self):
        self.assertEqual(len(self.data['story_events']),36)
        self.assertEqual({w['work_id']:sum(e['work_id']==w['work_id'] for e in self.data['story_events']) for w in self.data['works']},
            {x:12 for x in v.WORK_IDS})
    def test_07_childhood_and_previous_history_separated(self):
        ev={e['event_id']:e for e in self.data['story_events']}
        self.assertEqual(ev['L06-01']['event_type'],'personal_backstory')
        self.assertEqual(ev['L06-04']['event_type'],'revealed_past')
        self.assertEqual(ev['U08-01']['event_type'],'narrative_presentation_frame')
    def test_08_seven_independent_artifacts(self):
        self.assertEqual(len(self.data['artifacts']),7)
    def test_09_mjolnir_prerequisite_edges(self):
        self.assertEqual({(x['from_event_id'],x['to_event_id']) for x in self.data['narrative_links'] if x['link_type']=='prerequisite'},
             {('U08-02','U08-07'),('U08-03','U08-07'),('U08-06','U08-07'),('U08-07','U08-12')})
    def test_10_18_new_mechanics(self):
        self.assertEqual([x['mechanic_id'] for x in self.data['mechanics']],[f'LAU-{i:03d}' for i in range(1,19)])
    def test_11_50_evidence_links(self):
        self.assertEqual(len(self.data['mechanic_evidence']),50)
    def test_12_36_links_to_prior_research(self):
        self.assertEqual(len(self.data['prior_links']),36)
    def test_13_remake_never_equated_with_classic_canon(self):
        self.assertEqual(len(self.data['remake_analogues']),5)
        self.assertTrue(all(x['link_type']=='remake_analogue_not_same_event_or_canon' for x in self.data['remake_analogues']))
    def test_14_six_editorial_boundaries(self):
        self.assertEqual(len(self.data['editorial_boundaries']),6)
    def test_15_zero_story_evaluations(self):
        self.assertFalse(v.rows('quality_evaluations'))
        self.assertFalse(v.rows('lumi_usage_history'))
        self.assertEqual(self.report['new_paid_model_calls'],0)
    def test_16_source_sha_matches(self):
        m=json.loads((builder.BASE/'manifest.json').read_text(encoding='utf8'))
        self.assertEqual(m['source_sha256'],hashlib.sha256(builder.SRC.read_bytes()).hexdigest())
    def test_17_rebuild_deterministic(self):
        paths=[builder.BASE/(n+'.jsonl') for n in v.TABLES]
        before=[hashlib.sha256(x.read_bytes()).hexdigest() for x in paths]
        builder.build()
        self.assertEqual(before,[hashlib.sha256(x.read_bytes()).hexdigest() for x in paths])
    def test_18_sqlite_fk_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            result=sql.build(Path(directory)/'tr_lau.sqlite')
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(result['foreign_key_violations'],0)
            self.assertEqual(result['counts']['classic_events'],36)
    def test_19_prior_corpus_validators(self):
        import validate as v01
        import validate_cross_media as v02
        import validate_prince_of_persia as v03
        import validate_prototype as v04
        import validate_tomb_raider as v05
        import validate_tomb_raider_classic as v06
        self.assertEqual(v01.validate()['status'],'PASS')
        self.assertEqual(v02.check()['status'],'PASS')
        self.assertEqual(v03.validate()['status'],'PASS')
        self.assertEqual(v04.check()['status'],'PASS')
        self.assertEqual(v05.validate()['status'],'PASS')
        self.assertEqual(v06.validate()['status'],'PASS')
    def mutation(self,table,mutator):
        original=v.rows
        def patched(name):
            out=copy.deepcopy(original(name))
            if name==table:mutator(out)
            return out
        with mock.patch.object(v,'rows',side_effect=patched):
            return v.validate()
    def test_20_wrong_story_rank_fails(self):
        self.assertEqual(self.mutation('narrative_chronology',lambda x:x[1].update(story_rank=3))['status'],'FAIL')
    def test_21_fake_source_fails(self):
        self.assertEqual(self.mutation('story_events',lambda x:x[0].update(source_ids=['UNKNOWN']))['status'],'FAIL')
    def test_22_wrong_remake_canon_fails(self):
        self.assertEqual(self.mutation('remake_analogues',lambda x:x[0].update(link_type='same_event_same_canon'))['status'],'FAIL')
    def test_23_missing_second_gauntlet_fails(self):
        self.assertEqual(self.mutation('narrative_links',lambda x:x.remove(next(y for y in x if y['from_event_id']=='U08-03' and y['to_event_id']=='U08-07')))['status'],'FAIL')
    def test_24_wrong_narrative_type_fails(self):
        self.assertEqual(self.mutation('story_events',lambda x:x[24].update(event_type='main_plot'))['status'],'FAIL')
    def test_25_false_story_quality_fails(self):
        self.assertEqual(self.mutation('mechanics',lambda x:x[0].update(quality_effect='proven'))['status'],'FAIL')
    def test_26_fabricated_evaluation_fails(self):
        self.assertEqual(self.mutation('quality_evaluations',lambda x:x.append({'fake':'pass'}))['status'],'FAIL')
    def test_27_wrong_artifact_owner_fails(self):
        self.assertEqual(self.mutation('artifacts',lambda x:x[0].update(primary_work_id='TR96'))['status'],'FAIL')
    def test_28_duplicate_event_fails(self):
        self.assertEqual(self.mutation('story_events',lambda x:x.append(copy.deepcopy(x[0])))['status'],'FAIL')
    def test_29_conceptual_link_as_fact_fails(self):
        self.assertEqual(self.mutation('narrative_links',lambda x:next(y for y in x if y['link_type']=='thematic_parallel').update(inference=False))['status'],'FAIL')
    def test_30_misassigned_evidence_source_fails(self):
        self.assertEqual(self.mutation('mechanic_evidence',lambda x:x[0].update(source_ids=['LAU-GUIDE']))['status'],'FAIL')
if __name__=='__main__':
    unittest.main(verbosity=2)
