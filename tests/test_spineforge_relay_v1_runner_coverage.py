import json
from pathlib import Path

import pytest

from src.spineforge_relay_v1_runner import build_chain, execute_story, prepare, runner_request_for
from src.spineforge_relay_v1_paid_entry import prepare_reserved_story
from tests.test_spineforge_relay_v1_runner import _guard

FIXTURE = Path('tests/fixtures/spineforge_relay_v1/q9_greenhouse_complete_coverage.json')


def fake_provider(calls, *, reverse=False, residual_block=False):
    def call(**kwargs):
        payload = json.loads(kwargs['user_prompt'])
        writer = 'gpt-5.6-sol' in kwargs['model']
        stage = 'writer' if writer else 'guard'
        calls.append(payload)
        assert 'plan_coverage_contract' in payload
        assert 'source_text' in kwargs['system_prompt']
        if writer:
            anchors = [f"{e['id']} {p['subject']} {p['action']} {p['target']}." for e in payload['scene_contract']['required_events'] for p in e['predicates']]
            if reverse:
                anchors.reverse()
            text = ' '.join(anchors + ['calm'] * 190)
        else:
            report = _guard(payload, payload['candidate_prose'], block=residual_block)
            for row in report['event_evidence']:
                row['exact_text'] = f"{row['event_id']} {row['subject']} {row['action']} {row['target']}."
            text = json.dumps(report)
        _, request = runner_request_for(stage, payload)
        return text, {'choices': [{'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 1200, 'completion_tokens': 450, 'total_tokens': 1650, 'cost': .01}}, request
    return call


def test_complete_story_shares_coverage_and_previous_prose(tmp_path):
    calls = []
    result = execute_story(fixture_path=FIXTURE, api_key='fake', preflight=prepare(FIXTURE), output=tmp_path/'run', call_fn=fake_provider(calls))
    assert result['status'] == 'ACCEPT'
    assert result['state_advanced_to_revision'] == 2
    assert result['next_spine_beat'] is None
    assert len(calls) == 4
    for writer, guard in zip(calls[::2], calls[1::2]):
        assert writer['plan_coverage_contract'] == guard['plan_coverage_contract']
    assert calls[0]['previous_accepted_scene'] is None
    previous = calls[2]['previous_accepted_scene']
    assert previous['state_after']['revision'] == 1
    assert previous['prose'] == calls[1]['candidate_prose']


@pytest.mark.parametrize('mode', ['reverse', 'residual_block'])
def test_order_and_residual_failure_stop_without_advancing(tmp_path, mode):
    calls = []
    result = execute_story(fixture_path=FIXTURE, api_key='fake', preflight=prepare(FIXTURE), output=tmp_path/mode, call_fn=fake_provider(calls, **{mode: True}))
    assert result['status'] == 'REJECT_NON_CONVERGENT'
    assert result['state_advanced_to_revision'] == 0
    assert len(calls) == 4
    assert all(p['scene_contract']['scene_id'] == 'A1' for p in calls)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'stale', 'wrong_actor'])
def test_bad_coverage_fails_before_any_dispatch(tmp_path, mutation):
    fixture = json.loads(FIXTURE.read_text())
    if mutation == 'missing':
        fixture['coverage_plans'].pop()
    elif mutation == 'duplicate':
        fixture['coverage_plans'][1] = fixture['coverage_plans'][0]
    elif mutation == 'stale':
        fixture['scene_plans'][0]['turn'] += ' Changed.'
    else:
        fixture['coverage_plans'][0]['obligations'][0]['required_predicates'][0]['subject'] = 'wrong_actor'
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(fixture))
    calls = []
    with pytest.raises((RuntimeError, ValueError)):
        execute_story(fixture_path=path, api_key='fake', preflight={}, output=tmp_path/'out', call_fn=fake_provider(calls))
    assert calls == []


def test_v2_preflight_binds_all_coverage_and_prompt_sources():
    preflight = prepare(FIXTURE)
    assert preflight['schema'].endswith('.v2')
    assert preflight['max_calls'] == 8
    assert len(preflight['coverage_contract_sha256']) == 2
    paths = {row['path'] for row in preflight['sources']}
    assert {'src/spineforge_relay_v1_runner.py', 'src/spineforge_relay_v1_coverage.py', 'prompts/spineforge_relay_v1_coverage_writer.md', 'prompts/spineforge_relay_v1_coverage_guard.md'} <= paths
    assert build_chain(FIXTURE)[3].revision == 0


def test_saved_q9_preflight_is_current_and_has_no_paid_authority():
    root = Path('evidence/spineforge-relay/SFR-V1-Q9-PREFLIGHT-20261008')
    assert json.loads((root/'preflight.json').read_text()) == prepare_reserved_story(FIXTURE)
    proposal = json.loads((root/'proposal.json').read_text())
    assert proposal['grant_registered'] is False
    assert proposal['paid_execution_authorized'] is False
    assert proposal['new_provider_calls'] == 0
