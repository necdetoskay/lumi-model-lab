from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_scene_plan_smoke import (
    build_labeled_brief,
    evaluate_plan_candidate,
    parse_json_object,
    run as run_plan_smoke,
)
from src.generate import call_openrouter, count_words, load_yaml, parse_cost, parse_usage
from src.generator_benchmark_v2 import repeated_ngram_ratio
from src.model_registry import require_judge_runtime_profile, require_qualification_runtime_profile
from src.openrouter_jev import (
    call_openrouter_jev,
    choice_question,
    choice_value,
    load_jev_profile,
    noul_probability,
    noul_question,
)
from src.schemas import StorySpec

SCENE_WRITER_PROMPT = Path("prompts/story_scene_writer_en_v1.md")
SCENE_REPAIR_PROMPT = Path("prompts/story_scene_repair_en_v1.md")
SCENE_WORD_BUDGET_REPAIR_PROMPT = Path("prompts/story_scene_word_budget_repair_en_v1.md")
PLAN_REPAIR_PROMPT = Path("prompts/story_scene_plan_repair_en_v1.md")
FINAL_JUDGE_PROMPT = Path("prompts/story_final_judge_en_v1.md")
FINAL_TARGETED_REPAIR_PROMPT = Path("prompts/story_final_targeted_repair_en_v1.md")
TOTAL_STORY_MIN_RATIO = 0.75
TOTAL_STORY_MAX_RATIO = 1.25
SCENE_WORD_BUDGET_MIN_RATIO = 0.80
SCENE_WORD_BUDGET_MAX_RATIO_TOLERANCE = 0.25
SCENE_WORD_BUDGET_MAX_ABSOLUTE_SLACK = 20
DEFAULT_SPEC = Path("data/specifications/benchmark_en/01_exploration_mystery.yaml")
GENERATION_PROTOCOL_VERSION = "english-story-production.v3"
EVALUATION_PROTOCOL_VERSION = "english-story-evaluation.v1"

FINAL_CRITERIA = (
    "instruction_following",
    "coherence",
    "character_consistency",
    "age_appropriateness",
    "creativity",
    "style_quality",
    "continuity",
    "ending_quality",
)

SCENE_LIST_FIELDS = (
    "knowledge_gained",
    "facts_established",
    "clues_added",
    "objects_changed",
    "relationships_changed",
    "threads_opened",
    "threads_resolved",
)


def allocate_scene_budgets(target_words: int) -> list[int]:
    weights = (0.13, 0.155, 0.17, 0.17, 0.205, 0.17)
    budgets = [round(target_words * weight) for weight in weights]
    budgets[-1] += target_words - sum(budgets)
    return budgets


def sum_plan_stage_cost_usd(cost_history: list[dict[str, Any]]) -> float:
    total = 0.0
    for costs in cost_history:
        for value in costs.values():
            if isinstance(value, dict):
                usd = value.get("usd")
                if isinstance(usd, (int, float)):
                    total += float(usd)
            elif isinstance(value, (int, float)):
                total += float(value)
    return total


def scene_word_budget_bounds(
    target_words: int,
    *,
    min_ratio: float = SCENE_WORD_BUDGET_MIN_RATIO,
    max_ratio_tolerance: float = SCENE_WORD_BUDGET_MAX_RATIO_TOLERANCE,
    max_absolute_slack: int = SCENE_WORD_BUDGET_MAX_ABSOLUTE_SLACK,
) -> tuple[int, int]:
    if target_words <= 0:
        raise ValueError("target_words must be positive")
    if not 0 < min_ratio <= 1:
        raise ValueError("min_ratio must be within (0, 1]")
    if max_ratio_tolerance < 0:
        raise ValueError("max_ratio_tolerance must be non-negative")
    if max_absolute_slack < 0:
        raise ValueError("max_absolute_slack must be non-negative")
    minimum = max(1, round(target_words * min_ratio))
    maximum_slack = max(
        round(target_words * max_ratio_tolerance),
        max_absolute_slack,
    )
    return minimum, target_words + maximum_slack


def validate_scene_envelope(
    envelope: dict[str, Any],
    *,
    target_words: int,
) -> tuple[list[str], int]:
    errors: list[str] = []
    prose = envelope.get("prose")
    if not isinstance(prose, str) or not prose.strip():
        return ["prose_missing"], 0

    word_count = count_words(prose)
    minimum, maximum = scene_word_budget_bounds(target_words)
    if word_count < minimum:
        errors.append(f"below_scene_word_budget:{word_count}<{minimum}")
    if word_count > maximum:
        errors.append(f"above_scene_word_budget:{word_count}>{maximum}")

    delta = envelope.get("state_delta")
    if not isinstance(delta, dict):
        errors.append("state_delta_missing")
        return errors, word_count

    for field in ("location", "character_goal", "handoff_state"):
        value = delta.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"state_delta_{field}_missing")

    for field in SCENE_LIST_FIELDS:
        value = delta.get(field)
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            errors.append(f"state_delta_{field}_invalid")

    return errors, word_count


def build_scene_jev_questions(scene_index: int, is_final: bool) -> dict[str, dict[str, Any]]:
    questions = {
        "continues_prior_state": noul_question(
            "Does this scene begin from and remain compatible with the accepted prior story state?",
            true_criteria="The scene continues the prior state without reset or unexplained jump.",
            false_criteria="The scene resets, contradicts, or jumps away from the prior state.",
        ),
        "scene_purpose_obeyed": noul_question(
            f"Does Scene {scene_index} fulfill its declared SceneContract purpose without replacing it with a different plot?",
            true_criteria="The scene materially fulfills its declared purpose.",
            false_criteria="The scene ignores or replaces its declared purpose.",
        ),
        "no_unexplained_dependency": noul_question(
            "Are all important facts, objects, locations, clues, and inferences in this scene supported by prior evidence or the current SceneContract?",
            true_criteria="Important dependencies are established before use.",
            false_criteria="The scene depends on an unexplained element or unjustified inference.",
        ),
        "no_contradiction": noul_question(
            "Is the scene free of contradictions with the StoryContract, SceneGraph, and ContinuityLedger?",
            true_criteria="No material contradiction is present.",
            false_criteria="At least one material contradiction is present.",
        ),
        "goal_preserved": noul_question(
            "Does the protagonist's central goal and motivation remain consistent in this scene?",
            true_criteria="The central goal remains stable and motivates actions.",
            false_criteria="The central goal disappears, changes without cause, or stops motivating actions.",
        ),
        "no_future_leakage": noul_question(
            (
                "Does Scene 5 deliver the decisive payoff while avoiding Scene 6's aftermath, closure, and future-hook material?"
                if scene_index == 5
                else (
                    "Does the final scene resolve consequences without opening a new main problem beyond the bounded future-discovery hook?"
                    if is_final
                    else "Does the scene avoid performing decisive events reserved for later scenes?"
                )
            ),
            true_criteria=(
                "Scene 5 contains the decisive payoff but leaves aftermath, closure, and the future hook to Scene 6."
                if scene_index == 5
                else (
                    "The final scene closes the main problem and leaves at most the allowed bounded hook."
                    if is_final
                    else "Later-scene events and the decisive payoff remain protected."
                )
            ),
            false_criteria=(
                "Scene 5 consumes Scene 6's aftermath, closure, or future-hook work."
                if scene_index == 5
                else (
                    "The final scene opens a new main problem or fails to close the existing one."
                    if is_final
                    else "The scene leaks or performs a later-scene event too early."
                )
            ),
        ),
        "handoff_valid": noul_question(
            "Does the scene's handoff_state create a concrete, coherent state that the next scene can inherit?"
            if not is_final
            else "Does the final scene's handoff_state accurately describe the resolved ending state?",
            true_criteria="The handoff is concrete and consistent with the scene outcome.",
            false_criteria="The handoff is vague, contradictory, or unsupported.",
        ),
    }
    questions["next_action"] = choice_question(
        "Choose the safest bounded action after reviewing this scene.",
        {
            "CONTINUE": "The scene is coherent enough to continue.",
            "TARGETED_REPAIR": "A local continuity defect should be repaired in this scene.",
            "ESCALATE": "The scene is ambiguous or broadly risky and requires a stronger judge.",
        },
    )
    return questions


