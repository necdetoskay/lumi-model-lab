from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_INPUTS={"spine","reader","fixture","state","premise"}


def load_case_manifest(path:Path)->dict[str,Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version")!="story-lane-case.v1":
        raise RuntimeError("Unsupported story lane case schema.")
    if not str(payload.get("case_id") or "").strip():
        raise RuntimeError("Case manifest requires case_id.")
    if not str(payload.get("lane_profile") or "").strip():
        raise RuntimeError("Case manifest requires lane_profile.")
    inputs=payload.get("inputs") or {}
    missing=REQUIRED_INPUTS-set(inputs)
    if missing:
        raise RuntimeError("Case manifest missing inputs: "+", ".join(sorted(missing)))
    for key in REQUIRED_INPUTS:
        if not Path(str(inputs[key])).exists():
            raise RuntimeError(f"Case input does not exist: {key}={inputs[key]}")
    return payload
