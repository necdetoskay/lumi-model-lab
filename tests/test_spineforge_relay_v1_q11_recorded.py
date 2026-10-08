import json
import shutil
from pathlib import Path

import pytest

from scripts.spineforge_relay_story_replay import verify_story

ROOT=Path('evidence/spineforge-relay/SFR-V1-Q11-JOINT-MOSAIC-20261008')
FIXTURE=Path('tests/fixtures/spineforge_relay_v1/q11_joint_mosaic_chain.json')


def test_recorded_rejection_replays_without_advancing_or_extra_attempt():
    proof=verify_story(ROOT,FIXTURE)
    assert proof['recorded_decision']=='REJECT_NON_CONVERGENT'
    assert proof['accepted_scenes']==['S01','S02','S03']
    assert proof['provider_calls']==10 and proof['rewrite_count']==1
    assert proof['cost_usd']==.2376985 and proof['total_tokens']==87681
    assert proof['final_revision']==3 and proof['next_spine_beat']=='S04'
    assert not (ROOT/'S04-accepted.json').exists()
    assert not (ROOT/'S04-3-writer-request.json').exists()
    assert not (ROOT/'S05-1-writer-request.json').exists()
    closed=json.loads(Path('evidence/spineforge-relay/SFR-V1-Q11-PREFLIGHT-20261008/closed-authority.json').read_text())
    assert closed['status']=='CLOSED'
    assert closed['reservations']['complete-story']['actual_calls']==10
    assert float(closed['reservations']['complete-story']['actual_cost_usd'])==proof['cost_usd']


def test_failure_is_quote_typography_while_joint_quote_is_exact():
    analysis=json.loads((ROOT/'failure-analysis.json').read_text())
    assert analysis['diagnostic_normalization_used_for_acceptance'] is False
    for row in analysis['attempts']:
        assert row['original_quote'].replace('\u2019', "'")==row['guard_quote']
        assert row['original_quote'] != row['guard_quote']
        assert row['joint_move_exact_match'] is True


@pytest.mark.parametrize('target',['decision','state','cost','retroactive_quote_repair'])
def test_saved_rejection_cannot_be_reclassified_or_patched(tmp_path,target):
    root=tmp_path/'records'
    shutil.copytree(ROOT,root)
    if target in ('decision','state'):
        path=root/'result.json';data=json.loads(path.read_text())
        if target=='decision':data['status']='ACCEPT'
        else:data['state_advanced_to_revision']=4
        path.write_text(json.dumps(data))
    elif target=='cost':
        path=root/'S04-2-guard-ledger.json';data=json.loads(path.read_text());data['cost_usd']=0
        path.write_text(json.dumps(data))
    else:
        path=root/'S04-2-guard-text.json';data=json.loads(path.read_text());report=json.loads(data['text'])
        for row in report['event_evidence']:
            if row['event_id']=='S04-E04' and row['predicate_id']=='P1':
                row['exact_text']=row['exact_text'].replace("Mert's",'Mert\u2019s')
        data['text']=json.dumps(report);path.write_text(json.dumps(data))
        path=root/'S04-2-guard-response.json';response=json.loads(path.read_text())
        response['choices'][0]['message']['content']=data['text'];path.write_text(json.dumps(response))
    with pytest.raises(RuntimeError,match='Saved Relay evidence mismatch'):
        verify_story(root,FIXTURE)