def summarize_jev(
    body: dict[str, Any],
    *,
    question_ids: list[str],
) -> dict[str, Any]:
    profile = load_jev_profile()
    answers = body.get("answers") or {}
    probabilities = {
        key: noul_probability(answers[key])
        for key in question_ids
    }
    below = {
        key: value
        for key, value in probabilities.items()
        if value < profile.positive_probability_threshold
    }
    next_action, confidence = choice_value(answers["next_action"])
    return {
        "mode": profile.mode,
        "threshold": profile.positive_probability_threshold,
        "positive_probabilities": probabilities,
        "below_threshold": below,
        "next_action": next_action,
        "next_action_confidence": confidence,
        "shadow_signal": (
            "CONTINUE"
            if not below and next_action == "CONTINUE"
            else "REVIEW"
        ),
        "resolved_model": body.get("model"),
        "provider": body.get("provider"),
        "usage": body.get("usage") or {},
    }


def jev_targeted_repair_reasons(jev: dict[str, Any]) -> list[str]:
    threshold = float(jev.get("threshold") or 0.0)
    reasons = [
        f"jev:{metric}:{float(probability):.3f}<{threshold:.3f}"
        for metric, probability in sorted((jev.get("below_threshold") or {}).items())
    ]
    if jev.get("next_action") == "TARGETED_REPAIR":
        reasons.append("jev:next_action:TARGETED_REPAIR")
    return reasons


def jev_needs_targeted_repair(jev: dict[str, Any]) -> bool:
    return bool(jev_targeted_repair_reasons(jev))


def jev_requires_final_escalation(jev: dict[str, Any]) -> bool:
    return bool(jev.get("below_threshold")) or jev.get("next_action") in {
        "TARGETED_REPAIR",
        "ESCALATE",
    }


def evaluate_scene_jev(
    *,
    api_key: str,
    scene_index: int,
    story_contract: dict[str, Any],
    scene_contract: dict[str, Any],
    next_scene: dict[str, Any] | None,
    ledger: list[dict[str, Any]],
    envelope: dict[str, Any],
) -> dict[str, Any]:
    scene_questions = build_scene_jev_questions(
        scene_index,
        scene_index == 6,
    )
    body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "English LUMI scene continuity evaluation.",
            "story_contract": story_contract,
            "scene_contract": scene_contract,
            "next_scene_contract": next_scene,
            "prior_ledger": ledger,
            "current_scene": envelope,
        },
        questions=scene_questions,
    )
    return summarize_jev(
        body,
        question_ids=[
            key for key in scene_questions
            if key != "next_action"
        ],
    )


class StructuredJsonCallError(RuntimeError):
    def __init__(self, message: str, trace: dict[str, Any]):
        super().__init__(message)
        self.trace = trace


def call_structured_json_with_retry(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int | None,
    seed: int | None,
    request_class: str,
    max_parse_attempts: int = 2,
    forbid_output_token_limit: bool = False,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    parse_failures: list[dict[str, Any]] = []
    last_text: str | None = None
    last_body: dict[str, Any] | None = None
    last_request: dict[str, Any] | None = None
    for parse_attempt in range(1, max_parse_attempts + 1):
        effective_prompt = user_prompt
        effective_temperature = temperature
        effective_seed = seed
        if parse_attempt > 1:
            effective_prompt += (
                "\n\nFORMAT RECOVERY: The previous response was malformed or incomplete JSON. "
                "Return one complete JSON object only. Do not use markdown fences, commentary, "
                "or trailing text. Close every string, array, and object."
            )
            effective_temperature = min(temperature, 0.20)
            if seed is not None:
                effective_seed = seed + 9000 + parse_attempt

        text, body, request = call_openrouter(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_prompt=effective_prompt,
            temperature=effective_temperature,
            max_tokens=max_tokens,
            seed=effective_seed,
            request_class=request_class,
            structured_output=True,
            forbid_output_token_limit=forbid_output_token_limit,
        )
        last_text = text
        last_body = body
        last_request = request
        try:
            payload = parse_json_object(text)
        except (RuntimeError, json.JSONDecodeError) as exc:
            choice = (body.get("choices") or [{}])[0]
            finish_reason = choice.get("finish_reason")
            parse_failures.append(
                {
                    "parse_attempt": parse_attempt,
                    "error": str(exc),
                    "response_chars": len(text),
                    "raw_response": text,
                    "finish_reason": finish_reason,
                    "raw_usage": body.get("usage") or {},
                    "usage": parse_usage(body).model_dump(mode="json"),
                    "cost": parse_cost(body).model_dump(mode="json"),
                }
            )
            if finish_reason in {"length", "max_tokens"}:
                raise StructuredJsonCallError(
                    "STRUCTURED_JSON_RESPONSE_TRUNCATED",
                    {
                        "stage": "structured_json_parse",
                        "model": model,
                        "request_class": request_class,
                        "request": request,
                        "raw_response": text,
                        "body": body,
                        "raw_usage": body.get("usage") or {},
                        "usage": parse_usage(body).model_dump(mode="json"),
                        "cost": parse_cost(body).model_dump(mode="json"),
                        "parse_failures": parse_failures,
                        "retry_suppressed": True,
                        "retry_suppressed_reason": "finish_reason_length",
                    },
                ) from exc
            if parse_attempt >= max_parse_attempts:
                last_cost = parse_cost(last_body or {}).model_dump(mode="json")
                raise StructuredJsonCallError(
                    "STRUCTURED_JSON_RESPONSE_RETRY_EXHAUSTED",
                    {
                        "stage": "structured_json_parse",
                        "model": model,
                        "request_class": request_class,
                        "request": last_request,
                        "raw_response": last_text,
                        "body": last_body,
                        "raw_usage": (last_body or {}).get("usage") or {},
                        "usage": parse_usage(last_body or {}).model_dump(mode="json"),
                        "cost": last_cost,
                        "parse_failures": parse_failures,
                    },
                ) from exc
            continue
        return payload, body, request, parse_failures

    raise StructuredJsonCallError(
        "STRUCTURED_JSON_RESPONSE_RETRY_EXHAUSTED",
        {
            "stage": "structured_json_parse",
            "model": model,
            "request_class": request_class,
            "request": last_request,
            "raw_response": last_text,
            "body": last_body,
            "raw_usage": (last_body or {}).get("usage") or {},
            "usage": parse_usage(last_body or {}).model_dump(mode="json"),
            "cost": parse_cost(last_body or {}).model_dump(mode="json"),
            "parse_failures": parse_failures,
        },
    )


def repair_scene_for_jev(
    *,
    api_key: str,
    model: str,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scene_contract: dict[str, Any],
    next_scene: dict[str, Any] | None,
    envelope: dict[str, Any],
    jev: dict[str, Any],
    target_words: int,
    seed: int,
    repair_index: int,
    extra_reasons: list[str] | None = None,
) -> tuple[dict[str, Any], list[str], int, dict[str, Any]]:
    repair_reasons = jev_targeted_repair_reasons(jev)
    repair_reasons.extend(extra_reasons or [])
    repair_input = json.dumps(
        {
            "story_contract": plan["story_contract"],
            "scene_graph": plan["scenes"],
            "continuity_ledger": ledger,
            "scene_contract": scene_contract,
            "next_scene_guard": next_scene,
            "target_words": target_words,
            "repair_reasons": repair_reasons,
            "jev_continuity_evidence": {
                "threshold": jev.get("threshold"),
                "positive_probabilities": jev.get("positive_probabilities"),
                "below_threshold": jev.get("below_threshold"),
                "next_action": jev.get("next_action"),
                "next_action_confidence": jev.get("next_action_confidence"),
            },
            "current_scene_envelope": envelope,
        },
        ensure_ascii=False,
        indent=2,
    )
    attempt_started = time.perf_counter()
    repaired, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=repair_input,
        temperature=0.25,
        max_tokens=None,
        seed=seed + repair_index,
        request_class="scene_repair",
    )
    errors, word_count = validate_scene_envelope(
        repaired,
        target_words=target_words,
    )
    attempt = {
        "kind": f"jev_repair_{repair_index}",
        "elapsed_seconds": round(time.perf_counter() - attempt_started, 3),
        "repair_reasons": repair_reasons,
        "structured_parse_retries": parse_failures,
        "errors": errors,
        "word_count": word_count,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
    }
    return repaired, errors, word_count, attempt


