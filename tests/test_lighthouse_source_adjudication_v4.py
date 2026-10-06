import pytest
from src import lighthouse_source_adjudication_v4 as m
from src.spineforge_v21_wire import project_payload


def test_approved_four_dollar_cap_runs_control_and_stops_on_unresolved(tmp_path):
    p,_,c=m.prepare();assert p['total_story_budget_usd']==4
    calls=[]
    def call(stage,data):
        calls.append(stage);wire=project_payload(data)
        return {'findings':[],'advisory_notes':[],'unresolved_material_issues':['fixture'],
            'summary':'Synthetic control.', 'reviewed_requirements':list(range(1,len(c['requirements'])+1)),
            'usage':{'api_calls':1,'input_tokens':100,'output_tokens':100,'total_tokens':200,'reasoning_tokens':0,'cost_usd':.01,'latency_seconds':1},
            'request':{'wire_payload':wire,'wire_payload_sha256':m.digest_json(wire),'max_tokens':m.MAX_TOKENS[stage]}}
    r=m.run({**p,'explicit_paid_authorization':True},tmp_path,call)
    assert calls==['AUDIT'] and r['status']=='QUALIFICATION_FAILED'
    assert r['mandatory_controls_budget_required_usd']<4


def test_old_three_dollar_authorization_cannot_authorize_new_runtime(tmp_path):
    p,_,_=m.prepare();p['total_story_budget_usd']=3
    with pytest.raises(RuntimeError,match='Frozen authorization'):
        m.run({**p,'explicit_paid_authorization':True},tmp_path,lambda *_:pytest.fail('no call'))
