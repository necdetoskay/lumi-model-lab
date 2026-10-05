"""Two paid audits of saved versions of ONE story; no Writer or story edits."""
import json,hashlib
from pathlib import Path
from src.lighthouse_experiment import approved_input, dependency_manifest, digest_json
from src.spineforge_v20_story_audit_artifact import _segment_story
from src.spineforge_v21_quality_runtime import _usage
from src.lighthouse_audit_decision import call_audit, decision, PROMPT

PREPARED=Path('evidence/lighthouse-editorial/decision-qualification-prepared.json')
AUTH=Path('evidence/lighthouse-editorial/decision-qualification-authorization.json')
OUTPUT=Path('evidence/lighthouse-decision-qualification')
PRIOR=1.4208331
BUDGET=3.0
CASES=[('accepted_control',Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-04-20261005/accepted-story.txt')),
       ('recorded_plan_deviations',Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-03-20261005/accepted-story.txt'))]


def payload(story,plan):
    rows=[{'span_id':r['id'],'paragraph_id':r['paragraph_id'],'paragraph_index':r['paragraph_index'],
           'repaired_text':r['text']} for r in _segment_story(story)]
    return {'full_story':story,'story_segments':rows,'approved_plan':plan,'reader_profile':{'age':12,'language':'en'},
            'source_story_sha256':hashlib.sha256(story.encode()).hexdigest()}


def prepare():
    plan=approved_input();paths={x['path'] for x in dependency_manifest()}
    paths.update([str(PROMPT),'src/lighthouse_audit_decision.py','src/lighthouse_decision_qualification.py',
                  'src/lighthouse_patch_campaign.py','tests/test_lighthouse_audit_decision.py',
                  'tests/test_lighthouse_patch_campaign.py','tests/test_lighthouse_decision_qualification.py',
                  '.github/workflows/lighthouse-decision-qualification.yml',
                  'evidence/lighthouse-editorial/completion-summary.json'])
    paths.update(str(p) for _,p in CASES)
    # The patch tests replay these exact saved ledgers and independent findings.
    from src.lighthouse_patch_campaign import prepare as patch_prepare
    prior_prepared,*_=patch_prepare();paths.update(x['path'] for x in prior_prepared['runtime_manifest'])
    manifest=[{'path':p,'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    total=json.loads(Path('evidence/lighthouse-editorial/completion-summary.json').read_text())['actual_total_cost_usd']
    if total!=PRIOR:raise RuntimeError('Prior cost drift')
    return {'experiment_id':'LIGHTHOUSE-AUDIT-DECISION-V2','plan_sha256':digest_json(plan),
            'runtime_manifest':manifest,'runtime_manifest_sha256':digest_json(manifest),
            'prior_story_cost_usd':PRIOR,'total_story_budget_usd':BUDGET,
            'cases':[{'id':n,'path':str(p),'story_sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for n,p in CASES],
            'max_new_calls':2,'writer_calls':0,'story_edits':0},plan


def run(authorization,output_dir,call_fn):
    prepared,plan=prepare()
    for k in ['experiment_id','plan_sha256','runtime_manifest_sha256','prior_story_cost_usd','total_story_budget_usd','cases','max_new_calls']:
        if authorization.get(k)!=prepared[k]:raise RuntimeError('Authorization drift: '+k)
    if authorization.get('explicit_paid_authorization') is not True:raise RuntimeError('Paid authorization required')
    aid=authorization.get('authorization_id')
    import re
    if not isinstance(aid,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',aid):raise RuntimeError('Invalid authorization ID')
    out=Path(output_dir)/aid;out.mkdir(parents=True,exist_ok=False)
    def save(name,value):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    save('authorization-consumed.json',authorization);save('prepared-input.json',prepared)
    calls=[];results=[];cost=PRIOR
    status='STARTED'
    try:
        for case in prepared['cases']:
            story=Path(case['path']).read_text();data=payload(story,plan)
            reserve=(len(json.dumps(data,ensure_ascii=False).encode())+len(PROMPT.read_bytes())+12000)*2/1e6+.035
            if cost+reserve>BUDGET:raise RuntimeError('Budget lacks next-call reservation')
            row={'case_id':case['id'],'input':data,'status':'STARTED','reserved_cost_usd':reserve};calls.append(row);save('calls.json',calls)
            try:
                response=call_fn(data);row['response']=response;row['usage']=_usage(response,'AUDIT')
                cost+=row['usage']['cost_usd'];row['status']='COMPLETED';save('calls.json',calls)
                if cost>BUDGET:raise RuntimeError('Actual budget exceeded')
                choice=decision(response,data['story_segments'])
                if case['id']=='accepted_control':passed=choice['status']=='ACCEPT'
                else:
                    groups=[{'S054','S060','S061','S183'},{f'S{i:03}' for i in range(197,213)}]
                    reported={s for f in choice['findings'] for s in f['span_ids']}
                    passed=choice['status']=='REPAIR' and all(g & reported for g in groups)
                results.append({'case_id':case['id'],'passed':passed,**choice})
                save('case-results.json',results)
            except Exception as exc:
                row['status']='FAILED';row['failure_message']=getattr(exc,'diagnostic_message',str(exc))
                row['provider_evidence']=getattr(exc,'provider_evidence',None)
                if 'usage' not in row:
                    try:row['usage']=_usage({'usage':getattr(exc,'usage',None)},'AUDIT');cost+=row['usage']['cost_usd']
                    except RuntimeError:pass
                save('calls.json',calls);raise
        status='PASS' if all(x['passed'] for x in results) else 'QUALIFICATION_FAILED'
        failure=None
    except Exception as exc:status='REJECT_RUNTIME';failure=str(exc)
    result={'status':status,'failure':failure,'new_call_count':len(calls),'new_cost_usd':round(cost-PRIOR,10),
            'total_story_cost_usd':round(cost,10),'accounting_complete':all('usage' in x for x in calls),
            'model_latency_seconds':round(sum(x.get('usage',{}).get('latency_seconds',0) for x in calls),3),
            'writer_calls':0,'story_edits':0,'production_write':False,'cases':results}
    save('result.json',result);return result


if __name__=='__main__':
    import argparse,os
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:
        value,_=prepare();PREPARED.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in value.items() if k!='runtime_manifest'}))
    else:
        key=os.environ.get('OPENROUTER_API_KEY')
        if not key:p.error('API key required')
        result=run(json.loads(AUTH.read_text()),OUTPUT,lambda data:call_audit(key,data))
        print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['status']=='PASS' else 1)
