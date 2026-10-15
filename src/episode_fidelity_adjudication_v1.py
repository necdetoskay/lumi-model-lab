from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.model_registry import require_qualification_runtime_profile, runtime_profile_identity
from src.model_usage_rollup import normalize_model_call, rollup_model_calls
from src.story_stage_common import read_json, source_calls, write_json
from src.storyforge.runtime import _structured_call

DEFAULT_MODEL="openai/gpt-5.6-sol"
DEFAULT_PROMPT=Path("prompts/translation_fidelity_adjudicator_v1_generic.md")


def run(
    *,
    source_path:Path,
    out_path:Path,
    prompt_path:Path=DEFAULT_PROMPT,
    model:str=DEFAULT_MODEL,
    api_key:str|None=None,
)->dict[str,Any]:
    load_dotenv()
    source=read_json(source_path)
    if source.get("schema_version")!="episode-fidelity.v1":
        raise RuntimeError("Fidelity adjudication source schema mismatch.")
    findings=list(source.get("fidelity_findings") or [])
    if not findings:
        raise RuntimeError("No Luna fidelity findings require adjudication.")

    key=api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(model)

    english=str(source["accepted_english_master"])
    turkish=str(source["turkish_delivery"])
    started=time.perf_counter()
    payload,meta=_structured_call(
        api_key=key,
        model=model,
        system=prompt_path.read_text(encoding="utf-8").strip(),
        payload={
            "accepted_english_master":english,
            "turkish_translation":turkish,
            "fidelity_findings":findings,
        },
        seed=2026093008,
        request_class="editorial_audit",
        max_tokens=None,
    )
    latency=round(time.perf_counter()-started,3)

    evaluations=list(payload.get("evaluations") or [])
    if len(evaluations)!=len(findings):
        raise RuntimeError("Fidelity adjudicator must evaluate every finding.")
    by_index={int(row["finding_index"]):row for row in evaluations}
    if set(by_index)!=set(range(len(findings))):
        raise RuntimeError("Fidelity adjudication indices are incomplete.")
    indices=[int(x) for x in (payload.get("confirmed_finding_indices") or [])]
    if any(i<0 or i>=len(findings) for i in indices):
        raise RuntimeError("Invalid confirmed fidelity index.")

    confirmed=[]
    for i,row in by_index.items():
        decision=str(row.get("decision") or "")
        if decision not in {"CONFIRM","REJECT"}:
            raise RuntimeError("Invalid fidelity adjudication decision.")
        if (i in indices)!=(decision=="CONFIRM"):
            raise RuntimeError("Fidelity adjudication decisions disagree with indices.")
        if decision=="CONFIRM":
            confirmed.append(findings[i])

    call=normalize_model_call(
        stage="translation_fidelity_adjudication",
        model=model,
        provider=runtime_profile_identity(model).get("provider"),
        raw_usage=meta.get("raw_usage") or {},
        cost=meta.get("cost") or {},
        latency_seconds=latency,
    )
    rollup=rollup_model_calls(source_calls(source)+[call])
    clean=not confirmed
    result={
        "schema_version":"episode-fidelity-adjudication.v1",
        "status":"clean_after_adjudication" if clean else "confirmed_fidelity_findings",
        "accepted_english_master":english,
        "turkish_delivery":turkish,
        "original_fidelity_findings":findings,
        "evaluations":evaluations,
        "confirmed_fidelity_findings":confirmed,
        "translation_repair_attempts":int(source.get("translation_repair_attempts") or 0),
        "pipeline_usage_rollup":rollup,
        "total_cost_usd":rollup["totals"]["cost_usd"],
        "publication_ready":clean,
        "next_stage":"FINALIZE" if clean else "TRANSLATION_REPAIR",
        "next_stage_authorized":False,
    }
    write_json(out_path,result)
    return result


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--prompt",type=Path,default=DEFAULT_PROMPT)
    p.add_argument("--model",default=DEFAULT_MODEL)
    a=p.parse_args()
    result=run(source_path=a.source,out_path=a.out,prompt_path=a.prompt,model=a.model)
    print(json.dumps({
        "status":result["status"],
        "confirmed_findings":len(result["confirmed_fidelity_findings"]),
        "publication_ready":result["publication_ready"],
        "next_stage":result["next_stage"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
