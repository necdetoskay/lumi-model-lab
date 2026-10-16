#!/usr/bin/env python3
"""NOVA v0.12 integrity/ontology separation validator; no story quality claims."""
import hashlib,json,sys
from build_bioshock_infinite import ROOT,BASE,SRC,DOCS,TABLES
EXPECTED={'works':1,'sources':17,'story_events':33,'world_variants':7,
 'identity_variants':10,'knowledge_states':9,'player_choice_scopes':6,'narrative_links':19,
 'mechanics':20,'prior_bioshock_links':8,'editorial_boundaries':10,
 'mechanic_evidence':60,'prior_mechanic_links':41}
REQUIRED_DOCS=('README.md','EVENTS.md','MECHANICS.md','WORLD_TIMELINES.md',
 'IDENTITY_AND_KNOWLEDGE.md','PLAYER_CHOICES.md','SOURCES.md','CONTINUITY.md')
def rows(name):
 return [json.loads(v) for v in (BASE/(name+'.jsonl')).read_text(encoding='utf8').splitlines() if v.strip()]
def validate():
 errors=[]
 def ck(ok,msg):
  if not ok:errors.append(msg)
 c=json.loads(SRC.read_text(encoding='utf8'))
 manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
 d={k:rows(k) for k in TABLES}
 for k,n in EXPECTED.items():
  ck(len(d[k])==n,f'{k}: {len(d[k])} != {n}')
  ck(manifest.get('counts',{}).get(k)==n,'manifest count drift: '+k)
  if k in c:ck(d[k]==c[k],'compiled output drift: '+k)
 ck(manifest.get('schema_version')==c.get('schema_version')=='0.12.0-source-first-pass','schema mismatch')
 ck(manifest.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'source SHA changed')
 ck(c.get('scope')=='bioshock_infinite_2013_original_base_game_no_dlc','DLC leakage')
 ck(c.get('lumi_canon') is False and c.get('quality_effect')==manifest.get('quality_effect')=='not_evaluated',
   'unproven quality or LUMI canon')
 ck(c.get('story_quality_trials')==manifest.get('story_quality_trials')==0,'fake quality trials')
 ck(c.get('paid_model_calls')==manifest.get('new_paid_model_calls')==0,'fake paid usage')
 ck(c.get('lumi_production_modified') is False and manifest.get('lumi_production_modified') is False,'prod changed')
 ck(c.get('full_original_gameplay_independently_audited') is False
   and manifest.get('full_original_gameplay_independently_audited') is False,'firsthand gameplay falsely claimed')
 ck(rows('quality_evaluations')==[] and rows('lumi_usage_history')==[],'invented runtime history')
 works=d['works']
 ck(len(works)==1 and works[0]['work_id']=='BI-2013' and works[0]['release_year']==2013
   and works[0]['media_type']=='base_game' and works[0]['continuity']=='BI_INFINITE_BASE_ONLY'
   and works[0]['original_gameplay_audited'] is False,'original work and scope')
 sources={s['source_id']:s for s in d['sources']}
 ck(len(sources)==len(d['sources']),'duplicate source')
 ck(all(s['url'].startswith('https://') and
  s['verification']=='web_search_result_retrieved_2026-10-16'
  and s['independent_original_gameplay_capture'] is False
  and s['evidence_tier'] in ('official_base_product','official_dlc_boundary','release_and_developer_metadata',
  'primary_creator_design_intent','2013_secondary_plot_interpretation','2013_player_walkthrough',
  'later_secondary_walkthrough','community_nonindependent','tertiary_synthesis')
  for s in sources.values()),'false sources or confidence promoted')
 ck(sources.get('BI-2K',{}).get('evidence_tier')=='official_base_product'
   and sources.get('BI-FORBES-LEVINE',{}).get('evidence_tier')=='primary_creator_design_intent'
   and sources.get('BI-FAN-CHOICES',{}).get('evidence_tier')=='community_nonindependent',
   'publisher, interview, community confidence conflated')
 ck(set(works[0]['source_ids'])<=set(sources),'work missing source')
 events={e['event_id']:e for e in d['story_events']}
 ck(len(events)==len(d['story_events']) and len(events)==33,'duplicate event ID')
 ck([x['event_id'] for x in d['story_events']]==[f'BI-E{i:02d}' for i in range(1,34)],
   'event ordering or source section omitted')
 ck(all(x['source_ids'] and set(x['source_ids'])<=set(sources)
   and len(x['observation_tr'])>=90 and x['event_kind']
   and x['world_scope'] and x['narrative_time']
   and x['evidence_strength']=='2013_written_game_guide_plus_relevant_sources'
   and x['firsthand_gameplay_verified'] is False
   and x['quality_effect']=='not_evaluated' and isinstance(x['claim_inference'],bool)
   for x in events.values()),'event ungrounded, source inflated, or short')
 wk={w['world_id']:w for w in d['world_variants']}
 ck(len(wk)==len(d['world_variants'])==7,'world IDs duplicate')
 ck(len({w['scope'] for w in wk.values()})==7,'distinct world scopes flattened')
 ck(all(w['first_event'] in events and w['last_event'] in events
     and w['events_are_not_merged_with_other_worlds'] is True
     and w['quality_effect']=='not_evaluated' for w in wk.values()),
     'world state collapsed')
 ck(set(w['scope'] for w in wk.values())=={
    'BOOKER_BRANCH','COMSTOCK_BRANCH','COLUMBIA_A','COLUMBIA_B','COLUMBIA_C',
    'FUTURE_VARIANT','SEA_OF_DOORS'},'missing world variant')
 ck(events['BI-E18']['world_scope']=='COLUMBIA_A' and
    events['BI-E19']['world_scope']=='COLUMBIA_B' and
    events['BI-E21']['world_scope']=='COLUMBIA_C','Chen Lin dead/alive/Vox histories collapsed')
 ck(events['BI-E02']['event_kind']=='counterfactual_branch'
    and events['BI-E25']['world_scope']=='FUTURE_VARIANT'
    and events['BI-E33']['event_kind']=='ambiguous_epilogue',
    'world-branch / future / post-credit epistemic type changed')
 identities={x['identity_id']:x for x in d['identity_variants']}
 ck(len(identities)==10,'duplicate identity')
 ck(all(x['event_refs'] and set(x['event_refs'])<=set(events)
   and x['memory_continuity_not_automatic'] is True
   and x['quality_effect']=='not_evaluated' for x in identities.values()),
   'source characters incorrectly conflated')
 expected_ids={
   'IDENT-BOOKER':'base_person_branch','IDENT-COMSTOCK':'alternative_self_from_baptism',
   'IDENT-ANNA':'same_person_renamed_after_transfer','IDENT-ELIZABETH':'renamed_anna_not_clone',
   'IDENT-OLD-ELIZABETH':'alternative_future_self_not_same_knowledge',
   'IDENT-ROBERT':'counterpart_of_rosalind_not_literal_twin',
   'IDENT-ROSALIND':'counterpart_of_robert_not_literal_twin',
   'IDENT-CHEN-A':'dead_in_this_world','IDENT-CHEN-B':'alive_in_this_world_not_resurrected',
   'IDENT-BOOKER-MARTYR':'separate_world_historical_report_not_live_player_booker'
 }
 ck(all(identities.get(x,{}).get('identity_rule')==rule for x,rule in expected_ids.items()),
   'identity boundary unexpectedly changed')
 k={x['knowledge_id']:x for x in d['knowledge_states']}
 ck(len(k)==9 and len(k)==len(d['knowledge_states']),'duplicate knowledge record')
 ck(all(x['setup_event_id'] in events and x['revealed_event_id'] in events
   and x['is_character_belief_not_world_fact'] is True
   and x['initial_claim'] and x['actual_or_limited_truth'] for x in k.values()),
   'belief erroneously world fact')
 ck(k['K-CHEN']['setup_event_id']=='BI-E18'
   and k['K-CHEN']['revealed_event_id']=='BI-E19'
   and 'not revival' in k['K-CHEN']['actual_or_limited_truth'],'Chen Lin resurrection confusion')
 ck(k['K-POST']['setup_event_id']=='BI-E33'
   and 'unresolved' in k['K-POST']['actual_or_limited_truth'],
   'post-credit unproven certainty')
 choices={x['choice_id']:x for x in d['player_choice_scopes']}
 ck(len(choices)==len(d['player_choice_scopes'])==6,'choice scopes lost')
 ck(all(x['event_ids'] and set(x['event_ids'])<=set(events)
    and x['claim_single_new_player_ending'] is False
    and x['original_gameplay_audited'] is False for x in choices.values()),
    'player choice falsely asserts extra major ending')
 ck(choices['PLAYER-NECKLACE']['branch_type']=='no_major_story_branch'
   and choices['STORY-BAPTISM']['branch_type']=='authorial_cosmology_not_runtime_ui_choice',
   'cosmetic vs cosmological choices merged')
 ck(choices['COMBAT-TEAR']['branch_type']=='no_world_story_auto_transition',
   'combat tear incorrectly treated as world migration')
 links=d['narrative_links']
 ck(len({(e['from_event_id'],e['to_event_id'],e['link_type']) for e in links})==len(links),
   'duplicate graph link')
 ck(all(x['from_event_id'] in events and x['to_event_id'] in events
   and isinstance(x['interpretive_link'],bool)
   and x['quality_effect']=='not_evaluated' for x in links),'event graph orphan')
 must={('BI-E18','BI-E19','tear_world_switch'),('BI-E20','BI-E21','tear_world_switch'),
  ('BI-E28','BI-E29','physical_prerequisite'),('BI-E02','BI-E31','retrospective_interpretation')}
 ck(must<= {(x['from_event_id'],x['to_event_id'],x['link_type']) for x in links},
   'world transitions or reveal missing')
 ck(all(x['interpretive_link'] is False for x in links if x['link_type']=='physical_prerequisite'),
   'physical prereq is speculative')
 ck(all(x['interpretive_link'] is True for x in links if x['link_type'] in
   ('retrospective_interpretation','ambiguous_epilogue','metaphysical_plot_inference')),
   'interpretation upgraded as fact')
 earlier_ids=set()
 for path in (
   'v0.3/source_records/prince_mechanics.json',
   'v0.4/source_records/prototype_2009.json',
   'v0.5/source_records/tomb_raider_survivor.json',
   'v0.6/source_records/tomb_raider_classic.json',
   'v0.7/source_records/tomb_raider_lau.json',
   'v0.8/source_records/prototype2_2012.json',
   'v0.9/source_records/prototype_comic_bridge.json',
   'v0.10/source_records/bioshock_2007.json',
   'v0.11/source_records/bioshock2_minerva_2010.json'):
  earlier_ids.update(m['mechanic_id'] for m in
    json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['mechanics'])
 mechanics=d['mechanics'];mech_ids={x['mechanic_id'] for x in mechanics}
 ck(len(mech_ids)==20 and
   [x['mechanic_id'] for x in mechanics]==[f'BIM-{i:03d}' for i in range(1,21)]
   and not (mech_ids & earlier_ids),'mechanic ID duplicate or prior overlap')
 ck(all(x['event_anchors'] and set(x['event_anchors'])<=set(events)
   and x['related_prior_mechanic_ids'] and set(x['related_prior_mechanic_ids'])<=earlier_ids
   and len(x['abstraction_tr'])>=85 and len(x['guardrail_tr'])>=65
   and x['mechanism_inference'] is True
   and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
   and x['editorial_stage']=='source_grounded_first_pass'
   and x['copyright_guardrail'] for x in mechanics),
   'mechanic incorrect confidence, no evidence, prior refs, or missing safety')
 evidence=d['mechanic_evidence']
 expected={(m['mechanic_id'],eid) for m in mechanics for eid in m['event_anchors']}
 actual={(x['mechanic_id'],x['event_id']) for x in evidence}
 ck(actual==expected and len(actual)==len(evidence),'mechanic evidence coverage/duplication')
 ck(all(x['event_id'] in events
   and x['source_ids']==events[x['event_id']]['source_ids']
   and x['world_scope']==events[x['event_id']]['world_scope']
   and x['event_kind']==events[x['event_id']]['event_kind']
   and x['evidence_strength']==events[x['event_id']]['evidence_strength']
   and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
   for x in evidence),'mechanic proof falsely promoted')
 prior=d['prior_mechanic_links']
 expectedprior={(m['mechanic_id'],x) for m in mechanics for x in m['related_prior_mechanic_ids']}
 ck(len(prior)==len(expectedprior) and
   {(x['mechanic_id'],x['prior_mechanic_id']) for x in prior}==expectedprior
   and all(x['relation']=='conceptually_related_not_equivalent' and
       x['quality_effect']=='not_evaluated' for x in prior),
   'wrong prior candidate equivalence')
 prior_ev=set()
 for path in ('v0.10/source_records/bioshock_2007.json','v0.11/source_records/bioshock2_minerva_2010.json'):
  prior_ev.update(e['event_id'] for e in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['story_events'])
 cc=d['prior_bioshock_links']
 ck(len({(x['from_new_event_id'],x['to_prior_event_id']) for x in cc})==len(cc)
   and all(x['from_new_event_id'] in events and x['to_prior_event_id'] in prior_ev
      and x['inferential'] is True and x['quality_effect']=='not_evaluated' for x in cc),
   'cross-BioShock mistaken direct canon merge')
 b=d['editorial_boundaries']
 ck(len({x['boundary_id'] for x in b})==10 and
   all(x['status']=='first_pass_editorial_boundary' and set(x['source_ids'])<=set(sources) for x in b),
   'editorial boundaries missing')
 ck(len(c.get('continuity_firewall',[]))>=20,'missing world/time/copyright guardrails')
 ck(all((DOCS/file).is_file() and (DOCS/file).stat().st_size>160 for file in REQUIRED_DOCS),
   'generated docs missing')
 return {'status':'PASS' if not errors else 'FAIL',
   'scope':'OFFLINE_PROVENANCE_PARALLEL_WORLD_IDENTITY_KNOWLEDGE_AND_PLAYER_CHOICE_NOT_STORY_QUALITY',
   'counts':{k:len(v) for k,v in d.items()},'errors':errors,
   'firsthand_original_gameplay_audit':False,'story_quality_trials':0,
   'paid_model_calls':0,'lumi_production_modified':False}
if __name__=='__main__':
 try:report=validate()
 except Exception as ex:report={'status':'FAIL','fatal':repr(ex)}
 print(json.dumps(report,ensure_ascii=False,indent=2))
 sys.exit(0 if report['status']=='PASS' else 1)
