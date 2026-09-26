from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

WRITER_MODEL = "aion-labs/aion-3.5-mini"
EDITOR_MODEL = "openai/gpt-5.6-sol"
FINAL_JUDGE_MODEL = "anthropic/claude-sonnet-5"
SEED = 2026092601

PREMISE = """Late in the afternoon, Deniz hears a faint intermittent ticking sound on the apartment balcony. He cannot find the source right away, so he checks the flowerpots, the railing, and a small hanging ornament. Eventually he notices that the wind makes two little metal rings touch. Deniz turns the sound into a small rhythm game."""

STORY_SPINE = [
    {"density":"brief","beat":"Deniz is playing on the balcony in the late afternoon when he hears one short 'tick' and looks up."},
    {"density":"develop","beat":"The sound comes again and quickly disappears; Deniz looks around and tries to locate it."},
    {"density":"develop","beat":"He first checks the edge of a nearby flowerpot and the small stones on the floor, but a new tick comes from somewhere else."},
    {"density":"develop","beat":"He moves closer to the balcony railing and notices that the sound becomes easier to hear when the wind blows."},
    {"density":"anchor","beat":"One metal ring on a small hanging ornament swings in the wind and touches another ring, making the same tick."},
    {"density":"anchor","beat":"Deniz listens several times and observes that the ticking stops when the wind stops; the narrator does not explain the rule for him."},
    {"density":"anchor","beat":"Instead of pulling or touching the ornament, Deniz gently waves his palm to make a little air current; the rings tick again and the discovery becomes a game."},
    {"density":"anchor","beat":"At the end, Deniz tries his own rhythm: two short ticks, a long pause, then he waits and listens for the wind's reply."},
]

WRITER_SYSTEM = r"""
You are an experienced children's story writer in English.
Write a warm, natural read-aloud story for an EXACTLY 4-year-old child.

You will receive a STORY SPINE. The spine is not prose and not a scene plan.
Preserve its event order and causal relationships, but turn it into natural storytelling rather than mechanically expanding bullet points.

Density labels:
- brief: move quickly and naturally.
- develop: let the beat breathe through concrete action, sensory detail, or short dialogue.
- anchor: this is an important story moment; make the child's action and its consequence especially clear.

Hard rules:
- Deniz must remain the active discoverer.
- Do not add new family/relationship canon.
- Do not turn the story into a science lesson or moral.
- Do not have an adult explain the discovery.
- Keep the language concrete, simple, and read-aloud friendly.
- Avoid narrator mind-reading when observable behavior can show the same thing.
- Do not invent new plot events just to add length.
- Preserve the physical rule: the hanging metal rings make the tick when motion makes them touch.
- Deniz must NOT pull, grab, or directly shake the hanging ornament in the key experiment; he uses air from his palm.
- End with the concrete two-ticks-and-wait rhythm, not a general lesson.

LENGTH:
- Target: about 500 words.
- Preferred range: 475-525 words.
- Hard range: 375-625 words.
- Do not finish below 375 words.

Return only the finished story. First line must be the title.
""".strip()

EDITOR_SYSTEM = r"""
You are an independent children's book editor.
The draft is for an EXACTLY 4-year-old child and will be read aloud.

Do NOT rewrite the entire story. Repair only genuine defects with the smallest meaningful scope.

Check:
- causal or physical inconsistency,
- state/continuity error,
- story-spine violation,
- age mismatch,
- awkward/broken English,
- narrator mind-reading,
- didactic explanation,
- weak/reopened ending,
- hard length range 375-625 words.

For length: if the draft is below 375 words, you may expand ONLY existing beats using observable action, short dialogue, sound/sensory detail, or transitions. Do not add new events, characters, canon, morals, or filler.

Return JSON only:
{
  "repairs":[
    {
      "old":"exact draft text",
      "new":"replacement text",
      "class":"logic_physical|continuity|spine|age_fit|broken_english|mindread|didactic|ending|length",
      "severity":"serious|moderate|minor",
      "why":"brief reason"
    }
  ]
}
""".strip()

FINAL_SYSTEM = r"""
You are the final publication gate for one English read-aloud story for an EXACTLY 4-year-old child.
This is not a literary review. Report only publication-blocking defects.

Blocking classes:
- logic_or_physical_break
- continuity_break
- spine_break
- broken_english
- age_mismatch
- didactic_adult_takeover
- story_structure_break
- visible_generation_artifact

Only critical or serious defects block publication.
Moderate/minor polish does not block.
Return JSON only:
{
  "publication_ready": true,
  "counts":{"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects":[],
  "summary":"one short sentence"
}
""".strip()


