#!/usr/bin/env python3
"""v0.13 fail-closed provenance, identity, chapter separation and reuse-boundary tests."""
import hashlib,json,sys
from build_burial_at_sea import ROOT,BASE,SRC,DOC,TABLES
EXPECTED={'works':2,'sources':14,'story_events':28,'knowledge_states':10,
 'mechanics':16,'narrative_links':15,'cross_game_links':8,'editorial_boundaries':16,
 'mechanic_evidence':43,'prior_mechanic_links':32}
DOCS=('README.md','WORKS.md','EVENTS.md','MECHANICS.md','KNOWLEDGE.md','CROSS_GAME.md',
 'SOURCES.md','CONTINUITY.md')
def rows(k):return [json.loads(line) for line in (BASE/(k+'.jsonl')).read_text(encoding='utf8').splitlines() if line.strip()]
def validate():
 errors=[]
 def ck(cond,msg):
  if not cond:errors.append(msg)
 c=json.loads(SRC.read_text(encoding='utf8'))
 manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
 data={k:rows(k) for k in TABLES}
 for k,n in EXPECTED.items():
  ck(len(data[k])==n,f'{k} count {len(data[k])} != {n}')
  ck(manifest.get('counts',{}).get(k)==n,'manifest count mismatch '+k)
  if k in c:ck(data[k]==c[k],'derived source drift '+k)
 ck(c.get('schema_version')==manifest.get('schema_version')=='0.13.0-source-first-pass','schema drift')
 ck(c.get('scope')=='burial_at_sea_ep1_2013_ep2_2014_separate_original_dlc_only','scope drift')
 ck(manifest.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'canonical sha drift')
 ck(c.get('quality_effect')==manifest.get('quality_effect')=='not_evaluated'
    and c.get('lumi_canon') is False,'quality and canon overclaim')
 ck(c.get('new_paid_calls')==manifest.get('paid_model_calls')==0,'invented paid inference')
 ck(c.get('story_quality_trials')==manifest.get('story_quality_trials')==0,'invented A/B trials')
 ck(c.get('lumi_production_modified') is False and manifest.get('lumi_production_modified') is False,'prod change')
 ck(c.get('firsthand_original_gameplay_audited') is False
    and manifest.get('firsthand_original_gameplay_audited') is False,'invented audit')
 ck(not rows('quality_evaluations') and not rows('lumi_usage_history'),'invented quality/runtime rows')
 works={w['work_id']:w for w in data['works']}
 ck(list(works)==['BAS1','BAS2'],'Episode One and Two wrongly merged')
 ck(works.get('BAS1',{}).get('release_date')=='2013-11-12'
    and works.get('BAS2',{}).get('release_date')=='2014-03-25','release dates')
 ck(works['BAS1']['playable_character']=='Booker (Rapture alias Comstock variant)'
    and works['BAS2']['playable_character']=='Elizabeth (mortal returned instance)','playable character boundary')
 ck(works['BAS1']['format']=='original_story_dlc'
    and works['BAS2']['format']=='separate_story_dlc'
    and all(w['firsthand_gameplay_audited'] is False and w['quality_effect']=='not_evaluated' for w in works.values()),'wrong format or audit')
 src={x['source_id']:x for x in data['sources']}
 ck(len(src)==len(data['sources'])==14,'duplicate source')
 allowed={'official_release','contemporaneous_primary','contemporaneous_publisher_news',
   'later_secondary_walkthrough','community_nonindependent','retrospective_nonindependent',
   'contemporary_prior_game_walkthrough'}
 ck(all(x['url'].startswith('https://')
   and x['evidence_tier'] in allowed and x['verification']=='web_search_result_or_page_opened_2026-10-16'
   and x['direct_original_gameplay_audited'] is False for x in src.values()),'source confidence inflated')
 ck(src.get('BAS-STEAM1',{}).get('evidence_tier')=='official_release'
    and src.get('BAS-WIKI-EP2',{}).get('evidence_tier')=='community_nonindependent'
    and src.get('BAS-GF-EP2-COL',{}).get('evidence_tier')=='later_secondary_walkthrough',
    'publisher, community and walkthrough source class lost')
 ck(all(set(w['evidence_ids'])<=set(src) for w in works.values()),'work missing bibliography')
 events={e['event_id']:e for e in data['story_events']}
 ck(len(events)==len(data['story_events'])==28,'duplicate event')
 ck([e['event_id'] for e in data['story_events'] if e['work_id']=='BAS1']==
    [f'BAS1-E{i:02d}' for i in range(1,14)],'Episode One events mixed')
 ck([e['event_id'] for e in data['story_events'] if e['work_id']=='BAS2']==
    [f'BAS2-E{i:02d}' for i in range(1,16)],'Episode Two events mixed')
 strengths={'secondary_walkthrough','community_plot_plus_walkthrough','community_plot_retrospective',
 'official_premise_plus_community_plot','community_only','official_and_walkthrough',
 'secondary_walkthrough_plus_community','community_plus_contemporary_guide'}
 ck(all(e['work_id'] in works and e['source_ids'] and set(e['source_ids'])<=set(src)
     and len(e['observation_tr'])>=85
     and e['evidence_tier'] in strengths
     and e['quality_effect']=='not_evaluated' and e['independently_played'] is False
     for e in events.values()),'event evidence or audit incorrectly promoted')
 ck(events['BAS1-E10']['event_kind']=='identity_reveal'
    and events['BAS1-E11']['world_scope']=='ANNA_ALT_BRANCH'
    and events['BAS2-E02']['event_kind']=='episode_transition','world/identity ontology error')
 ck(events['BAS2-E03']['event_kind']=='subjective_guide'
    and events['BAS2-E14']['event_kind']=='episode_final','mental guide or mortality')
 ck(events['BAS1-E13']['evidence_tier']=='community_plot_retrospective'
    and events['BAS2-E14']['evidence_tier']=='community_only','final claims higher than sources')
 states={k['state_id']:k for k in data['knowledge_states']}
 ck(len(states)==len(data['knowledge_states'])==10,'duplicate knowledge')
 ck(all(k['setup_event_id'] in events and k['reveal_event_id'] in events
     and k['work_id']==events[k['setup_event_id']]['work_id']
     and k['work_id']==events[k['reveal_event_id']]['work_id']
     and k['is_belief_not_world_truth'] is True for k in states.values()),
    'knowledge crosses episodic character boundaries')
 expected_state={
 'K-COMSTOCK':'rapture_booker_is_distinct_comstock_variant',
 'K-ANNA':'anna_died_in_burial_branch_but_lost_finger_in_base',
 'K-ELIZABETH':'returned_elizabeth_mortal_without_tear_power',
 'K-BOOKER-VOICE':'guide_is_mental_image_not_physical_companion',
 'K-PARIS':'paris_is_subjective_presentation_not_verified_history',
 'K-JACK':'separate_information_transfer_and_future_action'}
 ck(all(states.get(k,{}).get('actual_rule')==v for k,v in expected_state.items()),
   'dead/resurrected or alternative identity changed')
 old=set()
 for path in (
 'v0.3/source_records/prince_mechanics.json','v0.4/source_records/prototype_2009.json',
 'v0.5/source_records/tomb_raider_survivor.json','v0.6/source_records/tomb_raider_classic.json',
 'v0.7/source_records/tomb_raider_lau.json','v0.8/source_records/prototype2_2012.json',
 'v0.9/source_records/prototype_comic_bridge.json','v0.10/source_records/bioshock_2007.json',
 'v0.11/source_records/bioshock2_minerva_2010.json',
 'v0.12/source_records/bioshock_infinite_2013.json'):
  old|={m['mechanic_id'] for m in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['mechanics']}
 mm=data['mechanics'];mids={m['mechanic_id'] for m in mm}
 ck(len(mids)==16 and list(mids)!=[] and
    [m['mechanic_id'] for m in mm]==[f'BASM-{i:03d}' for i in range(1,17)]
    and not mids.intersection(old),'wrong new mechanic ID')
 ck(all(m['event_anchors'] and set(m['event_anchors'])<=set(events)
     and m['prior_mechanic_ids'] and set(m['prior_mechanic_ids'])<=old
     and len(m['abstraction_tr'])>=85 and len(m['guardrail_tr'])>=75
     and m['mechanism_inference'] is True and m['quality_effect']=='not_evaluated'
     and m['lumi_canon'] is False and m['copyright_guardrail']
     for m in mm),'unsupported mechanism or unsafe reuse')
 evidence=data['mechanic_evidence']
 expected={(m['mechanic_id'],eid) for m in mm for eid in m['event_anchors']}
 actual={(x['mechanic_id'],x['event_id']) for x in evidence}
 ck(expected==actual and len(expected)==len(evidence),'orphan or duplicated evidence')
 ck(all(x['event_id'] in events and x['work_id']==events[x['event_id']]['work_id']
     and x['source_ids']==events[x['event_id']]['source_ids']
     and x['evidence_tier']==events[x['event_id']]['evidence_tier']
     and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
     for x in evidence),'derived evidence provenance mismatch')
 prior=data['prior_mechanic_links']
 expected_prior={(m['mechanic_id'],v) for m in mm for v in m['prior_mechanic_ids']}
 ck(len(prior)==len(expected_prior) and
  {(x['mechanic_id'],x['prior_mechanic_id']) for x in prior}==expected_prior
  and all(x['relation']=='conceptual_comparison_not_equivalence'
    and x['quality_effect']=='not_evaluated' for x in prior),
    'prior mechanism missing or falsely identical')
 links=data['narrative_links']
 ck(len({(x['from_event_id'],x['to_event_id']) for x in links})==len(links),'duplicate narrative link')
 ck(all(x['from_event_id'] in events and x['to_event_id'] in events
    and x['quality_effect']=='not_evaluated' and isinstance(x['inference'],bool) for x in links),
    'orphan causal link')
 ck({('BAS1-E13','BAS2-E01'),('BAS2-E07','BAS2-E09'),('BAS2-E12','BAS2-E13')}<=
    {(x['from_event_id'],x['to_event_id']) for x in links},'missing chapter transition and physical prereqs')
 ck(all(x['inference'] is False for x in links if x['kind']=='physical_prerequisite'),
    'speculative physical prerequisite falsely proven')
 prior_events=set()
 for path in ('v0.10/source_records/bioshock_2007.json',
  'v0.12/source_records/bioshock_infinite_2013.json'):
  prior_events|={e['event_id'] for e in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['story_events']}
 oldlinks=data['cross_game_links']
 ck(len({(x['from_event_id'],x['prior_event_id']) for x in oldlinks})==len(oldlinks)
   and all(x['from_event_id'] in events and x['prior_event_id'] in prior_events
     and x['inference'] is True and x['quality_effect']=='not_evaluated' for x in oldlinks),
     'cross-game event asserted as one physical event')
 ck(len(c['editorial_boundaries'])==16 and len({x['id'] for x in c['editorial_boundaries']})==16,
  'continuity guards missing')
 ck(all((DOC/f).is_file() and (DOC/f).stat().st_size>100 for f in DOCS),'missing docs')
 return {'status':'PASS' if not errors else 'FAIL','errors':errors,
  'counts':{k:len(v) for k,v in data.items()},'firsthand_gameplay_audits':0,
  'paid_calls':0,'story_quality_trials':0,'lumi_production_modified':False}
if __name__=='__main__':
 try:report=validate()
 except Exception as err:report={'status':'FAIL','fatal':repr(err)}
 print(json.dumps(report,ensure_ascii=False,indent=2))
 sys.exit(0 if report['status']=='PASS' else 1)
