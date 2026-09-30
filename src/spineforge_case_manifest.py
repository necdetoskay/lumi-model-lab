from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_INPUTS={"saga","reader","fixture","state","premise"}


def load_spineforge_case(path:Path)->dict[str,Any]:
    payload=json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version")!="spineforge-case.v1":
        raise RuntimeError("Unsupported SpineForge case schema.")
    if not str(payload.get("case_id") or "").strip():
        raise RuntimeError("SpineForge case requires case_id.")
    if not str(payload.get("runtime_profile") or "").strip():
        raise RuntimeError("SpineForge case requires runtime_profile.")
    inputs=payload.get("inputs") or {}
    missing=REQUIRED_INPUTS-set(inputs)
    if missing:
        raise RuntimeError("SpineForge case missing inputs: "+", ".join(sorted(missing)))
    for key in REQUIRED_INPUTS:
        p=Path(str(inputs[key]))
        if not p.exists():
            raise RuntimeError(f"SpineForge case input missing: {key}={p}")
    return payload
