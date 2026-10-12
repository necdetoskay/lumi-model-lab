import json,copy
from pathlib import Path
import pytest
from src.spineforge_simple_story import SimpleConfigV1,Extraction,extracted_state,prepare,execute,request_for,verify_saved
from src.spineforge_production_compact_ranges import range_table
from src.spineforge_seeded_design import verify_frozen_seed
from src.spineforge_relay_v1_contracts import canonical_sha256

FOLDER=Path('tests/fixtures/story_scenarios_v1')
PROSE='Nisa atlasın içinden kırmızı ayracı aldı. Nisa ve Eren Cem’den özür diledi. Nisa kırmızı ayracı hazırlık defterine koydu. Üçü okuma etkinliğine başladı.'

def paths(tmp_path):
    tmp_path.mkdir(parents=True,exist_ok=True)
    config=tmp_path/'config.json';config.write_text(json.dumps(SimpleConfigV1().model_dump(mode='json')),encoding='utf8')
    return [FOLDER/'library-bookmark-request.json',FOLDER/'library-bookmark-seed.json',FOLDER/'library-bookmark-frozen-seed.json',config]

def extraction(seed,prose=PROSE):
    table=range_table(prose);rid=next(r[0] for r in table['ranges'] if r[1:]==[0,len(table['units'])-1])
    changes=[('/objects/red_bookmark/state/container','"preparation_notebook"'),('/objects/blue_atlas/state/contains','[]'),('/objects/preparation_notebook/state/contains','["red_bookmark"]')]
    return dict(source_sha256=table['source_sha256'],seed_sha256=canonical_sha256(seed),changes=[dict(path=p,value_json=v,source_range_id=rid) for p,v in changes],resolved_threads=[dict(id=i,source_range_id=rid) for i in seed.open_threads],satisfied_obligations=[dict(id=o.id,source_range_id=rid) for o in seed.narrative_obligations],uncertainties=[])

def fake(config,calls,defect=None):
    def invoke(**kwargs):
        stage=kwargs['request_class'].split('_simple_')[-1];payload=json.loads(kwargs['user_prompt']);calls.append(stage)
        assert kwargs['max_tokens'] is None
        if stage=='ideator':raw=dict(ideas=[dict(id='I'+str(i),synopsis='Fikir '+str(i),conflict='Çatışma '+str(i),character_decision='Karar '+str(i),resolution='Çözüm '+str(i),distinctiveness='Yaklaşım '+str(i)) for i in (1,2,3)])
        elif stage=='selector':raw=dict(selected_id='I2',reason='Synthetic choice',quality_limitations=['Synthetic control; no originality judgment'])
        elif stage=='planner':raw=dict(beats=[dict(purpose='Amaç',action='Eylem',consequence='Sonuç') for _ in range(payload['request']['scene_count'])],ending='Çözüm')
        elif stage=='writer':raw=None
        elif stage=='extractor':
            seed=verify_frozen_seed(FOLDER/'library-bookmark-seed.json',FOLDER/'library-bookmark-frozen-seed.json');raw=extraction(seed,payload['candidate_prose'])
            if defect=='stale_extraction':raw['source_sha256']='0'*64
        else:
            rewrite=defect=='nonconvergent' or defect in ['prose_repair','extraction_repair'] and calls.count('reviewer')==1
            raw=dict(source_sha256=payload['source_range_table']['source_sha256'],candidate_state_sha256=payload['candidate_state_sha256'],decision='REWRITE' if rewrite else 'PASS',findings=[dict(category='STATE_EXTRACTION' if defect=='extraction_repair' else 'PROSE',reason='Synthetic blocker',repair_instruction='Repair indicated artifact',source_range_id=payload['source_range_table']['ranges'][0][0])] if rewrite else [],summary='Synthetic review, not semantic gold')
        text=PROSE if raw is None else json.dumps(raw,ensure_ascii=False)
        kwargs_expected=request_for(stage,{k:v for k,v in payload.items() if k!='output_schema'},config)[1]
        assert 'max_tokens' not in kwargs_expected
        cost=2.0 if defect=='over_budget' else .01
        body=dict(id='synthetic-'+str(len(calls)),model=kwargs['model'],choices=[dict(finish_reason='length' if defect=='truncated' else 'stop',message=dict(content=text))],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30,cost=cost))
        return text,body,kwargs_expected
    return invoke

