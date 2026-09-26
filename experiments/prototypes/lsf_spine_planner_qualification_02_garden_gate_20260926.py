from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE = Path("experiments/fixtures/lsf_spine_planner_qualification_02_garden_gate_20260926.json")
OUT = Path("runs/lsf-spine-planner-qualification-02-garden-gate/result.json")

PLANNER = "aion-labs/aion-3.5-mini"
PLAN_VALIDATOR = "anthropic/claude-sonnet-5"
WRITER = "aion-labs/aion-3.5-mini"
PRIMARY_AUDITOR = "anthropic/claude-sonnet-5"
SECONDARY_AUDITOR = "openai/gpt-5.6-sol"
TRANSLATOR = "google/gemini-3.8-flash"
FIDELITY_GATE = "openai/gpt-5.6-luna"
SEED = 2026092761

PLANNER_SYSTEM = r"""
You are the Story Planner inside LUMI StoryForge.

Create PLAN ONLY, not prose.

Input:
- StoryIntent
- minimal Story Context Packet
- generation profile
- one protected knowledge boundary

Goals:
- exactly age 4
- about 500 English words later
- low-stakes exploration mystery
- concrete observable actions
- no moral/lesson
- no adult helper
- no new durable canon

CRITICAL KNOWLEDGE RULE:
GARDEN_GATE is only RUMORED for Deniz.
He has NOT opened or crossed it.
The plan MUST NOT:
- move Deniz through/beyond the gate,
- reveal what is beyond the gate as fact,
- let Deniz remember/recognize something from beyond it,
- place the sound source beyond the gate and then resolve it by knowledge he does not have,
- convert rumor into discovered/explored knowledge during this story unless the StoryIntent explicitly authorizes crossing. It does not.

The mystery may occur NEAR the gate and may be solved entirely on the courtyard side.

Use only facts present in the context packet for durable characters, objects, locations, world rules, and current state.
Transient sounds, gestures, dialogue, weather-like sensory details, and ordinary temporary actions are allowed if they do not create durable canon.
Normal everyday physics applies.
State changes in expected_outcome are proposals only, never already committed.

Return JSON only:
{
  "premise":"one concise English premise",
  "beats":[
    {
      "id":"B1",
      "density":"brief|develop|anchor",
      "beat":"one concrete ordered beat",
      "uses_fact_ids":["exact ids from context packet only"]
    }
  ],
  "assumptions":[
    {
      "text":"minimal transient assumption",
      "type":"transient_environment|action|dialogue|none",
      "why_safe":"brief"
    }
  ],
  "expected_outcome":{
    "proposed_state_changes":[
      {"kind":"knowledge|position|object_state|relationship|none","description":"proposed only"}
    ],
    "preserved_invariants":[
      "facts that must remain true"
    ]
  }
}

Hard shape:
- exactly 8 beats B1..B8
- at least 3 anchor beats
- B8 concrete ending
- no unknown fact ids
""".strip()

PLAN_VALIDATOR_SYSTEM = r"""
You are an independent Story Spine validator.

Judge the PLAN, not prose.

Check only serious/critical defects in:
- intent_alignment
- canon_state_consistency
- unavailable_object_or_character
- knowledge_boundary
- physical_causality
- event_order
- age_fit
- closure
- outcome_safety

Protected boundary:
- GARDEN_GATE is RUMORED only.
- Deniz has not opened/crossed it.
- This StoryIntent does NOT authorize crossing.
- The plan must resolve the mystery on the courtyard side without claiming factual knowledge of what lies beyond.

Normal everyday physics applies.
Do not require every available fact to be used.
Harmless transient sounds/actions/dialogue are allowed.
Proposed state changes must remain proposed, not committed.
Do not rewrite the plan.

Return JSON only:
{
  "valid":true,
  "counts":{"critical":0,"serious":0},
  "defects":[
    {
      "severity":"critical|serious",
      "class":"intent_alignment|canon_state_consistency|unavailable_object_or_character|knowledge_boundary|physical_causality|event_order|age_fit|closure|outcome_safety",
      "beat_ids":["B1"],
      "why":"brief"
    }
  ],
  "summary":"brief"
}
""".strip()

