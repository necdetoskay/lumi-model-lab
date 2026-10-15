from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_story_authority_guards import run_deterministic_authority_guards
from src.episode_postprocess_v2 import _hard_constraints
from src.generate import count_words
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_authority_packet_v2 import build_story_authority_packet_v2
from src.story_stage_common import read_json, source_calls, write_json
from src.storyforge.runtime import REPAIR_SYSTEM, _apply_local_repairs, _structured_call

DEFAULT_MODEL="openai/gpt-5.6-sol"
MAX_REPAIR_ATTEMPTS=1


def run(
    *,
    source_path: Path,
    approved_path: Path,
    out_path: Path,
    story_out_path: Path,
    model: str=DEFAULT_MODEL,
    api_key: str|None=None,
) -> dict[str, Any]:
    load_dotenv()
    source=read_json(source_path)
    approved=read_json(approved_path)
    attempts=int(source.get("english_repair_attempts") or 0)
    if attempts>=MAX_REPAIR_ATTEMPTS:
        raise RuntimeError("English bounded repair attempt limit reached.")
    findings=list(source.get("confirmed_findings") or [])
    if not findings:
        raise RuntimeError("Bounded repair requires confirmed findings.")
    if any(str(x.get("repair_scope"))!="local" for x in findings):
        raise RuntimeError("Bounded repair refuses non-local findings.")

    story=str(source.get("story") or "").strip()
    if not story:
        raise RuntimeError("Repair source is missing story.")

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    packet=build_story_authority_packet_v2(approved)
    spine=approved["episode_spine"]
    started=time.perf_counter()
    repair_payload,meta=_structured_call(
        api_key=key,
        model=model,
        system=REPAIR_SYSTEM,
        payload={
            "story_intent":approved["approved_premise"]["premise"],
            "authority_packet":packet,
            "hard_constraints":_hard_constraints(spine),
            "validated_spine":spine,
            "story":story,
            "confirmed_local_defects":findings,
            "repair_policy":{
                "minimal_exact_replacements_only":True,
                "do_not_rewrite_unaffected_prose":True,
                "do_not_change_branch_choice":True,
                "fix_only_confirmed_defects":True,
            },
        },
        seed=2026093004,
        request_class="editorial_audit",
        max_tokens=None,
    )
    latency=round(time.perf_counter()-started,3)

    repaired,applied=_apply_local_repairs(story,repair_payload)
    if not applied:
        raise RuntimeError("Repair model returned no applied replacements.")
    if len(applied)>max(6,len(findings)*2):
        raise RuntimeError("Repair exceeded bounded replacement count.")

    post_hard=run_deterministic_authority_guards(repaired,packet)
    min_words=int(spine["target_words_min"])
    max_words=int(spine["target_words_max"])
    words=count_words(repaired)

    call=normalize_model_call(
        stage="bounded_local_repair",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])
    status="repaired_recheck_required"
    if post_hard:
        status="repaired_still_has_hard_findings"
    if not (min_words<=words<=max_words):
        status="repaired_length_failed"

    result={
        "schema_version":"episode-bounded-repair.v1",
        "status":status,
        "story_before":story,
        "repaired_story":repaired,
        "confirmed_findings":findings,
        "applied_repairs":applied,
        "post_repair_hard_findings":post_hard,
        "repaired_word_count":words,
        "length_pass":min_words<=words<=max_words,
        "repair_model":model,
        "repair_meta":meta,
        "english_repair_attempts":attempts+1,
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "next_stage":"AUTHORITY_GATE_RECHECK" if status=="repaired_recheck_required" else "STOP",
        "next_stage_authorized":False,
    }
    write_json(out_path,result)
    story_out_path.parent.mkdir(parents=True,exist_ok=True)
    story_out_path.write_text(repaired.rstrip()+"\n",encoding="utf-8")
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--approved",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--story-out",type=Path,required=True)
    p.add_argument("--model",default=DEFAULT_MODEL)
    a=p.parse_args()
    result=run(
        source_path=a.source,approved_path=a.approved,out_path=a.out,
        story_out_path=a.story_out,model=a.model,
    )
    print(json.dumps({
        "status":result["status"],
        "applied_repairs":len(result["applied_repairs"]),
        "post_repair_hard_findings":len(result["post_repair_hard_findings"]),
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
