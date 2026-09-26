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

OUT=Path("runs/lsf-a4-w500-friendship-qualification-01/result.json")

WRITER="aion-labs/aion-3.5-mini"
PRIMARY_AUDITOR="anthropic/claude-sonnet-5"
VERIFIER="anthropic/claude-haiku-4.5"
TRANSLATOR="google/gemini-3.8-flash"
FIDELITY_GATE="openai/gpt-5.6-luna"
SEED=2026092701

PREMISE="""Deniz and Ada are drawing separate roads with sidewalk chalk for their toy cars. There is only one short red chalk piece left. They both reach for it at the same time, and while each is holding one end it snaps into two. After a quiet beat, they each use one red piece, and their two separate roads gradually become one shared crossing where their cars can meet and pass."""

SPINE=[
 {"density":"brief","beat":"Deniz and Ada sit on the courtyard floor drawing separate chalk roads for their toy cars; Deniz's road curves from one side and Ada's from the other."},
 {"density":"develop","beat":"They both notice the last short red chalk piece and reach for it at the same time. Their hands meet. Deniz says he needs red; Ada says she needs it too."},
 {"density":"develop","beat":"Each holds one end and gives a small pull. The chalk snaps into two pieces. Both stop. Ada looks at one broken end; Deniz sets his toy car down and looks at the other."},
 {"density":"develop","beat":"Deniz rubs the broken red half already in his hand on the pavement and sees that it still draws. Ada tries the broken half already in her own hand. Each adds a small red mark to their own road. Nobody gives a chalk piece to the other."},
 {"density":"anchor","beat":"Their two roads now come close but still stop with a gap between them. Ada rolls her car to her edge; Deniz rolls his car to his. The two cars face one another across the empty space."},
 {"density":"anchor","beat":"Ada draws a red line from her road toward the middle. Deniz continues it from his side. Together the two red halves make one shared red crossing that connects the roads."},
 {"density":"anchor","beat":"They test the crossing. The cars almost bump at the center, so Deniz pauses his car and says 'You go.' Ada crosses, then stops her car and lets Deniz pass on the next turn. Keep this playful, not moralizing."},
 {"density":"anchor","beat":"At the end, the two broken red chalk halves rest beside the finished crossing. Deniz and Ada roll their cars toward the red middle, pause, then pass through one after the other."},
]

WRITER_SYSTEM=r"""
You are an experienced English children's story writer.
Write a warm, natural read-aloud story for an EXACTLY 4-year-old child.

You receive a premise and a STORY SPINE. Preserve the spine's event order and causal structure, but write a real story, not expanded bullet points.

Density:
- brief = quick movement
- develop = concrete action, sensory detail, short dialogue
- anchor = important story moment; make action and consequence especially clear

Hard rules:
- Keep Deniz and Ada as active children; no adult solves the problem.
- Do not add family/canon/background facts.
- Do not turn the story into a lesson about sharing, kindness, manners, or friendship.
- Let behavior and dialogue carry the emotional change.
- Avoid narrator mind-reading when observable behavior or dialogue can show the same thing.
- Preserve the physical fact that the red chalk snaps into TWO usable pieces.
- Preserve object continuity: after the snap, Deniz already holds one red half and Ada already holds the other. Nobody transfers a red half to the other child. One broken red half remains with each child through the connecting-road beat.
- Colored chalk marks must match the chalk color being used; do not describe a blue chalk mark as gray or another color.
- The roads begin separate and become connected only after the chalk breaks.
- Do not add a different solution or new object.
- Keep language concrete, simple, rhythmic, and read-aloud friendly.
- End on the two cars approaching the red middle, pausing, and passing one after another.

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

Report ONLY serious or critical semantic defects. Ignore grammar, style, word count, repetition, optional polish, mild narrator-mindread, mild didactic phrasing, and taste unless they create a serious story failure.

Rules:
- Do not invent hidden constraints.
- Ordinary child play/personification is allowed.
- state_continuity: track the red chalk carefully; it starts as one piece, snaps into two usable halves, and later references must remain consistent.
- causal_logic: the two separate roads should only become connected after the children create the shared crossing.
- response_causality: busy hands/task load do not make speech physically impossible.
- closure_integrity: ending should not materially reopen after the crossing payoff.
- canon_integrity: do not invent/contradict durable facts beyond the supplied premise/spine.

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

Non-negotiable fidelity rules:
- Preserve characters, objects, actions, event order, state transitions, causal relations, and ending.
- Preserve the red chalk continuity exactly: one short red chalk piece -> snaps into two usable halves -> one half with each child -> shared red crossing.
- Preserve who says and does what.
- Preserve the two separate roads becoming connected only after the chalk snaps.
- Preserve the playful turn-taking scene without adding a moral or lesson.
- Preserve the final concrete ending: cars approach the red middle, pause, then pass one after another.
- Do not add or remove plot events, motivations, morals, canon, or dialogue.
- Do not repair or improve source logic.
- Keep Deniz and Ada names unchanged.
- Translate sound effects naturally where needed.

Turkish quality:
- Natural contemporary Turkish for a 4-year-old being read to by an adult.
- Short, speakable, warm sentences.
- Avoid stiff literal calques.
- Keep imagery understandable for age 4.
- Do not summarize.

Return only the finished Turkish story, no notes.
""".strip()