WRITER_SYSTEM = r"""
You are an experienced English children's story writer.

Write a warm, natural read-aloud story for an EXACTLY 4-year-old child from the validated premise and 8-beat spine.

Preserve:
- event order and causal solution
- object/state continuity
- GARDEN_GATE knowledge boundary
- no crossing the gate
- no factual revelation of what lies beyond the gate
- normal everyday physics
- concrete ending
- no adult helper
- no moral/lesson

Creative freedom is allowed for transient childlike behavior:
- short dialogue
- playful sounds
- gestures
- simple sensory details
- momentary comparisons
These must not invent durable canon or persistent object attributes.

Do not add new durable characters, owned objects, tools, family facts, or world facts.

Length:
- target about 500 English words
- preferred 475-525
- hard 375-625
- do not finish below 375.

Return only the finished English story. First line must be title.
""".strip()

AUDIT_SYSTEM = r"""
You are a strict publication-blocker auditor for one finished English read-aloud story for an EXACTLY 4-year-old child.

Evaluate every canonical semantic family:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Report ONLY serious or critical semantic defects.

Critical story-specific rules:
- GARDEN_GATE is only RUMORED.
- Deniz must not cross/open it.
- Deniz must not gain factual knowledge of what lies beyond it.
- Mystery must resolve on the courtyard side.
- story must materially follow validated spine.
- no unavailable durable object/person may appear as solution.
- normal everyday physics.
- no adult solves the mystery.
- transient childlike sounds/dialogue are allowed.
- unsupported durable attributes are canon_integrity defects only if materially persistent/specific, not harmless momentary prose.

Return JSON only:
{
  "evaluations":[
    {
      "family":"physical_feasibility",
      "present":false,
      "severity":null,
      "repair_scope":null,
      "span_ids":[],
      "reason":"brief"
    }
  ]
}
""".strip()

TRANSLATION_SYSTEM = r"""
You are a professional literary translator specializing in English -> Turkish children's read-aloud stories for EXACTLY age 4.

Translate the accepted English story into natural Turkish.

THIS IS TRANSLATION, NOT REWRITING.

Preserve:
- all characters/objects/actions
- event order and causal solution
- GARDEN_GATE knowledge boundary
- no crossing/opening the gate
- no new knowledge of what lies beyond
- mystery resolution on courtyard side
- childlike sounds/dialogue
- ending

Do not add/remove plot events, canon, helpers, motivations, morals, or explanations.
Keep names unchanged.
Use natural contemporary Turkish and speakable sentences.

Return only the finished Turkish story.
""".strip()

FIDELITY_SYSTEM = r"""
You are a strict bilingual EN->TR semantic fidelity gate.

Report ONLY serious/critical translation defects:
- omission
- addition
- character_shift
- object_shift
- state_shift
- causal_shift
- knowledge_shift
- ending_shift

Pay special attention to the GARDEN_GATE epistemic boundary and whether the translation accidentally implies crossing or factual knowledge beyond the gate.

Return JSON only:
{
  "findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"short EN quote",
      "translation_quote":"short TR quote",
      "why":"brief"
    }
  ],
  "fidelity_clean":true
}
""".strip()


def meta_cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    c = meta.get("cost")
    if isinstance(c, dict) and isinstance(c.get("usd"), (int, float)):
        return float(c["usd"])
    if isinstance(c, (int, float)):
        return float(c)
    return 0.0


