import pytest
from src.lighthouse_prompt_read_audit import prepare,run


def test_authorization_drift_blocks_audit(tmp_path):
    p,_=prepare();p['input_sha256']='changed';p['explicit_paid_authorization']=True
    with pytest.raises(RuntimeError):run(p,tmp_path,lambda _:pytest.fail('Paid call'))


def test_unknown_audit_charge_is_not_zero_and_no_retry(tmp_path):
    p,_=prepare();p['explicit_paid_authorization']=True;calls=[]
    def fail(data):calls.append(data);raise RuntimeError('Transport unavailable')
    r=run(p,tmp_path,fail)
    assert len(calls)==1 and r['new_cost_usd'] is None and not r['new_calls_accounting_complete']
    assert r['budget_committed_total_usd']>r['confirmed_story_cost_usd']+.04
    with pytest.raises(FileExistsError):run(p,tmp_path,fail)
