"""Two same-context Writers and same-contract audits; no retries or repair."""
import hashlib
import json
import time
from pathlib import Path
from src.lighthouse_experiment import approved_input, digest_json, dependency_manifest
from src.lighthouse_writer_once import request_payload, scene_artifact, MODEL, PROMPT
from src.lighthouse_audit_decision import call_audit, decision
from src.lighthouse_decision_qualification import payload
from src.lighthouse_writer_stream_transport import dispatch, MAX_TOKENS
from src.spineforge_v21_model_adapter import provider_usage
from src.spineforge_v21_quality_runtime import _usage

TRIAL_PROMPT = Path('prompts/lighthouse_editorial_writer_prompt_trial_v1.md')
ROOT = Path('evidence/lighthouse-writer-prompt-trial')
PREPARED = Path('evidence/lighthouse-editorial/writer-prompt-trial-prepared.json')
AUTH = Path('evidence/lighthouse-editorial/writer-prompt-trial-authorization.json')
PRIOR = 1.8284507
ID = 'LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005'
# First trial lost the provider body in its new harness error handler. Do not
# report its unknown charge as zero; reserve the entire failed-call allowance.
UNRECONCILED_PRIOR_RESERVE = .04


def requests(plan):
    baseline = request_payload(plan)
    baseline.update(max_tokens=MAX_TOKENS, reasoning_effort='low', stream=True, stream_options={"include_usage": True})
    enhanced = json.loads(json.dumps(baseline))
    enhanced['messages'][0]['content'] = TRIAL_PROMPT.read_text()
    if not enhanced['messages'][0]['content'].startswith(baseline['messages'][0]['content']):
        raise RuntimeError('Trial prompt must append to current baseline')
    return [('current_baseline', baseline), ('five_category_appendix', enhanced)]


