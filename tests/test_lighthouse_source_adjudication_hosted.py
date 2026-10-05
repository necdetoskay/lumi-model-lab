import json
import pytest
from src import lighthouse_source_adjudication_hosted as m
from tests.test_lighthouse_source_adjudication import response,wrap


def authorization():
    p,_,_=m.prepare();return {**p,'explicit_paid_authorization':True}


def test_hosted_reserve_and_paid_cancellation_gate(tmp_path,monkeypatch):
    p,_,_=m.prepare();assert p['hosted_runner_cost_reserve_usd']==.10
    f=tmp_path/'proof.json';f.write_text(json.dumps({'superseded_run_id':m.SUPERSEDED_RUN,'superseded_commit':m.SUPERSEDED_COMMIT,'confirmed_cancelled':True,'paid_step_never_started':False}))
    monkeypatch.setattr(m,'CANCELLATION_PROOF',f)
    with pytest.raises(RuntimeError,match='not proven'):m.run(authorization(),tmp_path,lambda *_:pytest.fail('no call'))


def test_no_duplicate_old_call_and_hosted_reserve_in_total(tmp_path,monkeypatch):
    f=tmp_path/'proof.json';f.write_text(json.dumps({'superseded_run_id':m.SUPERSEDED_RUN,'superseded_commit':m.SUPERSEDED_COMMIT,'confirmed_cancelled':True,'paid_step_never_started':True}))
    monkeypatch.setattr(m,'CANCELLATION_PROOF',f);calls=[]
    def fn(stage,data):calls.append(stage);return wrap(stage,data,response(data))
    r=m.run(authorization(),tmp_path,fn)
    assert r['status']=='QUALIFICATION_FAILED' and calls==['AUDIT','AUDIT']
    assert r['budget_committed_total_usd']==2.58645486 and r['hosted_runner_cost_reserve_usd']==.10
