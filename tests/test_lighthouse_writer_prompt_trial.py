import json
from pathlib import Path
import pytest
from src.lighthouse_experiment import approved_input
from src.lighthouse_writer_prompt_trial import requests,prepare,run


def test_only_system_prompt_changes_between_writer_requests():
    plan=approved_input();pairs=requests(plan);a,b=[r for _,r in pairs]
    assert a['model']==b['model']=='aion-labs/aion-3.5-mini'
    assert a['messages'][1]==b['messages'][1]
    assert {k:v for k,v in a.items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'}
    assert b['messages'][0]['content'].startswith(a['messages'][0]['content'])
    assert plan['target_words']=={'min':1400}


def authorization():
    prepared,_=prepare()
    return {**prepared,'explicit_paid_authorization':True}


@pytest.mark.parametrize('key',['plan_sha256','writer_requests','runtime_manifest_sha256','prior_story_cost_usd','max_new_calls'])
def test_changed_trial_cannot_call_provider(tmp_path,key):
    auth=authorization();auth[key]=None
    with pytest.raises(RuntimeError):
        run(auth,tmp_path,lambda _:pytest.fail('Unexpected paid call'),lambda _:pytest.fail('Unexpected paid call'))


def test_incomplete_writer_saves_charge_and_stops_without_audit_or_retry(tmp_path):
    auth=authorization();called=[]
    def writer(request):
        called.append(request)
        return {'story':'unfinished','actual_request':request,
                'provider_response':{'choices':[{'finish_reason':'length'}]},
                'usage':{'api_calls':1,'input_tokens':10,'output_tokens':10,'total_tokens':20,
                         'reasoning_tokens':0,'cost_usd':.001,'latency_seconds':1}}
    result=run(auth,tmp_path,writer,lambda _:pytest.fail('Unexpected audit'))
    assert result['status']=='REJECT_RUNTIME' and len(called)==1
    assert result['accounting_complete'] and result['new_cost_usd']==.001
    with pytest.raises(FileExistsError): run(auth,tmp_path,writer,lambda _:None)
