"""Seed-aware spatial capabilities and scene-local links; no inferred repair."""
from pathlib import Path
from typing import Literal
from pydantic import Field
from src.spineforge_production_compact_v3 import CompactSceneV3,CompactStoryPlanV3,compile_compact_v3
from src.spineforge_production_compact_v2 import SpatialStepV2
from src.spineforge_relay_v1_contracts import canonical_sha256

class SpatialStepV4(SpatialStepV2):
    kind: Literal['MOVE','BLOCK','RELEASE','ACCESS','JOINT_MOVE']

class CompactSceneV4(CompactSceneV3):
    spatial_operations: list[SpatialStepV4]=Field(default_factory=list)

class CompactStoryPlanV4(CompactStoryPlanV3):
    schema_name: Literal['spineforge.compact-story-plan.v4']='spineforge.compact-story-plan.v4'
    scenes: list[CompactSceneV4]=Field(min_length=2,max_length=12)

class PlanLinkErrorV4(ValueError):
    def __init__(self,findings):
        self.findings=findings
        super().__init__('Invalid plan links/capabilities: '+ '; '.join(f['path']+': '+f['message'] for f in findings))

def capabilities(seed):
    kinds=['ACCESS']
    if seed.world.get('spatial',{}).get('access_constraints'):kinds+=['BLOCK','RELEASE']
    if seed.topology.edges:kinds+=['MOVE','JOINT_MOVE']
    return dict(allowed_spatial_kinds=kinds,ordering_scope='CURRENT_SCENE_ONLY',
        discovery_is_narrative_event_not_spatial_locate=True)

def link_findings(raw,seed):
    findings=[]
    if not isinstance(raw,dict) or not isinstance(raw.get('scenes'),list):return findings
    allowed=capabilities(seed)['allowed_spatial_kinds']
    for i,scene in enumerate(raw['scenes']):
        if not isinstance(scene,dict):continue
        events=scene.get('events',[])
        ids=[e.get('id') for e in events if isinstance(e,dict) and isinstance(e.get('id'),str)] if isinstance(events,list) else []
        orders=scene.get('ordered_dependencies',[])
        for j,order in enumerate(orders if isinstance(orders,list) else []):
            if not isinstance(order,dict):continue
            for side in ['before','after']:
                anchor=order.get(side)
                if isinstance(anchor,dict) and isinstance(anchor.get('event_id'),str) and anchor['event_id'] not in ids:
                    findings.append(dict(code='NONLOCAL_ORDER_EVENT',path=f'/scenes/{i}/ordered_dependencies/{j}/{side}/event_id',message='Choose an event in this scene; route already orders different scenes',value=anchor['event_id'],allowed_event_ids=ids))
        ops=scene.get('spatial_operations',[])
        for j,op in enumerate(ops if isinstance(ops,list) else []):
            if not isinstance(op,dict):continue
            prefix=f'/scenes/{i}/spatial_operations/{j}'
            if isinstance(op.get('kind'),str) and op['kind'] not in allowed:
                findings.append(dict(code='UNAVAILABLE_SPATIAL_KIND',path=prefix+'/kind',message='Use an available spatial kind; discovering known objects is an evidence/knowledge event',value=op['kind'],allowed_kinds=allowed))
            if isinstance(op.get('event_id'),str) and op['event_id'] not in ids:
                findings.append(dict(code='UNKNOWN_SPATIAL_EVENT',path=prefix+'/event_id',message='Bind to an event in this scene',value=op['event_id'],allowed_event_ids=ids))
    return findings

def compact_planner_input_v4(request,seed):
    schema=CompactStoryPlanV4.model_json_schema()
    schema['$defs']['SpatialStepV4']['properties']['kind']['enum']=capabilities(seed)['allowed_spatial_kinds']
    return dict(schema='spineforge.compact-planner-input.v4',request=request.model_dump(mode='json'),seed=seed.model_dump(mode='json'),request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),instructions=Path('prompts/spineforge_production_compact_v4.md').read_text(encoding='utf8'),capabilities=capabilities(seed),output_schema=schema)

def parse_compact_v4(raw,seed):
    findings=link_findings(raw,seed)
    if findings:raise PlanLinkErrorV4(findings)
    return CompactStoryPlanV4.model_validate(raw)

def compile_compact_v4(request,seed,candidate):
    # Recheck at compiler entry; no silent dropping, aliases or inferred operations.
    candidate=parse_compact_v4(candidate.model_dump(mode='json'),seed)
    raw=candidate.model_dump(mode='json');raw['schema_name']='spineforge.compact-story-plan.v3'
    return compile_compact_v3(request,seed,CompactStoryPlanV3.model_validate(raw))
