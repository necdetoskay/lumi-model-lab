import json
from copy import deepcopy
from pathlib import Path
import pytest
import src.lighthouse_decision_qualification as q
from tests.test_lighthouse_experiment import usage


def grant():
    p,_=q.prepare()
    return {k:v for k,v in p.items() if k!='runtime_manifest'} | {'explicit_paid_authorization':True,'authorization_id':'FAKE-DECISION'}


def answer(data):
    from tests.test_lighthouse_audit_decision import empty
    d=empty(data['story_segments']);d['usage']=usage()
    if 'wide entrance stairs' in data['full_story']:
        fs=json.loads(Path('evidence/lighthouse-editorial/independent-review-03.json').read_text())['findings']
        for i,f in enumerate(fs):
            d['requirement_checks'][i].update(span_ids=f['span_ids'],exact_text=f['exact_text'],
                reason=f['reason'],repair_span_ids=f['span_ids'],assessment='MATERIAL_VIOLATION')
    return d


def test_two_saved_versions_consumed_once_without_story_change(tmp_path):
    before={p:p.read_bytes() for _,p in q.CASES};calls=[]
    def call(d):calls.append(d);return answer(d)
    r=q.run(grant(),tmp_path,call)
    assert r['status']=='PASS' and len(calls)==2 and r['story_edits']==0
    assert before=={p:p.read_bytes() for _,p in q.CASES}
    with pytest.raises(FileExistsError):q.run(grant(),tmp_path,call)


def test_negative_control_cannot_pass_with_empty_defects(tmp_path):
    def call(d):
        a=answer(d)
        for row in a['requirement_checks']:row.update(assessment='SATISFIED',repair_span_ids=[])
        return a
    r=q.run(grant(),tmp_path,call)
    assert r['status']=='QUALIFICATION_FAILED' and not r['cases'][1]['passed']


def test_budget_reservation_stops_without_dispatch(tmp_path,monkeypatch):
    monkeypatch.setattr(q,'BUDGET',q.PRIOR)
    r=q.run(grant(),tmp_path,lambda d:pytest.fail('No paid call allowed'))
    assert r['new_call_count']==0 and r['status']=='REJECT_RUNTIME'


def test_missing_cost_does_not_continue_to_next_case(tmp_path):
    r=q.run(grant(),tmp_path,lambda d:{k:v for k,v in answer(d).items() if k!='usage'})
    assert r['new_call_count']==1 and not r['accounting_complete']


def test_manifest_drift_fails_before_consumption(tmp_path):
    a=grant();a['runtime_manifest_sha256']='bad'
    with pytest.raises(RuntimeError):q.run(a,tmp_path,answer)
    assert not list(tmp_path.iterdir())
