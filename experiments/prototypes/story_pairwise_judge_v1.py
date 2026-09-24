from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_scene_plan_smoke import build_labeled_brief
from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import load_yaml, parse_cost, parse_usage
from src.schemas import StorySpec

DEFAULT_JUDGE = "anthropic/claude-sonnet-5"

PAIRWISE_PROMPT = """
You are a blind pairwise quality judge for two complete LUMI stories written from the
same story brief.

You do not know which model produced either story. Do not infer generator identity.
Do not assign 1-5 scalar scores. Compare A and B directly.

Judge these criteria:
- causal_coherence: events, clues, decisions and consequences form the stronger causal chain;
- pacing: the story uses its length efficiently and gives important moments appropriate space;
- age_fit: vocabulary, reasoning, emotional intensity and exposition fit the requested reader;
- prose_quality: sentences, dialogue, transitions and description read naturally;
- economy: less redundant recap, repeated explanation or decorative padding while preserving meaning;
- engagement: curiosity, narrative momentum and reader interest;
- ending: payoff and resolution feel earned, clear and proportionate;
- overall: which story is the better reader-facing artifact for this exact brief.

Allowed winner values: "A", "B", "TIE".

Important:
- Both stories may already be production-acceptable. Pick TIE when differences are genuinely
  too small or trade off without a clear overall advantage.
- Do not prefer a story merely because it is longer.
- Do not penalize length when it is within the supplied acceptable range unless the extra
  length causes pacing or redundancy problems.
- Base every preference on the current texts, not hypothetical repairs.
- Keep reasons concise and concrete.

Return JSON only:
{
  "criteria": {
    "causal_coherence": {"winner": "TIE", "reason": ""},
    "pacing": {"winner": "TIE", "reason": ""},
    "age_fit": {"winner": "TIE", "reason": ""},
    "prose_quality": {"winner": "TIE", "reason": ""},
    "economy": {"winner": "TIE", "reason": ""},
    "engagement": {"winner": "TIE", "reason": ""},
    "ending": {"winner": "TIE", "reason": ""}
  },
  "overall_winner": "TIE",
  "preference_strength": "SMALL",
  "overall_reason": ""
}
""".strip()

CRITERIA = (
    "causal_coherence",
    "pacing",
    "age_fit",
    "prose_quality",
    "economy",
    "engagement",
    "ending",
)


def validate_pairwise(payload: dict[str, Any]) -> dict[str, Any]:
    criteria = payload.get("criteria")
    if not isinstance(criteria, dict):
        raise RuntimeError("pairwise_criteria_missing")

    normalized: dict[str, dict[str, str]] = {}
    for key in CRITERIA:
        row = criteria.get(key)
        if not isinstance(row, dict):
            raise RuntimeError(f"pairwise_criterion_missing:{key}")
        winner = str(row.get("winner") or "").upper()
        if winner not in {"A", "B", "TIE"}:
            raise RuntimeError(f"pairwise_winner_invalid:{key}:{winner}")
        reason = str(row.get("reason") or "").strip()
        if not reason:
            raise RuntimeError(f"pairwise_reason_missing:{key}")
        normalized[key] = {"winner": winner, "reason": reason}

    overall = str(payload.get("overall_winner") or "").upper()
    if overall not in {"A", "B", "TIE"}:
        raise RuntimeError(f"pairwise_overall_invalid:{overall}")

    strength = str(payload.get("preference_strength") or "").upper()
    if strength not in {"SMALL", "CLEAR", "LARGE"}:
        raise RuntimeError(f"pairwise_strength_invalid:{strength}")

    reason = str(payload.get("overall_reason") or "").strip()
    if not reason:
        raise RuntimeError("pairwise_overall_reason_missing")

    return {
        "criteria": normalized,
        "overall_winner": overall,
        "preference_strength": strength,
        "overall_reason": reason,
    }


