"""Bound semantic review via code-owned source IDs, not model-authored pointers."""
from typing import Any, Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import StrictModel, canonical_sha256
from src.spineforge_relay_v1_compile import _value_at
from src.spineforge_relay_v1_q6 import _expected_advance

Category = Literal["USER_REQUEST","CAUSALITY","KNOWLEDGE","RESOURCES","DEADLINE","RESOLUTION","CHARACTER_ARC","LANGUAGE"]

class ReviewSelectionV2(StrictModel):
    field_id: str = Field(min_length=1)
    category: Category
    reason: str = Field(min_length=1)
    repair_instruction: str = Field(min_length=1)

class ReviewOutputV2(StrictModel):
    review_id: str
    decision: Literal["PASS","REWRITE"]
    findings: list[ReviewSelectionV2]
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def check(self):
        if (self.decision=="PASS") != (not self.findings):
            raise ValueError("Review decision/findings disagree")
        return self

class BoundFindingV2(ReviewSelectionV2):
    compact_pointer: str
    source_value: Any

class BoundReviewV2(ReviewOutputV2):
    request_sha256: str
    seed_sha256: str
    design_sha256: str
    compact_sha256: str
    findings: list[BoundFindingV2]

def source_fields(compact):
    raw=compact.model_dump(mode="json");fields=[]
    def add(pointer):
        exists,value=_value_at(raw,pointer)
        if not exists: raise ValueError("Missing compact source field")
        fields.append(dict(id=f"F{len(fields)+1:04}",compact_pointer=pointer,value=value))
    for key in ["premise","character_arc","resolution","request_bindings"]: add("/"+key)
    for i,scene in enumerate(compact.scenes):
        prefix=f"/scenes/{i}"
        for key in ["narrative_purpose","objective","turn","emotional_transition"]: add(prefix+"/"+key)
        for j,_ in enumerate(scene.events): add(prefix+f"/events/{j}")
        for key in ["goal_bindings","ordered_dependencies","spatial_operations","resolutions"]: add(prefix+"/"+key)
    return fields

def build_review_input(request,seed,compact,design,rows):
    fields=source_fields(compact)
    bindings=dict(request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),
        compact_sha256=canonical_sha256(compact),design_sha256=canonical_sha256(design))
    frames=[]
    for plan,contract,before in rows:
        after=_expected_advance(before,contract)
        def snapshot(state):
            return dict(positions=state.world["spatial"]["positions"],open_threads=state.open_threads,
                resolved_threads=state.resolved_threads,obligations=[dict(id=o.id,status=o.status) for o in state.narrative_obligations])
        previous=before.model_dump(mode="json");changes=[]
        for path,value in contract.required_exit_state.items():
            exists,old=_value_at(previous,path)
            if not exists or old!=value: changes.append(dict(path=path,before_present=exists,before=old,after=value))
        frames.append(dict(scene_id=plan.scene_id,entry=snapshot(before),exit=snapshot(after),proposed_changes=changes))
    review_id=canonical_sha256(dict(bindings=bindings,source_fields=fields,projected_transitions=frames))
    schema=ReviewOutputV2.model_json_schema()
    schema["properties"]["review_id"]={"type":"string","enum":[review_id]}
    schema["$defs"]["ReviewSelectionV2"]["properties"]["field_id"]={"type":"string","enum":[f["id"] for f in fields]}
    return dict(schema="spineforge.plan-review-input.v2",review_id=review_id,bindings=bindings,
        request=request.model_dump(mode="json"),seed=seed.model_dump(mode="json"),source_fields=fields,
        projected_transitions=frames,structural_status="PASS; projections are planned, not accepted scene evidence",output_schema=schema)

def bind_review(raw,payload,request,seed,compact,design,rows):
    expected=build_review_input(request,seed,compact,design,rows)
    if payload!=expected: raise ValueError("Semantic review input/table drift")
    review=ReviewOutputV2.model_validate(raw)
    if review.review_id!=expected["review_id"]: raise ValueError("Stale semantic review selection")
    fields={f["id"]:f for f in expected["source_fields"]};seen=set();findings=[]
    for finding in review.findings:
        source=fields.get(finding.field_id)
        if source is None: raise ValueError("Unknown semantic review source ID")
        key=(finding.field_id,finding.category,finding.reason)
        if key in seen: raise ValueError("Duplicate semantic review finding")
        seen.add(key)
        findings.append(BoundFindingV2(**finding.model_dump(mode="json"),compact_pointer=source["compact_pointer"],source_value=source["value"]))
    return BoundReviewV2(**{**review.model_dump(mode="json"),**expected["bindings"],"findings":findings})