def prepare():
    plan = approved_input()
    if json.loads(Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-03-20261005/result.json').read_text())['confirmed_story_cost_usd'] != PRIOR:
        raise RuntimeError('Prior accounting drift')
    paths = {x['path'] for x in dependency_manifest()}
    paths.update(['src/lighthouse_writer_prompt_trial.py', str(TRIAL_PROMPT),
        'src/lighthouse_writer_stream_transport.py', 'tests/test_lighthouse_writer_stream_transport.py',
        'evidence/lighthouse-editorial/writer-stream-profile-v2.json',
        'evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-02-20261005/result.json',
        'evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-03-20261005/result.json',
        'src/lighthouse_audit_decision.py', 'src/lighthouse_audit_requirements.py',
        'src/lighthouse_decision_qualification.py', 'prompts/lighthouse_decision_audit.md',
        'evidence/lighthouse-editorial/audit-requirements.json',
        'evidence/lighthouse-editorial/decision-stabilization-summary.json',
        'evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-01-20261005/calls.json',
        'evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-01-20261005/result.json',
        'tests/test_lighthouse_writer_prompt_trial.py',
        '.github/workflows/lighthouse-writer-prompt-trial.yml'])
    manifest = [{'path': p, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    return {'experiment_id': ID, 'plan_sha256': digest_json(plan),
            'runtime_manifest': manifest, 'runtime_manifest_sha256': digest_json(manifest),
            'writer_requests': [{'variant': name, 'request_sha256': digest_json(r)} for name,r in requests(plan)],
            'prior_story_cost_usd': PRIOR, 'total_story_budget_usd': 3,
            'prior_accounting_complete': False,
            'unreconciled_prior_cost_reserve_usd': UNRECONCILED_PRIOR_RESERVE,
            'max_new_calls': 4, 'max_writer_calls': 2, 'max_audit_calls': 2,
            'automatic_retry': False, 'repair_calls': 0, 'production_write': False}, plan


def writer(api_key, request):
    start = time.perf_counter()
    text, body, actual = dispatch(api_key, request)
    return {'story': text, 'usage': provider_usage(body, 'WRITER', round(time.perf_counter()-start,3)),
            'actual_request': actual, 'provider_response': {k:body[k] for k in ('id','model','choices','usage') if k in body}}


def run(authorization, output_dir, writer_fn, audit_fn):
    prepared, plan = prepare()
    for key in ('experiment_id','plan_sha256','runtime_manifest_sha256','writer_requests',
                'prior_story_cost_usd','total_story_budget_usd','max_new_calls',
                'prior_accounting_complete','unreconciled_prior_cost_reserve_usd'):
        if authorization.get(key) != prepared[key]:
            raise RuntimeError('Authorization drift: '+key)
    if authorization.get('explicit_paid_authorization') is not True:
        raise RuntimeError('Existing user budget authorization must be recorded')
    out = Path(output_dir)/ID
    out.mkdir(parents=True, exist_ok=False)
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    save('authorization-consumed.json',authorization);save('prepared-input.json',prepared)
    calls=[]; cases=[];cost=PRIOR;failure=None
    def invoke(stage, variant, data, fn):
        nonlocal cost
        reserve = .10 if stage=='WRITER' else (len(json.dumps(data,ensure_ascii=False).encode())+20000)*2/1e6+.035
        if cost+UNRECONCILED_PRIOR_RESERVE+reserve>3: raise RuntimeError('Budget lacks next-call reservation')
        row={'stage':stage,'variant':variant,'input':data,'status':'STARTED','reserved_cost_usd':reserve}
        calls.append(row);save('calls.json',calls)
        started=time.perf_counter()
        try:
            response=fn(data);row['response']=response
            row['usage']=_usage(response,stage);cost+=row['usage']['cost_usd']
            row['status']='COMPLETED';save('calls.json',calls)
            if cost>3: raise RuntimeError('Actual total exceeds budget')
            return response
        except Exception as exc:
            row['status']='FAILED';row['failure_type']=type(exc).__name__
            row['provider_evidence']=getattr(exc,'provider_evidence',None)
            trace=getattr(exc,'trace',None) or {}
            body=trace.get('body') or {}
            if body:
                row['provider_evidence']={'phase':trace.get('stage'),
                    'provider_response':{k:body[k] for k in ('id','model','choices','usage') if k in body}}
            if 'usage' not in row:
                try:
                    usage=provider_usage(body,stage,round(time.perf_counter()-started,3)) if body else getattr(exc,'usage',None)
                    row['usage']=_usage({'usage':usage},stage);cost+=row['usage']['cost_usd']
                except RuntimeError: pass
            save('calls.json',calls);raise
    try:
        for variant, request in requests(plan):
            try:
                generated=invoke('WRITER',variant,request,writer_fn)
                if generated['actual_request']!=request:
                    raise RuntimeError('Dispatched request differs from frozen trial')
                finish=(generated['provider_response'].get('choices') or [{}])[0].get('finish_reason')
                if finish!='stop': raise RuntimeError('Incomplete Writer response')
                artifact=scene_artifact(generated['story'],plan)
                save(variant+'-story-artifact.json',artifact)
                (out/(variant+'-story.txt')).write_text(artifact['story'])
                if not artifact['target_length_hit']: raise RuntimeError('Story below minimum length')
                # The auditor sees only plan and story: no variant label or expected result.
                data=payload(artifact['story'],plan)
                audited=invoke('AUDIT',variant,data,audit_fn)
                chosen=decision(audited,data['story_segments'],plan)
                cases.append({'variant':variant,'word_count':artifact['word_count'],
                              'story_sha256':artifact['story_sha256'],**chosen})
                save('case-results.json',cases)
            except Exception as exc:
                cases.append({'variant':variant,'status':'NO_VALID_COMPARISON',
                              'failure':type(exc).__name__+': '+str(exc)})
                save('case-results.json',cases)
                # Do not retry this variant. Continue the independent variant only
                # after its predecessor's usage is known and the budget is intact.
                if not calls or 'usage' not in calls[-1] or cost+UNRECONCILED_PRIOR_RESERVE>3:
                    raise
        status='COMPARISON_COMPLETED' if all(c['status'] in {'ACCEPT','REPAIR'} for c in cases) else 'COMPARISON_INCOMPLETE'
    except Exception as exc:
        status='REJECT_RUNTIME';failure=type(exc).__name__+': '+str(exc)
    result={'status':status,'failure':failure,'new_call_count':len(calls),
            'new_cost_usd':round(cost-PRIOR,10),'total_story_cost_usd':None,
            'confirmed_story_cost_usd':round(cost,10),
            'unreconciled_prior_cost_reserve_usd':UNRECONCILED_PRIOR_RESERVE,
            'budget_committed_total_usd':round(cost+UNRECONCILED_PRIOR_RESERVE,10),
            'accounting_complete':False,
            'new_calls_accounting_complete':all('usage' in c for c in calls),
            'model_latency_seconds':round(sum(c.get('usage',{}).get('latency_seconds',0) for c in calls),3),
            'cases':cases,'repair_calls':0,'production_write':False,'translation_executed':False,
            'single_sample_per_prompt_not_statistical_proof':True}
    save('result.json',result);return result


if __name__=='__main__':
    import argparse,os
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if not args.execute:
        value,_=prepare();PREPARED.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in value.items() if k!='runtime_manifest'}))
    else:
        key=os.environ.get('OPENROUTER_API_KEY')
        if not key: parser.error('API key required')
        result=run(json.loads(AUTH.read_text()),ROOT,lambda r:writer(key,r),lambda d:call_audit(key,d))
        print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['status']=='COMPARISON_COMPLETED' else 1)
