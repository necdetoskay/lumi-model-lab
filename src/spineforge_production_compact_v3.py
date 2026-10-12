"""Lower declared observer/clue intent into predicate requirements, never evidence."""
from typing import ClassVar, Literal
from pathlib import Path
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel, EventPredicateV1, canonical_sha256
from src.spineforge_production_compact import CompactEventV1
from src.spineforge_production_compact_v2 import CompactSceneV2, CompactStoryPlanV2, compile_compact_v2


class PhysicalClueV3(StrictModel):
    subject: str = Field(min_length=1)
    target: str = Field(min_length=1)


class CompactEventV3(CompactEventV1):
    # A boolean is insufficient to identify a separate demonstration's actor/target.
    separate_physical_clue_required: ClassVar[bool] = False
    physical_clue: PhysicalClueV3 | None = None


class CompactSceneV3(CompactSceneV2):
    events: list[CompactEventV3] = Field(min_length=1)


class CompactStoryPlanV3(CompactStoryPlanV2):
    schema_name: Literal["spineforge.compact-story-plan.v3"] = "spineforge.compact-story-plan.v3"
    scenes: list[CompactSceneV3] = Field(min_length=2, max_length=12)


def compact_planner_input_v3(request,seed):
    return dict(schema="spineforge.compact-planner-input.v3", request=request.model_dump(mode="json"),
        seed=seed.model_dump(mode="json"), request_sha256=canonical_sha256(request), seed_sha256=canonical_sha256(seed),
        instructions=Path("prompts/spineforge_production_compact_v3.md").read_text(encoding="utf8"),
        output_schema=CompactStoryPlanV3.model_json_schema())


def compile_compact_v3(request,seed,candidate: CompactStoryPlanV3):
    raw=candidate.model_dump(mode="json");raw["schema_name"]="spineforge.compact-story-plan.v2"
    for scene,row in zip(candidate.scenes,raw["scenes"]):
        for event,expanded in zip(scene.events,row["events"]):
            predicates=[p.model_copy(deep=True) for p in event.predicates]
            primary=predicates[0]
            def require_predicate(pid,subject,action,target):
                matches=[p for p in predicates if (p.subject,p.action,p.target)==(subject,action,target)]
                if len(matches)>1:
                    raise ValueError("Ambiguous existing derived predicate")
                if matches: return
                if any(p.id==pid for p in predicates):
                    raise ValueError("Derived observer/clue predicate ID collision")
                predicates.append(EventPredicateV1(id=pid,subject=subject,action=action,target=target))
            if event.required_observer:
                if event.required_observer not in seed.characters:
                    raise ValueError("Observer must be an established character")
                if not any(p.subject==event.required_observer and p.action in {"OBSERVE","ACKNOWLEDGE"} for p in predicates):
                    require_predicate("OBSERVER",event.required_observer,"OBSERVE",f"{primary.subject}_{primary.action}_{primary.target}")
            expanded.pop("physical_clue")
            expanded["separate_physical_clue_required"]=event.physical_clue is not None
            if event.physical_clue:
                if event.physical_clue.subject not in seed.characters or event.evidence_mode=="ESTABLISHED_KNOWLEDGE":
                    raise ValueError("Physical clue needs an established character and direct evidence")
                require_predicate("PHYSICAL_CLUE",event.physical_clue.subject,"SHOW_PHYSICAL_CLUE",event.physical_clue.target)
            expanded["predicates"]=[p.model_dump(mode="json") for p in predicates]
    return compile_compact_v2(request,seed,CompactStoryPlanV2.model_validate(raw))
