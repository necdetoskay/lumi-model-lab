"""V4.1 generic strictly scoped epistemic-claim repair from Luna evidence.

This narrows unjustified reversal claims, not a second Story Architect.
All beats, route, agency, branch alternatives and world facts remain untouched.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from typing import Any

from src.episode_spine_v2_contract import EpisodeSpineV2
from src.v4_logistics import canonical_beat_route


class V4EpistemicRepairRejected(ValueError):
    pass


TEXT_FIELDS=frozenset({
    "reversal.reinterpretation",
    "reversal.inference_ceiling",
    "reversal.unresolved_after_reversal",
})
EVIDENCE_FIELD=re.compile(r"reversal\.evidence\[([0-9]+)\]\.(claim|certainty)$")
CERTAINTY_ORDER={"HYPOTHESIS":0,"INFERRED":1,"OBSERVED":2}


def _sha(value:Any)->str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode("utf-8")).hexdigest()


def apply_epistemic_model_patch(source:dict[str,Any], proposal:dict[str,Any])->tuple[dict[str,Any],list[dict[str,str]]]:
    if not isinstance(source,dict) or not isinstance(proposal,dict):
        raise V4EpistemicRepairRejected("INVALID_PATCH_SOURCE")
    patches=proposal.get("patches")
    if not isinstance(patches,list) or not 1<=len(patches)<=6:
        raise V4EpistemicRepairRejected("PATCH_COUNT_OUT_OF_BOUNDS")
    candidate=copy.deepcopy(source)
    evidence=candidate.get("reversal",{}).get("evidence") or []
    if not isinstance(evidence,list):
        raise V4EpistemicRepairRejected("REVERSAL_EVIDENCE_INVALID")
    seen=set(); applied=[]
    for patch in patches:
        if not isinstance(patch,dict) or set(patch)!={"field","value"}:
            raise V4EpistemicRepairRejected("PATCH_SYNTAX_INVALID")
        field,value=patch["field"],patch["value"]
        if not isinstance(field,str) or field in seen:
            raise V4EpistemicRepairRejected("DUPLICATE_OR_INVALID_FIELD")
        seen.add(field)
        m=EVIDENCE_FIELD.fullmatch(field)
        if field in TEXT_FIELDS:
            if not isinstance(value,str) or not value.strip() or len(value)>1600:
                raise V4EpistemicRepairRejected("INVALID_TEXT_PATCH")
            key=field.split(".")[1]
            old=candidate["reversal"].get(key)
            if old==value:
                raise V4EpistemicRepairRejected("NOOP_PATCH")
            candidate["reversal"][key]=value
        elif m:
            index=int(m.group(1)); key=m.group(2)
            if not 0<=index<len(evidence):
                raise V4EpistemicRepairRejected("EVIDENCE_INDEX_INVALID")
            old=evidence[index].get(key)
            if not isinstance(value,str) or not value.strip() or len(value)>1600 or old==value:
                raise V4EpistemicRepairRejected("INVALID_OR_NOOP_EVIDENCE_PATCH")
            if key=="certainty":
                if value not in CERTAINTY_ORDER or old not in CERTAINTY_ORDER:
                    raise V4EpistemicRepairRejected("UNKNOWN_CERTAINTY")
                if CERTAINTY_ORDER[value]>=CERTAINTY_ORDER[old]:
                    raise V4EpistemicRepairRejected("CERTAINTY_ESCALATION_FORBIDDEN")
            evidence[index][key]=value
        else:
            raise V4EpistemicRepairRejected("UNAUTHORIZED_SPINE_CHANGE")
        applied.append({"field":field,"old_sha256":_sha(old),"new_sha256":_sha(value)})
    if candidate.get("beats")!=source.get("beats"):
        raise V4EpistemicRepairRejected("BEAT_MUTATION_FORBIDDEN")
    if candidate.get("decision_point")!=source.get("decision_point"):
        raise V4EpistemicRepairRejected("BRANCH_MUTATION_FORBIDDEN")
    if candidate.get("logistics_plan")!=source.get("logistics_plan"):
        raise V4EpistemicRepairRejected("LOGISTICS_MUTATION_FORBIDDEN")
    if canonical_beat_route(candidate["beats"])!=candidate["logistics_plan"]["location_sequence"]:
        raise V4EpistemicRepairRejected("ROUTE_CONTRACT_INVALID")
    EpisodeSpineV2.model_validate(candidate)
    return candidate,applied
