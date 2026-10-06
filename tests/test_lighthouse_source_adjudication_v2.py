import copy
import json
import pytest
from src import lighthouse_source_adjudication_v2 as m
from src.source_adjudication_v2 import decision
from src.spineforge_v21_wire import project_payload


def fixture():
    _, plan, contract = m.prepare()
    data = m.audit_payload(m.FLAWED.read_text(), plan, contract)
    text = {r['span_id']: r['repaired_text'] for r in data['story_segments']}
    refs = {r['id']: i for i,r in enumerate(contract['requirements'],1)}
    rescue = next(refs[r['id']] for r in contract['requirements'] if 'bir üst basamakta' in r['source_quote'])
    final = next(refs[r['id']] for r in contract['requirements'] if 'Son görüntü:' in r['source_quote'])
    findings = []
    for family,sid,source,witnesses in [('state_continuity','S196',[],['S008','S196']),
            ('spatial_consistency','S177',[rescue],['S177']),
            ('closure_integrity','S200',[final],['S200'])]:
        findings.append(dict(family=family,severity='moderate',repair_scope='SCENE_REPAIR',
            span_ids=[sid],exact_text=text[sid],reason='Fixture, not semantic qualification.',
            source_requirements=source,evidence=[{'span_id': s,'quote': text[s]} for s in witnesses]))
    return data,contract,dict(findings=findings,advisory_notes=[],unresolved_material_issues=[],
        summary='Synthetic fixture only.',reviewed_requirements=list(refs.values()))


def test_all_source_requirements_and_all_three_defects_required():
    data,c,r=fixture()
    chosen=decision(r,data['story_segments'],c)
    assert m.qualification_passed('recorded_deviations',r,chosen)
    for i in range(3):
        bad=copy.deepcopy(r);bad['findings'].pop(i)
        assert not m.qualification_passed('recorded_deviations',bad,decision(bad,data['story_segments'],c))
    for coverage in [r['reviewed_requirements'][:-1],r['reviewed_requirements']+[1],r['reviewed_requirements']+[255]]:
        bad=copy.deepcopy(r);bad['reviewed_requirements']=coverage
        with pytest.raises(RuntimeError):decision(bad,data['story_segments'],c)


def test_fabricated_evidence_and_unknown_source_rejected():
    data,c,r=fixture()
    for change in ['quote','span','requirement','single_state','unwitnessed_target']:
        bad=copy.deepcopy(r);f=bad['findings'][0]
        if change=='quote':f['evidence'][0]['quote']='cord left behind at the harbour'
        if change=='span':f['evidence'][0]['span_id']='S999'
        if change=='requirement':f['source_requirements']=[255]
        if change=='single_state':f['evidence']=f['evidence'][1:]
        if change=='unwitnessed_target':f['evidence']=f['evidence'][:1]
        with pytest.raises(RuntimeError):decision(bad,data['story_segments'],c)


def test_read_only_evidence_does_not_expand_repair_scope():
    data,c,r=fixture();chosen=decision(r,data['story_segments'],c)
    assert chosen['findings'][0]['span_ids']==['S196']
    assert 'S008' not in {sid for f in chosen['findings'] for sid in f['span_ids']}


def test_saved_failed_audit_is_not_silently_upgraded():
    data,c,_=fixture()
    saved=json.loads((m.PRIOR_PATH.parent/'calls.json').read_text())[-1]['response']
    with pytest.raises(RuntimeError):decision(saved,data['story_segments'],c)


def test_no_prior_labels_or_expected_defects_in_model_input():
    data,c,_=fixture()
    assert 'candidate_evidence' not in data and 'candidate_observations' not in data
    assert [r['number'] for r in data['source_requirements']]==list(range(1,len(c['requirements'])+1))


def test_bad_clean_control_stops_after_one_call(tmp_path):
    prepared,plan,c=m.prepare();calls=[]
    def call(stage,data):
        calls.append(stage)
        body={'findings':[],'advisory_notes':[],'unresolved_material_issues':['ambiguous fixture'],
              'summary':'Fixture.', 'reviewed_requirements':list(range(1,len(c['requirements'])+1))}
        wire=project_payload(data)
        return {**body,'usage':{'api_calls':1,'input_tokens':100,'output_tokens':100,'total_tokens':200,'reasoning_tokens':0,'cost_usd':.01,'latency_seconds':1},
          'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}
    result=m.run({**prepared,'explicit_paid_authorization':True},tmp_path,call)
    assert calls==['AUDIT'] and result['status']=='QUALIFICATION_FAILED'
    assert result['confirmed_story_cost_usd']==2.57949486
    assert result['budget_committed_total_usd']==2.71949486


def test_bounded_patch_reaudit_and_proof_with_synthetic_responses(tmp_path):
    prepared,plan,c=m.prepare();calls=[]
    _,_,negative=fixture()
    def call(stage,data):
        calls.append(stage)
        if stage=='PATCH':
            row=next(r for r in data['story_segments'] if r['span_id']=='S200')
            body={'patches':[{'span_id':'S200','old_text':row['repaired_text'],
                   'replacement_text':'Ekin turned the empty cord in her pocket as she caught up with Duru.'}],
                   'summary':'Plumbing fixture, not evidence of semantic repair.'}
        elif len(calls)==2:body=negative
        else:body={'findings':[],'advisory_notes':[],'unresolved_material_issues':[],
                   'summary':'Synthetic accept.', 'reviewed_requirements':list(range(1,len(c['requirements'])+1))}
        wire=project_payload(data)
        return {**body,'usage':{'api_calls':1,'input_tokens':100,'output_tokens':100,'total_tokens':200,'reasoning_tokens':0,'cost_usd':.01,'latency_seconds':1},
          'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}
    result=m.run({**prepared,'explicit_paid_authorization':True},tmp_path,call)
    assert result['status']=='ACCEPT' and calls==['AUDIT','AUDIT','PATCH','AUDIT']
    proof=json.loads((tmp_path/m.ID/'patch-proof-01.json').read_text())
    assert proof['outside_patches_unchanged'] and proof['changed_span_ids']==['S200']
