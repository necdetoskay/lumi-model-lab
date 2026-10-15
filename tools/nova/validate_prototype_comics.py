#!/usr/bin/env python3
"""NOVA v0.9 fail-closed provenance, serialized comic issue, inferred mechanic validator."""
import hashlib,json,sys
from collections import Counter
from build_prototype_comics import ROOT,BASE,SRC,DOCS,TABLES
EXPECTED={'works':3,'sources':9,'issues':6,'story_observations':12,
 'unverified_candidate_claims':4,'prior_game_links':5,'mechanics':12,
 'mechanic_evidence':33,'mechanic_prior_links':25}
ARC_IDS=('PC-ANCHOR','PC-SURVIVORS','PC-LABYRINTH')
DOCS_REQUIRED=('README.md','WORKS_AND_ISSUES.md','OBSERVATIONS.md','MECHANICS.md',
 'PENDING_CLAIMS.md','CROSS_GAME.md','SOURCES.md','FIREWALL.md')
def rows(k):
    return [json.loads(line) for line in (BASE/(k+'.jsonl')).read_text(encoding='utf8').splitlines() if line.strip()]
def validate():
    errors=[]
    def ck(valid,why):
        if not valid:errors.append(why)
    c=json.loads(SRC.read_text(encoding='utf8'))
    meta=json.loads((BASE/'manifest.json').read_text(encoding='utf8'))
    data={k:rows(k) for k in TABLES}
    for k,n in EXPECTED.items():
        ck(len(data[k])==n,f'count {k}: {len(data[k])}, expected {n}')
        ck(meta.get('counts',{}).get(k)==n,'manifest mismatch: '+k)
        if k in c:ck(data[k]==c[k],'canonical to compiled drift '+k)
    ck(meta.get('source_sha256')==hashlib.sha256(SRC.read_bytes()).hexdigest(),'canonical SHA drift')
    ck(meta.get('schema_version')==c.get('schema_version')=='0.9.0-research-first-pass','schema mismatch')
    ck(c.get('scope')=='prototype2_darkhorse_2012_3_comic_arcs_6_digital_issues','scope drift')
    ck(c.get('quality_effect')==meta.get('quality_effect')=='not_evaluated'
       and c.get('lumi_canon') is False,'canon or quality promoted')
    ck(c.get('story_quality_trials')==meta.get('story_quality_trials')==0,'story trial fabricated')
    ck(c.get('new_paid_model_calls')==meta.get('new_paid_model_calls')==0,'paid model calls fabricated')
    ck(c.get('lumi_production_modified') is False and meta.get('lumi_production_modified') is False,'LUMI touched')
    ck(c.get('primary_comic_panels_examined')==meta.get('primary_comic_panels_examined')==0,
       'claimed full-text comic review not performed')
    ck(not rows('quality_evaluations') and not rows('lumi_usage_history'),'invented trial or production usage')
    work={w['work_id']:w for w in data['works']}
    ck(len(work)==3 and tuple(work)==ARC_IDS,'must have three arcs exactly')
    ck(all(w['media_type']=='digital_comic_story_arc' and
       w['continuity']=='PROTOTYPE_CROSS_MEDIA_BRIDGE' and
       w['year']==2012 and w['writer']=='Dan Jolley'
       and w['independent_full_text_audit'] is False
       and w['editorial_stage']=='publisher_premise_and_solicitation_first_pass'
       and w['quality_effect']=='not_evaluated' and w['lumi_canon'] is False
       for w in work.values()),'comic arcs falsely promoted or wrong')
    src={s['source_id']:s for s in data['sources']}
    ck(len(src)==9,'duplicated sources')
    ck(all(s['url'].startswith('https://') and s['verification']=='web_result_or_page_opened'
       and s['retrieval_date']=='2026-10-16' for s in src.values()),
       'false source verification')
    ck(src.get('PC-PUBLISHER',{}).get('evidence_tier')=='primary_publisher' and
       src.get('PC-STEAM-REPOST',{}).get('evidence_tier')=='community_republication'
       and src.get('PC-OBNB',{}).get('evidence_tier')=='independent_bibliography',
       'sources hierarchy changed')
    ck(all(w['provenance_ids'] and set(w['provenance_ids'])<=set(src)
           for w in work.values()),'arc source invalid')
    issues=data['issues']
    ck([i['issue_id'] for i in issues]==[f'PC-ISS-{j:02d}' for j in range(1,7)],
       'issue count/IDs sequence drift')
    ck([i['digital_edition_issue_number'] for i in issues]==list(range(1,7)),
       'issue numbering drift')
    ck(Counter(i['arc_id'] for i in issues)==Counter({k:2 for k in ARC_IDS}),
       'issues not two per story arc')
    ck(all(i['arc_id'] in work and i['part_number'] in (1,2)
           and i['publication_year']==2012
           and i['exact_on_sale_date'] is None
           and i['issue_date_status'].startswith('publisher_launch_and_biweekly_plan_only')
           and i['actual_panels_examined'] is False
           and i['plot_premise_source_id']=='PC-STEAM-REPOST'
           and i['quality_effect']=='not_evaluated' for i in issues),
       'fictitious issue dates or panel audit')
    col=c['collection']
    ck(col['collection_id']=='PC-COLL-2012' and col['isbn13']=='9781595829184'
       and col['page_count']==80 and col['is_independent_story'] is False
       and col['year']==2012
       and col['contains_issues']==[i['issue_id'] for i in issues]
       and set(col['source_ids'])=={'PC-OBNB','PC-OPENLIBRARY'},
       'collected edition double counted or ungrounded')
    ev={e['event_id']:e for e in data['story_observations']}
    ck(len(ev)==12 and [e['event_id'] for e in data['story_observations']]==
       [f'PC-E{i:02d}' for i in range(1,13)],'observation IDs duplicate or missing')
    ck(Counter(e['work_id'] for e in ev.values())==Counter({k:4 for k in ARC_IDS}),
       'four synopsis observations per arc expected')
    ck(all(e['source_ids'] and 'PC-STEAM-REPOST' in e['source_ids']
           and set(e['source_ids'])<=set(src)
           and e['work_id'] in work and e['part_number'] in (1,2)
           and len(e['observed_public_summary_tr'])>90
           and e['is_publisher_confirmed_story_detail'] is False
           and e['evidence_tier']=='reproduced_issue_promo_blurb_not_verified_full_pages'
           and e['confidence']=='first_pass_solicitation_only'
           and e['editorial_stage']=='sourced_first_pass'
           and e['story_quality_effect']=='not_evaluated'
           for e in ev.values()),'marketing blurb overclaimed as seen panels or missing source')
    ck(all(i['part_number'] in (1,2) for i in issues) and
       set((e['work_id'],e['part_number']) for e in ev.values())==
       set((i['arc_id'],i['part_number']) for i in issues),
       'story blurb issue map incomplete')
    pending=data['unverified_candidate_claims']
    ck(len({x['candidate_id'] for x in pending})==4,
       'pending detail candidates missing/duplicated')
    ck(all(x['status'].startswith('not_evidence_pending')
           and x['exclude_from_mechanic_evidence'] is True
           and set(x['source_ids'])<=set(src)
           for x in pending),'fan claims promoted to comic canon')
    prior_2009=json.loads((ROOT/'data/nova/v0.4/source_records/prototype_2009.json').read_text(encoding='utf8'))
    prior_2012=json.loads((ROOT/'data/nova/v0.8/source_records/prototype2_2012.json').read_text(encoding='utf8'))
    prior_ids={e['event_id'] for e in prior_2009['story_events']}|\
              {e['event_id'] for e in prior_2012['story_events']}
    cross=data['prior_game_links']
    ck(len({x['link_id'] for x in cross})==len(cross),'duplicate cross-game links')
    ck(all(x['prior_event_id'] in prior_ids and x['target_work_id'] in work
           and x['quality_effect']=='not_evaluated' and isinstance(x['inference'],bool)
           for x in cross),'prior game event link orphan')
    ck(all(x['inference'] is True for x in cross if x['kind'] in
          ('research_question_not_proven_causality','thematic_exploration_not_exact_event_identity',
           'cross_media_world_state_comparison')),
       'interpretations promoted to objective causal facts')
    ck(all(x['inference'] is False for x in cross if x['kind'] in
          ('publisher_promised_prequel','publisher_promised_interstitial_continuity')),
       'explicit marketing scope misclassified')
    prior_mechs=set()
    for file in [
      'data/nova/v0.3/source_records/prince_mechanics.json',
      'data/nova/v0.4/source_records/prototype_2009.json',
      'data/nova/v0.5/source_records/tomb_raider_survivor.json',
      'data/nova/v0.6/source_records/tomb_raider_classic.json',
      'data/nova/v0.7/source_records/tomb_raider_lau.json',
      'data/nova/v0.8/source_records/prototype2_2012.json'
    ]:
        prior_mechs|={m['mechanic_id'] for m in json.loads((ROOT/file).read_text(encoding='utf8'))['mechanics']}
    mechs=data['mechanics']
    mids={x['mechanic_id'] for x in mechs}
    ck(len(mids)==12 and not mids.intersection(prior_mechs)
       and [x['mechanic_id'] for x in mechs]==[f'PCM-{i:03d}' for i in range(1,13)],
       'new mechanism IDs duplicated/overlap')
    ck(all(m['evidence_anchors'] and set(m['evidence_anchors'])<=set(ev)
           and m['related_prior_mechanic_ids'] and
           set(m['related_prior_mechanic_ids'])<=prior_mechs
           and len(m['abstraction_tr'])>=90 and len(m['guardrail_tr'])>=90
           and m['mechanism_inference'] is True
           and m['evidence_scope']=='reproduced_promotional_synopsis_only'
           and m['editorial_stage']=='first_pass_unverified_panels'
           and m['quality_effect']=='not_evaluated' and m['lumi_canon'] is False
           and m['copyright_guardrail']
           for m in mechs),'unsupported mechanics, incorrect guardrails or quality overclaim')
    derived=data['mechanic_evidence']
    expected_pairs={(m['mechanic_id'],eid) for m in mechs for eid in m['evidence_anchors']}
    actual_pairs={(x['mechanic_id'],x['observation_id']) for x in derived}
    ck(expected_pairs==actual_pairs and len(actual_pairs)==len(derived),
       'mechanic->observation evidences missing or duplicated')
    issue_by_pair={(i['arc_id'],i['part_number']):i['issue_id'] for i in issues}
    ck(all(x['observation_id'] in ev
       and x['work_id']==ev[x['observation_id']]['work_id']
       and x['issue_id']==issue_by_pair.get((ev[x['observation_id']]['work_id'],ev[x['observation_id']]['part_number']))
       and x['source_ids']==ev[x['observation_id']]['source_ids']
       and x['evidence_tier']==ev[x['observation_id']]['evidence_tier']
       and x['evidence_scope']=='solicitation_paraphrase_not_panel_audit'
       and x['quality_effect']=='not_evaluated' and x['lumi_canon'] is False
       for x in derived),'evidence falsely upgraded from promotional summary')
    mech_links=data['mechanic_prior_links']
    expected_links={(m['mechanic_id'],ref) for m in mechs for ref in m['related_prior_mechanic_ids']}
    got={(x['mechanic_id'],x['prior_mechanic_id']) for x in mech_links}
    ck(expected_links==got and len(got)==len(mech_links),'cross-version mechanic IDs missing or duplicated')
    ck(all(x['relation']=='related_concept_not_equivalent' and
           x['quality_effect']=='not_evaluated' for x in mech_links),'unproven equivalence')
    ck(len(c['firewall'])>=12,'missing media/copyright firewall')
    ck(all((DOCS/x).is_file() and (DOCS/x).stat().st_size>=150 for x in DOCS_REQUIRED),
       'generated documentation missing')
    return {'status':'PASS' if not errors else 'FAIL',
      'scope':'METADATA_AND_REPUBLISHED_SOLICITATIONS_ONLY_NOT_INDEPENDENT_COMIC_PAGE_AUDIT',
      'counts':{k:len(v) for k,v in data.items()},
      'primary_comic_panels_examined':0,'story_quality_trials':0,
      'paid_model_calls':0,'lumi_production_modified':False,'errors':errors}
if __name__=='__main__':
    try:out=validate()
    except Exception as exc:out={'status':'FAIL','fatal':repr(exc)}
    print(json.dumps(out,ensure_ascii=False,indent=2))
    sys.exit(0 if out['status']=='PASS' else 1)