def packet_fact_ids(packet: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("deterministic_core", "jev_selected_enrichment"):
        for row in packet.get(key) or []:
            fid = str(row.get("id") or "")
            if fid:
                ids.add(fid)
    return ids


def deterministic_plan_check(plan: dict[str, Any], allowed_fact_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.get("premise"), str) or not plan["premise"].strip():
        errors.append("missing_premise")
    beats = plan.get("beats")
    if not isinstance(beats, list) or len(beats) != 8:
        errors.append("beats_must_equal_8")
        beats = beats if isinstance(beats, list) else []
    actual_ids = [str(x.get("id") or "") for x in beats]
    if actual_ids != [f"B{i}" for i in range(1,9)]:
        errors.append(f"beat_ids_invalid:{actual_ids}")
    anchors = 0
    for beat in beats:
        density = str(beat.get("density") or "")
        if density not in {"brief","develop","anchor"}:
            errors.append(f"density_invalid:{beat.get('id')}:{density}")
        if density == "anchor":
            anchors += 1
        if not str(beat.get("beat") or "").strip():
            errors.append(f"empty_beat:{beat.get('id')}")
        refs = beat.get("uses_fact_ids") or []
        if not isinstance(refs, list):
            errors.append(f"fact_refs_not_list:{beat.get('id')}")
            continue
        unknown = sorted(set(str(x) for x in refs)-allowed_fact_ids)
        if unknown:
            errors.append(f"unknown_fact_refs:{beat.get('id')}:{unknown}")
    if anchors < 3:
        errors.append(f"anchors_lt_3:{anchors}")
    if not isinstance(plan.get("expected_outcome"), dict):
        errors.append("missing_expected_outcome")
    return errors


def normalize_audit(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    rows = payload.get("evaluations")
    if not isinstance(rows, list):
        raise RuntimeError("evaluations_missing")
    seen=set()
    findings=[]
    for row in rows:
        fam=str(row.get("family") or "")
        if fam not in DEFECT_FAMILIES or fam in seen:
            raise RuntimeError(f"family_invalid_or_duplicate:{fam}")
        seen.add(fam)
        present=row.get("present")
        if not isinstance(present,bool):
            raise RuntimeError(f"present_invalid:{fam}")
        if not present:
            continue
        sev=str(row.get("severity") or "")
        if sev not in {"serious","critical"}:
            raise RuntimeError(f"severity_invalid:{fam}:{sev}")
        spans=[str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"span_invalid:{fam}:{spans}")
        findings.append({
            "family":fam,
            "severity":sev,
            "span_ids":spans,
            "repair_scope":row.get("repair_scope"),
            "reason":str(row.get("reason") or "").strip(),
        })
    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError(f"families_missing:{sorted(set(DEFECT_FAMILIES)-seen)}")
    return findings


def audit_story(*, api_key:str, model:str, fixture:dict[str,Any], plan:dict[str,Any], story:str, seed:int):
    seg=segment_story(story)
    payload,meta=structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={
            "story_intent":fixture["story_intent"],
            "context_packet":fixture["context_packet"],
            "protected_boundary":fixture["protected_boundary"],
            "validated_spine":plan,
            "story_segments":seg,
        },
        seed=seed,
        max_tokens=2800,
        request_class="editorial_audit",
    )
    return normalize_audit(payload,{x["id"] for x in seg}),meta


def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    started=time.perf_counter()
    allowed=packet_fact_ids(fixture["context_packet"])

    plan,planner_meta=structured_call(
        api_key=key,
        model=PLANNER,
        system=PLANNER_SYSTEM,
        payload={
            "story_intent":fixture["story_intent"],
            "context_packet":fixture["context_packet"],
            "generation_profile":fixture["generation_profile"],
            "protected_boundary":fixture["protected_boundary"],
        },
        seed=SEED,
        max_tokens=None,
        request_class="story_planning",
    )

    det_errors=deterministic_plan_check(plan,allowed)
    validator,validator_meta=structured_call(
        api_key=key,
        model=PLAN_VALIDATOR,
        system=PLAN_VALIDATOR_SYSTEM,
        payload={
            "story_intent":fixture["story_intent"],
            "context_packet":fixture["context_packet"],
            "generation_profile":fixture["generation_profile"],
            "protected_boundary":fixture["protected_boundary"],
            "proposed_plan":plan,
            "deterministic_plan_errors":det_errors,
        },
        seed=SEED+1,
        max_tokens=2200,
        request_class="editorial_audit",
    )
    counts=validator.get("counts") or {}
    plan_pass=(
        not det_errors
        and bool(validator.get("valid"))
        and int(counts.get("critical",0) or 0)==0
        and int(counts.get("serious",0) or 0)==0
    )

    story=None; writer_cost=0.0; writer_usage=None; words=None; length_pass=False
    primary=None; primary_meta=None; secondary=None; secondary_meta=None; english_pass=False
    translation=None; trans_cost=0.0; trans_usage=None; fidelity=None; fidelity_meta=None; fidelity_pass=False

    if plan_pass:
        story,body,_=call_openrouter(
            api_key=key,
            model=WRITER,
            system_prompt=WRITER_SYSTEM,
            user_prompt=json.dumps({
                "story_intent":fixture["story_intent"],
                "context_packet":fixture["context_packet"],
                "protected_boundary":fixture["protected_boundary"],
                "validated_plan":plan,
                "generation_profile":fixture["generation_profile"],
            },ensure_ascii=False),
            temperature=0.72,
            max_tokens=None,
            seed=SEED+2,
            request_class="teacher_story_medium_reasoning",
            structured_output=False,
        )
        writer_cost=float(parse_cost(body).usd or 0.0)
        writer_usage=parse_usage(body).model_dump(mode="json")
        words=count_words(story)
        length_pass=375<=words<=625

        primary,primary_meta=audit_story(api_key=key,model=PRIMARY_AUDITOR,fixture=fixture,plan=plan,story=story,seed=SEED+3)
        secondary,secondary_meta=audit_story(api_key=key,model=SECONDARY_AUDITOR,fixture=fixture,plan=plan,story=story,seed=SEED+4)
        english_pass=length_pass and not primary and not secondary

    if english_pass and story:
        translation,body,_=call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=story,
            temperature=0.2,
            max_tokens=None,
            seed=SEED+5,
            request_class="translation",
            structured_output=False,
        )
        trans_cost=float(parse_cost(body).usd or 0.0)
        trans_usage=parse_usage(body).model_dump(mode="json")
        fidelity,fidelity_meta=structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language":"en",
                "target_language":"tr",
                "exact_age":4,
                "source_story":story,
                "translation":translation,
            },
            seed=SEED+6,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        blocking=[x for x in (fidelity.get("findings") or []) if str(x.get("severity") or "") in {"serious","critical"}]
        fidelity_pass=bool(fidelity.get("fidelity_clean")) and not blocking

    costs={
        "planner":meta_cost(planner_meta),
        "plan_validator":meta_cost(validator_meta),
        "writer":writer_cost,
        "primary_story_audit":meta_cost(primary_meta),
        "secondary_story_audit":meta_cost(secondary_meta),
        "translator":trans_cost,
        "fidelity_gate":meta_cost(fidelity_meta),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-spine-planner-qualification-02-garden-gate-result.v1",
        "profile":fixture["profile"],
        "source_context_builder_run":fixture["source_context_builder_run"],
        "story_intent":fixture["story_intent"],
        "context_packet":fixture["context_packet"],
        "protected_boundary":fixture["protected_boundary"],
        "models":{
            "planner":PLANNER,
            "plan_validator":PLAN_VALIDATOR,
            "writer":WRITER,
            "primary_story_auditor":PRIMARY_AUDITOR,
            "secondary_story_auditor":SECONDARY_AUDITOR,
            "translator":TRANSLATOR,
            "fidelity_gate":FIDELITY_GATE,
        },
        "planner_output":plan,
        "deterministic_plan_errors":det_errors,
        "plan_validation":validator,
        "plan_pass":plan_pass,
        "english_story":story,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "turkish_translation":translation,
        "fidelity_result":fidelity,
        "fidelity_pass":fidelity_pass,
        "publication_ready":plan_pass and english_pass and fidelity_pass,
        "cost_usd":costs,
        "writer_usage":writer_usage,
        "translator_usage":trans_usage,
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if story:
        (OUT.parent/"english.txt").write_text(story+"\n",encoding="utf-8")
    if translation:
        (OUT.parent/"turkish.txt").write_text(translation+"\n",encoding="utf-8")

    print(json.dumps({
        "plan_pass":plan_pass,
        "deterministic_plan_errors":det_errors,
        "plan_validation":validator,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "fidelity_pass":fidelity_pass,
        "publication_ready":result["publication_ready"],
        "cost_usd":costs,
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
