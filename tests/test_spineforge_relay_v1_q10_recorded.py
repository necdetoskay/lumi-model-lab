import json
import shutil
from pathlib import Path

import pytest

from scripts.spineforge_relay_story_replay import verify_story

ROOT = Path('evidence/spineforge-relay/SFR-V1-Q10-MOSAIC-SPATIAL-20261008')
FIXTURE = Path('tests/fixtures/spineforge_relay_v1/q10_mosaic_spatial_chain.json')


def test_q10_complete_saved_route_reproduces_usage_and_state():
    proof = verify_story(ROOT, FIXTURE)
    assert proof['accepted_scenes'] == ['S01','S02','S03','S04','S05','S06']
    assert proof['provider_calls'] == 12
    assert proof['rewrite_count'] == 0
    assert proof['cost_usd'] == 0.3088475
    assert proof['total_tokens'] == 112582
    assert proof['final_revision'] == 6 and proof['next_spine_beat'] is None
    ledger = json.loads(Path('evidence/spineforge-relay/SFR-V1-Q10-PREFLIGHT-20261008/closed-authority.json').read_text())
    assert ledger['status'] == 'CLOSED'
    scope = ledger['reservations']['complete-story']
    assert scope['status'] == 'SETTLED' and scope['actual_calls'] == 12
    assert float(scope['actual_cost_usd']) == proof['cost_usd']


@pytest.mark.parametrize('target', ['spatial','state','coverage','usage','predecessor'])
def test_q10_tampered_evidence_is_rejected(tmp_path, target):
    root = tmp_path/'records'
    shutil.copytree(ROOT, root)
    filename = {'spatial':'S03-spatial-contract.json','state':'S06-accepted.json','coverage':'S04-coverage-contract.json','usage':'S05-1-guard-ledger.json','predecessor':'S04-1-writer-request.json'}[target]
    path = root/filename
    data = json.loads(path.read_text())
    if target == 'spatial':
        data['exit']['access_constraints'][0]['active'] = True
    elif target == 'state':
        data['state_after']['objects']['mosaic_panel']['state']['intact'] = False
    elif target == 'coverage':
        data['obligations'][0]['source_text'] += ' altered'
    elif target == 'usage':
        data['cost_usd'] = 0
    else:
        payload = json.loads(data['messages'][1]['content'])
        payload['previous_accepted_scene']['prose'] = 'substitute'
        data['messages'][1]['content'] = json.dumps(payload)
    path.write_text(json.dumps(data))
    with pytest.raises(RuntimeError, match='Saved Relay evidence mismatch'):
        verify_story(root, FIXTURE)
