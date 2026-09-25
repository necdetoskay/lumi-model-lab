from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import call_openrouter, parse_cost

TRANSLATOR_MODEL = "openai/gpt-5.6-luna"
VERIFIER_MODEL = "anthropic/claude-haiku-4.5"

TRANSLATOR_PROMPT = """
You are the final Turkish literary localization stage for a production LUMI story.

Translate the complete English story into natural, fluent Turkish for the specified exact reader age.

Hard invariants:
- Preserve every event, fact, clue, causal dependency, character action, relationship, and ending state.
- Preserve uncertainty exactly. Rumors, hypotheses, unknowns, doubts and best-supported explanations must NOT become facts.
- Do not add new lore, scenes, explanations, morals, dialogue, danger, objects, characters or outcomes.
- Do not omit story-relevant details.
- Preserve names and canonical entity identity.
- Preserve age-appropriate emotional intensity and reading difficulty while making the Turkish idiomatic.
- Translate the title as well.
- Do not mention translation, benchmarks, prompts, models, tests, or these instructions.
- Output ONLY the finished Turkish story, beginning with its Turkish title, then a blank line, then the story.
""".strip()

VERIFIER_PROMPT = """
You are a bilingual production translation gate for LUMI.
Compare an accepted English source story with its Turkish finalization.

Score each 1-5:
- semantic_fidelity
- fact_preservation
- uncertainty_preservation
- character_and_entity_preservation
- age_tone_preservation
- turkish_naturalness

A score of 4 means solid production quality; 5 means exceptional.

Critical failure means any material addition/omission, changed causal outcome, changed canon fact,
rumor/hypothesis/unknown upgraded to fact, altered character decision, or materially wrong target-age tone.

Return JSON only:
{
  "scores": {
    "semantic_fidelity": 1,
    "fact_preservation": 1,
    "uncertainty_preservation": 1,
    "character_and_entity_preservation": 1,
    "age_tone_preservation": 1,
    "turkish_naturalness": 1
  },
  "critical_failure": false,
  "issues": [],
  "repair_instructions": []
}
""".strip()


def verify(api_key: str, source: str, translated: str, age: int) -> tuple[dict[str, Any], dict[str, Any]]:
    payload, body, _, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=VERIFIER_MODEL,
        system_prompt=VERIFIER_PROMPT,
        user_prompt=json.dumps(
            {
                "exact_reader_age": age,
                "english_source": source,
                "turkish_translation": translated,
            },
            ensure_ascii=False,
        ),
        temperature=0.0,
        max_tokens=None,
        seed=20260925 + age,
        request_class="judge",
    )
    scores = payload.get("scores") or {}
    required = (
        "semantic_fidelity",
        "fact_preservation",
        "uncertainty_preservation",
        "character_and_entity_preservation",
        "age_tone_preservation",
        "turkish_naturalness",
    )
    minimum = min((int(scores.get(k, 0)) for k in required), default=0)
    average = sum(int(scores.get(k, 0)) for k in required) / len(required)
    accepted = (
        minimum >= 4
        and average >= 4.0
        and payload.get("critical_failure") is False
    )
    meta = {
        "accepted": accepted,
        "minimum": minimum,
        "average": round(average, 3),
        "verdict": payload,
        "parse_failures": parse_failures,
        "cost": parse_cost(body).model_dump(mode="json"),
    }
    return payload, meta


def translate(api_key: str, source: str, age: int, repair_feedback: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    prompt = (
        f"Exact reader age: {age}\n\n"
        "Translate this accepted English story into Turkish:\n\n"
        + source
    )
    if repair_feedback:
        prompt += (
            "\n\nThe previous Turkish version failed the bilingual fidelity gate. "
            "Correct these issues without changing the source story:\n- "
            + "\n- ".join(repair_feedback)
        )
    text, body, _ = call_openrouter(
        api_key=api_key,
        model=TRANSLATOR_MODEL,
        system_prompt=TRANSLATOR_PROMPT,
        user_prompt=prompt,
        temperature=0.25 if not repair_feedback else 0.15,
        max_tokens=None,
        seed=20260925 + age + (1000 if repair_feedback else 0),
        request_class="scene_story",
        structured_output=False,
    )
    return text.strip(), parse_cost(body).model_dump(mode="json")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--age", required=True, type=int)
    parser.add_argument("--output", required=True)
    parser.add_argument("--meta", required=True)
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    source_path = Path(args.source)
    source = source_path.read_text(encoding="utf-8").strip()
    attempts: list[dict[str, Any]] = []

    translated, translation_cost = translate(api_key, source, args.age)
    verdict, verification = verify(api_key, source, translated, args.age)
    attempts.append(
        {
            "attempt": 1,
            "translation_cost": translation_cost,
            "verification": verification,
        }
    )

    if not verification["accepted"]:
        feedback = [
            str(x)
            for x in (verdict.get("repair_instructions") or verdict.get("issues") or [])
            if str(x).strip()
        ]
        translated, translation_cost = translate(api_key, source, args.age, feedback)
        verdict, verification = verify(api_key, source, translated, args.age)
        attempts.append(
            {
                "attempt": 2,
                "translation_cost": translation_cost,
                "verification": verification,
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(translated + "\n", encoding="utf-8")

    meta = {
        "protocol": "story-v5-final-tr-translation.v1",
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "translation_sha256": hashlib.sha256(translated.encode("utf-8")).hexdigest(),
        "exact_reader_age": args.age,
        "translator_model": TRANSLATOR_MODEL,
        "verifier_model": VERIFIER_MODEL,
        "accepted": bool(verification["accepted"]),
        "final_verification": verification,
        "attempts": attempts,
    }
    Path(args.meta).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "translation_accepted": meta["accepted"],
        "translation_minimum": verification["minimum"],
        "translation_average": verification["average"],
        "output": str(output),
        "meta": args.meta,
    }, ensure_ascii=False, indent=2), flush=True)

    if not meta["accepted"]:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
