import json,os,subprocess,sys
from pathlib import Path
from dotenv import dotenv_values
from src.spineforge_simple_story import prepare
from src.spineforge_simple_paid_entry import main
from src.spineforge_production_reservations_v2 import GitHubLedgerStoreV2,PaidLedgerV2,PaidGrantV2
from src.spineforge_relay_v1_contracts import canonical_sha256
from src.spineforge_relay_v1_q5t import save
root=Path('evidence/spineforge-relay/SFR-V1-Q24-SIMPLE-AION-FINAL-PREFLIGHT-20261012')
output=Path('evidence/spineforge-relay/SFR-V1-Q24-SIMPLE-AION-MYSTERY-20261012')
folder=Path('tests/fixtures/story_scenarios_v1')
inputs=[folder/n for n in ('library-bookmark-request.json','library-bookmark-seed.json','library-bookmark-frozen-seed.json','simple-aion-config.json')]
grant_id='SFR-V1-Q24-SIMPLE-AION-MYSTERY-20261012';scope_id='whole-story'
try:
    frozen=json.loads((root/'preflight.json').read_text(encoding='utf8'))
    assert frozen==prepare(*inputs)
    assert canonical_sha256(frozen)=='a80546895281ead2746d3f6fbf06b840baddfadd920632a418ae871a3917e312'
    assert not output.exists()
    approval=dict(qualification_id=grant_id,preflight_sha256=canonical_sha256(frozen),destination='OpenRouter',user_answer='Evet, Q24’ü bu kapsamla başlat',question_item_id='call_9689100352aa40148017da75545d4250',max_calls=9,max_cost_usd='1.20',budget_policy='BETWEEN_CALLS',provider_spend_cap_guaranteed=False,local_output_token_cap=None,per_call_cost_cap=None,models=frozen['allowed_models'],max_repairs=1,automatic_retry=False,shared_authority_required=True,local_green_test_count=582,ci_status_at_approval='QUEUED',paid_execution_authorized=True,prior_scopes_not_reopened=True,production_write=False,merge=False)
    token=subprocess.check_output(['gh','auth','token'],text=True).strip()
    key=dotenv_values(Path('E:/Projeler/ai-studio-projects/lumi-model-lab/.env')).get('OPENROUTER_API_KEY')
    assert token and key
    save(root/'approval.json',approval)
    store=GitHubLedgerStoreV2(repository='necdetoskay/lumi-model-lab',token=token)
    grant=PaidGrantV2(id=grant_id,approval_evidence_sha256=canonical_sha256(approval),max_calls=9,max_cost_usd='1.20',scopes=[dict(id=scope_id,preflight_sha256=canonical_sha256(frozen),max_calls=9,max_cost_usd='1.20',allowed_models=frozen['allowed_models'])])
    version=store.write(grant_id,None,PaidLedgerV2(grant=grant,status='OPEN'))
    save(root/'registered-authority.json',dict(grant=grant.model_dump(mode='json'),registry_blob_sha=version))
    os.environ['GH_TOKEN']=token;os.environ['OPENROUTER_API_KEY']=key
    sys.argv=['simple-paid-entry','--repository','necdetoskay/lumi-model-lab','--grant-id',grant_id,'--scope-id',scope_id,'--executor-id','local:q24-20261012','--request',inputs[0].as_posix(),'--seed',inputs[1].as_posix(),'--freeze',inputs[2].as_posix(),'--config',inputs[3].as_posix(),'--preflight',(root/'preflight.json').as_posix(),'--output',output.as_posix()]
    code=main()
    version,ledger=store.read(grant_id);ledger.status='CLOSED';ledger.closure=dict(reason='Single approved Q24 execution finished; no retry or reopening',entry_exit_code=code)
    store.write(grant_id,version,ledger);save(root/'closed-authority.json',ledger.model_dump(mode='json'))
    print('Q24 finished; authority CLOSED; entry exit code '+str(code));raise SystemExit(code)
except Exception as exc:
    print('Q24 stopped without retry; failure type: '+type(exc).__name__);raise SystemExit(2)
