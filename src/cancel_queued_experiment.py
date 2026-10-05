"""Cancel one exact queued predecessor and prove its paid step never started."""
import json
import time
import urllib.request
from pathlib import Path

REPO='necdetoskay/lumi-model-lab'
RUN=37370235996
COMMIT='05a4bf29935aecd7e6428020b983beda710905f3'
PAID_STEP='Qualify on saved controls and repair only if both pass'
OUTPUT=Path('evidence/lighthouse-source-audit/LIGHTHOUSE-SOURCE-ADJUDICATION-HOSTED-01-20261005-cancellation.json')


def cancel(api, pause):
    base=f'/repos/{REPO}/actions/runs/{RUN}'
    before=api('GET',base)
    if before['head_sha']!=COMMIT or before['status']!='queued':
        raise RuntimeError('Predecessor is not the exact queued experiment; no new model call allowed')
    api('POST',base+'/cancel')
    for _ in range(12):
        after=api('GET',base)
        if after['status']=='completed':break
        pause(2)
    else:raise RuntimeError('Cancellation not confirmed; no new model call allowed')
    if after['conclusion']!='cancelled':raise RuntimeError('Predecessor completed unexpectedly; inspect its ledger before continuing')
    jobs=api('GET',base+'/jobs')['jobs']
    if len(jobs)>1:raise RuntimeError('Unexpected predecessor job count')
    paid=[s for s in ((jobs[0].get('steps') or []) if jobs else []) if s['name']==PAID_STEP]
    if paid and (len(paid)!=1 or paid[0].get('started_at') is not None):
        raise RuntimeError('Predecessor paid step may have started; no new call allowed')
    return {'superseded_run_id':RUN,'superseded_commit':COMMIT,'confirmed_cancelled':True,
            'paid_step_never_started':True,'new_model_call_authorized_by_existing_budget':True}


if __name__=='__main__':
    import os
    token=os.environ['GITHUB_TOKEN']
    def api(method,path):
        request=urllib.request.Request('https://api.github.com'+path,method=method,
            data=b'' if method=='POST' else None,
            headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        with urllib.request.urlopen(request,timeout=20) as response:
            body=response.read()
        return json.loads(body) if body else None
    result=cancel(api,time.sleep)
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
