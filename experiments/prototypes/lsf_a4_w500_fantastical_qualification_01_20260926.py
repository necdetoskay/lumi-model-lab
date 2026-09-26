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

OUT=Path("runs/lsf-a4-w500-fantastical-qualification-01/result.json")

WRITER="aion-labs/aion-3.5-mini"
PRIMARY_AUDITOR="anthropic/claude-sonnet-5"
SECONDARY_AUDITOR="openai/gpt-5.6-sol"
TRANSLATOR="google/gemini-3.8-flash"
FIDELITY_GATE="openai/gpt-5.6-luna"
SEED=2026092721

PREMISE="""After a rainy afternoon, Deniz finds a tiny cloud floating at knee height beside a metal bucket in the courtyard. The little cloud does not behave like a normal cloud: when Deniz hums a low, gentle note, it trembles and lets one raindrop fall into the bucket. Deniz tests the strange rule carefully and turns the drops into a tiny rhythm game. In the end, the cloud rises toward the evening sky while Deniz listens to the last two drops ring in the bucket."""

SPINE=[
 {"density":"brief","beat":"After the rain, Deniz returns to the courtyard and notices a tiny gray-white cloud floating at about knee height beside an empty metal bucket."},
 {"density":"develop","beat":"He crouches and watches. He waves one hand near it without touching it. The little cloud drifts a handspan away, then settles again above the bucket."},
 {"density":"develop","beat":"Deniz makes a quiet low hum — 'mmmm'. The cloud gives a small shiver and one raindrop falls into the metal bucket: ting. Deniz stops humming. The cloud becomes still and no more drops fall."},
 {"density":"develop","beat":"He tests the rule again: one gentle hum, one small shiver, one drop, one ting. He pauses. No hum, no drop. Show the pattern through repeated action rather than narrator explanation."},
 {"density":"anchor","beat":"Deniz tries a short rhythm: hum, pause, hum-hum. The cloud answers with one drop, a pause, then two drops. Keep the cloud's behavior consistent with the established hum->drop rule."},
 {"density":"anchor","beat":"He becomes playful but careful. He does not grab, squeeze, trap, or touch the cloud. He changes only the timing of his humming and listens to the drops make different little rhythms in the bucket."},
 {"density":"anchor","beat":"The tiny cloud begins to rise slowly on its own toward a larger evening cloud above the courtyard. Deniz does not cause the rising and does not try to stop it."},
 {"density":"anchor","beat":"Before it gets too high, Deniz hums two slow notes. The little cloud gives two final drops — ting... ting — into the bucket, then continues upward. End with Deniz beside the bucket listening to the two fading rings while the tiny cloud joins the evening sky."},
]

WRITER_SYSTEM=r"""
You are an experienced English children's story writer.
Write a warm, imaginative read-aloud story for an EXACTLY 4-year-old child.

You receive a premise and a STORY SPINE. Preserve the spine's event order and internal magical rule, but write a real story, not expanded bullet points.

Density:
- brief = quick movement
- develop = concrete action, sensory detail, short dialogue
- anchor = important story moment; make action and consequence especially clear

Hard rules:
- This is gentle fantasy. The tiny cloud may be magical, but its established rule must stay internally consistent.
- The magical rule is: one gentle low hum produces one small shiver and one raindrop; multiple hums may produce matching multiple drops, with pauses preserved.
- Silence must not spontaneously produce a drop before the final rising sequence.
- Deniz must not touch, grab, squeeze, trap, bottle, or physically manipulate the cloud.
- Waving his hand early may make the cloud drift away slightly, but waving does NOT produce raindrops.
- Deniz's humming does NOT cause the cloud to rise at the end. The cloud begins rising on its own.
- Preserve the metal bucket; do not replace it with another container.
- Do not invent family/canon/background facts.
- Do not turn the story into a lesson about nature, kindness, letting go, music, or patience.
- Avoid narrator mind-reading when observable behavior or dialogue can show the same thing.
- Keep language concrete, simple, rhythmic, and read-aloud friendly.
- The ending must contain exactly two final slow hums followed by two final drops, then the cloud continues upward and Deniz listens to the fading rings.

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

This story intentionally contains gentle fantasy. Do not flag the existence of a tiny floating cloud as physically impossible merely because it is magical.

Canonical story rules for this audit:
- one gentle low hum -> one small cloud shiver -> one raindrop into the same metal bucket;
- multiple hums may yield matching multiple drops, preserving pauses;
- silence does not produce extra drops before the final rising sequence;
- waving a hand may move the cloud slightly but does not create drops;
- Deniz never touches/grabs/squeezes/traps the cloud;
- the cloud starts rising on its own; Deniz's humming does not cause that rising;
- the final beat is two slow hums -> exactly two final drops -> cloud continues upward -> Deniz listens to the fading rings;
- do not invent durable family/canon facts.

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
- Preserve every character, object, action, event, state transition, causal relation, magical rule, and ending.
- Preserve the same metal bucket throughout.
- Preserve the magical rule exactly: one gentle low hum -> one small shiver -> one raindrop; multiple hums may produce matching multiple drops with pauses preserved.
- Do not make waving, touching, or another action produce drops.
- Deniz never touches/grabs/squeezes/traps the cloud.
- The cloud begins rising on its own; Deniz does not cause the rise.
- Preserve the ending exactly in meaning: two slow hums -> two final drops -> cloud continues upward -> Deniz listens to the fading rings.
- Do not add or remove plot events, morals, explanations, canon, or dialogue.
- Keep Deniz unchanged.

Turkish quality:
- Natural contemporary Turkish for a 4-year-old being read to by an adult.
- Short, speakable, warm sentences.
- Use natural Turkish sound effects for the metal bucket.
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
- the same metal bucket throughout;
- one gentle low hum -> one cloud shiver -> one raindrop;
- matching multiple hums/drops and pauses;
- Deniz never touching or trapping the cloud;
- cloud rising on its own;
- exactly two final slow hums -> two final drops -> cloud continues upward -> Deniz listens.

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
            "story_family":"fantastical_discovery",
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
        "schema_version":"lsf-a4-w500-fantastical-qualification-01-result.v1",
        "profile":"LSF-A4-W500-v0.1",
        "story_family":"fantastical_discovery",
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
