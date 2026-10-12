import json,copy
from pathlib import Path
import pytest
from src.spineforge_production_state_effects import effect_context,effect_schema,resolve_effect_guard
from src.spineforge_production_compact_ranges import range_table,resolve_range_guard
from src.spineforge_production_compact_range_story import build_chain
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_production_pipeline import prepare,execute
from src.spineforge_production_config import RunConfigV1
from tests.test_spineforge_relay_v1_production_pipeline import sample,provider

ROOT=Path('evidence/spineforge-relay/SFR-V1-Q22-PLAN-V4-MYSTERY-20261009')

def case():
    plan,contract,state=build_chain(ROOT/'plan-1-fixture.json')[4][-1]
    prose=json.loads((ROOT/'story'/f'{plan.scene_id}-1-writer-text.json').read_text())['text'].strip()
    raw=json.loads(json.loads((ROOT/'story'/f'{plan.scene_id}-1-guard-text.json').read_text())['text'])
    context=effect_context(state,contract);table=range_table(prose)
    field=next(f for f in context['fields'] if f[1]=='/objects/red_bookmark/state/container')
    unit=next(i for i,u in enumerate(table['units']) if 'hazırlık defterindeki' in u[2])
    source=next(r[0] for r in table['ranges'] if r[1:]==[unit,unit])
    raw['state_effect_audit']=dict(audit_id=context['audit_id'],status='COMPLETE',observed_effects=[dict(field_id=field[0],observed_value_json='"preparation_notebook"',source_range_id=source)])
    return prose,raw,context,table

def test_q22_observed_containment_conflict_blocks_without_mutating_state():
    prose,raw,context,_=case();snapshot=copy.deepcopy(context)
    report,findings,proof=resolve_effect_guard(raw,prose,context)
    assert report.residual.decision=='PASS'  # Original event/residual review missed this.
    assert [f.code for f in findings]==['PROSE_STATE_EFFECT_MISMATCH']
    assert '/objects/red_bookmark/state/container' in findings[0].message
    assert 'hazırlık defterindeki' in findings[0].evidence[0]
    assert proof['effects'][0]['projected_after'] is None and not proof['effects'][0]['matches']
    assert context==snapshot

def test_historical_guard_is_preserved_but_cannot_omit_new_audit():
    prose,raw,context,_=case();raw.pop('state_effect_audit')
    assert resolve_range_guard(raw,prose).residual.decision=='PASS'
    with pytest.raises(ValueError):resolve_effect_guard(raw,prose,context)

@pytest.mark.parametrize('defect',['stale','unknown_field','unknown_range','duplicate','nonfinite','overflow','duplicate_json_key','incomplete'])
def test_bad_effect_evidence_cannot_admit_scene(defect):
    prose,raw,context,_=case();audit=raw['state_effect_audit'];row=audit['observed_effects'][0]
    if defect=='stale':audit['audit_id']='0'*64
    elif defect=='unknown_field':row['field_id']='missing'
    elif defect=='unknown_range':row['source_range_id']='missing'
    elif defect=='duplicate':audit['observed_effects'].append(copy.deepcopy(row))
    elif defect=='nonfinite':row['observed_value_json']='NaN'
    elif defect=='overflow':row['observed_value_json']='1e999'
    elif defect=='duplicate_json_key':row['observed_value_json']='{"a":1,"a":2}'
    elif defect=='incomplete':audit['status']='INCOMPLETE'
    if defect=='incomplete':
        assert 'STATE_EFFECT_SCAN_INCOMPLETE' in [f.code for f in resolve_effect_guard(raw,prose,context)[1]]
    else:
        with pytest.raises(ValueError):resolve_effect_guard(raw,prose,context)

def test_matching_report_value_and_bound_schema_do_not_prove_extraction_truth():
    prose,raw,context,table=case();raw['state_effect_audit']['observed_effects'][0]['observed_value_json']='null'
    assert not resolve_effect_guard(raw,prose,context)[1]
    schema=effect_schema(table,context)
    assert schema['$defs']['EffectAuditV1']['properties']['audit_id']['enum']==[context['audit_id']]
    assert schema['$defs']['ObservedEffectV1']['properties']['field_id']['enum']==[f[0] for f in context['fields']]

def test_boolean_effect_is_not_integer_one():
    prose,raw,context,_=case()
    field=next(f for f in context['fields'] if f[1]=='/objects/red_bookmark/state/found')
    row=raw['state_effect_audit']['observed_effects'][0];row['field_id']=field[0];row['observed_value_json']='1'
    assert resolve_effect_guard(raw,prose,context)[1][0].code=='PROSE_STATE_EFFECT_MISMATCH'

def test_missing_projected_field_is_not_null():
    prose,raw,context,_=case()
    field=next(f for f in context['fields'] if f[1]=='/objects/red_bookmark/state/container')
    field[3]=False
    context['audit_id']=canonical_sha256({k:v for k,v in context.items() if k!='audit_id'})
    raw['state_effect_audit']['audit_id']=context['audit_id']
    raw['state_effect_audit']['observed_effects'][0]['observed_value_json']='null'
    _,findings,proof=resolve_effect_guard(raw,prose,context)
    assert findings and proof['fidelity_audit']['findings'][0]['recorded_exists'] is False

def test_effect_scan_nonconvergence_stops_real_pipeline_before_freeze(tmp_path):
    paths,design=sample(tmp_path/'inputs','dialogue');config=RunConfigV1();calls=[];fake=provider(config,design,calls)
    def incomplete(**kwargs):
        text,body,actual=fake(**kwargs)
        if 'candidate_prose' in json.loads(kwargs['user_prompt']):
            raw=json.loads(text);raw['state_effect_audit']['status']='INCOMPLETE';text=json.dumps(raw)
            body['choices'][0]['message']['content']=text
        return text,body,actual
    pf=prepare(paths['request'],paths['seed'],paths['freeze'],paths['config'])
    result=execute(request_path=paths['request'],seed_path=paths['seed'],freeze_path=paths['freeze'],config_path=paths['config'],preflight=pf,output=tmp_path/'run',api_key='synthetic',call_fn=incomplete)
    assert result['status']=='REJECT_NON_CONVERGENT' and result['provider_calls']==6
    assert result['story_result']['state_advanced_to_revision']==0
    assert not list((tmp_path/'run'/'story').glob('*-accepted.json'))
    assert result['story_result']['accepted_scenes']==[]
