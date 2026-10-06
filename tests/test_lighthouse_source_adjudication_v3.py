import json
import pytest
from src import lighthouse_source_adjudication_v3 as m


def test_recovered_truncation_is_not_an_accepted_clean_control():
    prior=json.loads((m.PRIOR_PATH.parent/'calls.json').read_text())[0]
    provider=prior['provider_evidence']['provider_response']
    assert provider['choices'][0]['finish_reason']=='length'
    assert prior['usage']['output_tokens']==2500
    assert prior['usage']['reasoning_tokens']==2087
    assert m.MAX_TOKENS['AUDIT']==6000
    assert json.loads(m.PRIOR_PATH.read_text())['qualification_passed'] is False


def test_budget_stops_before_either_mandatory_control(tmp_path):
    p,_,_=m.prepare()
    assert p['prior_confirmed_cost_usd']==2.64901286
    result=m.run({**p,'explicit_paid_authorization':True},tmp_path,
                 lambda *_:pytest.fail('No paid call allowed'))
    assert result['status']=='BUDGET_BLOCKED'
    assert result['new_call_count']==0 and result['new_cost_usd']==0
    assert result['mandatory_controls_budget_required_usd']>3
    assert result['budget_committed_total_usd']==2.78901286
    assert not (tmp_path/m.ID/'accepted-story.txt').exists()
