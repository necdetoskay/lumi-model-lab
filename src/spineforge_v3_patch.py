from __future__ import annotations

import copy
import re
from typing import Any

from src.episode_spine_v3_contract import EpisodeSpineV3
from src.spineforge_v3_contract import SpineHardeningPlanV1

# Sonnet is an engineer, not the creative author. These identities may never change.
FORBIDDEN_EXACT_PATHS={
    "/schema",
    "/premise_key",
    "/title",
    "/exact_age",
    "/session",
    "/target_words_min",
    "/target_words_max",
    "/episode_role",
    "/story_promise",
    "/protagonist_role",
    "/immediate_objective",
    "/central_question",
    "/stakes",
    "/opening_hook",
    "/forward_hook",
}
FORBIDDEN_PATTERNS=[
    re.compile(r"^/beats/\d+/(key|phase|location_ref|purpose)$"),
    re.compile(r"^/decision_point/branches/\d+/(key|option)$"),
]

# Hardening is restricted to structural/execution fields. A change outside these
# fields means the creative author must replan instead of Sonnet taking ownership.
ALLOWED_PATTERNS=[
    re.compile(r"^/logistics_plan/(time_window|location_sequence|movement_constraints|feasibility_rationale)$"),
    re.compile(r"^/beats/\d+/(character_action|external_event|new_information|causal_dependency_keys|escalation_delta|state_change|payoff_contribution)$"),
    re.compile(r"^/escalation_ladder$"),
    re.compile(r"^/reversal/(prior_belief|reinterpretation|inference_ceiling|unresolved_after_reversal)$"),
    re.compile(r"^/reversal/evidence/\d+/(claim|supporting_beat_keys|certainty)$"),
    re.compile(r"^/decision_point/(pressure|what_is_unknown)$"),
    re.compile(r"^/decision_point/branches/\d+/(immediate_action|evidence_state_after_choice|cost_or_risk|relationship_or_access_effect|climax_requirement|local_payoff_if_earned)$"),
    re.compile(r"^/climax$"),
    re.compile(r"^/local_payoff$"),
    re.compile(r"^/persistent_outcome_candidates/\d+/(description|commit_condition)$"),
    re.compile(r"^/saga_progression/completion_evidence$"),
    re.compile(r"^/anti_repetition_signature/(core_problem_shape|primary_activity|main_location_pattern|climax_shape|distinct_from_recent_episodes_because)$"),
    re.compile(r"^/writer_rules$"),
]


def _parts(path:str)->list[str]:
    if not path.startswith("/") or path=="/":
        raise RuntimeError(f"Invalid hardening patch path: {path}")
    return [
        x.replace("~1","/").replace("~0","~")
        for x in path.lstrip("/").split("/")
    ]


def _get(root:Any,path:str)->Any:
    current=root
    for part in _parts(path):
        if isinstance(current,list):
            current=current[int(part)]
        elif isinstance(current,dict):
            current=current[part]
        else:
            raise RuntimeError(f"Patch path traverses scalar: {path}")
    return current


def _set(root:Any,path:str,value:Any)->None:
    parts=_parts(path)
    current=root
    for part in parts[:-1]:
        current=current[int(part)] if isinstance(current,list) else current[part]
    last=parts[-1]
    if isinstance(current,list):
        current[int(last)]=value
    else:
        current[last]=value


def _allowed(path:str)->bool:
    if path in FORBIDDEN_EXACT_PATHS:
        return False
    if any(p.fullmatch(path) for p in FORBIDDEN_PATTERNS):
        return False
    return any(p.fullmatch(path) for p in ALLOWED_PATTERNS)


def apply_hardening_plan(
    creative_spine:EpisodeSpineV3,
    plan:SpineHardeningPlanV1,
)->tuple[EpisodeSpineV3,list[dict[str,Any]]]:
    raw=creative_spine.model_dump(mode="json",by_alias=True)
    if plan.decision=="REPLAN":
        raise RuntimeError("Cannot apply REPLAN hardening plan")
    if plan.decision=="KEEP":
        return creative_spine,[]

    result=copy.deepcopy(raw)
    applied=[]
    seen=set()
    for patch in plan.patches:
        path=patch.path
        if path in seen:
            raise RuntimeError(f"Duplicate hardening patch path: {path}")
        seen.add(path)
        if not _allowed(path):
            raise RuntimeError(f"Hardening patch may not modify creative identity: {path}")
        current=_get(result,path)
        if current!=patch.expected_old:
            raise RuntimeError(
                f"Hardening patch stale expected_old at {path}: "
                f"expected {patch.expected_old!r}, actual {current!r}"
            )
        if patch.creative_impact not in {"NONE","LOW"}:
            raise RuntimeError("Hardening patch exceeds creative-impact budget")
        _set(result,path,patch.replacement)
        applied.append({
            "path":path,
            "old":current,
            "new":patch.replacement,
            "defect_class":patch.defect_class,
            "reason":patch.reason,
            "creative_impact":patch.creative_impact,
        })

    hardened=EpisodeSpineV3.model_validate(result)
    return hardened,applied