FIDELITY_SYSTEM=r"""
You are a strict bilingual EN->TR semantic fidelity gate for a children's read-aloud story.

Report ONLY serious or critical translation defects that change meaning or story state:
- omission
- addition
- character_shift
- object_shift
- state_shift
- causal_shift
- knowledge_shift
- ending_shift

Pay special attention to:
- one red chalk piece snapping into two usable halves,
- one half remaining with each child,
- separate roads becoming one connected crossing,
- which child speaks/acts,
- final pause-and-pass ending.

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
    if not isinstance(rows,list): raise RuntimeError("evaluations_missing")
    seen=set(); findings=[]
    for row in rows:
        fam=str(row.get("family") or "")
        if fam not in DEFECT_FAMILIES or fam in seen: raise RuntimeError(f"family_invalid_or_duplicate:{fam}")
        seen.add(fam)
        present=row.get("present")
        if not isinstance(present,bool): raise RuntimeError(f"present_invalid:{fam}")
        if not present: continue
        sev=str(row.get("severity") or "")
        if sev not in {"serious","critical"}: raise RuntimeError(f"severity_invalid:{fam}:{sev}")
        spans=[str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_ids): raise RuntimeError(f"span_invalid:{fam}:{spans}")
        findings.append({"family":fam,"severity":sev,"span_ids":spans,"reason":str(row.get("reason") or "").strip()})
    if seen!=set(DEFECT_FAMILIES): raise RuntimeError("families_missing")
    return findings

def audit(api_key:str, model:str, story:str, seed:int, request_class:str):
    seg=segment_story(story)
    payload,meta=structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={"exact_age":4,"story_family":"friendship_emotional_social","story_segments":seg},
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
    verifier,verifier_meta=audit(key,VERIFIER,draft,SEED+2,"judge")

    english_pass=length_pass and not primary and not verifier
    translation=None
    translator_cost=0.0
    fidelity_payload=None
    fidelity_meta=None
    fidelity_pass=False
    translator_usage=None

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
        fidelity_payload,fidelity_meta=structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={"source_language":"en","target_language":"tr","exact_age":4,"source_story":draft,"translation":translation},
            seed=SEED+4,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        findings=fidelity_payload.get("findings") or []
        serious=[x for x in findings if str(x.get("severity") or "") in {"serious","critical"}]
        fidelity_pass=bool(fidelity_payload.get("fidelity_clean")) and not serious

    costs={
        "writer":float(parse_cost(writer_body).usd or 0.0),
        "primary_audit":meta_cost(primary_meta),
        "verifier":meta_cost(verifier_meta),
        "translator":translator_cost,
        "fidelity_gate":meta_cost(fidelity_meta),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-a4-w500-friendship-qualification-01.v1",
        "profile":"LSF-A4-W500-v0.1",
        "story_family":"friendship_emotional_social",
        "premise":PREMISE,
        "spine":SPINE,
        "models":{"writer":WRITER,"primary_auditor":PRIMARY_AUDITOR,"verifier":VERIFIER,"translator":TRANSLATOR,"fidelity_gate":FIDELITY_GATE},
        "english_story":draft,
        "english_word_count":words,
        "length_pass":length_pass,
        "primary_findings":primary,
        "verifier_findings":verifier,
        "english_pass":english_pass,
        "turkish_translation":translation,
        "fidelity_result":fidelity_payload,
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
        "verifier_findings":verifier,
        "english_pass":english_pass,
        "fidelity_pass":fidelity_pass,
        "publication_ready":result["publication_ready"],
        "cost_usd":costs,
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
