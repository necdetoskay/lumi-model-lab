from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.deterministic_translation_semantic_guards import run_translation_semantic_guards
from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_stage_common import extract_turkish, read_json, source_calls, write_json
from src.storyforge.runtime import _structured_call

DEFAULT_MODEL="google/gemini-3.8-flash"
DEFAULT_PROMPT=Path("prompts/translation_local_repair_v1_generic.md")
MAX_REPAIR_ATTEMPTS=1


def _apply(text:str,payload:dict[str,Any])->tuple[str,list[dict[str,Any]]]:
    current=text
    applied=[]
    repairs=list(payload.get("repairs") or [])
    if not repairs:
        raise RuntimeError("Translation repair returned no replacements.")
    for row in repairs:
        old=str(row.get("old") or "")
        new=str(row.get("new") or "")
        if not old or not new or old==new:
            raise RuntimeError("Invalid translation repair.")
        if current.count(old)!=1:
            raise RuntimeError("Translation repair target must exist exactly once.")
        current=current.replace(old,new,1)
        applied.append({"old":old,"new":new,"why":str(row.get("why") or "")})
    return current,applied


def run(
    *,
    source_path:Path,
    out_path:Path,
    tr_out_path:Path,
    prompt_path:Path=DEFAULT_PROMPT,
    model:str=DEFAULT_MODEL,
    api_key:str|None=None,
)->dict[str,Any]:
    load_dotenv()
    source=read_json(source_path)
    english=str(source.get("accepted_english_master") or "").strip()
    turkish=extract_turkish(source)
    attempts=int(source.get("translation_repair_attempts") or 0)
    if attempts>=MAX_REPAIR_ATTEMPTS:
        raise RuntimeError("Translation repair attempt limit reached.")

    findings=list(
        source.get("translation_semantic_findings")
        or source.get("confirmed_fidelity_findings")
        or source.get("confirmed_findings")
        or []
    )
    if not english or not findings:
        raise RuntimeError("Translation repair source is missing English or confirmed findings.")

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    started=time.perf_counter()
    payload,meta=_structured_call(
        api_key=key,
        model=model,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "accepted_english_master":english,
            "turkish_translation":turkish,
            "confirmed_fidelity_defects":findings,
        },
        seed=2026093006,
        request_class="translation",
        max_tokens=2000,
    )
    latency=round(time.perf_counter()-started,3)
    repaired,applied=_apply(turkish,payload)
    semantic=run_translation_semantic_guards(english,repaired)

    call=normalize_model_call(
        stage="translation_local_repair",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])
    clean=not semantic
    result={
        "schema_version":"episode-translation-repair.v1",
        "status":"semantic_guard_clean" if clean else "semantic_guard_still_blocked",
        "accepted_english_master":english,
        "turkish_delivery":repaired,
        "applied_translation_repairs":applied,
        "translation_semantic_findings":semantic,
        "translation_repair_attempts":attempts+1,
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "next_stage":"FIDELITY" if clean else "STOP",
        "next_stage_authorized":False,
    }
    write_json(out_path,result)
    tr_out_path.parent.mkdir(parents=True,exist_ok=True)
    tr_out_path.write_text(repaired.rstrip()+"\n",encoding="utf-8")
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--tr-out",type=Path,required=True)
    p.add_argument("--prompt",type=Path,default=DEFAULT_PROMPT)
    p.add_argument("--model",default=DEFAULT_MODEL)
    a=p.parse_args()
    result=run(
        source_path=a.source,out_path=a.out,tr_out_path=a.tr_out,
        prompt_path=a.prompt,model=a.model,
    )
    print(json.dumps({
        "status":result["status"],
        "applied_repairs":len(result["applied_translation_repairs"]),
        "semantic_findings":len(result["translation_semantic_findings"]),
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
