#!/usr/bin/env python3
"""Fail-closed NOVA v0.5 Tomb Raider Survivor provenance and data contract validation."""
import json,hashlib,sys
from collections import Counter
from build_tomb_raider import ROOT,BASE,SRC,DOCS,TABLES

EXPECTED={'works':3,'sources':18,'story_events':37,'character_states':9,
          'cross_work_links':10,'supplementary_releases':3,'mechanics':18,
          'mechanic_evidence':59,'prior_links':46}
EXPECTED_WORKS=('TR2013','RISE2015','SHADOW2018')
EXPECTED_EVENTS={'TR2013':12,'RISE2015':12,'SHADOW2018':13}
DOCS_EXPECTED=('README.md','MECHANICS.md','CHARACTER_ARC.md',
               'CROSS_GAME.md','SOURCES.md','CONTINUITY_FIREWALL.md')

def read(name):
    return [json.loads(line) for line in (BASE/(name+'.jsonl')).read_text(encoding='utf8').splitlines() if line.strip()]

def validate():
    errors=[]
    def assert_true(value,reason):
        if not value:errors.append(reason)
    source=json.loads(SRC.read_text(encoding='utf8'))
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    compiled={name:read(name) for name in TABLES}
    for k,n in EXPECTED.items():
        assert_true(len(compiled[k])==n,f'{k}: {len(compiled[k])} != {n}')
        assert_true(manifest.get('counts',{}).get(k)==n,'manifest expected count wrong: '+k)
        if k in source:
            assert_true(compiled[k]==source[k],'source->derived drift: '+k)
    assert_true(manifest.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),
                'canonical source SHA mismatch')
    assert_true(source.get('schema_version')==manifest.get('schema_version')=='0.5.0-research-first-pass',
                'schema version mismatch')
    assert_true(source.get('scope')=='tomb_raider_survivor_trilogy_only','scope widened into other timeline')
    assert_true(source.get('lumi_canon') is False and source.get('quality_effect')=='not_evaluated'
                and manifest.get('quality_effect')=='not_evaluated','false canon/quality promotion')
    assert_true(source.get('story_quality_trials')==manifest.get('story_quality_trials')==0,
                'fake story trial number')
    assert_true(source.get('new_paid_model_calls')==manifest.get('new_paid_model_calls')==0,
                'fake paid call number')
    assert_true(source.get('lumi_production_modified') is False and
                manifest.get('lumi_production_modified') is False,'production modified')
    assert_true(not read('quality_evaluations') and not read('lumi_usage_history'),
                'unperformed evaluation/usage must be empty')
    works=compiled['works']
    wids={x['work_id'] for x in works}
    assert_true(tuple(x['work_id'] for x in works)==EXPECTED_WORKS,'three works out of order / not distinct')
    assert_true(tuple(x['year'] for x in works)==(2013,2015,2018),'release years changed')
    assert_true(all(x.get('continuity')=='SURVIVOR_TRILOGY' and x.get('lumi_canon') is False
                    and x.get('quality_effect')=='not_evaluated' for x in works),'work promoted to canon')
    sources={x['source_id']:x for x in compiled['sources']}
    assert_true(len(sources)==len(compiled['sources']),'duplicate source ids')
    assert_true(all(x.get('url','').startswith('https://www.tombraider.com/') and
                    x.get('verification')=='web_search_result_retrieved'
                    and x.get('publisher','').startswith('Tomb Raider official') for x in sources.values()),
                'unverified source/provenance promotion')
    events={x['event_id']:x for x in compiled['story_events']}
    assert_true(len(events)==len(compiled['story_events']),'duplicate event id')
    for wid,n in EXPECTED_EVENTS.items():
        subset=[e for e in compiled['story_events'] if e['work_id']==wid]
        assert_true(len(subset)==n,'events per game wrong: '+wid)
    assert_true(tuple(x['event_id'] for x in compiled['story_events'])==
       tuple([f'T13-{i:02d}' for i in range(1,13)]+
             [f'R15-{i:02d}' for i in range(1,13)]+
             [f'S18-{i:02d}' for i in range(1,14)]),'source event order/id changed')
    assert_true(all(x['work_id'] in wids and set(x['source_ids'])<=set(sources)
                and x['source_ids'] and len(x['observed_event_tr'])>=90
                and x.get('editorial_stage')=='sourced_first_pass'
                and x.get('confidence')=='publisher_editorial_retrospective_not_gameplay_audited'
                and x.get('chronological_scope')=='main_plot_relative_not_all_gameplay'
                and x.get('character_state_delta_tr') for x in events.values()),
                'orphan event/source or overclaimed gameplay chronology')
    assert_true(all(x['source_ids'] and set(x['source_ids'])<=set(sources) for x in works),
                'work missing source provenance')
    states=compiled['character_states']
    assert_true(len({x['state_id'] for x in states})==len(states),'duplicate character state')
    assert_true([x['state_id'] for x in states]==[f'TR-ARC-{i:02d}' for i in range(1,10)],
                'ordered character growth markers changed')
    assert_true(all(x['work_id'] in wids and x['anchor_event_id'] in events
                    and events[x['anchor_event_id']]['work_id']==x['work_id']
                    and x['interpretation'] is True and x['quality_effect']=='not_evaluated'
                    for x in states),'character memory/event state wrong')
    links=compiled['cross_work_links']
    assert_true(len({(x['from_event_id'],x['to_event_id']) for x in links})==len(links),
                'duplicate cross game links')
    byyear={w['work_id']:w['year'] for w in works}
    assert_true(all(x['from_event_id'] in events and x['to_event_id'] in events and
                byyear[events[x['from_event_id']]['work_id']]<
                byyear[events[x['to_event_id']]['work_id']]
                and x['quality_effect']=='not_evaluated'
                and ((x['edge_kind']=='interpretive_comparison' and x['inference'] is True) or
                     (x['edge_kind']=='franchise_continuity' and x['inference'] is False))
                for x in links),'cross timeline links invalid/unmarked')
    expected_releases={'TR2013-DE-2014','RISE-20TH-2016','SHADOW-DE-2019'}
    assert_true({x['release_id'] for x in compiled['supplementary_releases']}==expected_releases,
                'edition double-counted or missing')
    assert_true(all(x['work_id'] in wids and x['source_ids'] and
                    set(x['source_ids'])<=set(sources)
                    for x in compiled['supplementary_releases']),'release parent/source invalid')
    pop=json.loads((ROOT/'data/nova/v0.3/source_records/prince_mechanics.json').read_text(encoding='utf8'))
    prt=json.loads((ROOT/'data/nova/v0.4/source_records/prototype_2009.json').read_text(encoding='utf8'))
    pid={m['mechanic_id'] for m in pop['mechanics']}
    rid={m['mechanic_id'] for m in prt['mechanics']}
    new=compiled['mechanics']
    mid={m['mechanic_id'] for m in new}
    assert_true(len(mid)==len(new) and [m['mechanic_id'] for m in new]==
                [f'TRS-{i:03d}' for i in range(1,19)],'mechanic id duplicate or not ordered')
    assert_true(not (mid & pid or mid & rid),'mechanic collision previous version')
    assert_true(all(m['evidence_anchors'] and set(m['evidence_anchors'])<=set(events)
         and len(m['abstraction_tr'])>=90 and len(m['guardrail_tr'])>=90
         and m.get('copyright_guardrail') and m.get('mechanism_inference') is True
         and m.get('editorial_stage')=='sourced_first_pass'
         and m.get('quality_effect')=='not_evaluated' and m.get('lumi_canon') is False
         and set(m['related_pop_ids'])<=pid and set(m['related_prt_ids'])<=rid
         for m in new),'mechanic evidence/copyright/quality/previous ids invalid')
    ev=compiled['mechanic_evidence']
    expected={(m['mechanic_id'],a) for m in new for a in m['evidence_anchors']}
    actual={(x['mechanic_id'],x['event_id']) for x in ev}
    assert_true(expected==actual and len(actual)==len(ev),'mechanic evidence link wrong')
    for x in ev:
        eid=x['event_id']
        if eid not in events:
            errors.append('evidence points to missing event: '+eid)
            continue
        event=events[eid]
        assert_true(x['work_id']==event['work_id'] and
                    x['source_ids']==event['source_ids'] and
                    x['observed_event_tr']==event['observed_event_tr']
                    and x.get('mechanism_inference') is True and
                    x.get('quality_effect')=='not_evaluated' and x.get('lumi_canon') is False,
                    'evidence claims wrong observation: '+x['evidence_id'])
    prior=compiled['prior_links']
    expected_prior={(m['mechanic_id'],r,'0.3') for m in new for r in m['related_pop_ids']}
    expected_prior|={(m['mechanic_id'],r,'0.4') for m in new for r in m['related_prt_ids']}
    actual_prior={(l['mechanic_id'],l['prior_mechanic_id'],l['prior_version']) for l in prior}
    assert_true(actual_prior==expected_prior and len(actual_prior)==len(prior),
                'cross corpus connection missing/duplicated or wrong version')
    assert_true(all(l['relation']=='related_concept_not_equivalent' and
                     l['quality_effect']=='not_evaluated' for l in prior),
                'mechanics equivalence falsely proved')
    assert_true(len(source.get('continuity_firewall',[]))>=9,'insufficient continuity rules')
    assert_true(all((DOCS/x).is_file() and (DOCS/x).stat().st_size>150 for x in DOCS_EXPECTED)
         and all((DOCS/'works'/(w.lower()+'.md')).is_file() for w in EXPECTED_WORKS),
         'missing generated docs')
    return {'status':'PASS' if not errors else 'FAIL',
       'scope':'OFFLINE_STRUCTURE_PROVENANCE_CROSS_WORK_AND_FIREWALL_NOT_GAMEPLAY_EXPERT_AUDIT',
       'counts':{k:len(v) for k,v in compiled.items()},
       'story_quality_trials':0,'new_paid_api_calls':0,'lumi_production_modified':False,
       'errors':errors}
if __name__=='__main__':
    try:r=validate()
    except Exception as ex:r={'status':'FAIL','fatal':repr(ex)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='PASS' else 1)
