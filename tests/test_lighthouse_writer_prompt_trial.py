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


def test_mutable_comparison_report_is_not_a_budget_checkpoint(monkeypatch):
    original=Path.read_text
    def read(path,*args,**kwargs):
        if str(path)=='evidence/lighthouse-writer-prompt-trial/comparison-summary.json':
            return '{"confirmed_story_cost_usd":9999}'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    prepared,_=prepare()
    assert prepared['prior_story_cost_usd']==1.8284507
    assert all(x['path']!='evidence/lighthouse-writer-prompt-trial/comparison-summary.json'
               for x in prepared['runtime_manifest'])


def test_immutable_budget_checkpoint_drift_still_blocks(monkeypatch):
    original=Path.read_text
    def read(path,*args,**kwargs):
        if str(path)=='evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-03-20261005/result.json':
            return '{"confirmed_story_cost_usd":9999}'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',read)
    with pytest.raises(RuntimeError):prepare()


@pytest.mark.parametrize('key',['plan_sha256','writer_requests','runtime_manifest_sha256','prior_story_cost_usd','max_new_calls'])
def test_changed_trial_cannot_call_provider(tmp_path,key):
    auth=authorization();auth[key]=None
    with pytest.raises(RuntimeError):
        run(auth,tmp_path,lambda _:pytest.fail('Unexpected paid call'),lambda _:pytest.fail('Unexpected paid call'))


def test_incomplete_writer_saves_charge_and_continues_other_variant_without_audit_or_retry(tmp_path):
    auth=authorization();called=[]
    def writer(request):
        called.append(request)
        return {'story':'unfinished','actual_request':request,
                'provider_response':{'choices':[{'finish_reason':'length'}]},
                'usage':{'api_calls':1,'input_tokens':10,'output_tokens':10,'total_tokens':20,
                         'reasoning_tokens':0,'cost_usd':.001,'latency_seconds':1}}
    result=run(auth,tmp_path,writer,lambda _:pytest.fail('Unexpected audit'))
    assert result['status']=='COMPARISON_INCOMPLETE' and len(called)==2
    assert result['new_calls_accounting_complete'] and result['new_cost_usd']==.002
    assert result['accounting_complete'] is False and result['total_story_cost_usd'] is None
    with pytest.raises(FileExistsError): run(auth,tmp_path,writer,lambda _:None)


def test_empty_provider_response_retains_actual_cost_and_raw_evidence(tmp_path):
    from src.generate import OpenRouterCallError
    auth=authorization()
    body={'id':'synthetic-empty-response','model':'aion-labs/aion-3.5-mini',
          'choices':[{'message':{'content':''},'finish_reason':'length'}],
          'usage':{'prompt_tokens':10,'completion_tokens':7000,'total_tokens':7010,
                   'cost':.009807,'completion_tokens_details':{'reasoning_tokens':7000}}}
    def writer(_): raise OpenRouterCallError('No text',{'stage':'provider_response','body':body})
    result=run(auth,tmp_path,writer,lambda _:pytest.fail('Unexpected audit'))
    assert result['new_calls_accounting_complete'] and result['new_cost_usd']==.019614
    calls=json.loads(next(tmp_path.glob('*/calls.json')).read_text())
    assert calls[0]['provider_evidence']['provider_response']==body


def test_unknown_charge_blocks_other_variant(tmp_path):
    auth=authorization();called=[]
    def writer(request):
        called.append(request);raise RuntimeError('No provider usage available')
    result=run(auth,tmp_path,writer,lambda _:pytest.fail('Unexpected audit'))
    assert len(called)==1 and result['status']=='REJECT_RUNTIME'
    assert result['new_calls_accounting_complete'] is False
