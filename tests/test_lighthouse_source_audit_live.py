import copy
import json
from pathlib import Path
import pytest
from src import lighthouse_source_audit_live as m
from src.spineforge_v21_wire import project_payload


def response(data, negative=False):
    rows={r['span_id']:r['repaired_text'] for r in data['story_segments']}
    checks=[{'requirement_id':r['id'],'span_ids':['S001'], 'exact_text':rows['S001'],
             'reason':'Saved source evidence.', 'repair_span_ids':[], 'assessment':'SATISFIED'}
            for r in data['audit_contract']['requirements']]
    observations=[]
    if negative:
        for check in checks:
            sid={'SCENE_SC05_ACTION':'S177','SCENE_SC06_END_STATE':'S200'}.get(check['requirement_id'])
            if sid:
                check.update(span_ids=[sid],exact_text=rows[sid],repair_span_ids=[sid],assessment='MATERIAL_VIOLATION')
        observations=[{'family':'state_continuity','span_ids':['S008','S196'],
                       'exact_text':rows['S196'],'reason':'Missing causal object transfer.',
                       'material_impact':'Closing object possession is unexplained.','classification':'DEFECT_SCENE'}]
    return {'requirement_checks':checks,'observations':observations,'summary':'Recorded-control test response.'}


def wrapped(stage,data,body):
    wire=project_payload(data)
    return {**body,'usage':{'cost_usd':.01,'latency_seconds':1,'api_calls':1,'input_tokens':100,'output_tokens':100,'reasoning_tokens':0,'total_tokens':200},
            'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}


def auth():
    prepared,_,_=m.prepare()
    return {**prepared,'explicit_paid_authorization':True}


def test_real_source_plan_and_contract_binding():
    prepared,plan,contract=m.prepare()
    assert len(contract['requirements'])==16
    assert contract['length_policy']=={'min_words':1400,'max_words':None}
    assert prepared['prior_confirmed_cost_usd']==1.95169086
    assert prepared['max_new_calls']==6 and prepared['writer_calls']==0
    assert all('expected' not in x for x in prepared['cases'])


def test_missing_cord_detection_fails_gate():
    _,plan,contract=m.prepare();data=m.audit_payload(m.FLAWED.read_text(),plan,contract)
    raw=response(data,True);chosen=m.decision(raw,data['story_segments'],contract,plan,m.digest_json(plan))
    assert m.qualification_passed('recorded_deviations',raw,chosen)
    raw['observations']=[]
    assert not m.qualification_passed('recorded_deviations',raw,chosen)


def test_controls_fail_no_patch(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        return wrapped(stage,data,response(data))
    result=m.run(auth(),tmp_path,fn)
    assert calls==['AUDIT','AUDIT'] and result['status']=='QUALIFICATION_FAILED'
    assert result['new_cost_usd']==.02
    with pytest.raises(FileExistsError): m.run(auth(),tmp_path,fn)


def test_invalid_quote_stops_without_paid_retry(tmp_path):
    def fn(stage,data):
        r=response(data);r['requirement_checks'][0]['exact_text']='fabricated evidence'
        return wrapped(stage,data,r)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='REJECT_RUNTIME' and r['new_call_count']==1 and r['new_calls_accounting_complete']


def test_unknown_charge_reserves_and_stops(tmp_path):
    def fn(*_): raise RuntimeError('No provider body delivered')
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='REJECT_RUNTIME' and r['new_call_count']==1
    assert r['unknown_call_reserve_usd']>.04 and not r['new_calls_accounting_complete']
    assert r['accounting_complete'] is False


def test_provider_error_retains_usage_and_evidence(tmp_path):
    class Fail(RuntimeError):
        usage={'cost_usd':.007,'latency_seconds':2,'api_calls':1,'input_tokens':20,'output_tokens':20,'reasoning_tokens':0,'total_tokens':40}
        provider_evidence={'id':'saved-provider-id','phase':'response_validation'}
    def fn(*_): raise Fail('invalid JSON')
    r=m.run(auth(),tmp_path,fn)
    rows=json.loads((tmp_path/m.ID/'calls.json').read_text())
    assert r['new_cost_usd']==.007 and r['unknown_call_reserve_usd']==.04
    assert rows[0]['provider_evidence']['id']=='saved-provider-id'


def test_no_expected_labels_sent_to_model():
    _,p,c=m.prepare();d=m.audit_payload(m.FLAWED.read_text(),p,c)
    assert set(d)=={'full_story','story_segments','approved_plan','reader_profile','source_story_sha256','audit_contract'}


def test_actual_request_drift_stops_after_usage_logged(tmp_path):
    def fn(stage,data):
        r=wrapped(stage,data,response(data));r['request']['max_tokens']=10;return r
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='REJECT_RUNTIME' and r['new_call_count']==1 and r['new_cost_usd']==.01


def test_complete_bounded_flow_uses_real_patch_proof(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            s=next(r for r in data['story_segments'] if r['span_id']=='S200')['repaired_text']
            body={'patches':[{'span_id':'S200','old_text':s,'replacement_text':'Ekin turned the empty cord inside her pocket as she caught up with Duru.'}], 'summary':'Change within approved scope.'}
        else: body=response(data,negative=len(calls)==2)
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert calls==['AUDIT','AUDIT','PATCH','AUDIT'] and r['status']=='ACCEPT'
    proof=json.loads((tmp_path/m.ID/'patch-proof-01.json').read_text())
    assert proof['outside_patches_unchanged'] is True
    assert r['budget_committed_total_usd']==2.03169086


def test_authorization_drift_prevents_every_call(tmp_path):
    a=auth();a['max_new_calls']=10
    with pytest.raises(RuntimeError,match='drift'):m.run(a,tmp_path,lambda *_:pytest.fail('must not call'))


def test_two_patch_limit_stops_even_if_auditor_keeps_finding_defects(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            s=next(r for r in data['story_segments'] if r['span_id']=='S177')['repaired_text']
            replacement=s.replace('half-flight','one step') if 'half-flight' in s else s.replace('one step','two steps')
            body={'patches':[{'span_id':'S177','old_text':s,'replacement_text':replacement}], 'summary':'Bounded test change.'}
        else: body=response(data,negative=len(calls)!=1)
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert calls==['AUDIT','AUDIT','PATCH','AUDIT','PATCH','AUDIT']
    assert r['status']=='BOUNDED_REPAIR_INCOMPLETE' and not (tmp_path/m.ID/'accepted-story.txt').exists()


def test_false_positive_clean_control_blocks_repair(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage);body=response(data,negative=len(calls)==2)
        if len(calls)==1:
            body['requirement_checks'][0].update(assessment='MATERIAL_VIOLATION',repair_span_ids=['S001'])
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='QUALIFICATION_FAILED' and calls==['AUDIT','AUDIT']


def test_budget_uses_actual_cumulative_cost_before_next_call(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage);r=wrapped(stage,data,response(data));r['usage']['cost_usd']=.99;return r
    r=m.run(auth(),tmp_path,fn)
    assert r['new_call_count']==1 and r['status']=='REJECT_RUNTIME'
    assert 'budget limit' in r['failure'] and r['budget_committed_total_usd']<3