def build_whole_story_jev_questions() -> dict[str, dict[str, Any]]:
    checks = {
        "causal_chain": (
            "Does the final six-scene story form one causal chain from initial goal through solution and consequences?",
            "The full story forms one causal chain.",
            "The story contains disconnected or unjustified narrative jumps.",
        ),
        "goal_continuity": (
            "Does the protagonist keep a coherent central goal and motivation across the full story?",
            "The protagonist's goal is coherent throughout.",
            "The protagonist's goal changes or disappears without narrative cause.",
        ),
        "clue_solution_progression": (
            "Is the final solution earned by clues, observations, and decisions established before the payoff?",
            "The solution is earned by prior evidence.",
            "The solution depends on coincidence, retroactive explanation, or missing setup.",
        ),
        "no_contradictions": (
            "Using the ContinuityLedger as canonical state, is the assembled story free of direct factual contradictions? Treat added descriptive detail or elaboration as non-contradictory unless two claims cannot both be true.",
            "No direct factual contradiction exists between canonical scene states and the assembled story.",
            "At least two factual claims cannot both be true, or the story directly conflicts with canonical ledger state.",
        ),
        "no_repeated_event": (
            "Does each scene advance the story rather than repeating an event, discovery, or narrative function already completed?",
            "Scenes progress without redundant event repetition.",
            "At least one scene repeats an already-completed event or narrative function.",
        ),
        "ending_consistency": (
            "Does the ending follow from Scene 5's payoff, resolve the central problem, and leave only the allowed bounded future hook?",
            "The ending is a coherent consequence of the payoff.",
            "The ending contradicts the payoff, leaves the main problem unresolved, or opens a new main problem.",
        ),
    }
    questions = {
        key: noul_question(
            instructions,
            true_criteria=yes,
            false_criteria=no,
        )
        for key, (instructions, yes, no) in checks.items()
    }
    questions["next_action"] = choice_question(
        "Choose the safest bounded action for the completed English story.",
        {
            "CONTINUE": "The story is coherent enough for final literary judging.",
            "TARGETED_REPAIR": "A local scene repair is indicated.",
            "ESCALATE": "The story requires stronger semantic review.",
        },
    )
    return questions


def validate_final_judge(payload: dict[str, Any]) -> dict[str, Any]:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("Final Haiku judge scores missing.")
    normalized: dict[str, int] = {}
    for criterion in FINAL_CRITERIA:
        score = scores.get(criterion)
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise RuntimeError(f"Invalid final judge score for {criterion}: {score!r}")
        normalized[criterion] = score

    critical = payload.get("critical_failures")
    repair_targets = payload.get("repair_targets")
    if not isinstance(critical, list):
        raise RuntimeError("Final judge critical_failures must be a list.")
    if not isinstance(repair_targets, list):
        raise RuntimeError("Final judge repair_targets must be a list.")

    normalized_targets: list[dict[str, Any]] = []
    for target in repair_targets:
        if not isinstance(target, dict):
            raise RuntimeError("Final judge repair target must be an object.")
        scene = target.get("scene")
        if (
            not isinstance(scene, int)
            or isinstance(scene, bool)
            or not 1 <= scene <= 6
        ):
            raise RuntimeError(
                f"Invalid final judge repair target scene: {scene!r}"
            )
        repair_scene = target.get("repair_scene", scene)
        if (
            not isinstance(repair_scene, int)
            or isinstance(repair_scene, bool)
            or not 1 <= repair_scene <= 6
        ):
            raise RuntimeError(
                "Invalid final judge repair target repair_scene: "
                f"{repair_scene!r}"
            )
        issue = str(target.get("issue") or "").strip()
        if not issue:
            raise RuntimeError("Final judge repair target issue must be non-empty.")
        normalized_targets.append(
            {
                "scene": scene,
                "repair_scene": repair_scene,
                "issue": issue,
            }
        )

    average = round(sum(normalized.values()) / len(normalized), 3)
    minimum = min(normalized.values())
    return {
        "scores": normalized,
        "average": average,
        "minimum": minimum,
        "critical_failures": critical,
        "repair_targets": normalized_targets,
        "summary": str(payload.get("summary") or ""),
        "accepted": average >= 4.0 and minimum >= 3 and not critical,
    }


def scene_request_payload(
    *,
    spec: StorySpec,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scene_contract: dict[str, Any],
    next_scene: dict[str, Any] | None,
    previous_prose: str,
    target_words: int,
    plan_review: dict[str, Any],
) -> str:
    return json.dumps(
        {
            "story_brief": {
                "age_range": [spec.age_min, spec.age_max],
                "protagonist": spec.protagonist,
                "setting": spec.setting,
                "theme": spec.theme,
                "premise": spec.premise,
                "constraints": spec.constraints,
            },
            "story_contract": plan["story_contract"],
            "scene_graph": plan["scenes"],
            "continuity_ledger": ledger,
            "previous_scene_prose": previous_prose,
            "current_scene_contract": scene_contract,
            "next_scene_guard": next_scene,
            "target_words": target_words,
            "allowed_word_range": [
                round(target_words * 0.85),
                round(target_words * 1.15),
            ],
            "plan_review_risks": plan_review,
        },
        ensure_ascii=False,
        indent=2,
    )


SCENE_WORD_BUDGET_ERROR_PREFIXES = (
    "below_scene_word_budget:",
    "above_scene_word_budget:",
    "word_budget_repair_preferred_range_miss:",
    "word_budget_repair_required_range_miss:",
)


def is_scene_word_budget_error(error: str) -> bool:
    return any(
        error.startswith(prefix)
        for prefix in SCENE_WORD_BUDGET_ERROR_PREFIXES
    )


def partition_scene_validation_errors(
    errors: list[str],
) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    word_budget_warnings: list[str] = []
    for error in errors:
        if is_scene_word_budget_error(error):
            word_budget_warnings.append(error)
        else:
            blocking.append(error)
    return blocking, word_budget_warnings


def only_word_budget_errors(errors: list[str]) -> bool:
    return bool(errors) and all(
        is_scene_word_budget_error(error)
        for error in errors
    )


def repair_scene_word_budget(
    *,
    api_key: str,
    model: str,
    envelope: dict[str, Any],
    target_words: int,
    seed: int,
    repair_index: int,
) -> tuple[dict[str, Any], list[str], int, dict[str, Any]]:
    current_prose = str(envelope.get("prose") or "")
    current_words = count_words(current_prose)
    hard_min, hard_max = scene_word_budget_bounds(target_words)
    preferred_slack = max(round(target_words * 0.08), 8)
    preferred_min = max(hard_min + 1, target_words - preferred_slack)
    preferred_max = min(hard_max - 1, target_words + preferred_slack)
    mode = "COMPRESS" if current_words > hard_max else "EXPAND"

    if repair_index <= 1:
        required_min = preferred_min
        required_max = preferred_max
        aggressiveness = "normal"
    elif mode == "COMPRESS":
        required_min = max(hard_min + 5, round(target_words * 0.88))
        required_max = min(hard_max - 5, round(target_words * 0.98))
        aggressiveness = "high"
    else:
        required_min = max(hard_min + 5, round(target_words * 1.02))
        required_max = min(hard_max - 5, round(target_words * 1.10))
        aggressiveness = "high"

    repair_input = json.dumps(
        {
            "mode": mode,
            "aggressiveness": aggressiveness,
            "repair_index": repair_index,
            "previous_attempt_missed_target": repair_index > 1,
            "target_words": target_words,
            "hard_word_range": [hard_min, hard_max],
            "required_word_range": [required_min, required_max],
            "current_word_count": current_words,
            "minimum_words_to_remove": (
                max(0, current_words - required_max)
                if mode == "COMPRESS"
                else 0
            ),
            "minimum_words_to_add": (
                max(0, required_min - current_words)
                if mode == "EXPAND"
                else 0
            ),
            "maximum_output_words": required_max,
            "minimum_output_words": required_min,
            "maximum_sentences": max(8, round(required_max / 22)),
            "immutable_state_delta": envelope.get("state_delta"),
            "current_prose": current_prose,
        },
        ensure_ascii=False,
        indent=2,
    )
    attempt_started = time.perf_counter()
    payload, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_WORD_BUDGET_REPAIR_PROMPT.read_text(
            encoding="utf-8"
        ).strip(),
        user_prompt=repair_input,
        temperature=(0.0 if repair_index == 1 else 0.15),
        max_tokens=None,
        seed=seed + repair_index,
        request_class="scene_repair",
    )
    repaired_prose = payload.get("prose")
    if not isinstance(repaired_prose, str) or not repaired_prose.strip():
        repaired = {
            "prose": "",
            "state_delta": envelope.get("state_delta"),
        }
        errors = ["word_budget_repair_prose_missing"]
        word_count = 0
    else:
        repaired = {
            "prose": repaired_prose.strip(),
            "state_delta": envelope.get("state_delta"),
        }
        errors, word_count = validate_scene_envelope(
            repaired,
            target_words=target_words,
        )
        if not required_min <= word_count <= required_max:
            errors.append(
                "word_budget_repair_required_range_miss:"
                f"{word_count} not in [{required_min},{required_max}]"
            )

    attempt = {
        "kind": f"word_budget_repair_{repair_index}",
        "elapsed_seconds": round(time.perf_counter() - attempt_started, 3),
        "mode": mode,
        "required_word_range": [required_min, required_max],
        "aggressiveness": aggressiveness,
        "structured_parse_retries": parse_failures,
        "errors": errors,
        "word_count": word_count,
        "ignored_output_keys": sorted(
            key for key in payload if key != "prose"
        ),
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
    }
    return repaired, errors, word_count, attempt


