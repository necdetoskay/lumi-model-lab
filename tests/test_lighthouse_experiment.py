import json
import pytest
from src.lighthouse_experiment import (
    approved_input, writer_request, bind_story, constraints_for_findings, run_once,
    dependency_manifest, EXPERIMENT_ID, LIMITS, TOTAL_BUDGET,
)
from src.spineforge_v21_constraints import digest_json


def raw_story():
    # Deliberately synthetic prose. It proves wiring, never story quality.
    prose = ' '.join(['This synthetic paragraph tests exact scene boundary preservation'] * 33) + '.'
    return 'Synthetic Title\n' + '\n'.join(f'[[SC{i:02}]]\n{prose}' for i in range(1, 7))


def usage(cost=.001):
    return {'api_calls': 1, 'input_tokens': 10, 'output_tokens': 10,
            'total_tokens': 20, 'reasoning_tokens': 0, 'cost_usd': cost,
            'latency_seconds': .01}


def finding(sid):
    return {'family': 'spatial_consistency', 'severity': 'serious',
            'repair_scope': 'SCENE_REPAIR', 'span_ids': [sid],
            'exact_text': 'synthetic', 'reason': 'synthetic controlled defect'}


def audit(rows):
    return {'findings': rows, 'summary': 'synthetic test', 'usage': usage()}


def authorization(plan):
    return {'experiment_id': EXPERIMENT_ID, 'plan_sha256': digest_json(plan),
            'writer_request_sha256': digest_json(writer_request(plan)),
            'runtime_manifest_sha256': digest_json(dependency_manifest()),
            'explicit_paid_authorization': True, 'budget_usd': TOTAL_BUDGET,
            'authorization_id': 'FAKE-OFFLINE-TEST'}


def run(tmp_path, initial=None, final=None, cost=.001):
    plan = approved_input()
    def repair(payload):
        return {'replacement_scene': payload['source_scene'],
                'resolved_blocking_finding_indexes': [0], 'preserved_invariants': [],
                'summary': 'synthetic unchanged repair', 'usage': usage()}
    return run_once(plan=plan, authorization=authorization(plan), output_dir=tmp_path,
        writer_fn=lambda req: {'story': raw_story(), 'usage': usage(cost)},
        initial_fn=initial or (lambda payload: audit([])), repair_fn=repair,
        final_fn=final or (lambda payload: audit([])))


def test_clean_path_and_consumed_authorization(tmp_path):
    result = run(tmp_path)
    assert result['status'] == 'ACCEPT' and result['call_count'] == 2
    assert result['repair_count'] == 0
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_single_repair_and_targeted_final(tmp_path):
    plan = approved_input()
    artifact = bind_story(raw_story(), plan)
    sid = next(r['span_id'] for r in artifact['segments'] if r['scene_id'] == 'SC05')
    def final(payload):
        assert payload['audit_phase'] == 'FINAL'
        assert payload['routing_policy']['full_story_reaudit_forbidden']
        return audit([])
    result = run(tmp_path, initial=lambda p: audit([finding(sid)]), final=final)
    assert result['status'] == 'ACCEPT' and result['call_count'] == 4
    assert result['repair_count'] == 1
    rewrite = json.loads((tmp_path / 'FAKE-OFFLINE-TEST/rewrite.json').read_text())
    assert rewrite['outside_cluster_unchanged'] is True


def test_nonconvergent_stops_without_second_repair(tmp_path):
    artifact = bind_story(raw_story(), approved_input())
    sid = next(r['span_id'] for r in artifact['segments'] if r['scene_id'] == 'SC05')
    result = run(tmp_path, initial=lambda p: audit([finding(sid)]),
                 final=lambda p: audit([finding('R001')]))
    assert result['status'] == 'REJECT_NON_CONVERGENT'
    assert result['call_count'] == 4 and result['repair_count'] == 1
    assert not (tmp_path / 'FAKE-OFFLINE-TEST/accepted-story.txt').exists()


def test_writer_cost_overrun_stops_before_audit(tmp_path):
    result = run(tmp_path, cost=.031)
    assert result['status'] == 'REJECT_RUNTIME' and result['call_count'] == 1


def test_invalid_final_preserves_response(tmp_path):
    artifact = bind_story(raw_story(), approved_input())
    sid = next(r['span_id'] for r in artifact['segments'] if r['scene_id'] == 'SC05')
    result = run(tmp_path, initial=lambda p: audit([finding(sid)]),
                 final=lambda p: {'findings': [], 'usage': usage()})
    assert result['status'] == 'REJECT_RUNTIME' and result['call_count'] == 4
    calls = json.loads((tmp_path / 'FAKE-OFFLINE-TEST/calls.json').read_text())
    assert calls[-1]['response']['findings'] == []
    assert 'summary' in calls[-1]['failure_message']


@pytest.mark.parametrize('key,value', [('explicit_paid_authorization', False),
    ('plan_sha256', 'stale'), ('writer_request_sha256', 'stale'),
    ('runtime_manifest_sha256', 'stale'), ('budget_usd', .20)])
def test_invalid_authority_never_calls(tmp_path, key, value):
    plan = approved_input()
    auth = authorization(plan)
    auth[key] = value
    def forbidden(_):
        pytest.fail('Model dispatch must not occur')
    with pytest.raises(RuntimeError):
        run_once(plan=plan, authorization=auth, output_dir=tmp_path,
                 writer_fn=forbidden, initial_fn=forbidden, repair_fn=forbidden, final_fn=forbidden)


def test_actual_scene_boundaries_and_multi_scene_rejection():
    plan = approved_input()
    artifact = bind_story(raw_story(), plan)
    first = next(r['span_id'] for r in artifact['segments'] if r['scene_id'] == 'SC01')
    last = next(r['span_id'] for r in artifact['segments'] if r['scene_id'] == 'SC06')
    assert '[[SC' not in artifact['story']
    with pytest.raises(RuntimeError, match='more than one'):
        constraints_for_findings(plan, artifact, [finding(first), finding(last)])


@pytest.mark.parametrize('raw', [raw_story().replace('[[SC02]]', '[[SC01]]'),
                                raw_story().replace('[[SC06]]', '')])
def test_invalid_scene_markers_stop(raw):
    with pytest.raises(RuntimeError):
        bind_story(raw, approved_input())


def test_missing_usage_does_not_become_zero(tmp_path):
    plan = approved_input()
    def forbidden(_):
        pytest.fail('No audit after unknown cost')
    result = run_once(plan=plan, authorization=authorization(plan), output_dir=tmp_path,
        writer_fn=lambda p: {'story': raw_story()}, initial_fn=forbidden,
        repair_fn=forbidden, final_fn=forbidden)
    assert result['status'] == 'REJECT_RUNTIME'
    assert result['accounting_complete'] is False and result['call_count'] == 1


def test_writer_transport_timeout_is_not_retried(monkeypatch):
    import requests
    from src.lighthouse_experiment import writer_call_once
    calls = []
    def timeout(*args, **kwargs):
        calls.append(kwargs)
        raise requests.Timeout('synthetic timeout')
    monkeypatch.setattr(requests, 'post', timeout)
    from src.spineforge_v21_model_adapter import AdapterResponseError
    with pytest.raises(AdapterResponseError):
        writer_call_once('fake-test-key', writer_request(approved_input()))
    assert len(calls) == 1
