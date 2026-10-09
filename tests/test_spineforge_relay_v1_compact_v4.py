import json,copy
from pathlib import Path
import pytest
from src.spineforge_production_compact_v3 import CompactStoryPlanV3,compile_compact_v3
from src.spineforge_production_compact_v4 import compact_planner_input_v4,parse_compact_v4,compile_compact_v4,PlanLinkErrorV4,link_findings,capabilities
from src.spineforge_seeded_design import verify_frozen_seed
from src.spineforge_story_design import StoryRequestV1
from tests.test_spineforge_relay_v1_production_pipeline import sample
from tests.spineforge_compact_controls import compact_control_v3

ROOT=Path('evidence/spineforge-relay/SFR-V1-Q21-FRESH-MYSTERY-20261009')
def context():
    request=StoryRequestV1.model_validate_json((ROOT/'request-input.json').read_bytes())
    seed=verify_frozen_seed(ROOT/'seed-input.json',ROOT/'frozen-seed.json')
    return request,seed

def test_seed_capabilities_exclude_dead_locate_and_unavailable_movement():
    request,seed=context();payload=compact_planner_input_v4(request,seed)
    assert payload['capabilities']['allowed_spatial_kinds']==['ACCESS']
    assert payload['output_schema']['$defs']['SpatialStepV4']['properties']['kind']['enum']==['ACCESS']
    assert payload['capabilities']['ordering_scope']=='CURRENT_SCENE_ONLY'

def test_posture_capabilities_require_established_access_constraints():
    _,seed=context()
    assert 'BLOCK' not in capabilities(seed)['allowed_spatial_kinds']
    world=copy.deepcopy(seed.world)
    world['spatial']['access_constraints']=[dict(id='established',blocker='Cem',subject='Nisa',target='blue_atlas',active=False)]
    with_constraint=seed.model_copy(update=dict(world=world))
    assert capabilities(with_constraint)['allowed_spatial_kinds']==['ACCESS','BLOCK','RELEASE']

@pytest.mark.parametrize('attempt,count',[(1,6),(2,2)])
def test_q21_all_local_link_and_capability_errors_are_reported_together(attempt,count):
    _,seed=context();raw=json.loads((ROOT/f'plan-{attempt}-compact.json').read_text());raw['schema_name']='spineforge.compact-story-plan.v4'
    with pytest.raises(PlanLinkErrorV4) as exc:parse_compact_v4(raw,seed)
    assert len(exc.value.findings)==count
    assert all(f['path'].startswith('/scenes/') for f in exc.value.findings)
    assert len([f for f in exc.value.findings if f['code']=='UNAVAILABLE_SPATIAL_KIND'])==2

def test_q21_rejections_remain_reproducible_under_frozen_v3():
    request,seed=context()
    for n,error in [(1,'Unknown ordered event'),(2,'LOCATE can only establish an untracked entity at a declared location')]:
        raw=json.loads((ROOT/f'plan-{n}-compact.json').read_text())
        with pytest.raises(ValueError,match=error):compile_compact_v3(request,seed,CompactStoryPlanV3.model_validate(raw))
    assert not (ROOT/'accepted-design.json').exists()

@pytest.mark.parametrize('kind',['mosaic','dialogue'])
def test_valid_existing_control_has_identical_expanded_design(tmp_path,kind):
    paths,design=sample(tmp_path,kind);seed=verify_frozen_seed(paths['seed'],paths['freeze']);request=StoryRequestV1.model_validate_json(paths['request'].read_bytes())
    old=compact_control_v3(design);raw=old.model_dump(mode='json');raw['schema_name']='spineforge.compact-story-plan.v4'
    new=parse_compact_v4(raw,seed)
    assert compile_compact_v4(request,seed,new)==compile_compact_v3(request,seed,old)

def test_spatial_event_and_order_errors_are_not_silently_repaired():
    _,seed=context();raw=json.loads((ROOT/'plan-2-compact.json').read_text());raw['schema_name']='spineforge.compact-story-plan.v4'
    for s in raw['scenes']:s['spatial_operations']=[]
    raw['scenes'][0]['spatial_operations']=[dict(id='bad',kind='MOVE',subject='Nisa',target='library_reading_room',event_id='missing')]
    findings=link_findings(raw,seed)
    assert {f['code'] for f in findings}=={'UNAVAILABLE_SPATIAL_KIND','UNKNOWN_SPATIAL_EVENT'}
    assert raw['scenes'][0]['spatial_operations'][0]['event_id']=='missing'