def produce_scene(
    *,
    api_key: str,
    model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scene_contract: dict[str, Any],
    next_scene: dict[str, Any] | None,
    previous_prose: str,
    target_words: int,
    plan_review: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], list[str], int, list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    user_prompt = scene_request_payload(
        spec=spec,
        plan=plan,
        ledger=ledger,
        scene_contract=scene_contract,
        next_scene=next_scene,
        previous_prose=previous_prose,
        target_words=target_words,
        plan_review=plan_review,
    )

    attempt_started = time.perf_counter()
    envelope, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_WRITER_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=None,
        seed=seed,
        request_class="scene_story",
    )
    errors, word_count = validate_scene_envelope(
        envelope,
        target_words=target_words,
    )
    attempts.append(
        {
            "kind": "generate",
            "elapsed_seconds": round(time.perf_counter() - attempt_started, 3),
            "structured_parse_retries": parse_failures,
            "errors": errors,
            "word_count": word_count,
            "usage": parse_usage(body).model_dump(mode="json"),
            "cost": parse_cost(body).model_dump(mode="json"),
            "request": {
                "temperature": request.get("temperature"),
                "max_tokens": request.get("max_tokens"),
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
            },
        }
    )

    for repair_index in range(1, 3):
        if not errors:
            break
        repair_input = json.dumps(
            {
                "story_contract": plan["story_contract"],
                "scene_graph": plan["scenes"],
                "continuity_ledger": ledger,
                "scene_contract": scene_contract,
                "next_scene_guard": next_scene,
                "target_words": target_words,
                "repair_reasons": errors,
                "current_scene_envelope": envelope,
            },
            ensure_ascii=False,
            indent=2,
        )
        attempt_started = time.perf_counter()
        envelope, body, request, parse_failures = call_structured_json_with_retry(
            api_key=api_key,
            model=model,
            system_prompt=SCENE_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
            user_prompt=repair_input,
            temperature=0.35,
            max_tokens=None,
            seed=seed + repair_index,
            request_class="scene_repair",
        )
        errors, word_count = validate_scene_envelope(
            envelope,
            target_words=target_words,
        )
        attempts.append(
            {
                "kind": f"repair_{repair_index}",
                "elapsed_seconds": round(time.perf_counter() - attempt_started, 3),
                "structured_parse_retries": parse_failures,
                "errors": errors,
                "word_count": word_count,
                "usage": parse_usage(body).model_dump(mode="json"),
                "cost": parse_cost(body).model_dump(mode="json"),
                "request": {
                    "temperature": request.get("temperature"),
                    "max_tokens": request.get("max_tokens"),
                    "reasoning": request.get("reasoning"),
                    "response_format": request.get("response_format"),
                },
            }
        )

    if only_word_budget_errors(errors):
        locked_state_delta = envelope.get("state_delta")
        for budget_repair_index in range(1, 3):
            candidate, candidate_errors, candidate_word_count, attempt = (
                repair_scene_word_budget(
                    api_key=api_key,
                    model=model,
                    envelope=envelope,
                    target_words=target_words,
                    seed=seed + 100,
                    repair_index=budget_repair_index,
                )
            )
            attempts.append(attempt)
            state_changed = (
                candidate.get("state_delta") != locked_state_delta
            )
            if state_changed:
                errors = candidate_errors
                continue

            envelope = candidate
            errors = candidate_errors
            word_count = candidate_word_count
            if not errors:
                break

    return envelope, errors, word_count, attempts


def plan_repair_feedback(plan_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "deterministic_errors": plan_result.get("deterministic_errors") or [],
        "jev": {
            "threshold": (plan_result.get("jev") or {}).get("threshold"),
            "below_threshold": (plan_result.get("jev") or {}).get("below_threshold") or {},
            "next_action": (plan_result.get("jev") or {}).get("next_action"),
            "next_action_confidence": (plan_result.get("jev") or {}).get(
                "next_action_confidence"
            ),
        },
        "haiku": {
            "scores": (plan_result.get("haiku") or {}).get("scores") or {},
            "critical_failures": (plan_result.get("haiku") or {}).get(
                "critical_failures"
            ) or [],
            "scene_risks": (plan_result.get("haiku") or {}).get("scene_risks") or [],
            "summary": (plan_result.get("haiku") or {}).get("summary") or "",
        },
    }


def repair_plan_once(
    *,
    api_key: str,
    model: str,
    judge_model: str,
    spec: StorySpec,
    plan_result: dict[str, Any],
    repair_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    brief = build_labeled_brief(spec)
    repair_input = json.dumps(
        {
            "story_brief": brief,
            "current_plan": plan_result["plan"],
            "repair_feedback": plan_repair_feedback(plan_result),
        },
        ensure_ascii=False,
        indent=2,
    )
    repaired_plan, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=PLAN_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=repair_input,
        temperature=0.15,
        max_tokens=None,
        seed=6400 + repair_index,
        request_class="story_plan",
    )
    choice = (body.get("choices") or [{}])[0]
    if choice.get("finish_reason") == "length":
        usage = body.get("usage") or {}
        raise RuntimeError(
            "PLAN_REPAIR_TRUNCATED_AT_PROVIDER_LIMIT: "
            f"completion_tokens={usage.get('completion_tokens')!r}."
        )

    evaluation = evaluate_plan_candidate(
        api_key=api_key,
        plan=repaired_plan,
        spec=spec,
        judge_model=judge_model,
    )
    repaired_result = {
        "pipeline": "english_scene_plan_repair_v1",
        "planner_model": model,
        "judge_model": judge_model,
        "accepted": evaluation["accepted"],
        "deterministic_errors": evaluation["deterministic_errors"],
        "plan": repaired_plan,
        "jev": evaluation["jev"],
        "haiku": evaluation["haiku"],
        "costs": {
            "planner_repair": parse_cost(body).model_dump(mode="json"),
            **evaluation["costs"],
        },
        "usage": {
            "planner_repair": parse_usage(body).model_dump(mode="json"),
            **evaluation["usage"],
        },
        "request_evidence": {
            "structured_parse_retries": parse_failures,
            "planner_repair": {
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
                "max_tokens": request.get("max_tokens"),
            },
            **evaluation["request_evidence"],
        },
    }
    attempt = {
        "repair": repair_index,
        "before": plan_repair_feedback(plan_result),
        "after": plan_repair_feedback(repaired_result),
        "accepted": repaired_result["accepted"],
        "usage": repaired_result["usage"],
        "costs": repaired_result["costs"],
        "request_evidence": repaired_result["request_evidence"],
    }
    return repaired_result, attempt


def final_repair_scene_ids(final_judge: dict[str, Any], *, limit: int = 3) -> list[int]:
    if final_judge.get("critical_failures"):
        return []
    scene_ids: list[int] = []
    for target in final_judge.get("repair_targets") or []:
        if not isinstance(target, dict):
            continue
        repair_scene = target.get("repair_scene", target.get("scene"))
        if (
            not isinstance(repair_scene, int)
            or isinstance(repair_scene, bool)
            or not 1 <= repair_scene <= 6
        ):
            continue
        if repair_scene not in scene_ids:
            scene_ids.append(repair_scene)
        if len(scene_ids) >= limit:
            break
    return scene_ids


