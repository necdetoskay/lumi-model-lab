import json
from pathlib import Path

import pytest

from src.spineforge_spatial_story_runner import build_chain, execute_story, prepare, runner_request_for
from src.spineforge_relay_v1_paid_entry import prepare_reserved_story as historical_prepare
from tests.test_spineforge_relay_v1_runner import _guard

FIXTURE = Path('tests/fixtures/spineforge_relay_v1/q10_mosaic_spatial_chain.json')


def fake(calls, *, block_scene=None):
    def call(**kwargs):
        payload = json.loads(kwargs['user_prompt'])
        calls.append(payload)
        writer = 'gpt-5.6-sol' in kwargs['model']
        stage = 'writer' if writer else 'guard'
        assert 'spatial_contract' in payload
        assert 'plan_coverage_contract' in payload
        if writer:
            anchors = [f"{e['id']} {p['subject']} {p['action']} {p['target']}." for e in payload['scene_contract']['required_events'] for p in e['predicates']]
            text = ' '.join(anchors + ['calm'] * 190)
        else:
            report = _guard(payload, payload['candidate_prose'], block=payload['scene_contract']['scene_id'] == block_scene)
            for row in report['event_evidence']:
                row['exact_text'] = f"{row['event_id']} {row['subject']} {row['action']} {row['target']}."
            text = json.dumps(report)
        _, request = runner_request_for(stage, payload)
        return text, {'id':'synthetic-'+str(len(calls)), 'choices': [{'finish_reason':'stop','message':{'content':text}}], 'usage':{'prompt_tokens':1200,'completion_tokens':450,'total_tokens':1650,'cost':.01}}, request
    return call


def test_six_scenes_keep_blocker_until_release_and_panel_positions(tmp_path):
    calls = []
    result = execute_story(fixture_path=FIXTURE, api_key='fake', preflight=prepare(FIXTURE), output=tmp_path/'run', call_fn=fake(calls))
    assert result['status'] == 'ACCEPT'
    assert result['state_advanced_to_revision'] == 6
    assert result['next_spine_beat'] is None
    assert len(calls) == 12
    for writer, guard in zip(calls[::2], calls[1::2]):
        assert writer['spatial_contract'] == guard['spatial_contract']
        assert writer['plan_coverage_contract'] == guard['plan_coverage_contract']
    assert calls[2]['spatial_contract']['entry']['access_constraints'][0]['active'] is True
    assert calls[4]['spatial_contract']['exit']['access_constraints'][0]['active'] is False
    for index, payload in enumerate(calls[::2]):
        assert payload['story_state']['revision'] == index
        if index:
            assert payload['previous_accepted_scene']['state_after']['revision'] == index
    assert calls[10]['spatial_contract']['exit']['positions']['mosaic_panel'] == 'display_alcove'
    from scripts.spineforge_relay_story_replay import verify_story
    replay = verify_story(tmp_path/'run', FIXTURE)
    assert replay['final_revision'] == 6 and replay['provider_calls'] == 12


def test_failure_does_not_skip_a_scene_or_reopen_blocker(tmp_path):
    calls = []
    result = execute_story(fixture_path=FIXTURE, api_key='fake', preflight=prepare(FIXTURE), output=tmp_path/'blocked', call_fn=fake(calls, block_scene='S03'))
    assert result['status'] == 'REJECT_NON_CONVERGENT'
    assert result['state_advanced_to_revision'] == 2
    assert result['next_spine_beat'] == 'S03'
    assert len(calls) == 8
    assert all(p['spatial_contract']['entry']['access_constraints'][0]['active'] for p in calls)
    assert not any(p['scene_contract']['scene_id'] == 'S04' for p in calls)


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'edge', 'blocker', 'position'])
def test_bad_spatial_inputs_deny_before_dispatch(tmp_path, mutation):
    f = json.loads(FIXTURE.read_text())
    if mutation == 'missing':
        f['spatial_plans'].pop()
    elif mutation == 'duplicate':
        f['spatial_plans'][1] = f['spatial_plans'][0]
    elif mutation == 'edge':
        f['spatial_plans'][3]['operations'][0]['edge_id'] = 'invented_edge'
    elif mutation == 'blocker':
        f['spatial_plans'][2]['operations'] = []
    else:
        f['initial_state']['world']['spatial']['positions']['mosaic_panel'] = 'gallery_entry'
    path = tmp_path/'bad.json'
    path.write_text(json.dumps(f))
    calls = []
    with pytest.raises((ValueError, RuntimeError)):
        execute_story(fixture_path=path, api_key='fake', preflight={}, output=tmp_path/'out', call_fn=fake(calls))
    assert calls == []


def test_new_preflight_freezes_topology_and_historical_q9_is_current():
    pf = prepare(FIXTURE)
    assert pf['max_calls'] == 24
    assert pf['max_story_cost_usd'] == .60
    assert len(pf['spatial_contract_sha256']) == 6
    assert build_chain(FIXTURE)[3].revision == 0
    root = Path('evidence/spineforge-relay/SFR-V1-Q9-PREFLIGHT-20261008')
    assert json.loads((root/'preflight.json').read_text()) == historical_prepare(Path('tests/fixtures/spineforge_relay_v1/q9_greenhouse_complete_coverage.json'))
    from src.spineforge_spatial_paid_entry import prepare_reserved_story
    prepared = Path('evidence/spineforge-relay/SFR-V1-Q10-PREFLIGHT-20261008')
    assert json.loads((prepared/'preflight.json').read_text()) == prepare_reserved_story(FIXTURE)
    assert json.loads((prepared/'proposal.json').read_text())['paid_execution_authorized'] is False


@pytest.mark.parametrize('closed', [False, True])
def test_spatial_engine_uses_one_shared_paid_scope_without_fallback(tmp_path, closed):
    from src.spineforge_spatial_paid_entry import prepare_reserved_story
    from src.spineforge_relay_v1_contracts import canonical_sha256
    from src.spineforge_relay_v1_reservations import PaidGrantV1, PaidLedgerV1, run_reserved, ReservationError
    from tests.test_spineforge_relay_v1_reservations import MemoryAuthority
    pf = prepare_reserved_story(FIXTURE)
    grant = PaidGrantV1(id='synthetic-q10', approval_evidence_sha256='a'*64, max_calls=24, max_cost_usd='.60', scopes=[dict(id='story',preflight_sha256=canonical_sha256(pf),max_calls=24,max_cost_usd='.60',allowed_models=['openai/gpt-5.6-sol','anthropic/claude-sonnet-5.5'])])
    store = MemoryAuthority(PaidLedgerV1(grant=grant,status='CLOSED' if closed else 'OPEN'))
    calls = []
    def invoke(call):
        return execute_story(fixture_path=FIXTURE, api_key='synthetic-secret', preflight=pf['runner_preflight'], output=tmp_path/'reserved', call_fn=call)
    kwargs = dict(store=store,grant_id=grant.id,scope_id='story',preflight=pf,executor_id='synthetic-local',invoke=invoke,transport=fake(calls))
    if closed:
        with pytest.raises(ReservationError):
            run_reserved(**kwargs)
        assert not calls
    else:
        assert run_reserved(**kwargs)['status'] == 'ACCEPT'
        assert store.ledger.reservations['story']['actual_calls'] == 12
        with pytest.raises(ReservationError):
            run_reserved(**kwargs)
        assert len(calls) == 12
