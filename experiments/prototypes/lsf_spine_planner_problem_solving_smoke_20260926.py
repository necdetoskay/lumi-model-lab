from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_scene_plan_smoke import call_structured_json_with_retry
from src.generate import parse_cost, parse_usage

FIXTURE=Path("experiments/fixtures/lsf_spine_planner_problem_solving_smoke_20260926.json")
OUT=Path("runs/lsf-spine-planner-problem-solving-smoke/result.json")

PLANNER="aion-labs/aion-3.5-mini"
PRIMARY_VALIDATOR="anthropic/claude-sonnet-5"
SECONDARY_VALIDATOR="openai/gpt-5.6-sol"
SEED=2026092741

PLANNER_SYSTEM=r"""
You are the Spine Planner inside LUMI StoryForge.

You receive a frozen minimal Story Context Packet, one StoryIntent, and one generation profile.
Your job is to PLAN the story, not write prose.

Important:
- Do not assume facts outside the supplied context.
- Do not introduce new named characters.
- Do not invent new durable canon or world facts.
- Do not write the finished story.
- Do not add morals or lessons.
- The solution must emerge from the available context, but the input does NOT tell you the solution.
- Preserve everyday physics when the guard says normal physics.
- Keep the plan suitable for EXACT age 4 and the requested word budget.
- Prefer observable actions over narrator explanation.
- Create exactly 8 ordered beats with density labels: brief, develop, or anchor.
- The beats must form a clear causal chain: setup -> failed attempt/observation -> usable idea -> test -> payoff -> closure.
- Keep the scope small enough for about 500 words.

Return one JSON object only:
{
  "logline":"one sentence",
  "premise":"2-4 concise sentences",
  "beats":[
    {"id":"B1","density":"brief|develop|anchor","beat":"concrete planned action/state"}
  ],
  "used_fact_ids":["..."],
  "guard_fact_ids":["..."],
  "assumptions":[
    {"assumption":"...", "why_safe":"..."}
  ],
  "story_outcome":{
    "summary":"what is true at the end of this story",
    "proposed_state_deltas":[],
    "canon_mutations":[]
  }
}

Rules for evidence fields:
- used_fact_ids may contain ONLY IDs supplied in always_required, deterministic_required, or soft_enrichment.
- guard_fact_ids may contain ONLY IDs supplied in deterministic_guards.
- List every deterministic_required fact actually needed to honor the StoryIntent.
- canon_mutations MUST be [].
- proposed_state_deltas should be [] unless a durable state change is clearly justified by the supplied context.
""".strip()

VALIDATOR_SYSTEM=r"""
You are a strict Spine Validator for LUMI StoryForge.

You receive:
1) the authoritative frozen planner input/context;
2) one candidate spine plan.

Judge the plan, not prose quality.

Blocking defect classes:
- canon_violation
- unsupported_entity_or_object
- physical_or_causal_failure
- state_continuity_failure
- knowledge_boundary_violation
- story_intent_miss
- age_scope_failure
- closure_failure
- hidden_moral_or_didactic_takeover
- unsafe_or_unbounded_state_mutation

For this smoke:
- Deniz is the only active character.
- The toy truck is intact.
- The platform has a vertical step.
- Available soft enrichment is sturdy cardboard + one small wooden block.
- Normal everyday physics applies.
- Do not require the planner to use every enrichment fact.
- A physically plausible ramp solution is allowed if the planner infers it, but do not require a specific wording or exact construction unless needed for feasibility.
- No adult/other child/new tool/new magical object may solve the problem.
- The plan must be small enough for an exact-age-4 ~500-word read-aloud story.
- Do not flag stylistic preferences, wordsmithing, or optional polish.
- proposed_state_deltas may be empty; do not require durable canon/state mutation.

Return JSON only:
{
  "blocking_findings":[
    {
      "severity":"serious|critical",
      "class":"canon_violation|unsupported_entity_or_object|physical_or_causal_failure|state_continuity_failure|knowledge_boundary_violation|story_intent_miss|age_scope_failure|closure_failure|hidden_moral_or_didactic_takeover|unsafe_or_unbounded_state_mutation",
      "beat_ids":["B1"],
      "why":"brief evidence-based reason"
    }
  ],
  "planner_ready":true,
  "summary":"brief"
}
""".strip()

def usd(body:dict[str,Any])->float:
    return float(parse_cost(body).usd or 0.0)

def context_ids(fixture:dict[str,Any])->tuple[set[str],set[str],set[str]]:
    packet=fixture["context_packet"]
    generative=set()
    for key in ("always_required","deterministic_required","soft_enrichment"):
        generative.update(str(x["id"]) for x in packet[key])
    guards={str(x["id"]) for x in packet["deterministic_guards"]}
    required={str(x["id"]) for x in packet["deterministic_required"]}
    return generative,guards,required

