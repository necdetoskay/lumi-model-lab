#!/usr/bin/env python3
"""NOVA v0.13 offline determinism/negative mutation/regression tests."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_burial_at_sea as build
import validate_burial_at_sea as v
import sqlite_burial_at_sea as sql
class BurialResearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data={k:v.rows(k) for k in v.EXPECTED}
  cls.report=v.validate()
 def test_01_pass(self):self.assertEqual(self.report['status'],'PASS',self.report.get('errors'))
 def test_02_distinct_episodes(self):self.assertEqual([w['work_id'] for w in self.data['works']],['BAS1','BAS2'])
 def test_03_release_dates(self):self.assertEqual([w['release_date'] for w in self.data['works']],['2013-11-12','2014-03-25'])
 def test_04_source_count(self):self.assertEqual(len(self.data['sources']),14)
 def test_05_event_count(self):self.assertEqual(len(self.data['story_events']),28)
 def test_06_e1_13_events(self):self.assertEqual(sum(x['work_id']=='BAS1' for x in self.data['story_events']),13)
 def test_07_e2_15_events(self):self.assertEqual(sum(x['work_id']=='BAS2' for x in self.data['story_events']),15)
 def test_08_mechanics(self):self.assertEqual(len(self.data['mechanics']),16)
 def test_09_43_evidence(self):self.assertEqual(len(self.data['mechanic_evidence']),43)
 def test_10_32_prior_links(self):self.assertEqual(len(self.data['prior_mechanic_links']),32)
 def test_11_10_belief_states(self):self.assertEqual(len(self.data['knowledge_states']),10)
 def test_12_15_narrative_links(self):self.assertEqual(len(self.data['narrative_links']),15)
 def test_13_8_cross_game_links(self):self.assertEqual(len(self.data['cross_game_links']),8)
 def test_14_16_boundaries(self):self.assertEqual(len(self.data['editorial_boundaries']),16)
 def test_15_no_fake_quality(self):
  self.assertEqual(self.report['story_quality_trials'],0)
  self.assertEqual(v.rows('quality_evaluations'),[])
 def test_16_no_fake_paid(self):self.assertEqual(self.report['paid_calls'],0)
 def test_17_source_sha(self):
  manifest=json.loads((build.BASE/'manifest.json').read_text(encoding='utf8'))
  self.assertEqual(manifest['source_sha256'],hashlib.sha256(build.SRC.read_bytes()).hexdigest())
 def test_18_determinism(self):
  files=[build.BASE/(k+'.jsonl') for k in v.TABLES]
  before=[hashlib.sha256(f.read_bytes()).hexdigest() for f in files]
  build.build()
  self.assertEqual(before,[hashlib.sha256(f.read_bytes()).hexdigest() for f in files])
 def test_19_sqlite(self):
  with tempfile.TemporaryDirectory() as folder:
   result=sql.build(Path(folder)/'test.sqlite')
   self.assertEqual(result['status'],'PASS',result)
   self.assertEqual(result['foreign_key_violations'],0)
 def test_20_previous_versions(self):
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
  import validate_bioshock2 as k
  import validate_bioshock_infinite as l
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
  self.assertEqual(k.validate()['status'],'PASS')
  self.assertEqual(l.validate()['status'],'PASS')
 def test_21_booker_variant(self):
  states={x['state_id']:x for x in self.data['knowledge_states']}
  self.assertEqual(states['K-COMSTOCK']['actual_rule'],'rapture_booker_is_distinct_comstock_variant')
 def test_22_elizabeth_mortality(self):
  states={x['state_id']:x for x in self.data['knowledge_states']}
  self.assertEqual(states['K-ELIZABETH']['actual_rule'],'returned_elizabeth_mortal_without_tear_power')
 def test_23_code_is_not_future_action(self):
  states={x['state_id']:x for x in self.data['knowledge_states']}
  self.assertEqual(states['K-JACK']['actual_rule'],'separate_information_transfer_and_future_action')
 def mutate(self,key,change):
  orig=v.rows
  def replace(name):
   rows=copy.deepcopy(orig(name))
   if name==key:change(rows)
   return rows
  with mock.patch.object(v,'rows',side_effect=replace):
   return v.validate()
 def test_24_false_release_date_fails(self):
  self.assertEqual(self.mutate('works',lambda x:x[1].update(release_date='2013-11-12'))['status'],'FAIL')
 def test_25_playable_actor_merge_fails(self):
  self.assertEqual(self.mutate('works',lambda x:x[1].update(playable_character='Booker (Rapture alias Comstock variant)'))['status'],'FAIL')
 def test_26_wrong_identity_fails(self):
  self.assertEqual(self.mutate('knowledge_states',lambda x:next(a for a in x if a['state_id']=='K-COMSTOCK').update(actual_rule='base_Booker_same_body'))['status'],'FAIL')
 def test_27_anna_reanimation_fails(self):
  self.assertEqual(self.mutate('knowledge_states',lambda x:next(a for a in x if a['state_id']=='K-ANNA').update(actual_rule='Anna_resurrected'))['status'],'FAIL')
 def test_28_power_restored_without_event_fails(self):
  self.assertEqual(self.mutate('knowledge_states',lambda x:next(a for a in x if a['state_id']=='K-ELIZABETH').update(actual_rule='Elizabeth_all_powers'))['status'],'FAIL')
 def test_29_mental_guide_resurrected_fails(self):
  self.assertEqual(self.mutate('knowledge_states',lambda x:next(a for a in x if a['state_id']=='K-BOOKER-VOICE').update(actual_rule='physical_companion'))['status'],'FAIL')
 def test_30_fake_gameplay_verification_fails(self):
  self.assertEqual(self.mutate('story_events',lambda x:x[0].update(independently_played=True))['status'],'FAIL')
 def test_31_bad_source_fails(self):
  self.assertEqual(self.mutate('story_events',lambda x:x[0].update(source_ids=['FAKE']))['status'],'FAIL')
 def test_32_community_pretends_official_fails(self):
  self.assertEqual(self.mutate('sources',lambda x:next(a for a in x if a['source_id']=='BAS-WIKI-EP2').update(evidence_tier='official_release'))['status'],'FAIL')
 def test_33_fabricated_final_confidence_fails(self):
  self.assertEqual(self.mutate('story_events',lambda x:next(a for a in x if a['event_id']=='BAS2-E14').update(evidence_tier='official_and_walkthrough'))['status'],'FAIL')
 def test_34_wrong_prior_mechanic_fails(self):
  self.assertEqual(self.mutate('prior_mechanic_links',lambda x:x[0].update(prior_mechanic_id='NOTHING'))['status'],'FAIL')
 def test_35_cross_game_same_event_fails(self):
  self.assertEqual(self.mutate('cross_game_links',lambda x:x[0].update(inference=False))['status'],'FAIL')
 def test_36_missing_episode_transition_fails(self):
  self.assertEqual(self.mutate('narrative_links',lambda x:next(a for a in x if a['relation']=='episode_transition_paris').update(to_event_id='BAS1-E01'))['status'],'FAIL')
 def test_37_unproven_physical_prereq_fails(self):
  self.assertEqual(self.mutate('narrative_links',lambda x:next(a for a in x if a['kind']=='physical_prerequisite').update(inference=True))['status'],'FAIL')
 def test_38_fake_trial_fails(self):
  self.assertEqual(self.mutate('quality_evaluations',lambda x:x.append({'fake':'trial'}))['status'],'FAIL')
 def test_39_no_new_canon(self):
  self.assertTrue(all(m['lumi_canon'] is False for m in self.data['mechanics']))
 def test_40_source_boundaries(self):
  self.assertTrue(all(x['quality_effect']=='not_evaluated' for x in self.data['mechanic_evidence']))
if __name__=='__main__':unittest.main(verbosity=2)
