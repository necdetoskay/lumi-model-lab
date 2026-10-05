import json
import pytest
import src.lighthouse_patch_campaign as campaign
from tests.test_lighthouse_experiment import usage, audit


def grant():
    p,*_=campaign.prepare()
    return {k:p[k] for k in ['experiment_id','plan_sha256','source_story_sha256','saved_findings_sha256',
        'runtime_manifest_sha256','total_story_budget_usd','prior_story_cost_usd','resume_patch_sha256']} | {
        'explicit_paid_authorization':True,'authorization_id':'FAKE-CAMPAIGN'}


def patch_rows(payload):
    by={r['span_id']:r for r in payload['story_segments']}
    sid=payload['allowed_span_ids'][0]
    old=by[sid]['repaired_text']
    return [{'span_id':sid,'old_text':old,'replacement_text':old + ' This is synthetic test prose.'}]


def test_saved_cross_scene_finding_completes_and_consumes_once(tmp_path):
    stages=[]
    def call(stage,payload):
        stages.append(stage)
        if stage=='PATCH':return {'patches':patch_rows(payload),'summary':'mock repair','usage':usage()}
        return audit([])
    r=campaign.run(authorization=grant(),output_dir=tmp_path,call_fn=call)
    assert r['status']=='ACCEPT' and r['writer_calls']==0 and stages==['PATCH','AUDIT']
    proof=json.loads((tmp_path/'FAKE-CAMPAIGN/patch-proof-01.json').read_text())
    assert proof['outside_patches_unchanged']
    with pytest.raises(FileExistsError):
        campaign.run(authorization=grant(),output_dir=tmp_path,call_fn=call)


@pytest.mark.parametrize('kind',['duplicate','unknown','mismatch','newline','empty','unchanged'])
def test_invalid_patches_rejected(kind):
    _,plan,raw,findings=campaign.prepare();payload,ids=campaign.scope_payload(raw,plan,findings)
    rows=patch_rows(payload)
    if kind=='duplicate':rows.append(rows[0].copy())
    if kind=='unknown':rows[0]['span_id']='S999'
    if kind=='mismatch':rows[0]['old_text']='wrong'
    if kind=='newline':rows[0]['replacement_text']='new\nparagraph'
    if kind=='empty':rows[0]['replacement_text']=''
    if kind=='unchanged':rows[0]['replacement_text']=rows[0]['old_text']
    with pytest.raises(RuntimeError):campaign.apply_patches(raw,plan,ids,rows)


def test_multiple_scene_edits_preserve_all_other_bytes():
    _,plan,raw,findings=campaign.prepare();payload,ids=campaign.scope_payload(raw,plan,findings)
    by={r['span_id']:r for r in payload['story_segments']}
    rows=[]
    for sid in sorted(ids):
        old=by[sid]['repaired_text'];new=old + ' This is synthetic test prose.'.replace("twice Ekin's height",'broad and grey')
        rows.append({'span_id':sid,'old_text':old,'replacement_text':new})
    candidate,proof=campaign.apply_patches(raw,plan,ids,rows)
    expected=raw
    for r in rows:expected=expected.replace(r['old_text'],r['replacement_text'],1)
    assert candidate==expected and proof['changed_span_ids']==sorted(ids)


def test_budget_blocks_before_dispatch(tmp_path,monkeypatch):
    monkeypatch.setattr(campaign,'BUDGET',.18)
    r=campaign.run(authorization=grant(),output_dir=tmp_path,
                   call_fn=lambda *a:pytest.fail('Budget must stop before call'))
    assert r['new_call_count']==0 and 'reservation' in r['failure_message']


def test_unknown_usage_stops_without_another_call(tmp_path):
    r=campaign.run(authorization=grant(),output_dir=tmp_path,
                   call_fn=lambda *a:{'patches':[],'summary':'mock'})
    assert r['new_call_count']==1 and not r['accounting_complete']


def test_story_hash_drift_stops_before_consumption(tmp_path):
    g=grant();g['source_story_sha256']='wrong'
    with pytest.raises(RuntimeError):campaign.run(authorization=g,output_dir=tmp_path,call_fn=lambda *a:None)
    assert not list(tmp_path.iterdir())
