#!/usr/bin/env python3
"""NOVA v0.11 fail-closed continuity, agent-agency, state and provenance validator."""
import hashlib,json,sys
from collections import Counter
from build_bioshock2 import ROOT,BASE,SRC,DOCS,TABLES
EXPECTED={'works':2,'sources':19,'story_events':30,'choice_axes':4,
 'ending_outcomes':3,'knowledge_states':8,'narrative_links':16,'object_states':6,
 'mechanics':18,'prior_bioshock_links':6,'editorial_boundaries':8,
 'mechanic_evidence':47,'mechanic_prior_links':36}
WIDS=('B2-BASE-2010','B2-MINERVA-2010')
DOCS_EXPECTED=('README.md','MECHANICS.md','CHOICES_AND_OUTCOMES.md',
    'KNOWLEDGE_AND_IDENTITY.md','OBJECT_STATE.md','CHRONOLOGY.md',
    'SOURCES.md','CONTINUITY_FIREWALL.md')
def rows(name):
    return [json.loads(v) for v in (BASE/(name+'.jsonl')).read_text(encoding='utf8').splitlines() if v.strip()]
def validate():
    errors=[]
    def ck(cond,msg):
        if not cond:errors.append(msg)
    c=json.loads(SRC.read_text(encoding='utf8'))
    m=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    d={key:rows(key) for key in TABLES}
    for key,n in EXPECTED.items():
        ck(len(d[key])==n,f'wrong count {key}: {len(d[key])}, expected {n}')
        ck(m.get('counts',{}).get(key)==n,'manifest '+key+' drift')
        if key in c:ck(d[key]==c[key],key+' derived records differ from canonical')
    ck(m.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'source sha mismatch')
    ck(m.get('schema_version')==c.get('schema_version')=='0.11.0-research-first-pass','schema version')
    ck(c.get('scope')=='bioshock2_2010_original_main_plus_minervas_den_original_story_dlc_two_work_records',
       'main/DLC scoped identities merged')
    ck(c.get('quality_effect')==m.get('quality_effect')=='not_evaluated'
       and c.get('lumi_canon') is False,'quality/canon assertion')
    ck(c.get('new_paid_model_calls')==m.get('new_paid_model_calls')==0,'paid models claimed')
    ck(c.get('story_quality_trials')==m.get('story_quality_trials')==0,'nonexistent story experiments')
    ck(c.get('lumi_production_modified') is False and m.get('lumi_production_modified') is False,
       'LUMI production modified')
    ck(c.get('original_gameplay_replayed_and_audited') is False
       and m.get('original_gameplay_replayed_and_audited') is False,
       'falsely claims full gameplay audit')
    ck(not rows('quality_evaluations') and not rows('lumi_usage_history'),
       'fabricated quality/runtime evidence')
    works={w['work_id']:w for w in d['works']}
    ck(tuple(works)==WIDS,'works not two separate records')
    ck(works.get('B2-BASE-2010',{}).get('media_type')=='original_game_main_campaign'
       and works.get('B2-MINERVA-2010',{}).get('media_type')=='original_story_dlc',
       'DLC type lost')
    ck(works['B2-BASE-2010']['original_release_date']=='2010-02-09'
       and works['B2-MINERVA-2010']['original_release_date']=='2010-08-31',
       'original 2010 dates changed')
    ck(works['B2-BASE-2010']['narrative_time_scope']=='prologue_1958_main_1968'
       and works['B2-MINERVA-2010']['narrative_time_scope']=='post_Rapture_fall_same_broad_era_precise_interleave_unverified',
       'chronology overstatement')
    ck(all(w['continuity']=='RAPTURE_BIOSHOCK_SERIES' and
       w['quality_effect']=='not_evaluated' and w['lumi_canon'] is False
       and w['editorial_stage']=='source_grounded_first_pass_not_original_playthrough'
       for w in works.values()),'work canon or primary audit inflated')
    src={s['source_id']:s for s in d['sources']}
    ck(len(src)==len(d['sources'])==19,'sources duplicate/missing')
    ck(all(s['url'].startswith('https://') and
           s['verification']=='web_result_or_page_opened_2026-10-16'
           and s['evidence_tier'] in (
           'official_product_synopsis','contemporaneous_official_dlc_description',
           'release_metadata_secondary','secondary_player_walkthrough',
           'licensed_guide','tertiary_summary')
           for s in src.values()),'source changed tier or fabricated audit')
    ck(src.get('B2-XBOX-MD',{}).get('evidence_tier')=='contemporaneous_official_dlc_description'
       and src.get('B2-PRIMA-END',{}).get('evidence_tier')=='licensed_guide'
       and src.get('B2-TERTIARY-MD',{}).get('evidence_tier')=='tertiary_summary',
       'source hierarchy falsely promoted')
    ck(all(w['sources'] and set(w['sources'])<=set(src) for w in works.values()),
       'work source missing')
    events={e['event_id']:e for e in d['story_events']}
    ck(len(events)==len(d['story_events'])==30,'duplicate events')
    ck([x['event_id'] for x in d['story_events'] if x['work_id']=='B2-BASE-2010']==
       [f'B2-E{i:02d}' for i in range(1,19)],'base event ids/order incorrect')
    ck([x['event_id'] for x in d['story_events'] if x['work_id']=='B2-MINERVA-2010']==
       [f'MD-E{i:02d}' for i in range(1,13)],'Minerva event ids/order incorrect')
    ck(Counter(e['work_id'] for e in events.values())==
       Counter({'B2-BASE-2010':18,'B2-MINERVA-2010':12}),'events by work incorrect')
    kinds={'historical_prologue','mandatory_story','world_state_backstory','world_rule',
      'player_choice_mechanic','physical_prerequisite','named_character_choice',
      'downstream_character_state','perspective_switch','ending_family',
      'ending_choice_rule','dlc_entry','world_system','unknown_voice_source',
      'antagonist_claim','optional_evidence','physical_tool_rule','institution_control',
      'identity_reveal','grief_resolution'}
    ck(all(e['work_id'] in works and
       e['source_ids'] and set(e['source_ids'])<=set(src)
       and len(e['observation_tr'])>=85 and e['event_kind'] in kinds
       and e['narrative_time_type'] in ('historical_1958','main_1968','between_1960_and_1968',
          'repeated_local_choices','separate_dlc_relative','historical_backstory')
       and e['evidence_strength'] in ('secondary_player_walkthrough','tertiary_with_walkthrough_context',
          'official_premise_plus_tertiary','official_premise_plus_walkthrough',
          'licensed_guide','official_dlc_and_walkthrough','official_dlc_and_tertiary',
          'tertiary_and_player_guide','secondary_guide_and_tertiary')
       and e['firsthand_gameplay_audited'] is False
       and e['quality_effect']=='not_evaluated' and e['lumi_canon'] is False
       for e in events.values()),'event source/timeline/quality inaccurate')
    ck(events['B2-E01']['narrative_time_type']=='historical_1958'
       and events['B2-E02']['narrative_time_type']=='main_1968'
       and events['MD-E01']['narrative_time_type']=='separate_dlc_relative',
       'historical and DLC chronology conflated')
    ck(events['B2-E13']['event_kind']=='mandatory_story'
       and 'kısa süreli' in events['B2-E13']['observation_tr']
       and events['B2-E14']['event_kind']=='perspective_switch',
       'Eleanor false-death or perspective changed')
    ck(events['MD-E11']['event_kind']=='identity_reveal' and
       events['MD-E12']['event_kind']=='grief_resolution',
       'Thinker/Porter/Pearl identity twist broken')
    axes={x['axis_id']:x for x in d['choice_axes']}
    ck(len(axes)==4 and set(axes)=={'B2-C-LITTLE','B2-C-GRACE','B2-C-STAN','B2-C-GIL'},
       'choice axes merged')
    ck(all(set(x['options'])==({'save','harvest'} if x['axis_id']=='B2-C-LITTLE' else {'spare','kill'})
       and x['evidence_event_ids'] and set(x['evidence_event_ids'])<=set(events)
       and x['specific_numeric_threshold'] is None
       and x['branch_conditions_status']=='licensed_guide_qualitative'
       and x['later_impacts'] for x in axes.values()),
       'choices have invented thresholds or lost outcomes')
    outs={o['outcome_id']:o for o in d['ending_outcomes']}
    ck(len(outs)==3 and set(outs)=={'B2-OUT-GOOD','B2-OUT-BAD','B2-OUT-MIXED'},
       'main outcome categories')
    ck(all(o['event_ref']=='B2-E17' and o['qualitative_verified'] is True
       and o['exact_numeric_threshold'] is None
       and set(o['exclusive_with'])==set(outs)-{o['outcome_id']} for o in outs.values()),
       'exclusive final variants lost or speculative numeric thresholds')
    state={x['knowledge_id']:x for x in d['knowledge_states']}
    ck(len(state)==8 and len(state)==len(d['knowledge_states']),'knowledge duplicate')
    ck(all(x['setup_event'] in events and x['correction_event'] in events
       and events[x['setup_event']]['work_id']==events[x['correction_event']]['work_id']
       and x['subjective_claim_is_objective_fact'] is False for x in state.values()),
       'false objective knowledge or cross-series mind share')
    ck(state['B2-K02']['actual_world_rule']=='heartbeat_temporarily_stopped_then_survives'
       and state['MD-K01']['actual_world_rule']=='thinker_simulates_porter_voice'
       and state['MD-K02']['actual_world_rule']=='sigma_is_transformed_physical_porter'
       and state['MD-K03']['actual_world_rule']=='voice_personality_emulation_is_not_original_person_resurrection',
       'identity, death, or imitation corrupted')
    obj={x['object_id']:x for x in d['object_states']}
    ck(len(obj)==6 and len(d['object_states'])==6,'object identity duplicated')
    ck(all(x['work_id'] in works and set(x['event_refs'])<=set(events) and
       all(events[e]['work_id']==x['work_id'] for e in x['event_refs']) and
       x['quality_effect']=='not_evaluated' for x in obj.values()),'object location/cross work inconsistency')
    ck(obj['OBJ-MD-PUNCHCARD']['state_rule']=='wahl_holder_then_sigma'
       and obj['OBJ-MD-THINKER']['state_rule']=='machine_with_simulated_voice_and_security'
       and obj['OBJ-MD-PEARL']['state_rule']=='emulation_does_not_restore_deceased_person',
       'stateful object ownership or identity invalid')
    links=d['narrative_links']
    ck(len({(x['from_event_id'],x['to_event_id'],x['kind']) for x in links})==len(links),
       'duplicate narrative edge')
    ck(all(x['from_event_id'] in events and x['to_event_id'] in events
       and events[x['from_event_id']]['work_id']==events[x['to_event_id']]['work_id']
       and x['quality_effect']=='not_evaluated' and isinstance(x['inference'],bool)
       for x in links),'cross-DLC accidental causal linkage')
    required={('B2-E03','B2-E13'),('B2-E14','B2-E15'),
       ('MD-E03','MD-E11'),('MD-E10','MD-E11')}
    ck(required<= {(x['from_event_id'],x['to_event_id']) for x in links},
       'bond/gear/Thinker identity link missing')
    ck(all(x['inference'] is False for x in links if x['kind']=='physical_prerequisite'),
       'physical preconditions asserted only as inference')
    prev=json.loads((ROOT/'data/nova/v0.10/source_records/bioshock_2007.json').read_text(encoding='utf8'))
    prior_events={x['event_id'] for x in prev['story_events']}
    cross=d['prior_bioshock_links']
    ck(len({(x['from_prior_event_id'],x['to_new_event_id']) for x in cross})==len(cross),
       'cross-story duplicate links')
    ck(all(x['from_prior_event_id'] in prior_events and x['to_new_event_id'] in events
       and x['inference'] is True and x['quality_effect']=='not_evaluated'
       for x in cross),'false hard canonical alignment with 2007 game')
    prev_mech=set()
    for file in (
       'data/nova/v0.3/source_records/prince_mechanics.json',
       'data/nova/v0.4/source_records/prototype_2009.json',
       'data/nova/v0.5/source_records/tomb_raider_survivor.json',
       'data/nova/v0.6/source_records/tomb_raider_classic.json',
       'data/nova/v0.7/source_records/tomb_raider_lau.json',
       'data/nova/v0.8/source_records/prototype2_2012.json',
       'data/nova/v0.9/source_records/prototype_comic_bridge.json',
       'data/nova/v0.10/source_records/bioshock_2007.json'):
        prev_mech|={z['mechanic_id'] for z in json.loads((ROOT/file).read_text(encoding='utf8'))['mechanics']}
    mechs=d['mechanics']
    mids={m['mechanic_id'] for m in mechs}
    ck(len(mids)==len(mechs) and not mids.intersection(prev_mech)
       and [m['mechanic_id'] for m in mechs]==[f'B2M-{i:03d}' for i in range(1,19)],
       'duplicate or colliding new mechanism ID')
    ck(all(m['event_anchors'] and set(m['event_anchors'])<=set(events)
       and m['prior_mechanic_ids'] and set(m['prior_mechanic_ids'])<=prev_mech
       and len(m['abstraction_tr'])>=90 and len(m['guardrail_tr'])>=80
       and m['inference'] is True and m['quality_effect']=='not_evaluated'
       and m['lumi_canon'] is False and m['copyright_guardrail']
       and m['editorial_stage']=='source_grounded_first_pass' for m in mechs),
       'mechanism evidence/guardrail/quality inflation')
    evidence=d['mechanic_evidence']
    expected={(m['mechanic_id'],eid) for m in mechs for eid in m['event_anchors']}
    actual={(x['mechanic_id'],x['event_id']) for x in evidence}
    ck(expected==actual and len(expected)==len(evidence),'missing/duplicated source evidence')
    ck(all(e['event_id'] in events and e['work_id']==events[e['event_id']]['work_id']
       and e['source_ids']==events[e['event_id']]['source_ids']
       and e['evidence_strength']==events[e['event_id']]['evidence_strength']
       and e['quality_effect']=='not_evaluated' and e['lumi_canon'] is False for e in evidence),
       'proof confidence increased or wrong link')
    priorlinks=d['mechanic_prior_links']
    expected_prior={(m['mechanic_id'],id) for m in mechs for id in m['prior_mechanic_ids']}
    ck({(x['mechanic_id'],x['prior_mechanic_id']) for x in priorlinks}==expected_prior
       and len(expected_prior)==len(priorlinks)
       and all(x['relation']=='related_concept_not_equivalent'
           and x['quality_effect']=='not_evaluated' for x in priorlinks),
       'prior-mechanic equivalence or orphan')
    boundaries=d['editorial_boundaries']
    ck(len({x['boundary_id'] for x in boundaries})==8
       and all(set(x['source_ids'])<=set(src) for x in boundaries),
       'editorial boundaries incomplete')
    ck(len(c.get('continuity_firewall',[]))>=18,'firewall incomplete')
    ck(all((DOCS/name).is_file() and (DOCS/name).stat().st_size>180 for name in DOCS_EXPECTED)
       and all((DOCS/'works'/(wid.lower()+'.md')).is_file() for wid in WIDS),
       'docs or work summaries missing')
    return {'status':'PASS' if not errors else 'FAIL',
       'scope':'OFFLINE_STRUCTURE_PROVENANCE_DLC_SEPARATION_CHOICE_AXIS_IDENTITY_AND_STATE_NOT_STORY_QUALITY',
       'counts':{key:len(value) for key,value in d.items()},
       'independent_original_gameplay_audits':0,'story_quality_trials':0,
       'paid_calls':0,'lumi_production_modified':False,'errors':errors}
if __name__=='__main__':
    try:result=validate()
    except Exception as exc:result={'status':'FAIL','fatal':repr(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
