#!/usr/bin/env python3
"""v0.12 offline source and graph validation with deliberate corruptions."""
import copy,hashlib,json,tempfile,unittest
from pathlib import Path
from unittest import mock
import build_bioshock_infinite as build
import validate_bioshock_infinite as v
import sqlite_bioshock_infinite as sql

class BioShockInfiniteTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.d={k:v.rows(k) for k in v.EXPECTED}
  cls.status=v.validate()
 def test_01_pass(self):self.assertEqual(self.status['status'],'PASS',self.status.get('errors'))
 def test_02_one_2013_game(self):
  self.assertEqual(self.d['works'][0]['release_year'],2013)
 def test_03_17_sources(self):self.assertEqual(len(self.d['sources']),17)
 def test_04_33_events(self):
  self.assertEqual([e['event_id'] for e in self.d['story_events']],[f'BI-E{i:02d}' for i in range(1,34)])
 def test_05_7_worlds(self):self.assertEqual(len(self.d['world_variants']),7)
 def test_06_chens_different_worlds(self):
  e={x['event_id']:x for x in self.d['story_events']}
  self.assertNotEqual(e['BI-E18']['world_scope'],e['BI-E19']['world_scope'])
 def test_07_10_identities(self):self.assertEqual(len(self.d['identity_variants']),10)
 def test_08_booker_comstock_distinct(self):
  ids={x['identity_id']:x for x in self.d['identity_variants']}
  self.assertNotEqual(ids['IDENT-BOOKER']['identity_rule'],ids['IDENT-COMSTOCK']['identity_rule'])
 def test_09_elizabeth_anna_same_person_renamed(self):
  ids={x['identity_id']:x for x in self.d['identity_variants']}
  self.assertEqual(ids['IDENT-ELIZABETH']['identity_rule'],'renamed_anna_not_clone')
 def test_10_not_literal_lutece_twins(self):
  self.assertTrue(all('not_literal_twin' in x['identity_rule'] for x in self.d['identity_variants'] if x['identity_id'] in ('IDENT-ROBERT','IDENT-ROSALIND')))
 def test_11_9_knowledge_states(self):self.assertEqual(len(self.d['knowledge_states']),9)
 def test_12_6_choices(self):self.assertEqual(len(self.d['player_choice_scopes']),6)
 def test_13_tactical_tear_not_world_move(self):
  x={x['choice_id']:x for x in self.d['player_choice_scopes']}
  self.assertEqual(x['COMBAT-TEAR']['branch_type'],'no_world_story_auto_transition')
 def test_14_cosmetic_necklace_not_new_end(self):
  x={x['choice_id']:x for x in self.d['player_choice_scopes']}
  self.assertEqual(x['PLAYER-NECKLACE']['branch_type'],'no_major_story_branch')
 def test_15_20_mechanics(self):
  self.assertEqual([x['mechanic_id'] for x in self.d['mechanics']],[f'BIM-{i:03d}' for i in range(1,21)])
 def test_16_60_evidence_edges(self):self.assertEqual(len(self.d['mechanic_evidence']),60)
 def test_17_41_links_to_old_mechanics(self):self.assertEqual(len(self.d['prior_mechanic_links']),41)
 def test_18_8_cross_bioshock_links(self):self.assertEqual(len(self.d['prior_bioshock_links']),8)
 def test_19_10_editorial_boundaries(self):self.assertEqual(len(self.d['editorial_boundaries']),10)
 def test_20_19_typed_event_transitions(self):self.assertEqual(len(self.d['narrative_links']),19)
 def test_21_no_fake_evaluation(self):
  self.assertEqual(self.status['story_quality_trials'],0)
  self.assertEqual(self.status['paid_model_calls'],0)
  self.assertEqual(v.rows('quality_evaluations'),[])
 def test_22_source_sha(self):
  m=json.loads((build.BASE/'manifest.json').read_text(encoding='utf8'))
  self.assertEqual(m['source_sha256'],hashlib.sha256(build.SRC.read_bytes()).hexdigest())
 def test_23_build_deterministic(self):
  paths=[build.BASE/(k+'.jsonl') for k in v.TABLES]
  before=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
  build.build()
  self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
 def test_24_sqlite_fk(self):
  with tempfile.TemporaryDirectory() as d:
   r=sql.build(Path(d)/'bi.sqlite')
   self.assertEqual(r['status'],'PASS')
   self.assertEqual(r['foreign_key_violations'],0)
   self.assertEqual(r['counts']['previous_mechanics'],149)
 def test_25_previous_versions_validate(self):
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
 def mutate(self,table,fn):
  prior=v.rows
  def patched(key):
   records=copy.deepcopy(prior(key))
   if key==table:fn(records)
   return records
  with mock.patch.object(v,'rows',side_effect=patched):
   return v.validate()
 def test_26_impossible_world_merge_fails(self):
  self.assertEqual(self.mutate('story_events',lambda x:x[18].update(world_scope='COLUMBIA_A'))['status'],'FAIL')
 def test_27_chens_resurrection_claim_fails(self):
  self.assertEqual(self.mutate('identity_variants',lambda x:next(y for y in x if y['identity_id']=='IDENT-CHEN-B').update(identity_rule='same_dead_body_resurrected'))['status'],'FAIL')
 def test_28_same_booker_comstock_body_fails(self):
  self.assertEqual(self.mutate('identity_variants',lambda x:next(y for y in x if y['identity_id']=='IDENT-COMSTOCK').update(identity_rule='single_body_booker'))['status'],'FAIL')
 def test_29_anna_elizabeth_clone_fails(self):
  self.assertEqual(self.mutate('identity_variants',lambda x:next(y for y in x if y['identity_id']=='IDENT-ELIZABETH').update(identity_rule='completely_unrelated_child'))['status'],'FAIL')
 def test_30_lutece_twins_fails(self):
  self.assertEqual(self.mutate('identity_variants',lambda x:next(y for y in x if y['identity_id']=='IDENT-ROBERT').update(identity_rule='biological_twin'))['status'],'FAIL')
 def test_31_world_sequence_broken_fails(self):
  self.assertEqual(self.mutate('narrative_links',lambda x:next(y for y in x if y['link_type']=='tear_world_switch').update(to_event_id='BI-E10'))['status'],'FAIL')
 def test_32_necklace_as_new_final_fails(self):
  self.assertEqual(self.mutate('player_choice_scopes',lambda x:next(y for y in x if y['choice_id']=='PLAYER-NECKLACE').update(branch_type='different_main_ending'))['status'],'FAIL')
 def test_33_combat_tear_as_full_world_fails(self):
  self.assertEqual(self.mutate('player_choice_scopes',lambda x:next(y for y in x if y['choice_id']=='COMBAT-TEAR').update(branch_type='full_world_migration'))['status'],'FAIL')
 def test_34_baptism_as_player_menu_fails(self):
  self.assertEqual(self.mutate('player_choice_scopes',lambda x:next(y for y in x if y['choice_id']=='STORY-BAPTISM').update(branch_type='user_ui_choice'))['status'],'FAIL')
 def test_35_missing_event_source_fails(self):
  self.assertEqual(self.mutate('story_events',lambda x:x[0].update(source_ids=['UNKNOWN']))['status'],'FAIL')
 def test_36_claim_fake_firsthand_fails(self):
  self.assertEqual(self.mutate('sources',lambda x:x[0].update(independent_original_gameplay_capture=True))['status'],'FAIL')
 def test_37_false_quality_fails(self):
  self.assertEqual(self.mutate('mechanics',lambda x:x[0].update(quality_effect='proven'))['status'],'FAIL')
 def test_38_fake_trial_fails(self):
  self.assertEqual(self.mutate('quality_evaluations',lambda x:x.append({'fake':'PASS'}))['status'],'FAIL')
 def test_39_unverified_postcredit_as_known_fails(self):
  self.assertEqual(self.mutate('knowledge_states',lambda x:next(y for y in x if y['knowledge_id']=='K-POST').update(actual_or_limited_truth='All universes have Anna'))['status'],'FAIL')
 def test_40_world_evidence_wrong_fails(self):
  self.assertEqual(self.mutate('mechanic_evidence',lambda x:x[0].update(world_scope='COLUMBIA_B'))['status'],'FAIL')
if __name__=='__main__':unittest.main(verbosity=2)