def run(tmp_path,defect=None):
    inputs=paths(tmp_path/'inputs');config=SimpleConfigV1();calls=[]
    result=execute(request_path=inputs[0],seed_path=inputs[1],freeze_path=inputs[2],config_path=inputs[3],preflight=prepare(*inputs),output=tmp_path/'run',api_key='synthetic',call_fn=fake(config,calls,defect))
    return result,calls

def test_full_story_and_state_come_from_prose_not_plan(tmp_path):
    before=(FOLDER/'library-bookmark-seed.json').read_bytes();result,calls=run(tmp_path)
    assert result['status']=='ACCEPT' and result['provider_calls']==6
    assert calls==['ideator','selector','planner','writer','extractor','reviewer']
    final=json.loads((tmp_path/'run'/'accepted-state.json').read_text())
    assert final['objects']['red_bookmark']['state']['container']=='preparation_notebook'
    assert final['revision']==1 and (FOLDER/'library-bookmark-seed.json').read_bytes()==before
    assert (tmp_path/'run'/'ideas.json').exists() and (tmp_path/'run'/'selection.json').exists()
    assert verify_saved(tmp_path/'run')['status']=='OFFLINE_SIMPLE_REPLAY_PASS'

@pytest.mark.parametrize('defect,count,accepted,writer_calls',[('prose_repair',9,True,2),('extraction_repair',8,True,1),('nonconvergent',9,False,2)])
def test_single_repair_targets_wrong_artifact_and_never_third_attempt(tmp_path,defect,count,accepted,writer_calls):
    result,calls=run(tmp_path,defect)
    assert result['provider_calls']==count and calls.count('writer')==writer_calls
    assert result['state_advanced']==accepted
    assert (tmp_path/'run'/'accepted-state.json').exists()==accepted
    if accepted:assert verify_saved(tmp_path/'run')['provider_calls']==count

@pytest.mark.parametrize('defect,count',[('stale_extraction',6),('truncated',1),('over_budget',1)])
def test_fail_closed_without_state_or_retry(tmp_path,defect,count):
    result,calls=run(tmp_path,defect)
    assert result['status']=='REJECT_NON_CONVERGENT' and len(calls)==count
    assert not (tmp_path/'run'/'accepted-state.json').exists()
    if defect=='over_budget':assert result['known_cost_usd']=='2.0'

@pytest.mark.parametrize('path,value',[('/revision','1'),('/world/rules','[]'),('/world/spatial/positions/Nisa','"elsewhere"'),('/characters/Invented/location','"library_reading_room"'),('/objects/red_bookmark/location','"unknown_room"'),('/objects/red_bookmark/state/container','NaN')])
def test_extractor_cannot_mutate_canon_metadata_or_invent_entity_location(path,value):
    seed=verify_frozen_seed(FOLDER/'library-bookmark-seed.json',FOLDER/'library-bookmark-frozen-seed.json');raw=extraction(seed);raw['changes'][0].update(path=path,value_json=value);before=canonical_sha256(seed)
    with pytest.raises(ValueError):extracted_state(seed,PROSE,Extraction.model_validate(raw))
    assert canonical_sha256(seed)==before

def test_overlapping_changes_and_stale_citations_reject():
    seed=verify_frozen_seed(FOLDER/'library-bookmark-seed.json',FOLDER/'library-bookmark-frozen-seed.json');raw=extraction(seed)
    raw['changes'].append(copy.deepcopy(raw['changes'][0]))
    with pytest.raises(ValueError,match='Overlapping'):extracted_state(seed,PROSE,Extraction.model_validate(raw))
    raw['changes']=raw['changes'][:1];raw['changes'][0]['source_range_id']='missing'
    with pytest.raises(ValueError,match='range'):extracted_state(seed,PROSE,Extraction.model_validate(raw))

def test_container_contents_inconsistency_rejects_before_freeze():
    seed=verify_frozen_seed(FOLDER/'library-bookmark-seed.json',FOLDER/'library-bookmark-frozen-seed.json');raw=extraction(seed);raw['changes']=raw['changes'][:1]
    with pytest.raises(ValueError,match='Container'):extracted_state(seed,PROSE,Extraction.model_validate(raw))

def test_saved_prose_tampering_is_detected(tmp_path):
    run(tmp_path);(tmp_path/'run'/'assembled-story.md').write_text('changed',encoding='utf8')
    with pytest.raises(ValueError,match='hash'):verify_saved(tmp_path/'run')
