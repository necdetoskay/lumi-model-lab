import copy
import json
import pytest
from src import lighthouse_atomic_audit_live as m
from src.plan_atomic_audit import compile_atomic_contract, validate_atomic_contract
from src.plan_audit_contract import compile_contract
from src.spineforge_v21_wire import project_payload


def auth():
    p,_,_=m.prepare();return {**p,'explicit_paid_authorization':True}


def response(data, negative=False):
    rows={r['span_id']:r['repaired_text'] for r in data['story_segments']}
    checks=[]
    for r in data['audit_contract']['requirements']:
        check={'requirement_id':r['id'],'span_ids':['S001'],'exact_text':rows['S001'],
               'reason':'Saved source evidence.','repair_span_ids':[],'assessment':'SATISFIED'}
        if negative:
            sid='S177' if r.get('parent_requirement_id')=='SCENE_SC05_ACTION' and 'bir üst basamakta' in r['source_quote'] else 'S200' if r.get('parent_requirement_id')=='SCENE_SC06_END_STATE' and 'Son görüntü:' in r['source_quote'] else None
            if sid: check.update(span_ids=[sid],exact_text=rows[sid],repair_span_ids=[sid],assessment='MATERIAL_VIOLATION')
        checks.append(check)
    observations=[{'family':'state_continuity','span_ids':['S008','S196'],'exact_text':rows['S196'],
                   'reason':'Missing object transfer.','material_impact':'Closing object possession unexplained.',
                   'classification':'DEFECT_SCENE'}] if negative else []
    return {'requirement_checks':checks,'observations':observations,'summary':'Control fixture.'}


def wrapped(stage,data,body):
    wire=project_payload(data)
    return {**body,'usage':{'cost_usd':.01,'latency_seconds':1,'api_calls':1,'input_tokens':100,'output_tokens':100,'reasoning_tokens':0,'total_tokens':200},
            'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}


def test_every_source_character_and_clause_context_is_retained():
    p=m.approved_input();parent=compile_contract(p,m.digest_json(p));c=compile_atomic_contract(p,m.digest_json(p))
    assert len(c['requirements'])==74
    for r in parent['requirements']:
        children=[q for q in c['requirements'] if q.get('parent_requirement_id')==r['id']]
        if children:
            assert ''.join(q['source_quote'] for q in children)==r['source_quote']
            for q in children: assert r['source_quote'][q['source_quote_start']:q['source_quote_end']]==q['source_quote']
    assert c['length_policy']['max_words'] is None
    assert validate_atomic_contract(c,p,m.digest_json(p))==c
    bad=copy.deepcopy(c);bad['requirements'][-1]['source_quote']='invented'
    with pytest.raises(ValueError):validate_atomic_contract(bad,p,m.digest_json(p))


def test_arbitrary_scene_ids_and_count_without_lighthouse_template():
    p=m.approved_input();p['scenes']=p['scenes'][:2]
    for i,s in enumerate(p['scenes']):s['scene_id']=f'CHAPTER_{i}'
    c=compile_atomic_contract(p,m.digest_json(p))
    assert c['scene_order']==['CHAPTER_0','CHAPTER_1']
    assert all('SC05' not in r['id'] for r in c['requirements'])


def test_atomic_qualification_requires_all_three_independent_errors():
    _,p,c=m.prepare();data=m.audit_payload(m.FLAWED.read_text(),p,c)
    r=response(data,True);chosen=m.decision(r,data['story_segments'],c,p,m.digest_json(p))
    assert m.qualification_passed('recorded_deviations',r,chosen)
    for key in ('rescue','ending','cord'):
        bad=copy.deepcopy(r)
        if key=='cord':bad['observations']=[]
        else:
            sid='S177' if key=='rescue' else 'S200'
            row=next(q for q in bad['requirement_checks'] if sid in q['repair_span_ids'])
            row.update(assessment='SATISFIED',repair_span_ids=[])
        assert not m.qualification_passed('recorded_deviations',bad,chosen)


def test_missing_atomic_requirement_cannot_accept():
    _,p,c=m.prepare();data=m.audit_payload(m.CLEAN.read_text(),p,c);r=response(data);r['requirement_checks'].pop()
    with pytest.raises(RuntimeError):m.decision(r,data['story_segments'],c,p,m.digest_json(p))


def test_failed_negative_control_stops_before_patch(tmp_path):
    calls=[]
    def fn(stage,data):calls.append(stage);return wrapped(stage,data,response(data))
    r=m.run(auth(),tmp_path,fn)
    assert calls==['AUDIT','AUDIT'] and r['status']=='QUALIFICATION_FAILED'
    assert r['confirmed_story_cost_usd']==2.10244886


def test_qualified_atomic_flow_with_actual_bounded_patch(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            s=next(x['repaired_text'] for x in data['story_segments'] if x['span_id']=='S200')
            body={'patches':[{'span_id':'S200','old_text':s,'replacement_text':'Ekin turned the empty cord inside her pocket as she caught up with Duru.'}],'summary':'Bounded patch fixture.'}
        else:body=response(data,len(calls)==2)
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='ACCEPT' and r['qualification_passed'] and calls==['AUDIT','AUDIT','PATCH','AUDIT']
    assert json.loads((tmp_path/m.ID/'patch-proof-01.json').read_text())['outside_patches_unchanged']
