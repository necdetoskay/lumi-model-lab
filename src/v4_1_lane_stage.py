from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.episode_authority_adjudication_v1 import run as run_authority_adjudication
from src.episode_authority_gate_v1 import run as run_authority_gate
from src.episode_bounded_repair_v1 import run as run_bounded_repair
from src.episode_fidelity_adjudication_v1 import run as run_fidelity_adjudication
from src.episode_fidelity_v1 import run as run_fidelity
from src.episode_final_delivery_v1 import run as run_final
from src.episode_spine_v4_1_generate import generate as run_spine
from src.episode_translation_repair_v1 import run as run_translation_repair
from src.episode_translation_v1 import run as run_translation
from src.episode_writer_v4_generate import WRITER_MODEL, generate as run_writer
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest

PAID_STAGES={
    "SPINE",
    "WRITER",
    "AUTHORITY_GATE",
    "SEMANTIC_ADJUDICATION",
    "BOUNDED_REPAIR",
    "TRANSLATION",
    "TRANSLATION_REPAIR",
    "FIDELITY",
    "FIDELITY_ADJUDICATION",
}
ALL_STAGES=PAID_STAGES|{"FINALIZE"}


def _read(path:Path)->dict[str,Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _required_path(trigger:dict[str,Any],key:str)->Path:
    value=str(trigger.get(key) or "").strip()
    if not value:
        raise RuntimeError(f"Trigger requires {key}.")
    path=Path(value)
    if not path.exists():
        raise RuntimeError(f"Trigger path does not exist: {key}={path}")
    return path


def run(*,trigger_path:Path,out_dir:Path)->dict[str,Any]:
    trigger=_read(trigger_path)
    if trigger.get("schema_version")!="frozen-lane-stage-trigger.v1":
        raise RuntimeError("Unsupported frozen lane trigger schema.")
    stage=str(trigger.get("stage") or "").upper()
    if stage not in ALL_STAGES:
        raise RuntimeError(f"Unsupported frozen lane stage: {stage}")
    if stage in PAID_STAGES and trigger.get("paid_authorized") is not True:
        raise RuntimeError(f"Paid stage {stage} is not explicitly authorized.")

    case_path=_required_path(trigger,"case_manifest")
    case=load_case_manifest(case_path)
    profile_path=Path(case["lane_profile"])
    freeze=verify_frozen_lane(profile_path)
    profile=_read(profile_path)
    runtime=profile["runtime"]
    inputs=case["inputs"]

    out_dir.mkdir(parents=True,exist_ok=True)
    result_path=out_dir/"result.json"

    if stage=="SPINE":
        feedback=trigger.get("revision_feedback")
        feedback_path=Path(feedback) if feedback else None
        if feedback_path is not None and not feedback_path.exists():
            raise RuntimeError("Revision feedback path does not exist.")
        result=run_spine(
            spine_path=Path(inputs["spine"]),
            reader_path=Path(inputs["reader"]),
            fixture_path=Path(inputs["fixture"]),
            state_path=Path(inputs["state"]),
            premise_path=Path(inputs["premise"]),
            architect_prompt_path=Path(runtime["spine"]["architect_prompt"]),
            gate_prompt_path=Path(runtime["spine"]["gate_prompt"]),
            out_path=result_path,
            architect_model_override=runtime["spine"]["architect_model"],
            gate_model_override=runtime["spine"]["gate_model"],
            revision_feedback_path=feedback_path,
            safe_normalize=True,
        )
    elif stage=="WRITER":
        approved=_required_path(trigger,"approved")
        if runtime["writer"]["model"]!=WRITER_MODEL:
            raise RuntimeError("Frozen profile writer model differs from pinned writer runtime.")
        result=run_writer(
            approved_path=approved,
            prompt_path=Path(runtime["writer"]["prompt"]),
            out_path=result_path,
            story_out_path=out_dir/"story_en.txt",
            authority_packet_version=runtime["writer"]["authority_packet_version"],
        )
    elif stage=="AUTHORITY_GATE":
        result=run_authority_gate(
            source_path=_required_path(trigger,"source"),
            approved_path=_required_path(trigger,"approved"),
            out_path=result_path,
            prompt_path=Path(runtime["authority"]["semantic_gate_prompt"]),
            model=runtime["authority"]["semantic_gate_model"],
        )
    elif stage=="SEMANTIC_ADJUDICATION":
        result=run_authority_adjudication(
            source_path=_required_path(trigger,"source"),
            out_path=result_path,
            prompt_path=Path(runtime["authority"]["adjudicator_prompt"]),
            model=runtime["authority"]["adjudicator_model"],
        )
    elif stage=="BOUNDED_REPAIR":
        result=run_bounded_repair(
            source_path=_required_path(trigger,"source"),
            approved_path=_required_path(trigger,"approved"),
            out_path=result_path,
            story_out_path=out_dir/"story_en_repaired.txt",
            model=runtime["repair"]["model"],
        )
    elif stage=="TRANSLATION":
        result=run_translation(
            source_path=_required_path(trigger,"source"),
            approved_path=_required_path(trigger,"approved"),
            out_path=result_path,
            tr_out_path=out_dir/"story_tr.txt",
            prompt_path=Path(runtime["translation"]["prompt"]),
            model=runtime["translation"]["model"],
        )
    elif stage=="TRANSLATION_REPAIR":
        result=run_translation_repair(
            source_path=_required_path(trigger,"source"),
            out_path=result_path,
            tr_out_path=out_dir/"story_tr_repaired.txt",
            prompt_path=Path(runtime["translation"]["repair_prompt"]),
            model=runtime["translation"]["model"],
        )
    elif stage=="FIDELITY":
        result=run_fidelity(
            source_path=_required_path(trigger,"source"),
            out_path=result_path,
            prompt_path=Path(runtime["fidelity"]["prompt"]),
            model=runtime["fidelity"]["model"],
        )
    elif stage=="FIDELITY_ADJUDICATION":
        result=run_fidelity_adjudication(
            source_path=_required_path(trigger,"source"),
            out_path=result_path,
            prompt_path=Path(runtime["fidelity"]["adjudicator_prompt"]),
            model=runtime["fidelity"]["adjudicator_model"],
        )
    elif stage=="FINALIZE":
        result=run_final(
            source_path=_required_path(trigger,"source"),
            approved_path=_required_path(trigger,"approved"),
            out_path=result_path,
        )
    else:
        raise AssertionError(stage)

    envelope={
        "schema_version":"frozen-lane-stage-envelope.v1",
        "stage":stage,
        "case_id":case["case_id"],
        "lane_id":profile["lane_id"],
        "runtime_revision":freeze["runtime_revision"],
        "runtime_verified_files":freeze["verified_files"],
        "result_status":result.get("status"),
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
    print(json.dumps(run(trigger_path=a.trigger,out_dir=a.out_dir),ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
