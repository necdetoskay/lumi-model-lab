from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

OUT=Path("runs/lsf-a4-w500-problem-solving-qualification-01/result.json")

WRITER="aion-labs/aion-3.5-mini"
PRIMARY_AUDITOR="anthropic/claude-sonnet-5"
SECONDARY_AUDITOR="openai/gpt-5.6-sol"
TRANSLATOR="google/gemini-3.8-flash"
FIDELITY_GATE="openai/gpt-5.6-luna"
SEED=2026092731

PREMISE="""Deniz wants his small toy truck to climb from the courtyard stones onto a low wooden platform, but the step is too high for the truck. He first tries pushing harder, then notices a flat piece of cardboard nearby. He tests it as a ramp, sees it slip, then places one end against the platform edge and steadies the bottom with a small wooden block. The truck can finally roll up the ramp. At the end he sends the truck down and up once more, listening to the wheels rumble over the cardboard."""

SPINE=[
 {"density":"brief","beat":"Deniz rolls his small toy truck across the courtyard stones toward a low wooden platform. The truck reaches the vertical step and stops because its front wheels cannot climb the height."},
 {"density":"develop","beat":"Deniz pushes the truck a little harder once. The front wheels bump the edge and fall back to the stones. He stops instead of forcing it."},
 {"density":"develop","beat":"He looks around and notices a flat rectangle of sturdy cardboard from a box. He places one end on the platform and the other on the stones, making a sloped ramp."},
 {"density":"develop","beat":"He tests the truck. The truck starts up, but the cardboard slides away from the platform edge and flattens. Deniz watches where it moved."},
 {"density":"anchor","beat":"Deniz resets the cardboard with its top edge pressed firmly against the platform. He then places one small wooden block at the bottom edge so the cardboard cannot slide backward. Do not add extra tools or adult help."},
 {"density":"anchor","beat":"He tests with one finger first by pressing lightly on the cardboard. It stays in place. Then he rolls the truck slowly up. The wheels climb the slope and reach the platform."},
 {"density":"anchor","beat":"Deniz does not celebrate with a lesson or explanation. He simply rolls the truck across the platform, then turns it around and sends it gently back down the cardboard ramp."},
 {"density":"anchor","beat":"For the ending, Deniz rolls the truck up the ramp one more time, listening to the small rumble of the wheels on the cardboard. End with the truck parked on the platform and the ramp still steady below it."},
]

WRITER_SYSTEM=r"""
You are an experienced English children's story writer.
Write a warm, concrete read-aloud story for an EXACTLY 4-year-old child.

You receive a premise and a STORY SPINE. Preserve the spine's event order and physical solution, but write a real story, not expanded bullet points.

Density:
- brief = quick movement
- develop = concrete action, sensory detail, short dialogue
- anchor = important story moment; make action and consequence especially clear

Hard rules:
- Keep the problem physical and understandable: the toy truck cannot climb a vertical step directly.
- Deniz may try one slightly harder push, but must stop when it fails; do not turn this into repeated force.
- The solution is ONLY the flat cardboard ramp plus ONE small wooden block stabilizing the lower edge.
- The top edge of the cardboard rests firmly against the platform edge.
- Do not add tape, glue, string, books, bricks, tools, adults, or a different solution.
- The cardboard first slips during the initial test, then is repositioned and stabilized.
- Test order after stabilization: light finger press -> slow truck roll upward.
- The ramp remains stable through the final up/down/up sequence.
- Do not add family/canon/background facts.
- Do not turn the story into a lesson about engineering, patience, persistence, or trying again.
- Avoid narrator mind-reading when observable behavior or dialogue can show the same thing.
- Keep language concrete, simple, rhythmic, and read-aloud friendly.
- End with the truck parked on the platform and the ramp still steady below it.

LENGTH:
- Target: about 500 words.
- Preferred range: 475-525.
- Hard range: 375-625.
- Do not finish below 375 words.

Return only the finished story. First line must be the title.
""".strip()

AUDIT_SYSTEM=r"""
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

Report ONLY serious or critical semantic defects. Ignore grammar, style, word count, repetition, optional polish, mild narrator-mindread, and taste unless they create a serious story failure.

Canonical story rules:
- the truck cannot climb the vertical step directly;
- one harder push may fail once, then Deniz stops forcing it;
- the solution is a sturdy flat cardboard ramp plus ONE small wooden block stabilizing the lower edge;
- the cardboard's top edge rests against the platform edge;
- first ramp test slips and flattens;
- after reset/stabilization, Deniz first presses lightly with one finger, then slowly rolls the truck upward;
- no extra tools/adult help/different solution;
- ramp remains stable for the final down-and-up sequence;
- ending: truck parked on platform, ramp steady below;
- do not invent durable canon/family facts.

Return JSON only:
{
  "evaluations":[
    {
      "family":"physical_feasibility",
      "present":false,
      "severity":null,
      "repair_scope":null,
      "span_ids":[],
      "reason":"brief evidence-based reason"
    }
  ]
}
""".strip()

TRANSLATION_SYSTEM=r"""
You are a professional literary translator specializing in English -> Turkish children's read-aloud stories for EXACTLY age 4.

Translate the supplied finished English story into natural Turkish.

THIS IS TRANSLATION, NOT REWRITING.

Non-negotiable fidelity:
- Preserve every character, object, action, event, state transition, causal relation, and ending.
- Preserve the physical problem: the toy truck cannot climb the vertical step directly.
- Preserve the exact solution: one flat cardboard ramp plus one small wooden block stabilizing the lower edge.
- Preserve that the first cardboard test slips; only after repositioning and stabilization does the ramp work.
- Preserve the test order: light finger press -> slow truck roll upward.
- Do not add tape, glue, string, books, bricks, tools, adults, or another solution.
- Preserve the final down-and-up sequence and the truck parked on the platform with the ramp still steady.
- Do not add morals, explanations, canon, or extra dialogue.
- Keep Deniz unchanged.

Turkish quality:
- Natural contemporary Turkish for a 4-year-old being read to by an adult.
- Short, speakable, warm sentences.
- Use natural Turkish sound effects where useful.
- Avoid stiff literal calques.
- Keep imagery understandable for age 4.
- Do not summarize.

Return only the finished Turkish story.
""".strip()

