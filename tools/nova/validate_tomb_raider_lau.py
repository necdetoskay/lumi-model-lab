#!/usr/bin/env python3
"""Fail-closed NOVA v0.7 LAU research provenance/continuity validator."""
import hashlib,json,sys
from collections import Counter
from build_tomb_raider_lau import ROOT,BASE,SRC,DOCS,TABLES

EXPECTED={'works':3,'sources':17,'story_events':36,'narrative_chronology':3,
 'narrative_links':16,'artifacts':7,'remake_analogues':5,
 'editorial_boundaries':6,'mechanics':18,'mechanic_evidence':50,'prior_links':36}
WORK_IDS=('LEG2006','ANN2007','UND2008')
DOCS_EXPECTED=('README.md','MECHANICS.md','CHRONOLOGY.md','ARTIFACTS.md',
              'REMAKE_FIREWALL.md','SOURCES.md','CONTINUITY.md')
def rows(name):
    return [json.loads(line) for line in (BASE/(name+'.jsonl')).read_text(encoding='utf8').splitlines() if line.strip()]
def validate():
    errors=[]
    def ck(ok,why):
        if not ok:errors.append(why)
    source=json.loads(SRC.read_text(encoding='utf8'))
    manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    data={key:rows(key) for key in TABLES}
    for key,n in EXPECTED.items():
        ck(len(data[key])==n,f'{key}: {len(data[key])} != {n}')
        ck(manifest.get('counts',{}).get(key)==n,'manifest count drift: '+key)
        if key in source:ck(data[key]==source[key],'source-derived drift: '+key)
    ck(manifest.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'source sha drift')
    ck(manifest.get('schema_version')==source.get('schema_version')=='0.7.0-research-first-pass',
       'schema version invalid')
    ck(source.get('scope')=='legend_anniversary_underworld_trilogy_original_main_games','scope drift')
    ck(source.get('quality_effect')==manifest.get('quality_effect')=='not_evaluated',
       'unproven positive quality effect')
    ck(source.get('lumi_canon') is False and source.get('lumi_production_modified') is False
       and manifest.get('lumi_production_modified') is False,'canon/production breach')
    ck(source.get('story_quality_trials')==manifest.get('story_quality_trials')==0,
       'fabricated story trial')
    ck(source.get('paid_model_calls')==manifest.get('new_paid_model_calls')==0,
       'fabricated paid model call')
    ck(not rows('quality_evaluations') and not rows('lumi_usage_history'),
       'nonexistent evaluations/usage must be empty')
    works={w['work_id']:w for w in data['works']}
    ck(len(works)==3 and tuple(works)==WORK_IDS,'missing/mixed/duplicated LAU work')
    ck(tuple(x['release_year'] for x in data['works'])==(2006,2007,2008),
       'incorrect release chronology')
    ck(all(w['continuity']=='LEGEND_ANNIVERSARY_UNDERWORLD'
           and w['quality_effect']=='not_evaluated' and w['lumi_canon'] is False
           and w['source_ids'] for w in works.values()),'wrong work continuity or canon')
    chronology={x['work_id']:x for x in data['narrative_chronology']}
    ck(len(chronology)==3 and set(chronology)==set(works),'chronology references bad works')
    ck([chronology[x]['story_rank'] for x in ('ANN2007','LEG2006','UND2008')]==[1,2,3],
       'Anniversary->Legend->Underworld story order corrupted')
    ck([chronology[x]['release_rank'] for x in WORK_IDS]==[1,2,3],
       'Legend->Anniversary->Underworld release order corrupted')
    src={x['source_id']:x for x in data['sources']}
    ck(len(src)==len(data['sources']),'duplicate source')
    ck(all(x['url'].startswith('https://www.tombraider.com/') and
           x['publisher']=='Tomb Raider official site' and
           x['verification']=='web_search_result_retrieved_2026-10-15'
           for x in src.values()),'fake provenance or source')
    ck(all(set(w['source_ids'])<=set(src) for w in works.values()),'work missing source')
    ev={x['event_id']:x for x in data['story_events']}
    ck(len(ev)==36 and len(data['story_events'])==len(ev),'duplicate event')
    ck(Counter(x['work_id'] for x in ev.values())==
       Counter({'LEG2006':12,'ANN2007':12,'UND2008':12}),'12 events per work broken')
    for wid,prefix in (('LEG2006','L06'),('ANN2007','A07'),('UND2008','U08')):
        ck([x['event_id'] for x in data['story_events'] if x['work_id']==wid]==
            [f'{prefix}-{i:02d}' for i in range(1,13)],wid+' event identifiers changed')
    ck(all(x['work_id'] in works and x['source_ids'] and
           set(x['source_ids'])<=set(src) and
           len(x['observation_tr'])>=80 and
           x['evidence_strength']=='official_editorial_retrospective_not_gameplay_audited'
           and x['editorial_stage']=='sourced_first_pass' and x['lumi_canon'] is False
           for x in ev.values()),'observation missing source, ungrounded or certainty inflated')
    ck(ev['L06-01']['event_type']=='personal_backstory' and
       ev['L06-04']['event_type']=='revealed_past' and
       ev['A07-12']['event_type']=='meta_narrative_remake' and
       ev['U08-01']['event_type']=='narrative_presentation_frame',
       'chronology semantic type regression')
    connections=data['narrative_links']
    ck(len({(x['from_event_id'],x['to_event_id'],x['link_type']) for x in connections})
       ==len(connections),'duplicate narrative edge')
    ck(all(x['from_event_id'] in ev and x['to_event_id'] in ev
           and x['quality_effect']=='not_evaluated'
           and isinstance(x['inference'],bool) for x in connections),
           'broken narrative links')
    ex={(x['from_event_id'],x['to_event_id'],x['link_type']) for x in connections}
    required={('L06-12','U08-04','artifact_causal_transfer'),
      ('A07-11','U08-10','reveal_continuity'),
      ('L06-11','U08-09','question_answer'),
      ('A07-12','L06-02','chronological_series_order'),
      ('U08-01','U08-04','presentation_to_actual_cause')}
    ck(required<=ex,'story continuity or presentation links missing')
    req_prereqs={('U08-02','U08-07'),('U08-03','U08-07'),('U08-06','U08-07'),
                 ('U08-07','U08-12')}
    actual_prereqs={(x['from_event_id'],x['to_event_id']) for x in connections
                    if x['link_type']=='prerequisite'}
    ck(actual_prereqs==req_prereqs,'Thor hammer prerequisite chain incomplete / unexpected')
    ck(all(x['inference'] is False for x in connections if x['link_type'] in
           ('prerequisite','chronological_series_order','artifact_causal_transfer',
            'question_answer','causal_knowledge','reveal_continuity')),
           'source-established causal link retyped as interpretation')
    ck(all(x['inference'] is True for x in connections if x['link_type'] in
           ('thematic_parallel','technical_family_comparison','artifact_dependency_comparison',
            'myth_cross_text_reinterpretation')),
           'interpretive relation improperly promoted to fact')
    # Forward prerequisite dependency subgraph must not contain a cycle.
    successor={}
    for a,b in actual_prereqs:successor.setdefault(a,[]).append(b)
    visited,stack=set(),set()
    def dfs(node):
        if node in stack:return False
        if node in visited:return True
        stack.add(node)
        for nex in successor.get(node,[]):
            if not dfs(nex):return False
        stack.remove(node);visited.add(node)
        return True
    ck(all(dfs(node) for node in successor),'prerequisite cyclic')
    artifacts={x['artifact_id']:x for x in data['artifacts']}
    ck(len(artifacts)==7,'duplicate artifact IDs')
    ck(all(x['primary_work_id'] in works and x['event_refs'] and
           set(x['event_refs'])<=set(ev) and x['is_copy_of_prior_timeline'] is False
           and x['state_note'] for x in artifacts.values()),'artifact provenance broken')
    ck(artifacts['LAU-ART-07']['event_refs']==['U08-07','U08-12'],
       'hammer artifact changed')
    ck({'LAU-ART-04','LAU-ART-05','LAU-ART-06','LAU-ART-07'}<=set(artifacts),
       'Thor system missing distinct pieces')
    classic=json.loads((ROOT/'data/nova/v0.6/source_records/tomb_raider_classic.json').read_text(encoding='utf8'))
    classic_events={e['event_id'] for e in classic['story_events']}
    analogues=data['remake_analogues']
    ck(len({(x['lau_event_id'],x['classic_event_id']) for x in analogues})==len(analogues),
       'remake links duplicated')
    ck(all(x['lau_event_id'] in ev and ev[x['lau_event_id']]['work_id']=='ANN2007'
           and x['classic_event_id'] in classic_events
           and x['link_type']=='remake_analogue_not_same_event_or_canon'
           and x['quality_effect']=='not_evaluated' for x in analogues),
       'Classic 1996 accidentally merged into LAU timeline')
    boundaries={x['id']:x for x in data['editorial_boundaries']}
    ck(len(boundaries)==6,'editorial boundaries missing')
    ck(all(set(x['sources'])<=set(src) and x['note'] for x in boundaries.values()),
       'editorial boundaries missing evidence')
    ck('main_game_vs_dlc' in {x['type'] for x in boundaries.values()} and
       'released_vs_early_prototype' in {x['type'] for x in boundaries.values()},
       'DLC or pre-release canon firewall missing')
    prior_paths=[
      ROOT/'data/nova/v0.3/source_records/prince_mechanics.json',
      ROOT/'data/nova/v0.4/source_records/prototype_2009.json',
      ROOT/'data/nova/v0.5/source_records/tomb_raider_survivor.json',
      ROOT/'data/nova/v0.6/source_records/tomb_raider_classic.json']
    previous=set()
    for path in prior_paths:
        previous|={m['mechanic_id'] for m in json.loads(path.read_text(encoding='utf8'))['mechanics']}
    mech=data['mechanics']
    ids={x['mechanic_id'] for x in mech}
    ck(len(ids)==len(mech) and [x['mechanic_id'] for x in mech]==
        [f'LAU-{i:03d}' for i in range(1,19)] and not ids.intersection(previous),
       'mechanic IDs duplicate or clash')
    ck(all(x['event_anchors'] and set(x['event_anchors'])<=set(ev)
           and x['prior_mechanic_ids'] and set(x['prior_mechanic_ids'])<=previous
           and len(x['abstraction_tr'])>=90 and len(x['guardrail_tr'])>=85
           and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
           and x['inference'] is True and x['editorial_stage']=='sourced_first_pass'
           and x['copyright_guardrail'] for x in mech),
       'mechanic evidence, guardrail or quality invalid')
    evidence=data['mechanic_evidence']
    expected={(m['mechanic_id'],a) for m in mech for a in m['event_anchors']}
    pairs={(x['mechanic_id'],x['event_id']) for x in evidence}
    ck(expected==pairs and len(pairs)==len(evidence),'mechanic evidence missing/duplicated')
    ck(all(x['event_id'] in ev and x['work_id']==ev[x['event_id']]['work_id']
           and x['source_ids']==ev[x['event_id']]['source_ids']
           and x['event_type']==ev[x['event_id']]['event_type']
           and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
           for x in evidence),'evidence work/source/event type drift')
    old=data['prior_links']
    expected_prior={(m['mechanic_id'],ref) for m in mech for ref in m['prior_mechanic_ids']}
    ck({(x['mechanic_id'],x['prior_mechanic_id']) for x in old}==expected_prior
       and len(old)==len(expected_prior),'prior links drift')
    ck(all(x['relation']=='conceptually_related_not_equivalent'
           and x['quality_effect']=='not_evaluated' for x in old),
       'prior mechanics promoted as equivalent')
    ck(len(source.get('continuity_firewall',[]))>=14,'firewall incomplete')
    ck(all((DOCS/p).is_file() and (DOCS/p).stat().st_size>170 for p in DOCS_EXPECTED) and
       all((DOCS/'works'/(x.lower()+'.md')).is_file() for x in WORK_IDS),
       'expected docs missing')
    return {'status':'PASS' if not errors else 'FAIL','scope':
      'OFFLINE_STRUCTURE_PROVENANCE_CHRONOLOGY_REMAKE_AND_DEPENDENCY_NOT_STORY_QUALITY',
      'counts':{k:len(v) for k,v in data.items()},
      'prerequisite_edges':len(actual_prereqs),
      'story_quality_trials':0,'new_paid_model_calls':0,
      'lumi_production_modified':False,'errors':errors}
if __name__=='__main__':
    try:res=validate()
    except Exception as ex:res={'status':'FAIL','fatal':repr(ex)}
    print(json.dumps(res,ensure_ascii=False,indent=2))
    sys.exit(0 if res['status']=='PASS' else 1)
