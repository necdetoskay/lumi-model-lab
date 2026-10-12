"""Zero-cost intake/design admission. Structural PASS is never semantic approval."""
from __future__ import annotations
import argparse
import json
import hashlib
from pathlib import Path
from typing import Any, Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import StrictModel, canonical_sha256
from src.spineforge_span_story_runner import build_chain
from src.spineforge_relay_v1_contracts import ScenePlanV1
from src.spineforge_relay_v1_coverage import PlanObligationV1, PredicateOrderV1
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialStateV1, SpatialOperationV1
from src.spineforge_joint_spatial import CarryGroupV1, JointMoveV1


class RequestRequirementV1(StrictModel):
    id: str = Field(min_length=1)
    source_text: str = Field(min_length=1)
    meaning: str = Field(min_length=1)


class StoryRequestV1(StrictModel):
    schema_name: Literal["spineforge.story-request.v1"] = "spineforge.story-request.v1"
    original_prompt: str = Field(min_length=1, max_length=20000)
    language: str = Field(min_length=2)
    reader_age: int = Field(ge=3, le=120)
    genre: str = Field(min_length=1)
    tone: list[str] = Field(min_length=1)
    scene_count: int = Field(ge=2, le=12)
    requirements: list[RequestRequirementV1] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check(self):
        if not self.original_prompt.strip():
            raise ValueError("Empty user request")
        if len({r.id for r in self.requirements}) != len(self.requirements):
            raise ValueError("Duplicate request requirement")
        if any(not r.source_text.strip() or r.source_text not in self.original_prompt for r in self.requirements):
            raise ValueError("Requirements must cite exact user-request text")
        return self


class RequestBindingV1(StrictModel):
    requirement_id: str = Field(min_length=1)
    scene_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    predicate_id: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class CoveragePlanV1(StrictModel):
    scene_id: str
    obligations: list[PlanObligationV1]
    ordered_dependencies: list[PredicateOrderV1]


class SpatialPlanV1(StrictModel):
    scene_id: str
    operations: list[JointMoveV1 | SpatialOperationV1]
    expected_exit: SpatialStateV1


class DesignFixtureV5(StrictModel):
    schema_name: Literal["spineforge-relay.repeatability-fixture.v5"] = Field(alias="schema")
    story_id: str
    story_intent: dict[str, Any]
    route: list[str]
    initial_state: dict[str, Any]
    relevant_character_canon: dict[str, Any]
    prop_authorization_policy: dict[str, Any]
    scene_plans: list[ScenePlanV1]
    coverage_plans: list[CoveragePlanV1]
    topology: SpatialTopologyV1
    spatial_plans: list[SpatialPlanV1]
    carry_groups: list[CarryGroupV1]


class StoryDesignV1(StrictModel):
    schema_name: Literal["spineforge.story-design.v1"] = "spineforge.story-design.v1"
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture: dict[str, Any]
    request_bindings: list[RequestBindingV1] = Field(min_length=1)
    unresolved_questions: list[str] = Field(default_factory=list)