def deterministic_validate(fixture:dict[str,Any],plan:dict[str,Any])->list[str]:
    errors=[]
    if not isinstance(plan.get("logline"),str) or not plan["logline"].strip():
        errors.append("logline_missing")
    if not isinstance(plan.get("premise"),str) or not plan["premise"].strip():
        errors.append("premise_missing")

    beats=plan.get("beats")
    if not isinstance(beats,list) or len(beats)!=8:
        errors.append("beat_count_not_8")
    else:
        expected=[f"B{i}" for i in range(1,9)]
        actual=[x.get("id") if isinstance(x,dict) else None for x in beats]
        if actual!=expected:
            errors.append("beat_ids_not_B1_to_B8")
        allowed_density={"brief","develop","anchor"}
        for beat in beats:
            if not isinstance(beat,dict):
                continue
            if beat.get("density") not in allowed_density:
                errors.append(f"invalid_density:{beat.get('id')}")
            if not isinstance(beat.get("beat"),str) or not beat["beat"].strip():
                errors.append(f"empty_beat:{beat.get('id')}")

    gen_ids,guard_ids,required_ids=context_ids(fixture)
    used=plan.get("used_fact_ids")
    guards=plan.get("guard_fact_ids")
    if not isinstance(used,list):
        errors.append("used_fact_ids_missing")
        used=[]
    if not isinstance(guards,list):
        errors.append("guard_fact_ids_missing")
        guards=[]

    unknown_used=sorted(set(map(str,used))-gen_ids)
    unknown_guards=sorted(set(map(str,guards))-guard_ids)
    if unknown_used:
        errors.append("unknown_used_fact_ids:"+",".join(unknown_used))
    if unknown_guards:
        errors.append("unknown_guard_fact_ids:"+",".join(unknown_guards))

    missing_required=sorted(required_ids-set(map(str,used)))
    missing_guards=sorted(guard_ids-set(map(str,guards)))
    if missing_required:
        errors.append("missing_required_fact_ids:"+",".join(missing_required))
    if missing_guards:
        errors.append("missing_guard_fact_ids:"+",".join(missing_guards))

    outcome=plan.get("story_outcome")
    if not isinstance(outcome,dict):
        errors.append("story_outcome_missing")
    else:
        if outcome.get("canon_mutations") != []:
            errors.append("canon_mutations_not_empty")
        deltas=outcome.get("proposed_state_deltas")
        if not isinstance(deltas,list):
            errors.append("proposed_state_deltas_not_list")

    raw=json.dumps(plan,ensure_ascii=False).casefold()
    prohibited=[
        "ada","emre","mother","father","mom","dad","teacher",
        "tape","glue","string","book","brick","magic","magical"
    ]
    for token in prohibited:
        if token in raw:
            errors.append("prohibited_content:"+token)

    return sorted(set(errors))

def structured_call(*,api_key:str,model:str,system:str,payload:dict[str,Any],seed:int,request_class:str):
    parsed,body,request,failures=call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=system,
        user_prompt=json.dumps(payload,ensure_ascii=False),
        temperature=0.0,
        max_tokens=2800,
        seed=seed,
        request_class=request_class,
        max_parse_attempts=2,
    )
    return parsed,body,request,failures

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    started=time.perf_counter()

    plan,planner_body,planner_request,planner_parse_failures=structured_call(
        api_key=key,
        model=PLANNER,
        system=PLANNER_SYSTEM,
        payload=fixture,
        seed=SEED,
        request_class="story_planning",
    )

    deterministic_errors=deterministic_validate(fixture,plan)

    primary,primary_body,_,primary_parse_failures=structured_call(
        api_key=key,
        model=PRIMARY_VALIDATOR,
        system=VALIDATOR_SYSTEM,
        payload={"planner_input":fixture,"candidate_plan":plan},
        seed=SEED+1,
        request_class="editorial_audit",
    )
    secondary,secondary_body,_,secondary_parse_failures=structured_call(
        api_key=key,
        model=SECONDARY_VALIDATOR,
        system=VALIDATOR_SYSTEM,
        payload={"planner_input":fixture,"candidate_plan":plan},
        seed=SEED+2,
        request_class="editorial_audit",
    )

    primary_findings=primary.get("blocking_findings") or []
    secondary_findings=secondary.get("blocking_findings") or []
    if not isinstance(primary_findings,list) or not isinstance(secondary_findings,list):
        raise RuntimeError("validator_blocking_findings_invalid")

    planner_ready=(
        not deterministic_errors
        and not primary_findings
        and not secondary_findings
        and bool(primary.get("planner_ready"))
        and bool(secondary.get("planner_ready"))
    )

    costs={
        "planner":usd(planner_body),
        "primary_validator":usd(primary_body),
        "secondary_validator":usd(secondary_body),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-spine-planner-problem-solving-smoke-result.v1",
        "profile":"LSF-A4-W500-spine-planner-v0.1",
        "planner_model":PLANNER,
        "planner_input":fixture,
        "plan":plan,
        "deterministic_errors":deterministic_errors,
        "primary_validator":{"model":PRIMARY_VALIDATOR,"result":primary},
        "secondary_validator":{"model":SECONDARY_VALIDATOR,"result":secondary},
        "planner_ready":planner_ready,
        "cost_usd":costs,
        "usage":{
            "planner":parse_usage(planner_body).model_dump(mode="json"),
            "primary_validator":parse_usage(primary_body).model_dump(mode="json"),
            "secondary_validator":parse_usage(secondary_body).model_dump(mode="json"),
        },
        "parse_failures":{
            "planner":planner_parse_failures,
            "primary_validator":primary_parse_failures,
            "secondary_validator":secondary_parse_failures,
        },
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "planner_ready":planner_ready,
        "deterministic_errors":deterministic_errors,
        "primary_findings":primary_findings,
        "secondary_findings":secondary_findings,
        "plan":plan,
        "cost_usd":costs,
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