def final_repair_targets_for_scene(
    final_judge: dict[str, Any],
    repair_scene_index: int,
) -> list[dict[str, Any]]:
    return [
        target
        for target in final_judge.get("repair_targets") or []
        if isinstance(target, dict)
        and target.get("repair_scene", target.get("scene"))
        == repair_scene_index
    ]


def final_repair_issue(final_judge: dict[str, Any], scene_index: int) -> str:
    issues = []
    for target in final_repair_targets_for_scene(final_judge, scene_index):
        observed_scene = target.get("scene")
        issue = str(target.get("issue") or "").strip()
        if issue:
            issues.append(
                f"Observed in Scene {observed_scene}: {issue}"
            )
    return "\n".join(issues)


def validate_prose_only_repair(
    *,
    original_envelope: dict[str, Any],
    repaired_envelope: dict[str, Any],
    target_words: int,
) -> tuple[list[str], int]:
    raw_errors, word_count = validate_scene_envelope(
        repaired_envelope,
        target_words=target_words,
    )
    errors, _ = partition_scene_validation_errors(raw_errors)
    if repaired_envelope.get("state_delta") != original_envelope.get("state_delta"):
        errors.append("final_repair_state_delta_changed")
    return errors, word_count


def repair_scene_for_final_judge(
    *,
    api_key: str,
    model: str,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    scene_index: int,
    issue: str,
    seed: int,
    observed_scene_indices: list[int] | None = None,
    repair_round: int = 1,
) -> tuple[dict[str, Any], list[str], int, dict[str, Any]]:
    position = scene_index - 1
    scene = scenes[position]
    original_envelope = scene["envelope"]
    previous_prose = (
        scenes[position - 1]["envelope"]["prose"]
        if position > 0
        else ""
    )
    next_prose = (
        scenes[position + 1]["envelope"]["prose"]
        if position + 1 < len(scenes)
        else ""
    )
    observed_scene_context = [
        {
            "scene": observed_index,
            "scene_contract": scenes[observed_index - 1]["contract"],
            "prose": scenes[observed_index - 1]["envelope"]["prose"],
        }
        for observed_index in (observed_scene_indices or [])
        if 1 <= observed_index <= len(scenes)
        and observed_index != scene_index
    ]
    payload = json.dumps(
        {
            "story_contract": plan["story_contract"],
            "scene_contract": scene["contract"],
            "observed_scene_context": observed_scene_context,
            "prior_ledger": ledger[:position],
            "immutable_state_delta": original_envelope["state_delta"],
            "repair_issue": issue,
            "repair_round": repair_round,
            "strict_retry": repair_round > 1,
            "target_words": scene["target_words"],
            "allowed_word_range": [
                round(scene["target_words"] * 0.80),
                round(scene["target_words"] * 1.20),
            ],
            "previous_scene_prose": previous_prose,
            "current_scene_envelope": original_envelope,
            "next_scene_prose": next_prose,
        },
        ensure_ascii=False,
        indent=2,
    )
    repaired, body, request, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=FINAL_TARGETED_REPAIR_PROMPT.read_text(
            encoding="utf-8"
        ).strip(),
        user_prompt=payload,
        temperature=0.0,
        max_tokens=None,
        seed=seed,
        request_class="scene_repair",
    )
    model_state_delta_changed = (
        repaired.get("state_delta") != original_envelope.get("state_delta")
    )
    repaired = {
        **repaired,
        "state_delta": original_envelope["state_delta"],
    }
    raw_validation_errors, _ = validate_scene_envelope(
        repaired,
        target_words=scene["target_words"],
    )
    _, word_budget_warnings = partition_scene_validation_errors(
        raw_validation_errors
    )
    errors, word_count = validate_prose_only_repair(
        original_envelope=original_envelope,
        repaired_envelope=repaired,
        target_words=scene["target_words"],
    )
    attempt = {
        "kind": "final_haiku_targeted_repair",
        "scene": scene_index,
        "repair_issue": issue,
        "repair_round": repair_round,
        "ignored_model_state_delta_change": model_state_delta_changed,
        "structured_parse_retries": parse_failures,
        "word_budget_warnings": word_budget_warnings,
        "errors": errors,
        "word_count": word_count,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
    }
    return repaired, errors, word_count, attempt


def evaluate_completed_story(
    *,
    api_key: str,
    judge_model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
    story = "\n\n".join(
        scene["envelope"]["prose"].strip()
        for scene in scenes
    )
    total_words = count_words(story)
    minimum_words = round(spec.target_words * TOTAL_STORY_MIN_RATIO)
    maximum_words = round(spec.target_words * TOTAL_STORY_MAX_RATIO)
    repetition = repeated_ngram_ratio(story, 8)
    deterministic_errors: list[str] = []
    if total_words < minimum_words:
        deterministic_errors.append(
            f"below_total_word_budget:{total_words}<{minimum_words}"
        )
    if total_words > maximum_words:
        deterministic_errors.append(
            f"above_total_word_budget:{total_words}>{maximum_words}"
        )
    if repetition > 0.02:
        deterministic_errors.append(
            f"repeat_8gram_ratio_high:{repetition}>0.02"
        )

    whole_questions = build_whole_story_jev_questions()
    whole_jev_body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "Completed English LUMI six-scene story continuity ledger.",
            "story_contract": plan["story_contract"],
            "scene_graph": plan["scenes"],
            "continuity_ledger": ledger,
            "total_word_count": total_words,
            "story": story,
        },
        questions=whole_questions,
    )
    whole_jev = summarize_jev(
        whole_jev_body,
        question_ids=[
            key for key in whole_questions
            if key != "next_action"
        ],
    )

    brief = build_labeled_brief(spec)
    final_input = (
        "STORY BRIEF\n"
        + brief
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nSCENE GRAPH\n"
        + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
        + "\n\nCONTINUITY LEDGER\n"
        + json.dumps(ledger, ensure_ascii=False, indent=2)
        + "\n\nSCENE CONTINUITY EVIDENCE\n"
        + json.dumps(
            [
                {
                    "scene": scene["scene"],
                    "jev_history": scene["jev_history"],
                    "semantic_repairs": scene["semantic_repairs"],
                    "continuity_escalation_required": scene[
                        "continuity_escalation_required"
                    ],
                    "final_polish_repairs": scene.get(
                        "final_polish_repairs", []
                    ),
                }
                for scene in scenes
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nJEV WHOLE-STORY ADVISORY EVIDENCE\n"
        + json.dumps(whole_jev, ensure_ascii=False, indent=2)
        + "\n\nCOMPLETE ENGLISH STORY\n"
        + story
    )
    final_payload, final_body, final_request, final_parse_failures = (
        call_structured_json_with_retry(
            api_key=api_key,
            model=judge_model,
            system_prompt=FINAL_JUDGE_PROMPT.read_text(encoding="utf-8").strip(),
            user_prompt=final_input,
            temperature=0.0,
            max_tokens=2500,
            seed=None,
            request_class="judge",
        )
    )
    final_judge = validate_final_judge(final_payload)
    return {
        "story": story,
        "word_count": total_words,
        "repeat_8gram_ratio": repetition,
        "deterministic_errors": deterministic_errors,
        "whole_story_jev": whole_jev,
        "whole_jev_usage": whole_jev_body.get("usage") or {},
        "whole_jev_cost": (whole_jev_body.get("usage") or {}).get("cost"),
        "final_judge": final_judge,
        "final_judge_structured_parse_retries": final_parse_failures,
        "final_judge_usage": parse_usage(final_body).model_dump(mode="json"),
        "final_judge_cost": parse_cost(final_body).model_dump(mode="json"),
        "final_judge_request": {
            "temperature": final_request.get("temperature"),
            "max_tokens": final_request.get("max_tokens"),
            "reasoning": final_request.get("reasoning"),
            "response_format": final_request.get("response_format"),
        },
        "accepted": not deterministic_errors and final_judge["accepted"],
    }


def verify_final_repair_target(
    *,
    api_key: str,
    plan: dict[str, Any],
    scenes: list[dict[str, Any]],
    scene_index: int,
    issue: str,
    observed_scene_indices: list[int] | None = None,
) -> dict[str, Any]:
    position = scene_index - 1
    scene = scenes[position]
    previous_prose = (
        scenes[position - 1]["envelope"]["prose"]
        if position > 0
        else ""
    )
    next_prose = (
        scenes[position + 1]["envelope"]["prose"]
        if position + 1 < len(scenes)
        else ""
    )
    questions = {
        "target_resolved": noul_question(
            (
                "Has this exact final-judge repair issue been resolved in the current "
                f"Scene {scene_index} prose without introducing a new contradiction? "
                f"Repair issue: {issue}"
            ),
            true_criteria=(
                "The named issue is concretely resolved in the current scene prose, "
                "the surrounding scene transition remains coherent, and no new "
                "contradiction was introduced."
            ),
            false_criteria=(
                "The named issue remains, is only partially addressed, or the repair "
                "creates a new contradiction with adjacent prose or the SceneContract."
            ),
        ),
        "no_residual_ambiguity": noul_question(
            (
                "At the first wording relevant to this exact repair issue, is the intended "
                "meaning now explicit and free of the ambiguity or contradiction described "
                f"by the judge? Repair issue: {issue}"
            ),
            true_criteria=(
                "The cited ambiguity is eliminated at its first relevant mention; a careful "
                "reader does not need a later sentence to reinterpret or rescue the wording."
            ),
            false_criteria=(
                "The problematic or equivalently ambiguous wording remains, or the intended "
                "meaning only becomes clear later in the scene."
            ),
        ),
    }
    body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "Focused verification of one Haiku final-repair target.",
            "story_contract": plan["story_contract"],
            "scene_contract": scene["contract"],
            "repair_issue": issue,
            "observed_scene_context": [
                {
                    "scene": observed_index,
                    "scene_contract": scenes[observed_index - 1]["contract"],
                    "prose": scenes[observed_index - 1]["envelope"]["prose"],
                }
                for observed_index in (observed_scene_indices or [])
                if 1 <= observed_index <= len(scenes)
                and observed_index != scene_index
            ],
            "previous_scene_prose": previous_prose,
            "current_scene_prose": scene["envelope"]["prose"],
            "next_scene_prose": next_prose,
        },
        questions=questions,
    )
    probabilities = {
        key: noul_probability(body["answers"][key])
        for key in questions
    }
    probability = min(probabilities.values())
    threshold = load_jev_profile().positive_probability_threshold
    return {
        "probability": probability,
        "probabilities": probabilities,
        "threshold": threshold,
        "verified": all(value >= threshold for value in probabilities.values()),
        "usage": body.get("usage") or {},
        "resolved_model": body.get("model"),
        "provider": body.get("provider"),
    }


