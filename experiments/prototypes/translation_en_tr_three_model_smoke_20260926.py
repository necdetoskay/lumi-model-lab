from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SOURCE_FIXTURE = Path("experiments/fixtures/aion35_mini_raw_story_for_serious_audit_20260926.json")
OUT = Path("runs/translation-en-tr-three-model-smoke/result.json")

TRANSLATORS = [
    ("A", "google/gemini-3.8-flash"),
    ("B", "qwen/qwen3-max"),
    ("C", "qwen/qwen3-30b-a3b-instruct-2507"),
]
EVALUATOR_MODEL = "openai/gpt-5.6-sol"

TRANSLATION_SYSTEM = r"""
You are a professional literary translator specializing in English -> Turkish children's read-aloud stories for EXACTLY age 4.

Translate the supplied finished English story into natural Turkish.

THIS IS TRANSLATION, NOT REWRITING.

Non-negotiable fidelity rules:
- Preserve every character, object, action, event, state transition, discovery, causal relation, and ending.
- Preserve the order of events.
- Do not add, remove, merge, or invent plot events.
- Do not add explanations, morals, lessons, canon, family facts, motivations, or new dialogue.
- Do not repair or improve the underlying story logic. If the source says something, translate it faithfully.
- Preserve the physical rule of the hanging metal rings and Deniz's palm-made air current exactly.
- Preserve the final open waiting-for-the-wind beat exactly; do not manufacture a new resolution.
- Keep Deniz as Deniz.
- Translate sound effects naturally for Turkish read-aloud where appropriate, but preserve their function and count/rhythm.
- Do not summarize.

Turkish quality rules:
- Natural contemporary Turkish suitable for a 4-year-old being read to by an adult.
- Short, speakable sentences; warm but not babyish.
- Avoid stiff literal calques when a natural Turkish equivalent exists.
- Keep imagery only when it is understandable for age 4.
- Maintain paragraph/rhythm structure where practical.
- Title must be translated naturally.

Return ONLY the finished Turkish story, no notes.
""".strip()

EVALUATOR_SYSTEM = r"""
You are a bilingual EN-TR children's-book translation quality evaluator.

You receive:
1) one authoritative English source story;
2) three anonymized Turkish translations A, B, C.

Evaluate translation quality only. Do not reward creative rewriting.

For EACH candidate independently inspect:
A. FIDELITY / SEMANTIC PRESERVATION
- characters, objects, actions, event order
- causal relationships and physical rules
- state continuity
- discovery/knowledge order
- dialogue meaning
- ending meaning and openness/closure
- omissions, additions, invented canon
B. TURKISH QUALITY
- natural Turkish, not translationese
- grammar and morphology
- read-aloud flow
- exact-age-4 vocabulary/register
- sound effects/rhythm preserved naturally

Classify issues:
- critical: changes the core story/canon/causal architecture or makes translation unusable
- serious: meaningful semantic omission/addition/state/causal/ending distortion
- moderate: noticeable fidelity or Turkish/read-aloud weakness but story meaning remains intact
- minor: polish-level issue

Do not invent source requirements.
Do not penalize natural Turkish restructuring when meaning is preserved.

Return JSON only:
{
  "candidates": {
    "A": {
      "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
      "fidelity_pass":true,
      "age4_turkish_pass":true,
      "issues":[
        {"severity":"moderate","class":"omission|addition|causal_shift|state_shift|ending_shift|dialogue_shift|translationese|grammar|read_aloud|age_register|rhythm","source_quote":"short exact EN quote","translation_quote":"short exact TR quote","why":"brief reason"}
      ],
      "summary":"brief"
    },
    "B": {},
    "C": {}
  },
  "comparative_notes":"brief factual comparison"
}
""".strip()

def usd(body: dict) -> float:
    return float(parse_cost(body).usd or 0.0)

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    source=json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    story=source["story"]
    started=time.perf_counter()

    translations={}
    translator_meta={}
    total_cost=0.0

    for i,(label,model) in enumerate(TRANSLATORS):
        text,body,payload=call_openrouter(
            api_key=key,
            model=model,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=story,
            temperature=0.2,
            max_tokens=None,
            seed=2026092650+i,
            request_class="translation",
            structured_output=False,
        )
        translations[label]=text.strip()
        c=usd(body)
        total_cost+=c
        translator_meta[label]={
            "model":model,
            "cost_usd":c,
            "usage":parse_usage(body).model_dump(mode="json"),
            "request_payload":payload,
        }

    evaluation, eval_meta=structured_call(
        api_key=key,
        model=EVALUATOR_MODEL,
        system=EVALUATOR_SYSTEM,
        payload={
            "source_language":"en",
            "target_language":"tr",
            "exact_age":4,
            "source_story":story,
            "translations":translations,
        },
        seed=2026092660,
        max_tokens=None,
        request_class="editorial_audit",
    )
    eval_cost=float(((eval_meta.get("cost") or {}).get("usd")) or 0.0)
    total_cost+=eval_cost

    result={
        "schema_version":"translation-en-tr-three-model-smoke-result.v1",
        "source_writer":"aion-labs/aion-3.5-mini",
        "source_run_id":36257356137,
        "source_story":story,
        "translator_labels":{label:model for label,model in TRANSLATORS},
        "translations":translations,
        "translator_meta":translator_meta,
        "evaluator":{"model":EVALUATOR_MODEL,"result":evaluation,"meta":eval_meta},
        "total_cost_usd":round(total_cost,6),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for label,text in translations.items():
        (OUT.parent/f"translation_{label}.txt").write_text(text+"\n",encoding="utf-8")

    print(json.dumps({
        "translator_costs":{k:v["cost_usd"] for k,v in translator_meta.items()},
        "evaluation":evaluation,
        "evaluator_cost_usd":eval_cost,
        "total_cost_usd":result["total_cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
