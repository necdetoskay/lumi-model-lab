#!/usr/bin/env python3
"""NOVA v0.10 BioShock fail-closed offline structure/provenance/agency checks."""
import json,hashlib,sys
from build_bioshock import ROOT,BASE,SRC,DOCS,TABLES
EXPECTED={'works':1,'sources':14,'story_events':23,'mechanics':16,'knowledge_states':5,
 'narrative_links':13,'ending_variants':2,'prior_mechanic_references':34,
 'editorial_boundaries':6,'mechanic_evidence':48}
REQUIRED_DOCS=('README.md','EVENTS.md','MECHANICS.md','KNOWLEDGE.md',
 'CHOICE_AND_ENDINGS.md','WORLD_STATE.md','SOURCES.md','FIREWALL.md')
def rows(k):
    return [json.loads(v) for v in (BASE/(k+'.jsonl')).read_text(encoding='utf8').splitlines() if v.strip()]
def validate():
    errors=[]
    def ck(ok,reason):
        if not ok:errors.append(reason)
    c=json.loads(SRC.read_text(encoding='utf8'))
    meta=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    d={name:rows(name) for name in TABLES}
    for key,n in EXPECTED.items():
        ck(len(d[key])==n,f'wrong count {key}: {len(d[key])}, expected {n}')
        ck(meta.get('counts',{}).get(key)==n,'manifest count mismatch '+key)
        if key in c:ck(d[key]==c[key],'compiled canonical drift '+key)
    ck(c.get('schema_version')==meta.get('schema_version')=='0.10.0-research-first-pass','version drift')
    ck(meta.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'canonical hash mismatch')
    ck(c.get('scope')=='bioshock_original_2007_base_main_campaign_only','wrong scope')
    ck(c.get('quality_effect')==meta.get('quality_effect')=='not_evaluated'
       and c.get('lumi_canon') is False,'false story quality or LUMI canon')
    ck(c.get('story_quality_trials')==meta.get('story_quality_trials')==0,'claimed story trial')
    ck(c.get('new_paid_model_calls')==meta.get('new_paid_model_calls')==0,'claimed paid calls')
    ck(c.get('lumi_production_modified') is False and meta.get('lumi_production_modified') is False,'production change')
    ck(c.get('original_gameplay_captured_and_audited') is False
       and meta.get('original_gameplay_captured_and_audited') is False,'fabricated first hand gameplay')
    ck(rows('quality_evaluations')==[] and rows('lumi_usage_history')==[],'invented A/B or runtime usage')
    works=d['works']
    ck(len(works)==1 and works[0].get('work_id')=='BS2007'
       and works[0].get('original_release_year')==2007
       and works[0].get('release_date')=='2007-08-21'
       and works[0].get('continuity')=='ORIGINAL_BIOSHOCK_2007_MAIN_CAMPAIGN'
       and works[0].get('remaster_is_distinct_story') is False
       and works[0].get('quality_effect')=='not_evaluated','wrong original work/edition')
    sources={s['source_id']:s for s in d['sources']}
    ck(len(sources)==len(d['sources']),'duplicate source ids')
    ck(all(s['url'].startswith('https://') and
       s['verification']=='web_search_result_or_open_retrieved_2026-10-16'
       and s['evidence_tier'] in ('official_release','contemporary_walkthrough','creator_design_commentary',
          'contemporary_independent_analysis','community_game_walkthrough','later_player_walkthrough',
          'later_creator_recollection','fan_claim_unverified') for s in sources.values()),
       'source provenance tier or false HTTP audit')
    ck(sources.get('BS-ST',{}).get('evidence_tier')=='official_release'
       and sources.get('BS-FAN-ENDING',{}).get('evidence_tier')=='fan_claim_unverified'
       and sources.get('BS-GS-QA',{}).get('evidence_tier')=='creator_design_commentary',
       'primary/product/fan hierarchy lost')
    ck(set(works[0]['source_ids'])<=set(sources),'work missing citations')
    events={e['event_id']:e for e in d['story_events']}
    ck(len(events)==len(d['story_events']) and len(events)==23,'duplicate event id')
    ck([e['event_id'] for e in d['story_events']]==[f'BS-E{i:02d}' for i in range(1,24)],
       'story beats reordered/omitted')
    ck(all(e['source_ids'] and set(e['source_ids'])<=set(sources)
        and len(e['observed_event_tr'])>=85
        and e['event_kind'] in ('mandatory_story','player_branch','optional_evidence','ending_variant')
        and e['player_choice']==(e['event_kind']=='player_branch')
        and e['evidence_strength'] in ('editorial_walkthrough_supported',
                                      'walkthrough_and_conflicting_community_rule')
        and e['quality_effect']=='not_evaluated' and e['editorial_stage']=='sourced_first_pass'
        for e in events.values()),'event source/choice/epistemic tier invalid')
    ck(events['BS-E05']['event_kind']=='player_branch'
       and events['BS-E15']['event_kind']=='mandatory_story'
       and events['BS-E11']['event_kind']=='optional_evidence'
       and events['BS-E22']['event_kind']=='ending_variant'
       and events['BS-E23']['event_kind']=='ending_variant',
       'free-choice, optional lore, scripted action and epilog conflated')
    ck(all(events[e]['evidence_strength']=='walkthrough_and_conflicting_community_rule'
       for e in ('BS-E22','BS-E23')),'ending certainty falsely raised')
    ks={s['state_id']:s for s in d['knowledge_states']}
    ck(len(ks)==5,'duplicate subjective knowledge')
    ck(all(s['setup_event_id'] in events and s['reveal_event_id'] in events
       and s['world_truth'] and s['claim'] and s['knowledge_status'] for s in ks.values()),
       'missing state knowledge references')
    ck(ks['BS-K01']['reveal_event_id']=='BS-E16'
       and 'Frank Fontaine' in ks['BS-K01']['world_truth'],
       'Atlas alias not resolved')
    ck(ks['BS-K02']['reveal_event_id']=='BS-E13'
       and 'Conditioned' in ks['BS-K02']['world_truth'],
       'false autonomous-choice belief')
    ck(ks['BS-K04']['knowledge_status']=='source_claim_not_automatically_real_event',
       'claimed Atlas family deaths promoted to objective world fact')
    ends={s['variant_id']:s for s in d['ending_variants']}
    ck(set(ends)=={'BS-END-RESCUE','BS-END-HARVEST'},'ending variants missing')
    ck({s['event_id'] for s in ends.values()}=={'BS-E22','BS-E23'},
       'ending variant points to wrong observed events')
    ck(all(s['specific_numeric_threshold'] is None and s['threshold_verified'] is False
       and s['canon_status']=='one_of_multiple_gameplay_outcomes_not_single_canonical_history'
       and set(s['source_ids'])<=set(sources) for s in ends.values()),
       'overclaims exact ending threshold or merges variants')
    lk=d['narrative_links']
    ck(len({(x['from_event_id'],x['to_event_id'],x['relation_kind']) for x in lk})==len(lk),
       'duplicate event links')
    ck(all(x['from_event_id'] in events and x['to_event_id'] in events
       and x['quality_effect']=='not_evaluated'
       and isinstance(x['inference'],bool) for x in lk),
       'orphan causal link')
    epilog_links={(x['from_event_id'],x['to_event_id']) for x in lk
                  if x['relation_kind']=='exclusive_epilogue'}
    ck(epilog_links=={('BS-E21','BS-E22'),('BS-E21','BS-E23')},
       'epilog choices flattened into one')
    required={('BS-E08','BS-E09'),('BS-E17','BS-E18'),('BS-E19','BS-E20'),
       ('BS-E13','BS-E15'),('BS-E02','BS-E16')}
    ck(required<= {(x['from_event_id'],x['to_event_id']) for x in lk},
       'world physical/identity causality broken')
    ck(all(x['inference'] is True for x in lk if x['relation_kind'] in
        ('claim_reinterpreted','branch_evidence')),
       'interpretive link canon promoted')
    ck(all(x['inference'] is False for x in lk if x['relation_kind'] in
        ('exclusive_epilogue','physical_prerequisite','mandatory_causal_sequence')),
       'observed prereq wrongly inferred')
    prior=set()
    for path in (
       'data/nova/v0.3/source_records/prince_mechanics.json',
       'data/nova/v0.4/source_records/prototype_2009.json',
       'data/nova/v0.5/source_records/tomb_raider_survivor.json',
       'data/nova/v0.6/source_records/tomb_raider_classic.json',
       'data/nova/v0.7/source_records/tomb_raider_lau.json',
       'data/nova/v0.8/source_records/prototype2_2012.json',
       'data/nova/v0.9/source_records/prototype_comic_bridge.json'
    ):
        prior|={x['mechanic_id'] for x in json.loads((ROOT/path).read_text(encoding='utf8'))['mechanics']}
    m=d['mechanics']
    mech_ids={x['mechanic_id'] for x in m}
    ck(len(mech_ids)==len(m) and [x['mechanic_id'] for x in m]==
       [f'BSM-{i:03d}' for i in range(1,17)] and not mech_ids.intersection(prior),
       'duplicate or old mechanic id')
    ck(all(x['event_anchors'] and set(x['event_anchors'])<=set(events)
       and x['prior_mechanic_ids'] and set(x['prior_mechanic_ids'])<=prior
       and len(x['abstraction_tr'])>=90 and len(x['guardrail_tr'])>=90
       and x['mechanism_inference'] is True
       and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
       and x['editorial_stage']=='sourced_first_pass' and x['copyright_guardrail']
       for x in m),'mechanic evidence/guardrail/quality problem')
    refs=d['prior_mechanic_references']
    expected={(x['mechanic_id'],p) for x in m for p in x['prior_mechanic_ids']}
    actual={(x['mechanic_id'],x['prior_mechanic_id']) for x in refs}
    ck(expected==actual and len(actual)==len(refs)
       and all(x['relation']=='similar_research_hypothesis_not_equivalent'
           and x['quality_effect']=='not_evaluated' for x in refs),
       'previous mechanics equivalents wrongly asserted or count mismatch')
    expected_ev={(x['mechanic_id'],e) for x in m for e in x['event_anchors']}
    evidence=d['mechanic_evidence']
    pairs={(x['mechanic_id'],x['event_id']) for x in evidence}
    ck(pairs==expected_ev and len(pairs)==len(evidence),'mechanic evidence linkage')
    ck(all(x['event_id'] in events and x['work_id']=='BS2007'
       and x['source_ids']==events[x['event_id']]['source_ids']
       and x['event_kind']==events[x['event_id']]['event_kind']
       and x['confidence']==events[x['event_id']]['evidence_strength']
       and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
       for x in evidence),'mechanic evidence falsely promoted')
    b={x['id']:x for x in d['editorial_boundaries']}
    ck(len(b)==6 and all(set(x['sources'])<=set(sources) for x in b.values()),
       'editorial caveats ungrounded')
    ck(b['BS-B02']['status']=='numeric_threshold_contested_pending_firsthand_replay',
       'ending threshold disagreement suppressed')
    ck(len(c['continuity_firewall'])>=15,'missing continuity and copyright rules')
    ck(all((DOCS/f).is_file() and (DOCS/f).stat().st_size>170 for f in REQUIRED_DOCS),
       'required generated docs missing')
    return {'status':'PASS' if not errors else 'FAIL',
       'scope':'OFFLINE_PROVENANCE_PLAYER_AGENCY_WORLD_STATE_AND_ALT_ENDINGS_NOT_GAMEPLAY_INDEPENDENT_AUDIT',
       'counts':{name:len(items) for name,items in d.items()},
       'independent_original_playthroughs':0,'story_quality_trials':0,'paid_calls':0,
       'lumi_production_modified':False,'errors':errors}
if __name__=='__main__':
    try:result=validate()
    except Exception as ex:result={'status':'FAIL','fatal':repr(ex)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
