import json
import shutil
from pathlib import Path

import pytest

from scripts.spineforge_relay_story_replay import verify_story

ROOT = Path('evidence/spineforge-relay/SFR-V1-Q9-GREENHOUSE-COMPLETE-20261008')
FIXTURE = Path('tests/fixtures/spineforge_relay_v1/q9_greenhouse_complete_coverage.json')


def test_q9_saved_calls_reproduce_state_and_complete_usage():
    result = verify_story(ROOT, FIXTURE)
    assert result['provider_calls'] == 4
    assert result['rewrite_count'] == 0
    assert result['cost_usd'] == 0.0834675
    assert result['total_tokens'] == 27635
    assert result['final_revision'] == 2
    assert result['next_spine_beat'] is None
    closed = json.loads(Path('evidence/spineforge-relay/SFR-V1-Q9-PREFLIGHT-20261008/closed-authority.json').read_text())
    assert closed['status'] == 'CLOSED'
    reservation = closed['reservations']['complete-story']
    assert reservation['status'] == 'SETTLED'
    assert reservation['actual_calls'] == 4
    assert float(reservation['actual_cost_usd']) == result['cost_usd']


@pytest.mark.parametrize('target', ['cost', 'state', 'coverage', 'predecessor'])
def test_q9_corrupted_saved_evidence_fails_closed(tmp_path, target):
    root = tmp_path/'evidence'
    shutil.copytree(ROOT, root)
    filename = {'cost':'A1-1-writer-ledger.json', 'state':'A2-accepted.json', 'coverage':'A1-coverage-contract.json', 'predecessor':'A2-1-writer-request.json'}[target]
    path = root/filename
    data = json.loads(path.read_text())
    if target == 'cost':
        data['cost_usd'] = 0
    elif target == 'state':
        data['state_after']['revision'] = 3
    elif target == 'coverage':
        data['obligations'][0]['source_text'] += ' altered'
    else:
        payload = json.loads(data['messages'][1]['content'])
        payload['previous_accepted_scene']['prose'] = 'replacement prose'
        data['messages'][1]['content'] = json.dumps(payload)
    path.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match='Saved Relay evidence mismatch'):
        verify_story(root, FIXTURE)
