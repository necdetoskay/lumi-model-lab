"""V4 generic single-source-of-truth location projection and bounded model patch.

This is structural normalization, not authoring: beats remain unchanged.
The logistics explanation remains model-authored and independently audited.
"""
from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from src.episode_spine_v2_contract import EpisodeSpineV2


ALLOWED_REPAIR_FIELDS = frozenset({
    "logistics_plan.feasibility_rationale",
    "logistics_plan.movement_constraints",
    "logistics_plan.time_window",
})


class V4RepairRejected(ValueError):
    pass


def _digest(value: Any) -> str:
    raw=json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(",",":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def canonical_beat_route(beats: list[dict[str, Any]]) -> list[str]:
    if not isinstance(beats,list) or not beats:
        raise V4RepairRejected("MISSING_BEATS")
    route=[]
    for beat in beats:
        if not isinstance(beat,dict):
            raise V4RepairRejected("INVALID_BEAT")
        ref=beat.get("location_ref")
        if not isinstance(ref,str) or not ref or ref!=ref.strip():
            raise V4RepairRejected("INVALID_BEAT_LOCATION_REF")
        if not route or route[-1]!=ref:
            route.append(ref)
    return route


def derive_spine_route(raw:dict[str,Any], *, allowed_locations:set[str]|None=None)->tuple[dict[str,Any],dict[str,Any]]:
    """Mechanically derive duplicate location_sequence from authored beat refs."""
    if not isinstance(raw,dict) or not isinstance(raw.get("logistics_plan"),dict):
        raise V4RepairRejected("LOGISTICS_PLAN_MISSING")
    before=_digest(raw)
    route=canonical_beat_route(raw.get("beats"))
    if allowed_locations is not None and not set(route).issubset(allowed_locations):
        raise V4RepairRejected("UNAUTHORIZED_LOCATION_REF")
    updated=copy.deepcopy(raw)
    old=updated["logistics_plan"].get("location_sequence")
    changed=old!=route
    updated["logistics_plan"]["location_sequence"]=route
    assert updated["beats"]==raw["beats"]
    report={
        "kind":"deterministic_derived_location_sequence",
        "changed":changed,
        "original_location_sequence":old,
        "derived_location_sequence":route,
        "input_sha256":before,
        "output_sha256":_digest(updated),
        "beat_fields_unchanged":True,
    }
    return updated,report


def apply_logistics_model_patch(raw:dict[str,Any],proposal:dict[str,Any], *, allowed_locations:set[str]|None=None)->tuple[dict[str,Any],list[dict[str,Any]]]:
    """Only accept model-authored bounded logistics prose/list patches."""
    patches=proposal.get("patches") if isinstance(proposal,dict) else None
    if not isinstance(patches,list) or not 1<=len(patches)<=3:
        raise V4RepairRejected("PATCH_COUNT_INVALID")
    updated=copy.deepcopy(raw)
    applied=[]
    seen=set()
    for row in patches:
        if not isinstance(row,dict) or set(row)!={"field","value"}:
            raise V4RepairRejected("PATCH_SCHEMA_INVALID")
        field=row["field"]
        if not isinstance(field,str) or field not in ALLOWED_REPAIR_FIELDS or field in seen:
            raise V4RepairRejected("PATCH_FIELD_NOT_ALLOWED")
        seen.add(field)
        val=row["value"]
        if field.endswith("movement_constraints"):
            if not isinstance(val,list) or not 1<=len(val)<=12 or any(not isinstance(x,str) or not x.strip() or len(x)>800 for x in val):
                raise V4RepairRejected("INVALID_MOVEMENT_CONSTRAINTS")
        else:
            if not isinstance(val,str) or not val.strip() or len(val)>2400:
                raise V4RepairRejected("INVALID_LOGISTICS_PROSE")
        key=field.split(".")[1]
        before=updated["logistics_plan"].get(key)
        if before==val:
            raise V4RepairRejected("NO_OP_REPAIR")
        updated["logistics_plan"][key]=val
        applied.append({"field":field,"old_sha256":_digest(before),"new_sha256":_digest(val)})
    # The model may not edit scene positions, route, world truth, or decisions.
    if updated["beats"]!=raw["beats"]:
        raise V4RepairRejected("BEATS_CHANGED")
    if updated["logistics_plan"]["location_sequence"]!=canonical_beat_route(raw["beats"]):
        raise V4RepairRejected("DERIVED_LOCATION_SEQUENCE_CHANGED")
    if allowed_locations is not None and not set(updated["logistics_plan"]["location_sequence"]).issubset(allowed_locations):
        raise V4RepairRejected("UNAUTHORIZED_LOCATION_REF")
    EpisodeSpineV2.model_validate(updated)
    return updated,applied
