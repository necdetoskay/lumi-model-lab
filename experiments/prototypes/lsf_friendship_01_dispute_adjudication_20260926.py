from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import call_openrouter, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

FIXTURE=Path("experiments/fixtures/lsf_friendship_01_verifier_dispute_20260926.json")
OUT=Path("runs/lsf-friendship-01-dispute-adjudication/result.json")

ARBITER="openai/gpt-5.6-sol"
TRANSLATOR="google/gemini-3.8-flash"
FIDELITY_GATE="openai/gpt-5.6-luna"

ARBITER_SYSTEM=r"""
You are the final arbiter for ONE disputed semantic finding in a finished English read-aloud story for an exact-age-4 child.

You receive:
- the full story;
- one disputed finding from a prior verifier.

Judge the STORY ITSELF. Do not trust the prior severity label.
The disputed family is state_continuity.

Question:
Does the red chalk state contain a real serious/critical contradiction?

Track only these facts:
1) one short red chalk piece exists;
2) it snaps into two usable halves;
3) Deniz holds one half and Ada holds the other;
4) each uses their own half to draw;
5) Ada draws from her side, Deniz from his side, and the two red lines meet;
6) after drawing, both broken halves may rest beside the finished crossing.

Do not report a defect merely because the story does not explicitly narrate the act of putting a chalk piece down after drawing. That is an ordinary implied transition unless it creates an actual contradiction.

Return JSON only:
{
  "defect_present": false,
  "severity": null,
  "reason": "brief evidence-based explanation"
}
If a real contradiction exists, defect_present=true and severity must be serious or critical.
""".strip()

TRANSLATION_SYSTEM=r"""
You are a professional literary translator specializing in English -> Turkish children's read-aloud stories for EXACTLY age 4.

Translate the supplied finished English story into natural Turkish.

THIS IS TRANSLATION, NOT REWRITING.

Non-negotiable fidelity:
- Preserve every character, object, action, event, state transition, causal relation, and ending.
- Preserve the red chalk continuity exactly:
  one short red chalk piece -> snaps into two usable halves -> Deniz keeps one, Ada keeps one -> each draws with their own half -> the two red lines meet -> after drawing, both halves may rest beside the finished crossing.
- Preserve who says and does what.
- Preserve the roads beginning separate and becoming connected only after the chalk breaks.
- Preserve the playful turn-taking without adding a moral or lesson.
- Preserve the final concrete ending with the cars approaching the red middle, stopping, then passing one after another.
- Do not add or remove events, motivations, morals, canon, or dialogue.
- Keep Deniz and Ada names unchanged.

Turkish quality:
- Natural contemporary Turkish for a 4-year-old being read to by an adult.
- Short, speakable, warm sentences.
- Avoid stiff literal calques.
- Keep imagery understandable for age 4.

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
- one red chalk piece snapping into two usable halves,
- one half remaining with Deniz and one with Ada,
- each child drawing with their own half,
- separate roads becoming one connected crossing,
- final stop-and-pass ending.

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
  "fidelity_clean": true
}
""".strip()

def meta_cost(meta:dict[str,Any]|None)->float:
    if not meta: return 0.0
    c=meta.get("cost")
    if isinstance(c,dict) and isinstance(c.get("usd"),(int,float)): return float(c["usd"])
    if isinstance(c,(int,float)): return float(c)
    return 0.0

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    story=fixture["english_story"]
    started=time.perf_counter()

    arbiter,arbiter_meta=structured_call(
        api_key=key,
        model=ARBITER,
        system=ARBITER_SYSTEM,
        payload={
            "exact_age":4,
            "story_family":"friendship_emotional_social",
            "story":story,
            "disputed_finding":fixture["disputed_finding"],
        },
        seed=2026092710,
        max_tokens=1200,
        request_class="editorial_audit",
    )

    defect_present=arbiter.get("defect_present")
    if not isinstance(defect_present,bool):
        raise RuntimeError("arbiter_defect_present_missing")

    translation=None
    trans_cost=0.0
    trans_usage=None
    fidelity=None
    fidelity_meta=None
    fidelity_pass=False

    if not defect_present:
        translation,body,_=call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=story,
            temperature=0.2,
            max_tokens=None,
            seed=2026092711,
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
            seed=2026092712,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        findings=fidelity.get("findings") or []
        serious=[x for x in findings if str(x.get("severity") or "") in {"serious","critical"}]
        fidelity_pass=bool(fidelity.get("fidelity_clean")) and not serious

    costs={
        "arbiter":meta_cost(arbiter_meta),
        "translator":trans_cost,
        "fidelity_gate":meta_cost(fidelity_meta),
    }
    costs["total"]=sum(costs.values())

    result={
        "schema_version":"lsf-friendship-01-dispute-adjudication-result.v1",
        "source_run_id":fixture["source_run_id"],
        "arbiter_model":ARBITER,
        "arbiter_result":arbiter,
        "translation_model":TRANSLATOR,
        "translation":translation,
        "translation_usage":trans_usage,
        "fidelity_model":FIDELITY_GATE,
        "fidelity_result":fidelity,
        "fidelity_pass":fidelity_pass,
        "publication_ready":(not defect_present) and fidelity_pass,
        "cost_usd":costs,
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if translation:
        (OUT.parent/"turkish.txt").write_text(translation+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