def apply_repairs(story, repairs):
    current = story
    applied = []
    skipped = []
    for r in repairs:
        old = str(r.get("old") or "")
        new = str(r.get("new") or "")
        if not old or not new or old == new:
            skipped.append({**r, "skip_reason":"empty_or_noop"})
            continue
        if old not in current:
            skipped.append({**r, "skip_reason":"old_not_found"})
            continue
        current = current.replace(old, new, 1)
        applied.append(r)
    return current, applied, skipped


def main():
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    spine_text = "\n".join(f"{i+1}. [{b['density']}] {b['beat']}" for i,b in enumerate(STORY_SPINE))
    user_prompt = f"PREMISE:\n{PREMISE}\n\nSTORY SPINE:\n{spine_text}\n\nTurn this spine into a natural finished children's story."

    draft, writer_body, writer_payload = call_openrouter(
        api_key=key,
        model=WRITER_MODEL,
        system_prompt=WRITER_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.72,
        max_tokens=None,
        seed=SEED,
        request_class="teacher_story_medium_reasoning",
        structured_output=False,
    )
    draft_words = count_words(draft)

    edit, edit_meta = structured_call(
        api_key=key,
        model=EDITOR_MODEL,
        system=EDITOR_SYSTEM,
        payload={
            "exact_age":4,
            "target_words":500,
            "hard_range":[375,625],
            "story_spine":STORY_SPINE,
            "story":draft,
        },
        seed=SEED+1,
        max_tokens=None,
        request_class="editorial_audit",
    )
    final_story, applied, skipped = apply_repairs(draft, edit.get("repairs") or [])
    final_words = count_words(final_story)

    audit, audit_meta = structured_call(
        api_key=key,
        model=FINAL_JUDGE_MODEL,
        system=FINAL_SYSTEM,
        payload={
            "exact_age":4,
            "hard_range":[375,625],
            "story_spine":STORY_SPINE,
            "story":final_story,
        },
        seed=SEED+2,
        max_tokens=None,
        request_class="editorial_audit",
    )
    counts = audit.get("counts") or {}
    publication_ready = (
        375 <= final_words <= 625
        and int(counts.get("critical",0) or 0) == 0
        and int(counts.get("serious",0) or 0) == 0
        and bool(audit.get("publication_ready"))
    )

    result = {
        "experiment":"aion-3.5-mini-one-story-english-smoke-v1",
        "language":"en",
        "exact_age":4,
        "premise":PREMISE,
        "story_spine":STORY_SPINE,
        "models":{"writer":WRITER_MODEL,"editor":EDITOR_MODEL,"final_acceptance":FINAL_JUDGE_MODEL},
        "seed":SEED,
        "draft":draft,
        "draft_word_count":draft_words,
        "draft_length_pass":375 <= draft_words <= 625,
        "editor_repairs":edit.get("repairs") or [],
        "applied_repairs":applied,
        "skipped_repairs":skipped,
        "final_story":final_story,
        "final_word_count":final_words,
        "final_length_pass":375 <= final_words <= 625,
        "final_acceptance":audit,
        "publication_ready":publication_ready,
        "cost_usd":{
            "writer":float(parse_cost(writer_body).usd or 0.0),
            "editor":float(((edit_meta.get("cost") or {}).get("usd")) or 0.0),
            "final_acceptance":float(((audit_meta.get("cost") or {}).get("usd")) or 0.0),
        },
        "writer_usage":parse_usage(writer_body).model_dump(mode="json"),
        "elapsed_seconds":round(time.perf_counter()-started,3),
        "writer_request_payload":writer_payload,
    }
    result["cost_usd"]["total"] = sum(result["cost_usd"].values())

    out = Path("runs/aion-3.5-mini-one-story-english-smoke")
    out.mkdir(parents=True, exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"draft.txt").write_text(draft+"\n",encoding="utf-8")
    (out/"final.txt").write_text(final_story+"\n",encoding="utf-8")
    (out/"spine.txt").write_text(spine_text+"\n",encoding="utf-8")

    print(json.dumps({
        "draft_words":draft_words,
        "draft_length_pass":375 <= draft_words <= 625,
        "final_words":final_words,
        "final_length_pass":375 <= final_words <= 625,
        "applied_repairs":len(applied),
        "final_counts":counts,
        "publication_ready":publication_ready,
        "cost_usd":result["cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
