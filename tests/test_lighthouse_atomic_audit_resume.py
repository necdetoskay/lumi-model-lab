import json
from pathlib import Path
import pytest
from src import lighthouse_atomic_audit_resume as m
from tests.test_lighthouse_atomic_audit_live import response,wrapped


def auth():
    p,_,_=m.prepare();return {**p,'explicit_paid_authorization':True}


def test_real_saved_clean_replay_accepts_without_call(tmp_path):
    calls=[]
    def fn(stage,data):calls.append(stage);return wrapped(stage,data,response(data))
    r=m.run(auth(),tmp_path,fn)
    assert calls==['AUDIT'] and r['cases'][0]['status']=='ACCEPT' and r['cases'][0]['passed']
    assert r['status']=='QUALIFICATION_FAILED' and r['new_call_count']==1 and r['new_cost_usd']==.01
    proof=json.loads((tmp_path/m.ID/'clean_control-citation-proof.json').read_text())
    assert len(proof)==1 and proof[0]['added_span_id']=='S168'
    assert not proof[0]['assessment_changed'] and not proof[0]['repair_scope_changed']


def test_qualified_resume_repair_does_not_rebill_clean(tmp_path):
    calls=[]
    def fn(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            s=next(x['repaired_text'] for x in data['story_segments'] if x['span_id']=='S200')
            body={'patches':[{'span_id':'S200','old_text':s,'replacement_text':'Ekin turned the empty cord inside her pocket as she caught up with Duru.'}],'summary':'Bounded fixture.'}
        else:body=response(data,negative=len(calls)==1)
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='ACCEPT' and calls==['AUDIT','PATCH','AUDIT']
    assert r['new_cost_usd']==.03 and r['confirmed_story_cost_usd']==2.28228086
    assert r['qualification_passed'] and json.loads((tmp_path/m.ID/'patch-proof-01.json').read_text())['outside_patches_unchanged']


def test_saved_clean_input_drift_stops_before_call(tmp_path,monkeypatch):
    saved=json.loads(m.SAVED_CLEAN.read_text());saved[0]['input']['source_story_sha256']='drift'
    folder=tmp_path/'saved';folder.mkdir();f=folder/'calls.json';f.write_text(json.dumps(saved))
    (folder/'prepared-input.json').write_bytes((m.SAVED_CLEAN.parent/'prepared-input.json').read_bytes())
    monkeypatch.setattr(m,'SAVED_CLEAN',f)
    r=m.run(auth(),tmp_path,lambda *_:pytest.fail('no call'))
    assert r['status']=='REJECT_RUNTIME' and r['new_call_count']==0


def test_material_bad_citation_remains_rejected(tmp_path):
    def fn(stage,data):
        body=response(data,True)
        row=next(x for x in body['requirement_checks'] if x['repair_span_ids']==['S177'])
        row['span_ids']=['S176']
        return wrapped(stage,data,body)
    r=m.run(auth(),tmp_path,fn)
    assert r['status']=='REJECT_RUNTIME' and r['new_call_count']==1 and not r['qualification_passed']


def test_runtime_freezes_saved_clean_prompt_and_checkpoint():
    prepared,_,_=m.prepare();paths={r['path'] for r in prepared['runtime_manifest']}
    assert str(m.SAVED_CLEAN) in paths and str(m.SAVED_CLEAN.parent/'prepared-input.json') in paths
    assert prepared['reuse_clean_audit_with_same_input_prompt_contract'] is True
    assert prepared['max_new_calls']==5
