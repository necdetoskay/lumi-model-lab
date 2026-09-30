from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.spineforge_case_manifest import load_spineforge_case
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v1 import run as run_spineforge


def _read(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(*,trigger_path:Path,out_dir:Path)->dict[str,Any]:
    trigger=_read(trigger_path)
    if trigger.get("schema_version")!="spineforge-trigger.v1":
        raise RuntimeError("Unsupported SpineForge trigger schema.")
    if trigger.get("paid_authorized") is not True:
        raise RuntimeError("SpineForge paid attempt is not explicitly authorized.")
    if str(trigger.get("scope") or "")!="SPINEFORGE_ATTEMPT":
        raise RuntimeError("Trigger scope must be SPINEFORGE_ATTEMPT.")

    case_path=Path(str(trigger.get("case_manifest") or ""))
    if not case_path.exists():
        raise RuntimeError("SpineForge case manifest does not exist.")
    case=load_spineforge_case(case_path)

    profile_path=Path(case["runtime_profile"])
    freeze=verify_spineforge_runtime(profile_path)
    profile=_read(profile_path)
    inputs=case["inputs"]

    revision_path=None
    if trigger.get("revision_feedback"):
        revision_path=Path(str(trigger["revision_feedback"]))
        if not revision_path.exists():
            raise RuntimeError("SpineForge revision feedback path does not exist.")

    requested_attempt=int(trigger.get("attempt_index") or 1)
    if revision_path is None and requested_attempt!=1:
        raise RuntimeError("Attempt >1 requires revision feedback.")
    if revision_path is not None:
        revision=_read(revision_path)
        if int(revision.get("next_attempt") or 0)!=requested_attempt:
            raise RuntimeError("Trigger attempt does not match revision feedback next_attempt.")

    out_dir.mkdir(parents=True,exist_ok=True)
    result_path=out_dir/"result.json"
    result=run_spineforge(
        saga_path=Path(inputs["saga"]),
        reader_path=Path(inputs["reader"]),
        fixture_path=Path(inputs["fixture"]),
        state_path=Path(inputs["state"]),
        premise_path=Path(inputs["premise"]),
        out_path=result_path,
        creative_prompt_path=Path(profile["runtime"]["creative_prompt"]),
        hardener_prompt_path=Path(profile["runtime"]["hardener_prompt"]),
        gate_prompt_path=Path(profile["runtime"]["product_gate_prompt"]),
        revision_feedback_path=revision_path,
        max_attempts=int(profile["runtime"]["max_attempts"]),
    )
    if int(result.get("attempt_index") or 0)!=requested_attempt:
        raise RuntimeError("Runtime attempt index differs from trigger.")

    envelope={
        "schema_version":"spineforge-stage-envelope.v1",
        "case_id":case["case_id"],
        "runtime_id":profile["runtime_id"],
        "runtime_revision":freeze["runtime_revision"],
        "runtime_verified_files":freeze["verified_files"],
        "attempt_index":requested_attempt,
        "result_status":result.get("status"),
        "writer_authorized":False,
        "result_path":str(result_path),
    }
    (out_dir/"stage_envelope.json").write_text(
        json.dumps(envelope,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )
    return envelope


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--trigger",type=Path,required=True)
    p.add_argument("--out-dir",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(
        run(trigger_path=a.trigger,out_dir=a.out_dir),
        ensure_ascii=False,indent=2
    ))


if __name__=="__main__":
    main()
