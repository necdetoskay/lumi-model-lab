#!/usr/bin/env python3
"""NOVA v0.6 Classic first pass: fail-closed data/provenance/chronology validation."""
import hashlib,json,sys
from collections import Counter
from build_tomb_raider_classic import BASE,ROOT,SRC,DOCS,TABLES

EXPECTED={'works':6,'sources':21,'story_events':36,'narrative_links':10,
    'supplementary_releases':3,'editorial_boundaries':3,'mechanics':19,
    'mechanic_evidence':54,'prior_links':38}
IDS=('TR96','TR97','TR98','TR99','TR00','TR03')
TIMES={'main_story_relative','legendary_past','historical_past','flashback_young_lara',
       'memorial_present','recalled_past','recalled_childhood','multi_time_lore',
       'memorial_frame','development_history'}
DOCUMENTS=('README.md','MECHANICS.md','CHRONOLOGY.md','SOURCE_REGISTER.md','CONTINUITY.md')
def records(key):
    return [json.loads(s) for s in (BASE/(key+'.jsonl')).read_text(encoding='utf8').splitlines() if s.strip()]
def validate():
    err=[]
    def ck(assertion,msg):
        if not assertion:err.append(msg)
    c=json.loads(SRC.read_text(encoding='utf8'))
    m=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    d={k:records(k) for k in TABLES}
    for k,n in EXPECTED.items():
        ck(len(d[k])==n,k+' count incorrect: '+str(len(d[k]))+' vs '+str(n))
        ck(m.get('counts',{}).get(k)==n,k+' manifest count mismatch')
        if k in c:ck(c[k]==d[k],k+' canonical derived data drift')
    ck(m.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'canonical sha hash drift')
    ck(m.get('schema_version')==c.get('schema_version')=='0.6.0-research-first-pass','version mismatch')
    ck(c.get('scope')=='tomb_raider_classic_core_design_six_games_only','Classic scope breached')
    ck(c.get('quality_effect')==m.get('quality_effect')=='not_evaluated','false quality proof')
    ck(c.get('lumi_canon') is False and c.get('lumi_production_modified') is False and
       m.get('lumi_production_modified') is False,'false LUMI canon or production claim')
    ck(c.get('story_quality_trials')==m.get('story_quality_trials')==0,'false story-quality trials')
    ck(c.get('paid_model_calls')==m.get('new_paid_model_calls')==0,'false paid model calls')
    ck(not records('quality_evaluations') and not records('lumi_usage_history'),
       'unperformed trial or production usage recorded')
    works=d['works']
    wk={w['work_id']:w for w in works}
    ck(tuple(wk)==IDS,'Classic work IDs not six games or incorrect order')
    ck(len(wk)==len(works),'duplicate Classic works')
    ck(tuple(w['year'] for w in works)==(1996,1997,1998,1999,2000,2003),'original release years shifted')
    ck(all(w['continuity']=='CLASSIC_CORE_DESIGN' and w.get('lumi_canon') is False
         and w.get('quality_effect')=='not_evaluated' for w in works),'cross continuity work canon')
    sources={s['source_id']:s for s in d['sources']}
    ck(len(sources)==len(d['sources']),'duplicate research source IDs')
    ck(all(s['url'].startswith('https://www.tombraider.com/') and
           s['verification']=='web_search_result_retrieved' and
           s['publisher']=='Tomb Raider official franchise editorial site'
           for s in sources.values()),'unsupported source or false independent verification')
    ck(all(w['source_ids'] and set(w['source_ids'])<=set(sources) for w in works),
       'work missing provenance')
    events={e['event_id']:e for e in d['story_events']}
    ck(len(events)==len(d['story_events']),'duplicate event IDs')
    ck(Counter(e['work_id'] for e in events.values())==Counter({x:6 for x in IDS}),
       'wrong 6 events per classic work')
    for wid in IDS:
        prefix={'TR96':'C96','TR97':'C97','TR98':'C98',
          'TR99':'C99','TR00':'C00','TR03':'C03'}[wid]
        ck([e['event_id'] for e in d['story_events'] if e['work_id']==wid]==
           [f'{prefix}-{i:02d}' for i in range(1,7)],wid+' ids incorrect')
    ck(all(e['work_id'] in wk and e['source_ids'] and
           set(e['source_ids'])<=set(sources) and
           len(e['observed_event_tr'])>=70 and
           e['narrated_time_type'] in TIMES and
           e['editorial_stage']=='sourced_first_pass' and
           e['evidence_strength']=='official_editorial_retrospective_not_gameplay_audited'
           for e in events.values()),'bad source/event chronology/claim status')
    ck(all(e['claim_kind']=='observed_game_story' for e in events.values()
           if e['event_id']!='C03-06'),'false event editorial type')
    ck(events['C03-06']['claim_kind']=='development_plan_not_game_canon' and
       events['C03-06']['narrated_time_type']=='development_history',
       'cut Putai training promoted to published game')
    ck(events['C00-01']['narrated_time_type']=='memorial_present' and
       events['C00-02']['narrated_time_type']=='recalled_past' and
       events['C00-03']['narrated_time_type']=='recalled_childhood' and
       events['C99-01']['narrated_time_type']=='flashback_young_lara',
       'Chronicles framing time or Lara youth mixed with game chronology')
    links=d['narrative_links']
    ck(len({(x['from_event_id'],x['to_event_id']) for x in links})==len(links),
       'duplicate narrative edges')
    ck(all(x['from_event_id'] in events and x['to_event_id'] in events and
            x['quality_effect']=='not_evaluated' and
            x['claim_scope']=='compare_narration_and_history_not_directed_game_chronology'
            for x in links),'broken / falsely causal timeline connection')
    ck(all(x['inference'] is True for x in links if x['edge_kind'] in
           ('retrospective_narration','within_work_thematic_mirror',
            'cross_work_structural_parallel','narrative_continuity')),
       'interpretive links wrongly declared canon fact')
    ck(all(x['inference'] is False for x in links if x['edge_kind'] in
           ('in_world_prior_event','frame_consequence')),
       'source continuity links wrongly marked inference')
    releases=d['supplementary_releases']
    ck({x['release_id'] for x in releases}=={
       'CLASSIC-I-III-REMASTERED-2024','CLASSIC-IV-VI-REMASTERED-2025',
       'TR97-GOLDEN-MASK-BONUS'},'edition double count or dropped')
    ck(all(x['covers_work_ids'] and set(x['covers_work_ids'])<=set(wk)
           and x['source_id'] in sources for x in releases),'invalid edition parent / source')
    b=d['editorial_boundaries']
    ck({x['issue_id'] for x in b}=={
       'CL-BOUNDARY-001','CL-BOUNDARY-002','CL-BOUNDARY-003'},'canon boundary missing')
    ck(all(set(x['source_ids'])<=set(sources) for x in b),'editorial boundary lacks source')
    prev={}
    for ver,path in [('0.3',ROOT/'data/nova/v0.3/source_records/prince_mechanics.json'),
                     ('0.4',ROOT/'data/nova/v0.4/source_records/prototype_2009.json'),
                     ('0.5',ROOT/'data/nova/v0.5/source_records/tomb_raider_survivor.json')]:
        old=json.loads(path.read_text(encoding='utf8'))
        prev[ver]={x['mechanic_id'] for x in old['mechanics']}
    old_ids=set.union(*prev.values())
    mechs=d['mechanics']
    mids={x['mechanic_id'] for x in mechs}
    ck(len(mids)==len(mechs) and [x['mechanic_id'] for x in mechs]==
       [f'TRC-{i:03d}' for i in range(1,20)],'new mechanisms not unique or out of sequence')
    ck(not mids.intersection(old_ids),'old mechanic ID duplicated')
    ck(all(x['evidence_anchors'] and set(x['evidence_anchors'])<=set(events)
           and set(x['related_survivor_mechanics'])<=prev['0.5']
           and set(x['related_older_mechanics'])<=prev['0.3']|prev['0.4']
           and len(x['abstraction_tr'])>=80 and len(x['guardrail_tr'])>=80
           and x['editorial_stage']=='sourced_first_pass'
           and x['quality_effect']=='not_evaluated'
           and x['lumi_canon'] is False and x['mechanism_inference'] is True
           and x['copyright_guardrail'] for x in mechs),
       'mechanic evidence/guardrail/quality is inconsistent')
    em=d['mechanic_evidence']
    expected={(m['mechanic_id'],id) for m in mechs for id in m['evidence_anchors']}
    actual={(x['mechanic_id'],x['event_id']) for x in em}
    ck(expected==actual and len(expected)==len(em),'source-based evidence missing or duplicated')
    for e in em:
        row=events.get(e['event_id'])
        ck(row is not None and e['work_id']==row['work_id']
           and e['source_ids']==row['source_ids']
           and e['claim_kind']==row['claim_kind']
           and e['narrated_time_type']==row['narrated_time_type']
           and e['quality_effect']=='not_evaluated' and e['lumi_canon'] is False,
           'evidence observation/source drift: '+e['evidence_id'])
    pl=d['prior_links']
    exp={(m['mechanic_id'],id,'0.5') for m in mechs for id in m['related_survivor_mechanics']}
    exp|={(m['mechanic_id'],id,'prior') for m in mechs for id in m['related_older_mechanics']}
    ck({(x['mechanic_id'],x['older_mechanic_id'],x['prior_version']) for x in pl}==exp
       and len(pl)==len(exp),'broken previous-mechanic links')
    ck(all(x['quality_effect']=='not_evaluated' and
           x['relation']=='related_concept_not_equivalent' for x in pl),
       'mechanism similarity asserted as equivalence')
    ck(len(c.get('continuity_firewall',[]))>=10,'continuity firewall missing')
    ck(all((DOCS/x).is_file() and (DOCS/x).stat().st_size>150 for x in DOCUMENTS) and
       all((DOCS/'works'/(w.lower()+'.md')).is_file() for w in IDS),
       'generated docs missing')
    return {'status':'PASS' if not err else 'FAIL',
      'scope':'OFFLINE_STRUCTURE_PROVENANCE_AND_FRAMING_NOT_INDEPENDENT_GAMEPLAY_AUDIT',
      'counts':{k:len(v) for k,v in d.items()},'errors':err,
      'story_quality_trials':0,'paid_calls':0,'lumi_production_modified':False}
if __name__=='__main__':
    try:r=validate()
    except Exception as exc:r={'status':'FAIL','fatal':repr(exc)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='PASS' else 1)