def validate_design(request: StoryRequestV1, design: StoryDesignV1, fixture_path: Path):
    if design.request_sha256 != canonical_sha256(request):
        raise ValueError("Stale request binding")
    if design.unresolved_questions:
        raise ValueError("Unresolved planning questions")
    if json.loads(fixture_path.read_text(encoding="utf8")) != design.fixture:
        raise ValueError("Fixture differs from recorded design")
    DesignFixtureV5.model_validate(design.fixture)
    fixture,intent,route,start,rows,end = build_chain(fixture_path)
    if len(rows) != request.scene_count:
        raise ValueError("Requested scene count differs")
    if intent.get("language") != request.language or intent.get("reader_age") != request.reader_age:
        raise ValueError("Requested language/age differs")
    if intent.get("tone") != request.tone:
        raise ValueError("Requested tone differs")
    ids={r.id for r in request.requirements}
    bound=set()
    unique=set()
    predicates={(p.scene_id,e.id,q.id) for p,_,_ in rows for e in p.required_events for q in e.predicates}
    for b in design.request_bindings:
        key=(b.requirement_id,b.scene_id,b.event_id,b.predicate_id)
        if key in unique or b.requirement_id not in ids or (b.scene_id,b.event_id,b.predicate_id) not in predicates:
            raise ValueError("Invalid or duplicate request predicate binding")
        unique.add(key);bound.add(b.requirement_id)
    if bound != ids:
        raise ValueError("Uncovered user requirement")
    if any(not set(request.forbidden) <= set(p.forbidden) for p,_,_ in rows):
        raise ValueError("User exclusions missing from scene plans")
    if (end.open_threads or not set(start.open_threads) <= set(end.resolved_threads)
        or not {o.id for o in start.narrative_obligations} <= {o.id for o in end.narrative_obligations}
        or any(o.status != "SATISFIED" for o in end.narrative_obligations)):
        raise ValueError("Unresolved terminal threads/obligations")
    return dict(status="STRUCTURAL_PASS",semantic_status="REQUIRES_REVIEW",
        request_sha256=canonical_sha256(request),design_sha256=canonical_sha256(design),
        fixture_sha256=canonical_sha256(fixture),route_sha256=canonical_sha256(route),
        scene_count=len(rows),start_state_sha256=canonical_sha256(start),
        projected_final_state_sha256=canonical_sha256(end),projected_final_revision=end.revision,
        actual_state_advanced=False,provider_calls=0,
        limits=["Predicate bindings do not prove request entailment, genre, causal coherence or literary quality.",
               "Projection validates planned transitions; it is not accepted scene evidence."])


def planner_input(request: StoryRequestV1):
    return dict(schema="spineforge.planner-input.v1",request=request.model_dump(mode="json"),
        request_sha256=canonical_sha256(request),
        instructions=Path("prompts/spineforge_story_design.md").read_text(encoding="utf8"),
        output_schema=StoryDesignV1.model_json_schema(),
        fixture_contract="spineforge-relay.repeatability-fixture.v5",
        fixture_schema=DesignFixtureV5.model_json_schema(by_alias=True),
        sources={name:hashlib.sha256(Path(name).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
                 for name in ["src/spineforge_story_design.py","prompts/spineforge_story_design.md"]})


def record_design(request_path: Path, proposal_path: Path, output: Path):
    # Exclusive directory: every successful/rejected attempt gets its own evidence.
    output.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        (output/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf8"))
    request_bytes=request_path.read_bytes(); proposal_bytes=proposal_path.read_bytes()
    (output/"request-input.json").write_bytes(request_bytes)
    (output/"proposal-input.json").write_bytes(proposal_bytes)
    try:
        request=StoryRequestV1.model_validate_json(request_bytes)
        design=StoryDesignV1.model_validate_json(proposal_bytes)
        save("planner-input.json",planner_input(request))
        save("candidate-fixture.json",design.fixture)
        proof=validate_design(request,design,output/"candidate-fixture.json")
    except (ValueError,RuntimeError,KeyError,TypeError) as exc:
        proof=dict(status="REJECTED_DESIGN",failure_type=type(exc).__name__,
                   message=str(exc),provider_calls=0,actual_state_advanced=False)
    save("validation.json",proof)
    save("manifest.json",dict(schema="spineforge.design-record.v1",validation_sha256=canonical_sha256(proof),
        files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        production_write=False,paid_authority_created=False))
    return proof


def main():
    parser=argparse.ArgumentParser(description="Record and structurally validate a proposed Relay design; no inference")
    parser.add_argument("--request",type=Path,required=True)
    parser.add_argument("--proposal",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    proof=record_design(args.request,args.proposal,args.output)
    print(json.dumps(proof,ensure_ascii=False))
    return 0 if proof["status"]=="STRUCTURAL_PASS" else 2


if __name__=="__main__":
    raise SystemExit(main())
