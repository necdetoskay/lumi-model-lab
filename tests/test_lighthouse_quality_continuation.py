import json
import pytest
from src.lighthouse_quality_continuation import prepare, run_once
from tests.test_lighthouse_experiment import usage, audit, finding


def grant():
    p, _, _ = prepare()
    return {k: p[k] for k in ['experiment_id', 'plan_sha256', 'source_story_sha256',
                              'runtime_manifest_sha256', 'budget_usd']} | {
        'explicit_paid_authorization': True, 'authorization_id': 'FAKE-CONTINUATION'}


def run(tmp_path, initial=None, authorization=None):
    return run_once(authorization=authorization or grant(), output_dir=tmp_path,
        initial_fn=initial or (lambda p: audit([])),
        repair_fn=lambda p: pytest.fail('Unexpected repair'),
        final_fn=lambda p: pytest.fail('Unexpected final'))


def test_saved_long_story_audited_without_writer(tmp_path):
    observed = []
    def initial(p):
        observed.append(p)
        assert len(p['full_story'].split()) == 2531
        return audit([])
    r = run(tmp_path, initial)
    assert r['status'] == 'ACCEPT' and r['call_count'] == 1 and r['writer_call_count'] == 0
    assert len(observed) == 1
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_cross_scene_findings_stop_before_repair(tmp_path):
    _, _, a = prepare()
    ids = [next(s['span_id'] for s in a['segments'] if s['scene_id'] == scene)
           for scene in ['SC01', 'SC03']]
    r = run(tmp_path, lambda p: audit([finding(i) for i in ids]))
    assert r['status'] == 'REJECT_RUNTIME' and r['call_count'] == 1
    assert 'more than one' in r['failure_message']


@pytest.mark.parametrize('key', ['source_story_sha256', 'runtime_manifest_sha256', 'budget_usd'])
def test_drift_stops_before_dispatch(tmp_path, key):
    g = grant(); g[key] = 'DRIFT'
    with pytest.raises(RuntimeError, match='authorization drift'):
        run(tmp_path, authorization=g)
    assert not list(tmp_path.iterdir())


def test_unknown_usage_is_not_zero_cost(tmp_path):
    r = run(tmp_path, lambda p: {'findings': [], 'summary': 'mock'})
    assert r['call_count'] == 1 and not r['accounting_complete']
