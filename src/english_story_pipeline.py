from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_scene_plan_smoke import (
    build_labeled_brief,
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
FINAL_JUDGE_PROMPT = Path("prompts/story_final_judge_en_v1.md")
DEFAULT_SPEC = Path("data/specifications/benchmark_en/01_exploration_mystery.yaml")

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


def validate_scene_envelope(
    envelope: dict[str, Any],
    *,
    target_words: int,
    min_ratio: float = 0.80,
    max_ratio: float = 1.20,
) -> tuple[list[str], int]:
    errors: list[str] = []
    prose = envelope.get("prose")
    if not isinstance(prose, str) or not prose.strip():
        return ["prose_missing"], 0

    word_count = count_words(prose)
    minimum = round(target_words * min_ratio)
    maximum = round(target_words * max_ratio)
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
            "story_contract": None,
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
    text, body, request = call_openrouter(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=repair_input,
        temperature=0.25,
        max_tokens=None,
        seed=seed + repair_index,
        request_class="scene_repair",
        structured_output=True,
    )
    repaired = parse_json_object(text)
    errors, word_count = validate_scene_envelope(
        repaired,
        target_words=target_words,
    )
    attempt = {
        "kind": f"jev_repair_{repair_index}",
        "repair_reasons": repair_reasons,
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

    average = round(sum(normalized.values()) / len(normalized), 3)
    minimum = min(normalized.values())
    return {
        "scores": normalized,
        "average": average,
        "minimum": minimum,
        "critical_failures": critical,
        "repair_targets": repair_targets,
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

    text, body, request = call_openrouter(
        api_key=api_key,
        model=model,
        system_prompt=SCENE_WRITER_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=user_prompt,
        temperature=0.7,
        max_tokens=None,
        seed=seed,
        request_class="scene_story",
        structured_output=True,
    )
    envelope = parse_json_object(text)
    errors, word_count = validate_scene_envelope(
        envelope,
        target_words=target_words,
    )
    attempts.append(
        {
            "kind": "generate",
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
        text, body, request = call_openrouter(
            api_key=api_key,
            model=model,
            system_prompt=SCENE_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
            user_prompt=repair_input,
            temperature=0.35,
            max_tokens=None,
            seed=seed + repair_index,
            request_class="scene_repair",
            structured_output=True,
        )
        envelope = parse_json_object(text)
        errors, word_count = validate_scene_envelope(
            envelope,
            target_words=target_words,
        )
        attempts.append(
            {
                "kind": f"repair_{repair_index}",
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

    return envelope, errors, word_count, attempts


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

    plan_result = run_plan_smoke(model, jev_model, judge_model, spec_path)
    if not plan_result["accepted"]:
        raise RuntimeError(
            "PLAN_NOT_ACCEPTED: "
            + json.dumps(
                {
                    "deterministic_errors": plan_result["deterministic_errors"],
                    "jev": plan_result["jev"],
                    "haiku": plan_result["haiku"],
                },
                ensure_ascii=False,
            )
        )

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
        if scene_errors:
            print(
                json.dumps(
                    {
                        "checkpoint": "scene_failed",
                        "scene": scene_index,
                        "target_words": budgets[position],
                        "word_count": word_count,
                        "errors": scene_errors,
                        "attempts": attempts,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            raise RuntimeError(
                f"SCENE_{scene_index}_TECHNICAL_REPAIR_EXHAUSTED: {scene_errors}"
            )

        jev = evaluate_scene_jev(
            api_key=api_key,
            scene_index=scene_index,
            scene_contract=scene_contract,
            next_scene=next_scene,
            ledger=ledger,
            envelope=envelope,
        )
        jev_history = [jev]
        semantic_repairs: list[dict[str, Any]] = []
        semantic_errors: list[str] = []

        for semantic_repair_index in range(1, 3):
            if not jev_needs_targeted_repair(jev) and not semantic_errors:
                break
            jev_before = jev
            envelope, semantic_errors, word_count, repair_attempt = repair_scene_for_jev(
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
            repair_record: dict[str, Any] = {
                "repair": semantic_repair_index,
                "before_jev": jev_before,
                "technical_errors": semantic_errors,
                "word_count": word_count,
            }
            if not semantic_errors:
                jev = evaluate_scene_jev(
                    api_key=api_key,
                    scene_index=scene_index,
                    scene_contract=scene_contract,
                    next_scene=next_scene,
                    ledger=ledger,
                    envelope=envelope,
                )
                jev_history.append(jev)
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
                "semantic_repairs": semantic_repairs,
                "continuity_escalation_required": continuity_escalation_required,
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
                    "jev_signal": jev["shadow_signal"],
                    "jev_below_threshold": jev["below_threshold"],
                    "continuity_escalation_required": continuity_escalation_required,
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        previous_prose = envelope["prose"]

    story = "\n\n".join(scene["envelope"]["prose"].strip() for scene in scenes)
    total_words = count_words(story)
    minimum_words = round(spec.target_words * 0.90)
    maximum_words = round(spec.target_words * 1.10)
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
    final_text, final_body, final_request = call_openrouter(
        api_key=api_key,
        model=judge_model,
        system_prompt=FINAL_JUDGE_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=final_input,
        temperature=0.0,
        max_tokens=2500,
        seed=None,
        request_class="judge",
        structured_output=True,
    )
    final_judge = validate_final_judge(parse_json_object(final_text))

    accepted = not deterministic_errors and final_judge["accepted"]

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

    return {
        "pipeline": "english_story_pipeline_v1",
        "models": {
            "generator": model,
            "jev": jev_model,
            "judge": judge_model,
        },
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
        "whole_story_jev": whole_jev,
        "final_judge": final_judge,
        "costs": {
            "scene_generation_usd": round(total_generator_cost, 9),
            "scene_jev_usd": round(total_scene_jev_cost, 9),
            "whole_jev_usd": (whole_jev_body.get("usage") or {}).get("cost"),
            "final_haiku": parse_cost(final_body).model_dump(mode="json"),
        },
        "usage": {
            "whole_jev": whole_jev_body.get("usage") or {},
            "final_haiku": parse_usage(final_body).model_dump(mode="json"),
        },
        "final_judge_request": {
            "temperature": final_request.get("temperature"),
            "max_tokens": final_request.get("max_tokens"),
            "reasoning": final_request.get("reasoning"),
            "response_format": final_request.get("response_format"),
        },
    }


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Run the English-first LUMI scene production pipeline."
    )
    parser.add_argument("--model", default="qwen/qwen3.8-flash")
    parser.add_argument("--jev-model", default="typesafe/jev-1.13")
    parser.add_argument("--judge-model", default="anthropic/claude-haiku-4.5")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument(
        "--output",
        default="runs/english_story_pipeline/result.json",
    )
    args = parser.parse_args()

    result = run(
        model=args.model,
        jev_model=args.jev_model,
        judge_model=args.judge_model,
        spec_path=Path(args.spec),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
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
