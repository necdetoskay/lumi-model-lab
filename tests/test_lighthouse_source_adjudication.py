import copy
import json
import pytest
from src import lighthouse_source_adjudication as m
from src.source_adjudication import adjudication_payload, decision
from src.spineforge_v21_wire import project_payload


def auth():
    p,_,_=m.prepare();return {**p,'explicit_paid_authorization':True}


def response(data,negative=False):
    text={r['span_id']:r['repaired_text'] for r in data['story_segments']}
    f=[{'family':family,'severity':'moderate','repair_scope':'SCENE_REPAIR','span_ids':[sid],
        'exact_text':text[sid],'reason':'Exact source material contradiction.'}
       for family,sid in [('state_continuity','S196'),('spatial_consistency','S177'),('closure_integrity','S200')]] if negative else []
    return {'findings':f,'advisory_notes':[],'unresolved_material_issues':[],'summary':'Source verdict fixture.'}


def wrap(stage,data,body):
    wire=project_payload(data)
    return {**body,'usage':{'api_calls':1,'input_tokens':100,'output_tokens':100,'total_tokens':200,'reasoning_tokens':0,'cost_usd':.01,'latency_seconds':1},
            'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}


def test_source_notes_drop_prior_verdict_labels_and_expected_results():
    prepared,p,c=m.prepare();saved=json.loads(m.NEGATIVE_NOTES.read_text())[0]
    d=m.audit_payload(m.FLAWED.read_text(),p,c,saved)
    assert len(d['source_requirements'])==74
    assert all('assessment' not in r and 'repair_span_ids' not in r for r in d['candidate_evidence'])
    assert all('parent_source_quote' not in r for r in d['source_requirements'])
    assert d['approved_plan']==p and d['contract_sha256']==c['contract_sha256']
    bad=copy.deepcopy(saved);bad['input']['source_story_sha256']='drift'
    with pytest.raises(RuntimeError):m.audit_payload(m.FLAWED.read_text(),p,c,bad)


def test_nonempty_material_scope_is_required():
    _,p,c=m.prepare();d=m.audit_payload(m.FLAWED.read_text(),p,c);r=response(d,True)
    r['findings'][0]['span_ids']=[]
    with pytest.raises(RuntimeError):decision(r,d['story_segments'])


def test_invented_quote_or_unknown_scope_is_rejected():
    _,p,c=m.prepare();d=m.audit_payload(m.FLAWED.read_text(),p,c)
    for field,val in [('exact_text','invented'),('span_ids',['S999'])]:
        r=response(d,True);r['findings'][0][field]=val
        with pytest.raises(RuntimeError):decision(r,d['story_segments'])


def test_unresolved_material_never_authorizes_patch():
    _,p,c=m.prepare();d=m.audit_payload(m.FLAWED.read_text(),p,c);r=response(d,True)
    r['unresolved_material_issues']=['Material source mismatch needs resolution.']
    chosen=decision(r,d['story_segments']);assert chosen['status']=='UNRESOLVED' and chosen['findings']==[]


def test_failed_control_stops_without_patch(tmp_path):
    calls=[]
    def fn(stage,data):calls.append(stage);return wrap(stage,data,response(data))
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='QUALIFICATION_FAILED' and calls==['AUDIT','AUDIT']
    assert r['confirmed_story_cost_usd']==2.44645486


def test_qualified_controls_then_bounded_patch_and_full_source_audit(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            s=next(x['repaired_text'] for x in data['story_segments'] if x['span_id']=='S200')
            body={'patches':[{'span_id':'S200','old_text':s,'replacement_text':'Ekin turned the empty cord inside her pocket as she caught up with Duru.'}],'summary':'Bounded fixture.'}
        else:body=response(data,negative=len(calls)==2)
        return wrap(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='ACCEPT' and calls==['AUDIT','AUDIT','PATCH','AUDIT']
    assert r['qualification_passed'] and r['budget_committed_total_usd']==2.50645486
    assert json.loads((tmp_path/m.ID/'patch-proof-01.json').read_text())['outside_patches_unchanged']


def test_each_known_defect_group_is_required():
    _,p,c=m.prepare();d=m.audit_payload(m.FLAWED.read_text(),p,c);r=response(d,True)
    assert m.qualification_passed('recorded_deviations',r,decision(r,d['story_segments']))
    for i in range(3):
        bad=copy.deepcopy(r);bad['findings'].pop(i)
        assert not m.qualification_passed('recorded_deviations',bad,decision(bad,d['story_segments']))