FIDELITY_SYSTEM=r"""
You are a strict bilingual EN->TR semantic fidelity gate for a children's read-aloud story.

Report ONLY serious or critical translation defects:
- omission
- addition
- character_shift
- object_shift
- state_shift
- causal_shift
- knowledge_shift
- ending_shift

Pay special attention to:
- truck cannot climb the vertical step directly;
- one flat cardboard ramp;
- first test slips;
- one small wooden block stabilizes the lower edge;
- top cardboard edge rests against platform;
- light finger press before truck test;
- final down-and-up sequence;
- truck parked on platform and ramp still steady.

Ignore style preferences and harmless restructuring.

Return JSON only:
{
  "findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"short exact EN quote",
      "translation_quote":"short exact TR quote",
      "why":"brief reason"
    }
  ],
  "fidelity_clean":true
}
""".strip()

def meta_cost(meta:dict[str,Any]|None)->float:
    if not meta: return 0.0
    c=meta.get("cost")
    if isinstance(c,dict) and isinstance(c.get("usd"),(int,float)): return float(c["usd"])
    if isinstance(c,(int,float)): return float(c)
    return 0.0

def normalize_audit(payload:dict[str,Any], valid_ids:set[str])->list[dict[str,Any]]:
    rows=payload.get("evaluations")
    if not isinstance(rows,list):
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

def audit(api_key:str, model:str, story:str, seed:int, request_class:str):
    seg=segment_story(story)
    payload,meta=structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={
            "exact_age":4,
            "story_family":"problem_solving_small_adventure",
            "story_segments":seg,
        },
        seed=seed,
        max_tokens=2600,
        request_class=request_class,
    )
    return normalize_audit(payload,{x["id"] for x in seg}),meta

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()

    spine_text="\n".join(f"{i+1}. [{b['density']}] {b['beat']}" for i,b in enumerate(SPINE))
    draft,writer_body,writer_payload=call_openrouter(
        api_key=key,
        model=WRITER,
        system_prompt=WRITER_SYSTEM,
        user_prompt=f"PREMISE:\n{PREMISE}\n\nSTORY SPINE:\n{spine_text}\n\nWrite the finished story.",
        temperature=0.72,
        max_tokens=None,
        seed=SEED,
        request_class="teacher_story_medium_reasoning",
        structured_output=False,
    )

    words=count_words(draft)
    length_pass=375<=words<=625

    primary,primary_meta=audit(key,PRIMARY_AUDITOR,draft,SEED+1,"editorial_audit")
    secondary,secondary_meta=audit(key,SECONDARY_AUDITOR,draft,SEED+2,"editorial_audit")
    english_pass=length_pass and not primary and not secondary

    translation=None
    translator_cost=0.0
    translator_usage=None
    fidelity_result=None
    fidelity_meta=None
    fidelity_pass=False

    if english_pass:
        translation,trans_body,_=call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=draft,
            temperature=0.2,
            max_tokens=None,
            seed=SEED+3,
            request_class="translation",
            structured_output=False,
        )
        translator_cost=float(parse_cost(trans_body).usd or 0.0)
        translator_usage=parse_usage(trans_body).model_dump(mode="json")
        fidelity_result,fidelity_meta=structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language":"en",
                "target_language":"tr",
                "exact_age":4,
                "source_story":draft,
                "translation":translation,
            },
            seed=SEED+4,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        findings=fidelity_result.get("findings") or []
        blocking=[x for x in findings if str(x.get("severity") or "") in {"serious","critical"}]
        fidelity_pass=bool(fidelity_result.get("fidelity_clean")) and not blocking

    costs={
        "writer":float(parse_cost(writer_body).usd or 0.0),
        "primary_audit":meta_cost(primary_meta),
        "secondary_audit":meta_cost(secondary_meta),
        "translator":translator_cost,
        "fidelity_gate":meta_cost(fidelity_meta),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-a4-w500-problem-solving-qualification-01-result.v1",
        "profile":"LSF-A4-W500-v0.1",
        "story_family":"problem_solving_small_adventure",
        "premise":PREMISE,
        "spine":SPINE,
        "models":{
            "writer":WRITER,
            "primary_auditor":PRIMARY_AUDITOR,
            "secondary_auditor":SECONDARY_AUDITOR,
            "translator":TRANSLATOR,
            "fidelity_gate":FIDELITY_GATE,
        },
        "english_story":draft,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "secondary_findings":secondary,
        "english_pass":english_pass,
        "turkish_translation":translation,
        "fidelity_result":fidelity_result,
        "fidelity_pass":fidelity_pass,
        "publication_ready":english_pass and fidelity_pass,
        "cost_usd":costs,
        "writer_usage":parse_usage(writer_body).model_dump(mode="json"),
        "translator_usage":translator_usage,
        "elapsed_seconds":round(time.perf_counter()-started,3),
        "writer_request_payload":writer_payload,
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"english.txt").write_text(draft+"\n",encoding="utf-8")
    if translation:
        (OUT.parent/"turkish.txt").write_text(translation+"\n",encoding="utf-8")

    print(json.dumps({
        "english_words":words,
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
