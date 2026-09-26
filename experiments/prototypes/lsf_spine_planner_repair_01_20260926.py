from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.lsf_spine_planner_qualification_01_20260926 import (
    FIDELITY_GATE,
    FIDELITY_SYSTEM,
    PRIMARY_AUDITOR,
    SECONDARY_AUDITOR,
    TRANSLATION_SYSTEM,
    TRANSLATOR,
    audit_story,
    meta_cost,
)
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.generate import call_openrouter, count_words, parse_cost, parse_usage

FIXTURE = Path("experiments/fixtures/lsf_spine_planner_repair_01_20260926.json")
OUT = Path("runs/lsf-spine-planner-repair-01/result.json")

REPAIR_MODEL = "openai/gpt-5.6-sol"
SEED = 2026092751

REPAIR_SYSTEM = r"""
You are a bounded local repair editor for an accepted children's story plan.

You receive:
- authoritative StoryIntent and Context Packet,
- validated spine,
- finished English story,
- one confirmed serious/critical defect with exact scope.

Your task is NOT to rewrite or improve the story.
Repair only the smallest exact span necessary to remove the confirmed defect.

Rules:
- Preserve all events, event order, causality, dialogue, tone, length, and ending.
- Do not add a new event, character, object, solution, canon fact, or moral.
- Do not alter the validated spine.
- If the defect is an unsupported durable visual/object attribute, remove only that unsupported attribute while preserving the harmless action.
- Return an exact substring from the story as "old".
- "new" must be the minimum replacement.
- One repair only.

Return JSON only:
{
  "repair": {
    "scope":"sentence|block",
    "old":"exact substring from story",
    "new":"minimal replacement",
    "class":"canon_integrity|physical_feasibility|causal_logic|state_continuity|other",
    "why":"brief"
  }
}
""".strip()


def apply_repair(story: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    repair = payload.get("repair")
    if not isinstance(repair, dict):
        raise RuntimeError("repair_missing")
    old = str(repair.get("old") or "")
    new = str(repair.get("new") or "")
    if not old or not new or old == new:
        raise RuntimeError("repair_invalid_or_noop")
    if old not in story:
        raise RuntimeError("repair_old_not_found")
    if story.count(old) != 1:
        raise RuntimeError("repair_old_not_unique")
    return story.replace(old, new, 1), repair


def main():
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.perf_counter()

    repair_payload, repair_meta = structured_call(
        api_key=key,
        model=REPAIR_MODEL,
        system=REPAIR_SYSTEM,
        payload={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
            "validated_plan": fixture["validated_plan"],
            "story": fixture["english_story"],
            "confirmed_defect": fixture["defect"],
            "exact_target_hint": fixture["exact_target_hint"],
        },
        seed=SEED,
        max_tokens=1200,
        request_class="editorial_audit",
    )

    repaired_story, repair = apply_repair(fixture["english_story"], repair_payload)
    word_count = count_words(repaired_story)
    length_pass = 375 <= word_count <= 625

    primary_findings, primary_meta = audit_story(
        api_key=key,
        model=PRIMARY_AUDITOR,
        fixture={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
        },
        plan=fixture["validated_plan"],
        story=repaired_story,
        seed=SEED + 1,
    )
    secondary_findings, secondary_meta = audit_story(
        api_key=key,
        model=SECONDARY_AUDITOR,
        fixture={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
        },
        plan=fixture["validated_plan"],
        story=repaired_story,
        seed=SEED + 2,
    )

    english_pass = (
        length_pass
        and not primary_findings
        and not secondary_findings
    )

    translation = None
    translator_cost = 0.0
    translator_usage = None
    fidelity_result = None
    fidelity_meta = None
    fidelity_pass = False

    if english_pass:
        translation, trans_body, _ = call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=repaired_story,
            temperature=0.2,
            max_tokens=None,
            seed=SEED + 3,
            request_class="translation",
            structured_output=False,
        )
        translator_cost = float(parse_cost(trans_body).usd or 0.0)
        translator_usage = parse_usage(trans_body).model_dump(mode="json")

        fidelity_result, fidelity_meta = structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language":"en",
                "target_language":"tr",
                "exact_age":4,
                "source_story":repaired_story,
                "translation":translation,
            },
            seed=SEED + 4,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        blocking = [
            x for x in (fidelity_result.get("findings") or [])
            if str(x.get("severity") or "") in {"serious","critical"}
        ]
        fidelity_pass = bool(fidelity_result.get("fidelity_clean")) and not blocking

    costs = {
        "repair": meta_cost(repair_meta),
        "primary_reaudit": meta_cost(primary_meta),
        "secondary_reaudit": meta_cost(secondary_meta),
        "translator": translator_cost,
        "fidelity_gate": meta_cost(fidelity_meta),
    }
    costs["total"] = sum(costs.values())

    result = {
        "schema_version":"lsf-spine-planner-repair-01-result.v1",
        "source_run_id":fixture["source_run_id"],
        "profile":fixture["profile"],
        "repair_model":REPAIR_MODEL,
        "confirmed_defect":fixture["defect"],
        "repair":repair,
        "repaired_story":repaired_story,
        "english_word_count":word_count,
        "length_pass":length_pass,
        "primary_findings":primary_findings,
        "secondary_findings":secondary_findings,
        "english_pass":english_pass,
        "translation_model":TRANSLATOR,
        "turkish_translation":translation,
        "fidelity_model":FIDELITY_GATE,
        "fidelity_result":fidelity_result,
        "fidelity_pass":fidelity_pass,
        "publication_ready":english_pass and fidelity_pass,
        "cost_usd":costs,
        "translator_usage":translator_usage,
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (OUT.parent/"english.txt").write_text(repaired_story+"\n",encoding="utf-8")
    if translation:
        (OUT.parent/"turkish.txt").write_text(translation+"\n",encoding="utf-8")

    print(json.dumps({
        "repair":repair,
        "english_word_count":word_count,
        "length_pass":length_pass,
        "primary_findings":primary_findings,
        "secondary_findings":secondary_findings,
        "english_pass":english_pass,
        "fidelity_pass":fidelity_pass,
        "publication_ready":result["publication_ready"],
        "cost_usd":costs,
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
