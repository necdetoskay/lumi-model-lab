import json,hashlib,shutil
from decimal import Decimal
from pathlib import Path
import pytest
from scripts.spineforge_production_compact_range_replay import verify_story

ROOT=Path('evidence/spineforge-relay/SFR-V1-Q20-COMPACT-RANGE-ROBOT-20261009')

def audit(root):
    read=lambda name:json.loads((root/name).read_text(encoding='utf8'))
    for name,digest in read('manifest.json')['files'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
    proof=verify_story(root/'story',root/'plan-1-fixture.json')
    result=read('result.json')
    assert result['status']=='ACCEPT' and result['provider_calls']==14
    assert proof['final_revision']==6 and proof['next_spine_beat'] is None
    assert proof['rewrite_count']==0 and len(proof['accepted_scenes'])==6
    assert sum(Decimal(str(r['cost_usd'])) for r in result['ledger'])==Decimal('0.5436625')
    assert read('state-comparison.json')['final_state_sha256']==proof['final_state_sha256']
    assert read('plan-1-review.json')['decision']=='PASS'
    return proof

def test_complete_q20_replays_without_seed_mutation_or_rewrites():
    audit(ROOT)

@pytest.mark.parametrize('target',['prose','cost','state','source'])
def test_accepted_q20_evidence_cannot_be_rewritten(tmp_path,target):
    root=tmp_path/'run';shutil.copytree(ROOT,root)
    path=root/{'prose':'assembled-story.md','cost':'result.json','state':'state-comparison.json','source':'frozen-sources/src/spineforge_production_compact_ranges.py'}[target]
    path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises((AssertionError,RuntimeError,ValueError)):audit(root)
