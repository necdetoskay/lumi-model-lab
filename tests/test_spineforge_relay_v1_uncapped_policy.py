import json
from decimal import Decimal
import pytest
from src.spineforge_production_config_v2 import RunConfigV2
from src.spineforge_production_reservations_v2 import PaidGrantV2,PaidLedgerV2,run_reserved,ReservationError
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_production_pipeline import prepare,execute,request_for
from tests.test_spineforge_relay_v1_reservations import MemoryAuthority,usage
from tests.test_spineforge_relay_v1_production_pipeline import sample,provider,write

PF={'config':{'budget_policy':'BETWEEN_CALLS'}}
def store():
    grant=PaidGrantV2(id='fresh-v2',approval_evidence_sha256='a'*64,max_calls=4,max_cost_usd='1.20',scopes=[dict(id='whole',preflight_sha256=canonical_sha256(PF),max_calls=4,max_cost_usd='1.20',allowed_models=['qualified'])])
    return MemoryAuthority(PaidLedgerV2(grant=grant,status='OPEN'))

def reserved(authority,invoke,transport):
    return run_reserved(store=authority,grant_id='fresh-v2',scope_id='whole',preflight=PF,executor_id='unit',invoke=invoke,transport=transport)

def test_complete_call_over_threshold_records_real_cost_then_denies_next_call():
    authority=store();dispatches=[]
    def transport(**kwargs):dispatches.append(kwargs);return usage(2.0)
    def invoke(call):
        call(model='qualified',max_tokens=None)
        with pytest.raises(ReservationError,match='threshold'):call(model='qualified',max_tokens=None)
        return 'stopped'
    assert reserved(authority,invoke,transport)=='stopped'
    row=authority.ledger.reservations['whole']
    assert row['status']=='SETTLED' and Decimal(row['actual_cost_usd'])==2
    assert row['budget_threshold_exceeded'] is True and len(dispatches)==1
    with pytest.raises(ReservationError):reserved(authority,invoke,transport)

def test_unknown_usage_remains_uncertain_without_retry():
    authority=store();calls=[]
    def fail(**kwargs):calls.append(kwargs);raise RuntimeError('transport')
    with pytest.raises(RuntimeError):reserved(authority,lambda call:call(model='qualified',max_tokens=None),fail)
    assert len(calls)==1 and authority.ledger.reservations['whole']['status']=='UNCERTAIN'

def test_v2_rejects_local_token_cap_before_dispatch():
    authority=store();calls=[]
    with pytest.raises(ReservationError):reserved(authority,lambda call:call(model='qualified',max_tokens=4000),lambda **kwargs:calls.append(kwargs))
    assert calls==[] and authority.ledger.reservations['whole']['actual_calls']==0

@pytest.mark.parametrize('limit,status,calls,revision',[(.055,'ACCEPT',6,2),(.05,'REJECT_NON_CONVERGENT',5,1)])
def test_uncapped_pipeline_replay_or_stop_between_calls(tmp_path,limit,status,calls,revision):
    paths,design=sample(tmp_path/'inputs','dialogue');config=RunConfigV2(max_total_cost_usd=limit);write(paths['config'],config.model_dump(mode='json'))
    seen=[];fake=provider(config,design,seen);requests=[]
    def capture(**kwargs):
        result=fake(**kwargs);requests.append(result[2])
        assert kwargs['max_tokens'] is None and 'max_tokens' not in result[2]
        return result
    pf=prepare(paths['request'],paths['seed'],paths['freeze'],paths['config'])
    result=execute(request_path=paths['request'],seed_path=paths['seed'],freeze_path=paths['freeze'],config_path=paths['config'],preflight=pf,output=tmp_path/'run',api_key='synthetic',call_fn=capture)
    assert result['status']==status and result['provider_calls']==calls
    assert result['story_result']['state_advanced_to_revision']==revision
    if status=='ACCEPT':assert result['known_cost_usd']>limit and (tmp_path/'run'/'offline-replay.json').exists()
    else:assert not (tmp_path/'run'/'story'/'S02-accepted.json').exists()
