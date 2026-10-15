#!/usr/bin/env python3
"""NOVA v0.8 offline provenance, prior-series, beliefs, quality firewall validation."""
import json,hashlib,sys
from build_prototype2 import ROOT,BASE,SRC,DOCS,TABLES
EXPECTED={'works':1,'sources':11,'story_events':20,'belief_states':7,
          'cross_game_links':8,'mechanics':14,'editorial_boundaries':6,
          'mechanic_evidence':42,'prior_links':38}
LOW_CONFIDENCE={'P2-E17','P2-E18','P2-E19','P2-E20'}
DOCS_EXPECTED=('README.md','EVENTS.md','MECHANICS.md','BELIEF_VS_TRUTH.md',
               'CROSS_GAME.md','SOURCES.md','CONTINUITY.md')
def rows(n):
    return [json.loads(l) for l in (BASE/(n+'.jsonl')).read_text(encoding='utf8').splitlines() if l.strip()]
def validate():
    error=[]
    def ck(ok,msg):
        if not ok:error.append(msg)
    c=json.loads(SRC.read_text(encoding='utf8'))
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    d={key:rows(key) for key in TABLES}
    for k,count in EXPECTED.items():
        ck(len(d[k])==count,f'{k} count mismatch expected {count} actual {len(d[k])}')
        ck(manifest.get('counts',{}).get(k)==count,'manifest '+k+' mismatch')
        if k in c:ck(d[k]==c[k],k+' derived source drift')
    ck(manifest.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'source SHA mismatch')
    ck(manifest.get('schema_version')==c.get('schema_version')=='0.8.0-research-first-pass','schema wrong')
    ck(c.get('scope')=='prototype2_2012_main_game_only','comic DLC other work imported')
    ck(c.get('quality_effect')==manifest.get('quality_effect')=='not_evaluated'
       and c.get('lumi_canon') is False,'claiming quality or LUMI canon')
    ck(c.get('paid_model_calls')==manifest.get('new_paid_model_calls')==0,'paid calls claimed')
    ck(c.get('story_quality_trials')==manifest.get('story_quality_trials')==0,'unperformed story trials claimed')
    ck(c.get('lumi_production_modified') is False
       and manifest.get('lumi_production_modified') is False,'production modified')
    ck(not rows('quality_evaluations') and not rows('lumi_usage_history'),'fabricated evaluations/usage')
    wk=d['works']
    ck(len(wk)==1 and wk[0]['work_id']=='PROTOTYPE2-2012' and wk[0]['release_year']==2012,
       'sequel work identity or year wrong')
    ck(all(x['lumi_canon'] is False and x['quality_effect']=='not_evaluated' for x in wk),
       'work canon promotion')
    sources={s['source_id']:s for s in d['sources']}
    ck(len(sources)==len(d['sources']),'duplicate source')
    ck(all(s['url'].startswith('https://') and
           s['verification']=='web_search_result_or_page_opened_2026-10-15'
           and s['evidence_tier'] in {'primary','primary_storefront','developer_interview',
                                      'contemporary_preview','contemporary_review',
                                      'contemporary_walkthrough','community_walkthrough',
                                      'community_mechanics_guide','tertiary_synopsis','retrospective_review'}
           for s in sources.values()),'source provenance changed')
    ck('P2-ACTIVISION' in sources and sources['P2-ACTIVISION']['evidence_tier']=='primary'
        and 'P2-DEV' in sources,'primary/developer anchors missing')
    ck(all(set(w['source_ids'])<=set(sources) for w in wk),'work lacks provenance')
    events={e['event_id']:e for e in d['story_events']}
    ck(len(events)==20 and len(events)==len(d['story_events']),'duplicate events')
    ck([e['event_id'] for e in d['story_events']]==[f'P2-E{i:02d}' for i in range(1,21)],
       'event sequence changed')
    ck(all(e['source_ids'] and set(e['source_ids'])<=set(sources)
           and len(e['observed_event_tr'])>=80
           and e['editorial_stage']=='sourced_first_pass'
           and e['confidence'] in {'primary_premise_plus_tertiary_endgame',
               'publisher_premise_and_preview','preview_and_player_guide',
               'player_guide_and_editorial_walkthrough','community_guide_and_tertiary',
               'guide_supported','tertiary_and_community_nonindependent'}
           and e['temporal_scope']=='relative_main_plot'
           and e['belief_truth_delta'] for e in events.values()),
       'event source/confidence/temporal scope invalid')
    ck(all(events[e]['confidence']=='tertiary_and_community_nonindependent'
           for e in LOW_CONFIDENCE),'final claims improperly promoted')
    ck('Maya' in events['P2-E01']['belief_truth_delta'] and
       'Maya' in events['P2-E15']['belief_truth_delta']
       and 'ölmediğini' in events['P2-E15']['observed_event_tr'],
       'daughter false death vs true living status lost')
    ck('nesnel doğruluk' in events['P2-E04']['belief_truth_delta'],
       'Mercer claim promoted to objective fact')
    belief={b['state_id']:b for b in d['belief_states']}
    ck(len(belief)==7,'duplicate belief state')
    ck(all(b['setup_event_id'] in events and b['reveal_event_id'] in events
           and b['interpretation'] is True and b['knowledge_boundary_tr'] and b['world_state_rule']
           for b in belief.values()),'belief-state event references broken')
    ck(belief['P2-STATE-MAYA']['setup_event_id']=='P2-E01'
        and belief['P2-STATE-MAYA']['reveal_event_id']=='P2-E15'
        and belief['P2-STATE-MAYA']['world_state_rule']=='always_alive_not_retroactively_resurrected',
       'Maya incorrectly resurrected or timeline misassigned')
    ck(belief['P2-STATE-MERCER-END']['reveal_event_id']=='P2-E20',
       'memory transfer chronology broken')
    prior=json.loads((ROOT/'data/nova/v0.4/source_records/prototype_2009.json').read_text(encoding='utf8'))
    older_events={e['event_id'] for e in prior['story_events']}
    links=d['cross_game_links']
    ck(len({(x['from_prior_event_id'],x['to_event_id']) for x in links})==len(links),
       'duplicate sequel link')
    ck(all(x['from_prior_event_id'] in older_events and x['to_event_id'] in events
           and x['quality_effect']=='not_evaluated'
           and isinstance(x['inference'],bool)
           for x in links),'bad 2009 vs 2012 link')
    ck(all(x['inference'] is True for x in links if x['edge_type'] in
           ('cross_media_reinterpretation','mechanic_comparison','thematic_continuity',
            'referential_plot_link','protagonist_role_reversal')),
       'cross media interpretation falsely canon')
    ck(all(x['inference'] is False for x in links if x['edge_type'] in
           ('narrative_continuation','shared_actor_continuity','shared_mechanic')),
       'explicit series continuity incorrectly marked inferential')
    prior_mechanic_ids={m['mechanic_id'] for m in prior['mechanics']}
    others=set()
    for file in ['data/nova/v0.3/source_records/prince_mechanics.json',
                 'data/nova/v0.5/source_records/tomb_raider_survivor.json',
                 'data/nova/v0.6/source_records/tomb_raider_classic.json',
                 'data/nova/v0.7/source_records/tomb_raider_lau.json']:
        others|={m['mechanic_id'] for m in json.loads((ROOT/file).read_text(encoding='utf8'))['mechanics']}
    new=d['mechanics'];ids={m['mechanic_id'] for m in new}
    ck(len(ids)==len(new) and [m['mechanic_id'] for m in new]==[f'P2M-{i:03d}' for i in range(1,15)]
       and not ids.intersection(prior_mechanic_ids|others),'mechanic collisions or missing')
    ck(all(m['event_anchors'] and set(m['event_anchors'])<=set(events)
           and m['related_prototype_ids'] and set(m['related_prototype_ids'])<=prior_mechanic_ids
           and m['related_other_ids'] and set(m['related_other_ids'])<=others
           and len(m['abstraction_tr'])>=85 and len(m['guardrail_tr'])>=80
           and m['mechanism_inference'] is True and m['lumi_canon'] is False
           and m['quality_effect']=='not_evaluated'
           and m['editorial_stage']=='sourced_first_pass' and m['copyright_guardrail']
           for m in new),'mechanic source / guardrail / quality problem')
    evid=d['mechanic_evidence']
    expected={(m['mechanic_id'],e) for m in new for e in m['event_anchors']}
    actual={(x['mechanic_id'],x['event_id']) for x in evid}
    ck(expected==actual and len(actual)==len(evid),'evidence pair missing/duplicated')
    ck(all(e['event_id'] in events and e['work_id']=='PROTOTYPE2-2012'
           and e['source_ids']==events[e['event_id']]['source_ids']
           and e['confidence']==events[e['event_id']]['confidence']
           and e['quality_effect']=='not_evaluated' and e['lumi_canon'] is False
           for e in evid),'evidence confidence/source false')
    before=d['prior_links']
    expected_before={(m['mechanic_id'],z,'0.4') for m in new for z in m['related_prototype_ids']}
    expected_before|={(m['mechanic_id'],z,'other') for m in new for z in m['related_other_ids']}
    ck({(x['mechanic_id'],x['prior_mechanic_id'],x['source_version']) for x in before}==expected_before
       and len(before)==len(expected_before),'older mechanism graph broken')
    ck(all(x['relation']=='related_concept_not_equivalent'
       and x['quality_effect']=='not_evaluated' for x in before),'prior equivalence asserted')
    ck(len(d['editorial_boundaries'])==6
       and all(set(x['sources'])<=set(sources) for x in d['editorial_boundaries']),
       'continuity boundaries ungrounded')
    ck(len(c.get('continuity_firewall',[]))>=12,'continuity rules missing')
    ck(all((DOCS/f).is_file() and (DOCS/f).stat().st_size>130 for f in DOCS_EXPECTED),
       'generated documents missing')
    return {'status':'PASS' if not error else 'FAIL',
       'scope':'OFFLINE_SOURCE_TRACEABILITY_BELIEF_VS_WORLD_SEQUEL_LINKS_NOT_INDEPENDENT_GAMEPLAY_OR_STORY_QUALITY',
       'counts':{k:len(v) for k,v in d.items()},
       'low_confidence_endgame_events':sorted(LOW_CONFIDENCE),
       'story_quality_trials':0,'paid_calls':0,'production_changed':False,
       'errors':error}
if __name__=='__main__':
    try:r=validate()
    except Exception as ex:r={'status':'FAIL','fatal':repr(ex)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='PASS' else 1)
