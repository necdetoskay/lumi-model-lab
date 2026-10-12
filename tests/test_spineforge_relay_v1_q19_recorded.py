import json,shutil
from pathlib import Path
import pytest
from scripts.spineforge_production_range_budget_audit import verify_story

ROOT=Path('evidence/spineforge-relay/SFR-V1-Q19-SOURCE-RANGE-ROBOT-20261009')

def test_q19_freezes_four_scenes_and_denies_guard_before_dispatch():
    proof=verify_story(ROOT/'story',ROOT/'plan-1-fixture.json')
    assert proof['status']=='OFFLINE_BUDGET_ADMISSION_AUDIT_PASS'
    assert proof['final_revision']==4 and proof['provider_calls']==9 and proof['rewrite_count']==0
    assert proof['admission_failure']==dict(scene_id='S5_DecisionMove',stage='guard',attempt=1,planned_cost_usd=.150578,allowed_cost_usd=.15,dispatched=False)
    assert not (ROOT/'assembled-story.md').exists()

@pytest.mark.parametrize('field,value',[('status','ACCEPT'),('state_advanced_to_revision',5),('known_cost_usd',0)])
def test_q19_cannot_be_reclassified_or_state_and_cost_changed(tmp_path,field,value):
    root=tmp_path/'story';shutil.copytree(ROOT/'story',root)
    path=root/'result.json';data=json.loads(path.read_text());data[field]=value
    path.write_text(json.dumps(data),encoding='utf8')
    with pytest.raises(RuntimeError):verify_story(root,ROOT/'plan-1-fixture.json')