def call_judge(
    *,
    api_key: str,
    model: str,
    spec: StorySpec,
    story_a: str,
    story_b: str,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    minimum = round(spec.target_words * 0.75)
    maximum = round(spec.target_words * 1.25)
    user = (
        "COMMON STORY BRIEF\n"
        + build_labeled_brief(spec)
        + f"\n\nTARGET WORDS: {spec.target_words}"
        + f"\nACCEPTABLE RANGE: {minimum}-{maximum}"
        + "\n\nCANDIDATE A\n"
        + story_a
        + "\n\nCANDIDATE B\n"
        + story_b
    )
    payload, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=PAIRWISE_PROMPT,
        user_prompt=user,
        temperature=0.0,
        max_tokens=2200,
        seed=None,
        request_class="pairwise_judge",
    )
    return validate_pairwise(payload), {
        "label": label,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "parse_failures": parse_failures,
        "request": {
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
            "max_tokens": request.get("max_tokens"),
        },
    }


def reverse_winner(winner: str) -> str:
    if winner == "A":
        return "B"
    if winner == "B":
        return "A"
    return winner


def normalize_reversed_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "criteria": {
            key: {
                "winner": reverse_winner(row["winner"]),
                "reason": row["reason"],
            }
            for key, row in result["criteria"].items()
        },
        "overall_winner": reverse_winner(result["overall_winner"]),
        "preference_strength": result["preference_strength"],
        "overall_reason": result["overall_reason"],
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--story-a", required=True)
    parser.add_argument("--story-b", required=True)
    parser.add_argument("--judge", default=DEFAULT_JUDGE)
    parser.add_argument("--output", default="runs/pairwise_judge/result.json")
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY")

    spec = StorySpec.model_validate(load_yaml(Path(args.spec)))
    story_a = Path(args.story_a).read_text(encoding="utf-8").strip()
    story_b = Path(args.story_b).read_text(encoding="utf-8").strip()

    forward, forward_meta = call_judge(
        api_key=api_key,
        model=args.judge,
        spec=spec,
        story_a=story_a,
        story_b=story_b,
        label="A_vs_B",
    )
    reverse_raw, reverse_meta = call_judge(
        api_key=api_key,
        model=args.judge,
        spec=spec,
        story_a=story_b,
        story_b=story_a,
        label="B_vs_A",
    )
    reverse = normalize_reversed_result(reverse_raw)

    overall_consistent = forward["overall_winner"] == reverse["overall_winner"]
    criterion_consistency = {
        key: forward["criteria"][key]["winner"] == reverse["criteria"][key]["winner"]
        for key in CRITERIA
    }
    consistent_count = sum(1 for value in criterion_consistency.values() if value)

    if overall_consistent:
        calibrated_winner = forward["overall_winner"]
        calibration_status = "STABLE"
    else:
        calibrated_winner = "INCONCLUSIVE"
        calibration_status = "POSITION_SENSITIVE"

    total_usd = sum(
        float(meta["cost"].get("usd") or 0.0)
        for meta in (forward_meta, reverse_meta)
    )

    result = {
        "protocol": "story-pairwise-judge.v1",
        "judge": args.judge,
        "blind": True,
        "story_a": args.story_a,
        "story_b": args.story_b,
        "forward": forward,
        "reverse_raw": reverse_raw,
        "reverse_normalized_to_original_labels": reverse,
        "calibration": {
            "status": calibration_status,
            "calibrated_winner": calibrated_winner,
            "overall_consistent": overall_consistent,
            "criterion_consistency": criterion_consistency,
            "consistent_criteria": consistent_count,
            "total_criteria": len(CRITERIA),
        },
        "costs": {
            "forward": forward_meta["cost"],
            "reverse": reverse_meta["cost"],
            "total_usd": round(total_usd, 9),
        },
        "request_evidence": {
            "forward": forward_meta,
            "reverse": reverse_meta,
        },
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
