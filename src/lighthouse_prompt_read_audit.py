"""Audit the documented reading copy; no Writer, retry or semantic repair."""
import hashlib
import json
from pathlib import Path
from src.lighthouse_experiment import approved_input, dependency_manifest, digest_json
from src.lighthouse_decision_qualification import payload
from src.lighthouse_audit_decision import call_audit, decision
from src.spineforge_v21_quality_runtime import _usage
from src.spineforge_v21_model_adapter import provider_usage

SOURCE=Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005')
AUTH=Path('evidence/lighthouse-editorial/prompt-read-audit-authorization.json')
ID='LIGHTHOUSE-READ-AUDIT-01-20261005'
ROOT=Path('evidence/lighthouse-writer-prompt-trial')


def prepare():
    plan=approved_input()
    prior=json.loads((SOURCE/'result.json').read_text())['confirmed_story_cost_usd']
    story=(SOURCE/'five_category_appendix-reading-story.txt').read_text()
    data=payload(story,plan)
    paths={x['path'] for x in dependency_manifest()}
    paths.update(['src/lighthouse_prompt_read_audit.py','src/lighthouse_audit_decision.py',
        'src/lighthouse_audit_requirements.py','src/lighthouse_decision_qualification.py',
        'prompts/lighthouse_decision_audit.md','evidence/lighthouse-editorial/audit-requirements.json',
        'tests/test_lighthouse_prompt_read_audit.py','.github/workflows/lighthouse-prompt-read-audit.yml'])
    paths.update(str(SOURCE/x) for x in ['result.json','reading-derivation-proof.json',
        'five_category_appendix-reading-story.txt','baseline-audit-rebound-decision.json'])
    manifest=[{'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    return {'experiment_id':ID,'input_sha256':digest_json(data),'runtime_manifest':manifest,
        'runtime_manifest_sha256':digest_json(manifest),'prior_confirmed_cost_usd':prior,
        'unknown_prior_call_reserve_usd':.04,'total_story_budget_usd':3,
        'max_new_calls':1,'writer_calls':0,'repair_calls':0,'automatic_retry':False,
        'scope':'AUDIT_READING_DERIVATIVE_NOT_RAW_DELIVERY_ACCEPTANCE'},data


def run(auth,out_dir,audit_fn):
    prepared,data=prepare()
    for k,v in prepared.items():
        if auth.get(k)!=v: raise RuntimeError('Audit continuation authorization drift: '+k)
    if auth.get('explicit_paid_authorization') is not True: raise RuntimeError('Budget authorization missing')
    reserve=(len(json.dumps(data,ensure_ascii=False).encode())+20000)*2/1e6+.035
    prior=prepared['prior_confirmed_cost_usd']
    if prior+.04+reserve>3: raise RuntimeError('Insufficient reserved budget')
    out=Path(out_dir)/ID;out.mkdir(parents=True,exist_ok=False)
    def save(n,v): (out/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
    save('authorization-consumed.json',auth);save('prepared-input.json',prepared)
    row={'stage':'AUDIT','variant':'five_category_appendix','input':data,'status':'STARTED','reserved_cost_usd':reserve}
    save('calls.json',[row]);cost=prior;chosen=None;failure=None
    try:
        response=audit_fn(data);row['response']=response;row['usage']=_usage(response,'AUDIT')
        cost+=row['usage']['cost_usd'];row['status']='COMPLETED';save('calls.json',[row])
        chosen=decision(response,data['story_segments'],data['approved_plan']);status='CONTENT_COMPARISON_AUDITS_AVAILABLE'
    except Exception as exc:
        failure=type(exc).__name__+': '+str(exc);row['status']='FAILED';row['failure']=failure
        body=(getattr(exc,'trace',None) or {}).get('body') or {}
        if body:
            row['provider_evidence']={k:body[k] for k in ('id','model','choices','usage') if k in body}
            if 'usage' not in row:
                try:
                    row['usage']=_usage({'usage':provider_usage(body,'AUDIT',0)},'AUDIT');cost+=row['usage']['cost_usd']
                except RuntimeError: pass
        save('calls.json',[row]);status='AUDIT_CONTINUATION_FAILED'
    result={'status':status,'failure':failure,'decision':chosen,'new_call_count':1,
        'new_cost_usd':round(cost-prior,10) if 'usage' in row else None,'confirmed_story_cost_usd':round(cost,10),
        'unknown_prior_call_reserve_usd':.04,'budget_committed_total_usd':round(cost+.04+(reserve if 'usage' not in row else 0),10),
        'accounting_complete':False,'new_calls_accounting_complete':'usage' in row,
        'model_latency_seconds':row.get('usage',{}).get('latency_seconds'),
        'raw_delivery_accepted':False,'writer_calls':0,'repair_calls':0,'production_write':False}
    save('result.json',result);return result


if __name__=='__main__':
    import os
    result=run(json.loads(AUTH.read_text()),ROOT,lambda d:call_audit(os.environ['OPENROUTER_API_KEY'],d))
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['status']=='CONTENT_COMPARISON_AUDITS_AVAILABLE' else 1)
