"""Two same-context Writers and same-contract audits; no retries or repair."""
import hashlib
import json
import time
from pathlib import Path
from src.lighthouse_experiment import approved_input, digest_json, dependency_manifest
from src.lighthouse_writer_once import request_payload, scene_artifact, MODEL, PROMPT
from src.lighthouse_audit_decision import call_audit, decision
from src.lighthouse_decision_qualification import payload
from src.spineforge_v19_transport import _request_once
from src.spineforge_v21_model_adapter import provider_usage
from src.spineforge_v21_quality_runtime import _usage

TRIAL_PROMPT = Path('prompts/lighthouse_editorial_writer_prompt_trial_v1.md')
ROOT = Path('evidence/lighthouse-writer-prompt-trial')
PREPARED = Path('evidence/lighthouse-editorial/writer-prompt-trial-prepared.json')
AUTH = Path('evidence/lighthouse-editorial/writer-prompt-trial-authorization.json')
PRIOR = 1.7585491
ID = 'LIGHTHOUSE-WRITER-PROMPT-TRIAL-01-20261005'


def requests(plan):
    baseline = request_payload(plan)
    enhanced = json.loads(json.dumps(baseline))
    enhanced['messages'][0]['content'] = TRIAL_PROMPT.read_text()
    if not enhanced['messages'][0]['content'].startswith(baseline['messages'][0]['content']):
        raise RuntimeError('Trial prompt must append to current baseline')
    return [('current_baseline', baseline), ('five_category_appendix', enhanced)]


def prepare():
    plan = approved_input()
    if json.loads(Path('evidence/lighthouse-editorial/decision-stabilization-summary.json').read_text())['actual_total_cost_usd'] != PRIOR:
        raise RuntimeError('Prior accounting drift')
    paths = {x['path'] for x in dependency_manifest()}
    paths.update(['src/lighthouse_writer_prompt_trial.py', str(TRIAL_PROMPT),
        'src/lighthouse_audit_decision.py', 'src/lighthouse_audit_requirements.py',
        'src/lighthouse_decision_qualification.py', 'prompts/lighthouse_decision_audit.md',
        'evidence/lighthouse-editorial/audit-requirements.json',
        'evidence/lighthouse-editorial/decision-stabilization-summary.json',
        'tests/test_lighthouse_writer_prompt_trial.py',
        '.github/workflows/lighthouse-writer-prompt-trial.yml'])
    manifest = [{'path': p, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    return {'experiment_id': ID, 'plan_sha256': digest_json(plan),
            'runtime_manifest': manifest, 'runtime_manifest_sha256': digest_json(manifest),
            'writer_requests': [{'variant': name, 'request_sha256': digest_json(r)} for name,r in requests(plan)],
            'prior_story_cost_usd': PRIOR, 'total_story_budget_usd': 3,
            'max_new_calls': 4, 'max_writer_calls': 2, 'max_audit_calls': 2,
            'automatic_retry': False, 'repair_calls': 0, 'production_write': False}, plan


def writer(api_key, request):
    start = time.perf_counter()
    text, body, actual = _request_once(api_key=api_key, model=MODEL,
        system_prompt=request['messages'][0]['content'], user_prompt=request['messages'][1]['content'],
        temperature=request['temperature'], max_tokens=request['max_tokens'], seed=None,
        request_class='spineforge_v20_story_writer', response_format={'type':'text'}, require_parameters=False)
    return {'story': text, 'usage': provider_usage(body, 'WRITER', round(time.perf_counter()-start,3)),
            'actual_request': actual, 'provider_response': {k:body[k] for k in ('id','model','choices','usage') if k in body}}


def run(authorization, output_dir, writer_fn, audit_fn):
    prepared, plan = prepare()
    for key in ('experiment_id','plan_sha256','runtime_manifest_sha256','writer_requests',
                'prior_story_cost_usd','total_story_budget_usd','max_new_calls'):
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
        reserve = .04 if stage=='WRITER' else (len(json.dumps(data,ensure_ascii=False).encode())+20000)*2/1e6+.035
        if cost+reserve>3: raise RuntimeError('Budget lacks next-call reservation')
        row={'stage':stage,'variant':variant,'input':data,'status':'STARTED','reserved_cost_usd':reserve}
        calls.append(row);save('calls.json',calls)
        try:
            response=fn(data);row['response']=response
            row['usage']=_usage(response,stage);cost+=row['usage']['cost_usd']
            row['status']='COMPLETED';save('calls.json',calls)
            if cost>3: raise RuntimeError('Actual total exceeds budget')
            return response
        except Exception as exc:
            row['status']='FAILED';row['failure_type']=type(exc).__name__
            row['provider_evidence']=getattr(exc,'provider_evidence',None)
            if 'usage' not in row:
                try:
                    row['usage']=_usage({'usage':getattr(exc,'usage',None)},stage);cost+=row['usage']['cost_usd']
                except RuntimeError: pass
            save('calls.json',calls);raise
    try:
        for variant, request in requests(plan):
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
        status='COMPARISON_COMPLETED'
    except Exception as exc:
        status='REJECT_RUNTIME';failure=type(exc).__name__+': '+str(exc)
    result={'status':status,'failure':failure,'new_call_count':len(calls),
            'new_cost_usd':round(cost-PRIOR,10),'total_story_cost_usd':round(cost,10),
            'accounting_complete':all('usage' in c for c in calls),
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