def apply_final_haiku_repairs(
    *,
    api_key: str,
    model: str,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    final_judge: dict[str, Any],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for scene_index in final_repair_scene_ids(final_judge):
        issue = final_repair_issue(final_judge, scene_index)
        if not issue:
            continue

        position = scene_index - 1
        repair_targets = final_repair_targets_for_scene(
            final_judge,
            scene_index,
        )
        observed_scene_indices = sorted(
            {
                int(target["scene"])
                for target in repair_targets
                if isinstance(target.get("scene"), int)
            }
        )
        repair_attempts: list[dict[str, Any]] = []
        verifications: list[dict[str, Any]] = []
        latest_word_count = scenes[position]["word_count"]
        technical_failure = False

        for repair_round in range(1, 3):
            repaired, errors, word_count, attempt = repair_scene_for_final_judge(
                api_key=api_key,
                model=model,
                plan=plan,
                ledger=ledger,
                scenes=scenes,
                scene_index=scene_index,
                issue=issue,
                seed=7600 + scene_index * 10 + repair_round,
                observed_scene_indices=observed_scene_indices,
                repair_round=repair_round,
            )
            attempt["repair_round"] = repair_round
            repair_attempts.append(attempt)

            if errors:
                records.append(
                    {
                        "scene": scene_index,
                        "accepted": False,
                        "target_verified": False,
                        "issue": issue,
                        "observed_scenes": observed_scene_indices,
                        "errors": errors,
                        "repair_attempts": repair_attempts,
                        "verifications": verifications,
                    }
                )
                technical_failure = True
                break

            scenes[position]["envelope"] = repaired
            scenes[position]["word_count"] = word_count
            scenes[position]["attempts"].append(attempt)
            ledger[position]["word_count"] = word_count
            latest_word_count = word_count

            verification = verify_final_repair_target(
                api_key=api_key,
                plan=plan,
                scenes=scenes,
                scene_index=scene_index,
                issue=issue,
                observed_scene_indices=observed_scene_indices,
            )
            verification["repair_round"] = repair_round
            verifications.append(verification)
            if verification["verified"]:
                break

        if technical_failure:
            continue

        target_verified = bool(
            verifications and verifications[-1]["verified"]
        )
        scenes[position].setdefault("final_polish_repairs", []).append(
            {
                "issue": issue,
                "observed_scenes": observed_scene_indices,
                "word_count": latest_word_count,
                "repair_attempts": len(repair_attempts),
                "target_verified": target_verified,
            }
        )

        post_jev = evaluate_scene_jev(
            api_key=api_key,
            scene_index=scene_index,
            story_contract=plan["story_contract"],
            scene_contract=scenes[position]["contract"],
            next_scene=(
                plan["scenes"][position + 1]
                if position + 1 < len(plan["scenes"])
                else None
            ),
            ledger=ledger[:position],
            envelope=scenes[position]["envelope"],
        )
        scenes[position]["jev"] = post_jev
        scenes[position]["jev_history"].append(post_jev)
        scenes[position]["continuity_escalation_required"] = (
            jev_requires_final_escalation(post_jev)
        )
        records.append(
            {
                "scene": scene_index,
                "accepted": True,
                "target_verified": target_verified,
                "issue": issue,
                "observed_scenes": observed_scene_indices,
                "word_count": latest_word_count,
                "post_jev": post_jev,
                "repair_attempts": repair_attempts,
                "verifications": verifications,
            }
        )
    return records


def run_final_polish_cycles(
    *,
    api_key: str,
    model: str,
    judge_model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
    max_cycles: int = 2,
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    final_evaluations: list[dict[str, Any]] = [
        evaluate_completed_story(
            api_key=api_key,
            judge_model=judge_model,
            spec=spec,
            plan=plan,
            ledger=ledger,
            scenes=scenes,
        )
    ]
    all_repairs: list[dict[str, Any]] = []
    cycle_records: list[dict[str, Any]] = []

    for cycle in range(1, max_cycles + 1):
        current = final_evaluations[-1]
        final_judge = current["final_judge"]
        target_scenes = final_repair_scene_ids(final_judge)
        if (
            current["accepted"]
            or final_judge["critical_failures"]
            or not target_scenes
        ):
            break

        repairs = apply_final_haiku_repairs(
            api_key=api_key,
            model=model,
            plan=plan,
            ledger=ledger,
            scenes=scenes,
            final_judge=final_judge,
        )
        tagged_repairs = [
            {**repair, "cycle": cycle}
            for repair in repairs
        ]
        all_repairs.extend(tagged_repairs)
        cycle_record = {
            "cycle": cycle,
            "requested_scenes": target_scenes,
            "repairs": tagged_repairs,
        }
        cycle_records.append(cycle_record)

        if not repairs or not all(repair["accepted"] for repair in repairs):
            break

        final_evaluations.append(
            evaluate_completed_story(
                api_key=api_key,
                judge_model=judge_model,
                spec=spec,
                plan=plan,
                ledger=ledger,
                scenes=scenes,
            )
        )

    return (
        final_evaluations[-1],
        final_evaluations,
        all_repairs,
        cycle_records,
    )


def run(
    *,
    model: str,
    jev_model: str,
    judge_model: str,
    spec_path: Path,
) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    require_qualification_runtime_profile(model)
    require_judge_runtime_profile(judge_model)
    jev_profile = load_jev_profile()
    if jev_model != jev_profile.model_id:
        raise RuntimeError(
            f"JEV model mismatch: expected {jev_profile.model_id}, got {jev_model}"
        )

    spec = StorySpec.model_validate(load_yaml(spec_path))
    if spec.language.lower() != "en":
        raise RuntimeError("English story pipeline requires language=en.")

    pipeline_started = time.perf_counter()
    plan_started = time.perf_counter()
    plan_result = run_plan_smoke(model, jev_model, judge_model, spec_path)
    plan_cost_history: list[dict[str, Any]] = [dict(plan_result.get("costs") or {})]
    plan_repair_attempts: list[dict[str, Any]] = []
    for repair_index in range(1, 3):
        if plan_result["accepted"]:
            break
        plan_result, repair_attempt = repair_plan_once(
            api_key=api_key,
            model=model,
            judge_model=judge_model,
            spec=spec,
            plan_result=plan_result,
            repair_index=repair_index,
        )
        plan_repair_attempts.append(repair_attempt)
        plan_cost_history.append(dict(plan_result.get("costs") or {}))
        print(
            json.dumps(
                {
                    "checkpoint": "plan_repair",
                    "repair": repair_index,
                    "accepted": plan_result["accepted"],
                    "deterministic_errors": plan_result["deterministic_errors"],
                    "jev_below_threshold": plan_result["jev"].get(
                        "below_threshold"
                    ) or {},
                    "haiku_average": plan_result["haiku"].get("average"),
                    "haiku_scene_risks": plan_result["haiku"].get(
                        "scene_risks"
                    ) or [],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    if not plan_result["accepted"]:
        raise RuntimeError(
            "PLAN_REPAIR_EXHAUSTED: "
            + json.dumps(
                {
                    "repairs": len(plan_repair_attempts),
                    "deterministic_errors": plan_result["deterministic_errors"],
                    "jev": plan_result["jev"],
                    "haiku": plan_result["haiku"],
                },
                ensure_ascii=False,
            )
        )

    plan_result["repair_attempts"] = plan_repair_attempts
    plan_elapsed_seconds = round(time.perf_counter() - plan_started, 3)
    plan = plan_result["plan"]
    budgets = allocate_scene_budgets(spec.target_words)
    ledger: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    previous_prose = ""
    plan_review = {
        "jev_below_threshold": plan_result["jev"].get("below_threshold") or {},
        "haiku_scene_risks": plan_result["haiku"].get("scene_risks") or [],
    }

    for position, scene_contract in enumerate(plan["scenes"]):
        scene_started = time.perf_counter()
        scene_index = position + 1
        next_scene = (
            plan["scenes"][position + 1]
            if position + 1 < len(plan["scenes"])
            else None
        )
        envelope, scene_errors, word_count, attempts = produce_scene(
            api_key=api_key,
            model=model,
            spec=spec,
            plan=plan,
            ledger=ledger,
            scene_contract=scene_contract,
            next_scene=next_scene,
            previous_prose=previous_prose,
            target_words=budgets[position],
            plan_review=plan_review,
            seed=4200 + scene_index * 10,
        )
        (
            scene_blocking_errors,
            scene_word_budget_warnings,
        ) = partition_scene_validation_errors(scene_errors)
        if scene_blocking_errors:
            print(
                json.dumps(
                    {
                        "checkpoint": "scene_failed",
                        "scene": scene_index,
                        "target_words": budgets[position],
                        "word_count": word_count,
                        "errors": scene_blocking_errors,
                        "word_budget_warnings": scene_word_budget_warnings,
                        "attempts": attempts,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            raise RuntimeError(
                f"SCENE_{scene_index}_TECHNICAL_REPAIR_EXHAUSTED: "
                f"{scene_blocking_errors}"
            )
        if scene_word_budget_warnings:
            print(
                json.dumps(
                    {
                        "checkpoint": "scene_word_budget_advisory",
                        "scene": scene_index,
                        "target_words": budgets[position],
                        "word_count": word_count,
                        "warnings": scene_word_budget_warnings,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

        continuity_eval_started = time.perf_counter()
        jev = evaluate_scene_jev(
            api_key=api_key,
            scene_index=scene_index,
            story_contract=plan["story_contract"],
            scene_contract=scene_contract,
            next_scene=next_scene,
            ledger=ledger,
            envelope=envelope,
        )
        jev_history = [jev]
        continuity_evaluator_elapsed_seconds = [
            round(time.perf_counter() - continuity_eval_started, 3)
        ]
        semantic_repairs: list[dict[str, Any]] = []
        semantic_errors: list[str] = []

        for semantic_repair_index in range(1, 3):
            if not jev_needs_targeted_repair(jev) and not semantic_errors:
                break
            jev_before = jev
            (
                envelope,
                raw_semantic_errors,
                word_count,
                repair_attempt,
            ) = repair_scene_for_jev(
                api_key=api_key,
                model=model,
                plan=plan,
                ledger=ledger,
                scene_contract=scene_contract,
                next_scene=next_scene,
                envelope=envelope,
                jev=jev_before,
                target_words=budgets[position],
                seed=5200 + scene_index * 10,
                repair_index=semantic_repair_index,
                extra_reasons=semantic_errors,
            )
            attempts.append(repair_attempt)
            (
                semantic_errors,
                semantic_word_budget_warnings,
            ) = partition_scene_validation_errors(raw_semantic_errors)
            scene_word_budget_warnings.extend(
                warning
                for warning in semantic_word_budget_warnings
                if warning not in scene_word_budget_warnings
            )
            repair_record: dict[str, Any] = {
                "repair": semantic_repair_index,
                "before_jev": jev_before,
                "technical_errors": semantic_errors,
                "word_budget_warnings": semantic_word_budget_warnings,
                "word_count": word_count,
            }
            if not semantic_errors:
                continuity_eval_started = time.perf_counter()
                jev = evaluate_scene_jev(
                    api_key=api_key,
                    scene_index=scene_index,
                    story_contract=plan["story_contract"],
                    scene_contract=scene_contract,
                    next_scene=next_scene,
                    ledger=ledger,
                    envelope=envelope,
                )
                jev_history.append(jev)
                continuity_evaluator_elapsed_seconds.append(
                    round(time.perf_counter() - continuity_eval_started, 3)
                )
                repair_record["after_jev"] = jev
            semantic_repairs.append(repair_record)

        if semantic_errors:
            raise RuntimeError(
                f"SCENE_{scene_index}_JEV_REPAIR_TECHNICAL_EXHAUSTED: {semantic_errors}"
            )

        continuity_escalation_required = jev_requires_final_escalation(jev)

        delta = envelope["state_delta"]
        ledger_entry = {
            "scene": scene_index,
            "purpose": scene_contract["purpose"],
            "word_count": word_count,
            "location": delta["location"],
            "character_goal": delta["character_goal"],
            "knowledge_gained": delta["knowledge_gained"],
            "facts_established": delta["facts_established"],
            "clues_added": delta["clues_added"],
            "objects_changed": delta["objects_changed"],
            "relationships_changed": delta["relationships_changed"],
            "threads_opened": delta["threads_opened"],
            "threads_resolved": delta["threads_resolved"],
            "handoff_state": delta["handoff_state"],
        }
        ledger.append(ledger_entry)
        scenes.append(
            {
                "scene": scene_index,
                "target_words": budgets[position],
                "word_count": word_count,
                "contract": scene_contract,
                "envelope": envelope,
                "attempts": attempts,
                "jev": jev,
                "jev_history": jev_history,
                "continuity_evaluator_elapsed_seconds": (
                    continuity_evaluator_elapsed_seconds
                ),
                "semantic_repairs": semantic_repairs,
                "word_budget_warnings": scene_word_budget_warnings,
                "continuity_escalation_required": continuity_escalation_required,
                "elapsed_seconds": round(time.perf_counter() - scene_started, 3),
            }
        )
        print(
            json.dumps(
                {
                    "checkpoint": "scene_accepted",
                    "scene": scene_index,
                    "target_words": budgets[position],
                    "word_count": word_count,
                    "attempt_count": len(attempts),
                    "semantic_repair_count": len(semantic_repairs),
                    "word_budget_warnings": scene_word_budget_warnings,
                    "jev_signal": jev["shadow_signal"],
                    "jev_below_threshold": jev["below_threshold"],
                    "continuity_escalation_required": continuity_escalation_required,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        previous_prose = envelope["prose"]

    final_stage_started = time.perf_counter()
    (
        final_evaluation,
        final_evaluations,
        final_polish_repairs,
        final_polish_cycles,
    ) = run_final_polish_cycles(
        api_key=api_key,
        model=model,
        judge_model=judge_model,
        spec=spec,
        plan=plan,
        ledger=ledger,
        scenes=scenes,
        max_cycles=2,
    )

    for cycle in final_polish_cycles:
        print(
            json.dumps(
                {
                    "checkpoint": "final_haiku_targeted_repair",
                    "cycle": cycle["cycle"],
                    "requested_scenes": cycle["requested_scenes"],
                    "targets": [
                        {
                            "scene": repair["scene"],
                            "accepted": repair["accepted"],
                            "target_verified": repair.get(
                                "target_verified"
                            ),
                            "errors": repair.get("errors") or [],
                        }
                        for repair in cycle["repairs"]
                    ],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    final_stage_elapsed_seconds = round(
        time.perf_counter() - final_stage_started, 3
    )
    total_pipeline_seconds = round(time.perf_counter() - pipeline_started, 3)

    story = final_evaluation["story"]
    total_words = final_evaluation["word_count"]
    repetition = final_evaluation["repeat_8gram_ratio"]
    deterministic_errors = final_evaluation["deterministic_errors"]
    whole_jev = final_evaluation["whole_story_jev"]
    final_judge = final_evaluation["final_judge"]
    accepted = final_evaluation["accepted"]

    total_plan_stage_cost = sum_plan_stage_cost_usd(plan_cost_history)
    total_generator_cost = 0.0
    total_scene_jev_cost = 0.0
    for scene in scenes:
        for attempt in scene["attempts"]:
            usd = (attempt.get("cost") or {}).get("usd")
            if usd is not None:
                total_generator_cost += float(usd)
        for evaluation in scene["jev_history"]:
            cost = (evaluation.get("usage") or {}).get("cost")
            if cost is not None:
                total_scene_jev_cost += float(cost)

    total_whole_jev_cost = sum(
        float(item.get("whole_jev_cost") or 0.0)
        for item in final_evaluations
    )
    total_final_haiku_cost = sum(
        float((item.get("final_judge_cost") or {}).get("usd") or 0.0)
        for item in final_evaluations
    )
    total_pipeline_cost = (
        total_plan_stage_cost
        + total_generator_cost
        + total_scene_jev_cost
        + total_whole_jev_cost
        + total_final_haiku_cost
    )

    return {
        "pipeline": "english_story_pipeline_v1",
        "models": {
            "generator": model,
            "continuity_evaluator": jev_model,
            "semantic_judge": judge_model,
            "jev": jev_model,
            "judge": judge_model,
        },
        "generation_protocol_version": GENERATION_PROTOCOL_VERSION,
        "evaluation_protocol_version": EVALUATION_PROTOCOL_VERSION,
        "spec": str(spec_path),
        "accepted": accepted,
        "plan_result": plan_result,
        "scene_budgets": budgets,
        "scenes": scenes,
        "continuity_ledger": ledger,
        "story_title": plan["story_title"],
        "story": story,
        "word_count": total_words,
        "target_words": spec.target_words,
        "deterministic_errors": deterministic_errors,
        "repeat_8gram_ratio": repetition,
        "whole_story_continuity": whole_jev,
        "whole_story_jev": whole_jev,
        "final_judge": final_judge,
        "final_polish_cycles": final_polish_cycles,
        "final_evaluation_history": [
            {
                "accepted": item["accepted"],
                "word_count": item["word_count"],
                "deterministic_errors": item["deterministic_errors"],
                "whole_story_jev": item["whole_story_jev"],
                "final_judge": item["final_judge"],
                "whole_jev_cost": item["whole_jev_cost"],
                "final_judge_cost": item["final_judge_cost"],
            }
            for item in final_evaluations
        ],
        "timings": {
            "plan_stage_seconds": plan_elapsed_seconds,
            "scene_stage_seconds": round(
                sum(float(scene.get("elapsed_seconds") or 0.0) for scene in scenes), 3
            ),
            "final_stage_seconds": final_stage_elapsed_seconds,
            "total_pipeline_seconds": total_pipeline_seconds,
        },
        "costs": {
            "plan_stage_usd_total": round(total_plan_stage_cost, 9),
            "scene_generation_usd": round(total_generator_cost, 9),
            "scene_continuity_evaluator_usd": round(total_scene_jev_cost, 9),
            "whole_continuity_evaluator_usd": final_evaluation["whole_jev_cost"],
            "whole_continuity_evaluator_usd_total": round(total_whole_jev_cost, 9),
            "semantic_judge_usd": final_evaluation["final_judge_cost"],
            "semantic_judge_usd_total": round(total_final_haiku_cost, 9),
            "scene_jev_usd": round(total_scene_jev_cost, 9),
            "whole_jev_usd": final_evaluation["whole_jev_cost"],
            "whole_jev_usd_total": round(total_whole_jev_cost, 9),
            "final_haiku": final_evaluation["final_judge_cost"],
            "final_haiku_usd_total": round(total_final_haiku_cost, 9),
            "total_pipeline_usd": round(total_pipeline_cost, 9),
        },
        "usage": {
            "whole_continuity_evaluator": final_evaluation["whole_jev_usage"],
            "semantic_judge": final_evaluation["final_judge_usage"],
            "whole_jev": final_evaluation["whole_jev_usage"],
            "final_haiku": final_evaluation["final_judge_usage"],
        },
        "final_judge_request": final_evaluation["final_judge_request"],
        "final_evaluation_history": [
            {
                "accepted": item["accepted"],
                "word_count": item["word_count"],
                "deterministic_errors": item["deterministic_errors"],
                "whole_story_jev": item["whole_story_jev"],
                "final_judge": item["final_judge"],
                "whole_jev_cost": item["whole_jev_cost"],
                "final_judge_cost": item["final_judge_cost"],
            }
            for item in final_evaluations
        ],
        "final_polish_repairs": final_polish_repairs,
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run the English-first LUMI scene production pipeline."
    )
    parser.add_argument("--model", default="openai/gpt-5.6-luna")
    parser.add_argument(
        "--continuity-evaluator-model",
        "--jev-model",
        dest="continuity_evaluator_model",
        default="typesafe/jev-1.13",
    )
    parser.add_argument(
        "--semantic-judge-model",
        "--judge-model",
        dest="semantic_judge_model",
        default="anthropic/claude-haiku-4.5",
    )
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument(
        "--output",
        default="runs/english_story_pipeline/result.json",
    )
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    cli_started = time.perf_counter()
    try:
        result = run(
            model=args.model,
            jev_model=args.continuity_evaluator_model,
            judge_model=args.semantic_judge_model,
            spec_path=Path(args.spec),
        )
    except Exception as exc:
        failure = {
            "pipeline": "english_story_pipeline_v1",
            "generation_protocol_version": GENERATION_PROTOCOL_VERSION,
            "evaluation_protocol_version": EVALUATION_PROTOCOL_VERSION,
            "models": {
                "generator": args.model,
                "continuity_evaluator": args.continuity_evaluator_model,
                "semantic_judge": args.semantic_judge_model,
            },
            "spec": args.spec,
            "accepted": False,
            "word_count": 0,
            "deterministic_errors": [],
            "terminal_error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
            "timings": {
                "total_pipeline_seconds": round(
                    time.perf_counter() - cli_started, 3
                )
            },
            "costs": {},
            "usage": {},
        }
        failure_path = output.with_name("failure.json")
        failure_path.write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "checkpoint": "pipeline_failed",
                    "error": failure["terminal_error"],
                    "failure_path": str(failure_path),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        raise
    output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    story_path = output.with_suffix(".story.txt")
    story_path.write_text(
        result["story_title"] + "\n\n" + result["story"],
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "accepted": result["accepted"],
                "word_count": result["word_count"],
                "target_words": result["target_words"],
                "deterministic_errors": result["deterministic_errors"],
                "repeat_8gram_ratio": result["repeat_8gram_ratio"],
                "scene_words": [
                    {
                        "scene": scene["scene"],
                        "target": scene["target_words"],
                        "actual": scene["word_count"],
                        "jev_signal": scene["jev"]["shadow_signal"],
                        "jev_below": scene["jev"]["below_threshold"],
                        "semantic_repairs": len(scene["semantic_repairs"]),
                        "continuity_escalation_required": scene[
                            "continuity_escalation_required"
                        ],
                    }
                    for scene in result["scenes"]
                ],
                "whole_story_jev": result["whole_story_jev"],
                "final_judge": result["final_judge"],
                "timings": result["timings"],
                "costs": result["costs"],
                "output": str(output),
                "story_path": str(story_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not result["accepted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
