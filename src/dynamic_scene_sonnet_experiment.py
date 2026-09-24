from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

import src.english_story_pipeline as pipeline
import src.english_scene_plan_smoke as plan_v3
from src.generate import count_words, load_yaml, parse_cost, parse_usage
from src.generator_benchmark_v2 import repeated_ngram_ratio
from src.model_registry import require_judge_runtime_profile, require_qualification_runtime_profile
from src.openrouter_jev import call_openrouter_jev, choice_question, load_jev_profile, noul_question
from src.schemas import StorySpec

PLANNER_MODEL = "anthropic/claude-sonnet-5"
WRITER_MODEL = "openai/gpt-5.6-luna"
CONTINUITY_MODEL = "typesafe/jev-1.13"
JUDGE_MODEL = "anthropic/claude-haiku-4.5"

PLAN_PROMPT = Path("prompts/story_scene_plan_dynamic_en_v4.md")
PLAN_REPAIR_PROMPT = Path("prompts/story_scene_plan_dynamic_repair_en_v4.md")
PLAN_JUDGE_PROMPT = Path("prompts/story_scene_plan_dynamic_judge_en_v4.md")
SCENE_WRITER_PROMPT = Path("prompts/story_scene_writer_dynamic_en_v4.md")
FINAL_JUDGE_PROMPT = Path("prompts/story_final_judge_dynamic_en_v4.md")
DEFAULT_SPEC = Path(
    "data/specifications/waves/age-relative-standard-v3-all-families/"
    "middle-child--puzzle-problem-solving.yaml"
)

PLAN_CRITERIA = (
    "causal_continuity",
    "protagonist_goal_continuity",
    "constraint_coverage",
    "information_progression",
    "no_unexplained_dependencies",
    "no_early_resolution",
    "ending_coherence",
)

_ACTIVE_PLAN: dict[str, Any] | None = None


def dynamic_plan_jev_questions() -> dict[str, dict[str, Any]]:
    checks = {
        "causal_continuity": (
            "Do all selected scenes form one causal chain in which each scene materially enables, constrains, advances, or resolves later work?",
            "The chosen decomposition forms one causal story with meaningful transitions.",
            "One or more scenes are disconnected, redundant, or fail to advance the causal chain.",
        ),
        "goal_continuity": (
            "Does the protagonist keep one coherent central goal across the selected scenes, with actions motivated by it?",
            "The central goal remains coherent and motivates actions.",
            "The goal changes, disappears, or stops motivating actions without narrative cause.",
        ),
        "constraint_coverage": (
            "Does the plan preserve and schedule every required constraint from the story brief?",
            "All required constraints are represented and schedulable.",
            "At least one required constraint is absent or cannot be satisfied.",
        ),
        "information_progression": (
            "Do clues, observations, decisions, and consequences accumulate without resetting knowledge or repeating completed narrative work?",
            "Information and consequences progress cumulatively.",
            "Knowledge resets or one or more scenes repeat already-completed narrative work.",
        ),
        "no_unexplained_dependencies": (
            "Can every important later event be explained using elements established before they are needed?",
            "Later events depend only on previously established or explicitly scheduled elements.",
            "A later event requires an unexplained character, object, location, fact, mechanism, power, or clue.",
        ),
        "no_early_resolution": (
            "Is the decisive solution reserved for the scene explicitly labeled PAYOFF, with earlier scenes only preparing or progressing toward it?",
            "The decisive solution is reserved for the declared PAYOFF scene.",
            "The central problem is decisively solved before the declared PAYOFF scene.",
        ),
        "ending_coherence": (
            "Does the declared PAYOFF earn the solution and does the final RESOLUTION follow from it, close the main thread, and avoid starting a new main plot?",
            "PAYOFF and final RESOLUTION form a coherent earned ending.",
            "The ending is unearned, contradictory, unresolved, or starts a new main plot.",
        ),
        "decomposition_fitness": (
            "Is the chosen scene count structurally justified, without redundant micro-scenes, overloaded scenes, or a missing causal step?",
            "The scene decomposition is a minimum sufficient structure for this story.",
            "The plan is fragmented, overloaded, redundant, or missing a needed narrative step.",
        ),
    }
    questions = {
        key: noul_question(instructions, true_criteria=yes, false_criteria=no)
        for key, (instructions, yes, no) in checks.items()
    }
    questions["next_action"] = choice_question(
        "Choose the safest bounded action after reviewing this dynamic SceneGraph.",
        {
            "CONTINUE": "The StoryContract and chosen decomposition are coherent enough to write.",
            "TARGETED_REPAIR": "A local plan defect should be repaired before prose generation.",
            "ESCALATE": "The plan is broadly ambiguous or structurally risky and needs stronger review.",
        },
    )
    return questions


def validate_dynamic_plan(plan: dict[str, Any], spec: StorySpec) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.get("story_title"), str) or not plan["story_title"].strip():
        errors.append("story_title_missing")
    rationale = plan.get("scene_count_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append("scene_count_rationale_missing")

    contract = plan.get("story_contract")
    required_fields = (
        "protagonist_goal",
        "central_problem",
        "solution_principle",
        "theme_thread",
        "ending_state",
    )
    if not isinstance(contract, dict):
        errors.append("story_contract_missing")
    else:
        for field in required_fields:
            if not isinstance(contract.get(field), str) or not contract[field].strip():
                errors.append(f"story_contract_{field}_missing")
        expected_ids = [f"C{index}" for index in range(1, len(spec.constraints) + 1)]
        if contract.get("required_constraint_ids") != expected_ids:
            errors.append("required_constraint_ids_mismatch")
        prohibited = contract.get("prohibited_events")
        if not isinstance(prohibited, list) or not prohibited:
            errors.append("prohibited_events_missing")

    scenes = plan.get("scenes")
    if not isinstance(scenes, list):
        errors.append("scenes_missing")
        return errors
    if not 2 <= len(scenes) <= 12:
        errors.append(f"scene_count_out_of_range:{len(scenes)}")
        return errors

    expected_indexes = list(range(1, len(scenes) + 1))
    actual_indexes = [
        scene.get("index") if isinstance(scene, dict) else None
        for scene in scenes
    ]
    if actual_indexes != expected_indexes:
        errors.append("scene_indexes_not_contiguous")

    purposes: list[str] = []
    handoffs: list[str] = []
    roles: list[str] = []
    scheduled_ids: set[str] = set()
    weights: list[int] = []

    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"scene_{index}_not_object")
            continue
        role = scene.get("narrative_role")
        if not isinstance(role, str) or not role.strip():
            errors.append(f"scene_{index}_narrative_role_missing")
            role = ""
        roles.append(str(role).strip().upper())

        weight = scene.get("relative_weight")
        if not isinstance(weight, int) or isinstance(weight, bool) or weight <= 0:
            errors.append(f"scene_{index}_relative_weight_invalid")
        else:
            weights.append(weight)

        for field in ("purpose", "entry_state", "handoff"):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                errors.append(f"scene_{index}_{field}_missing")

        for field in ("beats", "must_include", "must_not_do"):
            value = scene.get(field)
            if not isinstance(value, list) or not value or not all(
                isinstance(item, str) and item.strip() for item in value
            ):
                errors.append(f"scene_{index}_{field}_invalid")

        beats = scene.get("beats")
        if isinstance(beats, list) and not 2 <= len(beats) <= 4:
            errors.append(f"scene_{index}_beats_out_of_range")

        prior = scene.get("prior_evidence")
        if not isinstance(prior, list) or not all(
            isinstance(item, str) and item.strip() for item in prior
        ):
            errors.append(f"scene_{index}_prior_evidence_invalid")
        elif index > 1 and not prior:
            errors.append(f"scene_{index}_prior_evidence_missing")

        open_threads = scene.get("open_threads_after")
        if not isinstance(open_threads, list) or not all(
            isinstance(item, str) and item.strip() for item in open_threads
        ):
            errors.append(f"scene_{index}_open_threads_after_invalid")

        constraint_ids = scene.get("constraint_ids")
        if not isinstance(constraint_ids, list) or not all(
            isinstance(item, str) and item.strip() for item in constraint_ids
        ):
            errors.append(f"scene_{index}_constraint_ids_invalid")
        else:
            scheduled_ids.update(constraint_ids)

        purposes.append(str(scene.get("purpose") or "").strip().casefold())
        handoffs.append(str(scene.get("handoff") or "").strip().casefold())

    expected_ids = {f"C{index}" for index in range(1, len(spec.constraints) + 1)}
    if scheduled_ids != expected_ids:
        errors.append("scene_constraint_schedule_mismatch")
    if len(purposes) != len(set(purposes)):
        errors.append("duplicate_scene_purpose")
    if len(handoffs) != len(set(handoffs)):
        errors.append("duplicate_scene_handoff")
    if roles.count("PAYOFF") != 1:
        errors.append(f"payoff_role_count_invalid:{roles.count('PAYOFF')}")
    if not roles or roles[-1] != "RESOLUTION":
        errors.append("final_scene_role_not_resolution")
    if "PAYOFF" in roles and roles.index("PAYOFF") >= len(roles) - 1:
        errors.append("payoff_must_precede_resolution")
    if len(weights) == len(scenes) and sum(weights) <= 0:
        errors.append("relative_weight_sum_invalid")
    return errors


def evaluate_dynamic_plan(
    *,
    api_key: str,
    plan: dict[str, Any],
    spec: StorySpec,
    judge_model: str,
) -> dict[str, Any]:
    deterministic_errors = validate_dynamic_plan(plan, spec)
    questions = dynamic_plan_jev_questions()
    jev_body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "English LUMI story brief, StoryContract, and variable-length SceneGraph. Judge continuity and decomposition fitness.",
            "story_brief": {
                "protagonist": spec.protagonist,
                "setting": spec.setting,
                "theme": spec.theme,
                "premise": spec.premise,
                "constraints": spec.constraints,
                "target_words": spec.target_words,
                "age_min": spec.age_min,
                "age_max": spec.age_max,
            },
            "story_contract": plan.get("story_contract"),
            "scene_count_rationale": plan.get("scene_count_rationale"),
            "scenes": plan.get("scenes"),
        },
        questions=questions,
    )
    jev = pipeline.summarize_jev(
        jev_body,
        question_ids=[key for key in questions if key != "next_action"],
    )

    brief = plan_v3.build_labeled_brief(spec)
    judge_input = (
        "STORY BRIEF\n"
        + brief
        + "\n\nDYNAMIC PLAN\n"
        + json.dumps(plan, ensure_ascii=False, indent=2)
        + "\n\nJEV ADVISORY EVIDENCE\n"
        + json.dumps(jev, ensure_ascii=False, indent=2)
    )
    payload, body, request, parse_failures = plan_v3.call_structured_json_with_retry(
        api_key=api_key,
        model=judge_model,
        system_prompt=PLAN_JUDGE_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=judge_input,
        temperature=0.0,
        max_tokens=1800,
        seed=None,
        request_class="scene_plan_judge",
    )
    haiku = plan_v3.validate_haiku(payload)
    return {
        "accepted": not deterministic_errors and haiku["accepted"],
        "deterministic_errors": deterministic_errors,
        "jev": jev,
        "haiku": haiku,
        "costs": {
            "jev": (jev_body.get("usage") or {}).get("cost"),
            "haiku": parse_cost(body).model_dump(mode="json"),
        },
        "usage": {
            "jev": jev_body.get("usage") or {},
            "haiku": parse_usage(body).model_dump(mode="json"),
        },
        "request_evidence": {
            "haiku_structured_parse_retries": parse_failures,
            "haiku": {
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
            },
        },
    }


def run_dynamic_plan(
    _ignored_writer_model: str,
    jev_model: str,
    judge_model: str,
    spec_path: Path,
) -> dict[str, Any]:
    global _ACTIVE_PLAN
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(PLANNER_MODEL)
    require_judge_runtime_profile(judge_model)
    jev_profile = load_jev_profile()
    if jev_model != jev_profile.model_id:
        raise RuntimeError(f"JEV model mismatch: expected {jev_profile.model_id}, got {jev_model}")
    spec = StorySpec.model_validate(load_yaml(spec_path))
    brief = plan_v3.build_labeled_brief(spec)

    plan, plan_body, request, parse_failures = plan_v3.call_structured_json_with_retry(
        api_key=api_key,
        model=PLANNER_MODEL,
        system_prompt=PLAN_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=(
            "Create the immutable StoryContract and choose the minimum sufficient dynamic SceneGraph. "
            "Do not optimize toward any predetermined scene count.\n\nSTORY BRIEF\n" + brief
        ),
        temperature=0.2,
        max_tokens=None,
        seed=42,
        request_class="story_plan",
    )
    choice = (plan_body.get("choices") or [{}])[0]
    if choice.get("finish_reason") == "length":
        raise RuntimeError("DYNAMIC_PLAN_TRUNCATED_AT_PROVIDER_LIMIT")

    evaluation = evaluate_dynamic_plan(
        api_key=api_key,
        plan=plan,
        spec=spec,
        judge_model=judge_model,
    )
    _ACTIVE_PLAN = plan
    return {
        "pipeline": "english_dynamic_scene_plan_v4_experiment",
        "planner_model": PLANNER_MODEL,
        "jev_model": jev_model,
        "judge_model": judge_model,
        "spec": str(spec_path),
        "accepted": evaluation["accepted"],
        "deterministic_errors": evaluation["deterministic_errors"],
        "plan": plan,
        "jev": evaluation["jev"],
        "haiku": evaluation["haiku"],
        "costs": {
            "planner": parse_cost(plan_body).model_dump(mode="json"),
            **evaluation["costs"],
        },
        "usage": {
            "planner": parse_usage(plan_body).model_dump(mode="json"),
            **evaluation["usage"],
        },
        "request_evidence": {
            "planner_structured_parse_retries": parse_failures,
            "planner": {
                "reasoning": request.get("reasoning"),
                "response_format": request.get("response_format"),
                "max_tokens": request.get("max_tokens"),
            },
            **evaluation["request_evidence"],
        },
    }


def repair_dynamic_plan_once(
    *,
    api_key: str,
    model: str,
    judge_model: str,
    spec: StorySpec,
    plan_result: dict[str, Any],
    repair_index: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    del model
    global _ACTIVE_PLAN
    repair_input = json.dumps(
        {
            "story_brief": plan_v3.build_labeled_brief(spec),
            "current_plan": plan_result["plan"],
            "repair_feedback": pipeline.plan_repair_feedback(plan_result),
        },
        ensure_ascii=False,
        indent=2,
    )
    repaired, body, request, parse_failures = plan_v3.call_structured_json_with_retry(
        api_key=api_key,
        model=PLANNER_MODEL,
        system_prompt=PLAN_REPAIR_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=repair_input,
        temperature=0.15,
        max_tokens=None,
        seed=6400 + repair_index,
        request_class="story_plan",
    )
    evaluation = evaluate_dynamic_plan(
        api_key=api_key,
        plan=repaired,
        spec=spec,
        judge_model=judge_model,
    )
    _ACTIVE_PLAN = repaired
    repaired_result = {
        "pipeline": "english_dynamic_scene_plan_repair_v4_experiment",
        "planner_model": PLANNER_MODEL,
        "judge_model": judge_model,
        "accepted": evaluation["accepted"],
        "deterministic_errors": evaluation["deterministic_errors"],
        "plan": repaired,
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
        "before": pipeline.plan_repair_feedback(plan_result),
        "after": pipeline.plan_repair_feedback(repaired_result),
        "accepted": repaired_result["accepted"],
        "usage": repaired_result["usage"],
        "costs": repaired_result["costs"],
        "request_evidence": repaired_result["request_evidence"],
    }
    return repaired_result, attempt


def allocate_dynamic_scene_budgets(target_words: int) -> list[int]:
    if not _ACTIVE_PLAN or not isinstance(_ACTIVE_PLAN.get("scenes"), list):
        raise RuntimeError("DYNAMIC_PLAN_NOT_AVAILABLE_FOR_BUDGET_ALLOCATION")
    scenes = _ACTIVE_PLAN["scenes"]
    weights = [int(scene["relative_weight"]) for scene in scenes]
    total_weight = sum(weights)
    if total_weight <= 0:
        raise RuntimeError("DYNAMIC_SCENE_WEIGHTS_INVALID")
    exact = [target_words * weight / total_weight for weight in weights]
    budgets = [max(1, int(value)) for value in exact]
    remainder = target_words - sum(budgets)
    fractions = sorted(
        range(len(exact)),
        key=lambda index: exact[index] - int(exact[index]),
        reverse=True,
    )
    cursor = 0
    while remainder > 0:
        budgets[fractions[cursor % len(fractions)]] += 1
        remainder -= 1
        cursor += 1
    while remainder < 0:
        candidates = [i for i, value in enumerate(budgets) if value > 1]
        budgets[candidates[cursor % len(candidates)]] -= 1
        remainder += 1
        cursor += 1
    return budgets


def dynamic_scene_jev_questions(
    scene_index: int,
    is_final: bool,
    narrative_role: str,
) -> dict[str, dict[str, Any]]:
    role = narrative_role.upper()
    questions = {
        "continues_prior_state": noul_question(
            "Does this scene begin from and remain compatible with the accepted prior story state?",
            true_criteria="The scene continues prior state without reset or unexplained jump.",
            false_criteria="The scene resets, contradicts, or jumps away from prior state.",
        ),
        "scene_purpose_obeyed": noul_question(
            f"Does Scene {scene_index} fulfill its declared purpose and narrative role {role} without replacing them with a different plot?",
            true_criteria="The scene materially fulfills its declared purpose and role.",
            false_criteria="The scene ignores or replaces its declared purpose or role.",
        ),
        "no_unexplained_dependency": noul_question(
            "Are important facts, objects, locations, clues, mechanisms, and inferences supported by prior evidence or the current SceneContract?",
            true_criteria="Important dependencies are established before use.",
            false_criteria="The scene depends on an unexplained element or unjustified inference.",
        ),
        "no_contradiction": noul_question(
            "Is the scene free of contradictions with the StoryContract, SceneGraph, and ContinuityLedger?",
            true_criteria="No material contradiction is present.",
            false_criteria="At least one material contradiction is present.",
        ),
        "goal_preserved": noul_question(
            "Does the protagonist's central goal and motivation remain coherent in this scene?",
            true_criteria="The central goal remains coherent and motivates actions.",
            false_criteria="The goal disappears or changes without narrative cause.",
        ),
        "no_future_leakage": noul_question(
            (
                "Does the final RESOLUTION close consequences without opening a new main problem?"
                if is_final
                else (
                    "Does this PAYOFF deliver the planned decisive solution without consuming the later RESOLUTION work?"
                    if role == "PAYOFF"
                    else "Does the scene avoid performing decisive work reserved for the declared PAYOFF or later scenes?"
                )
            ),
            true_criteria=(
                "The final scene closes the main problem and leaves at most a bounded allowed hook."
                if is_final
                else (
                    "The PAYOFF is decisive but leaves consequence/closure work to the RESOLUTION."
                    if role == "PAYOFF"
                    else "Later-scene work remains protected."
                )
            ),
            false_criteria=(
                "The final scene leaves the central problem unresolved or starts a new main problem."
                if is_final
                else (
                    "The PAYOFF consumes work reserved for RESOLUTION or changes the planned solution."
                    if role == "PAYOFF"
                    else "The scene performs a decisive later event too early."
                )
            ),
        ),
        "handoff_valid": noul_question(
            "Does the handoff_state accurately create the concrete state inherited by the next scene?"
            if not is_final
            else "Does the final handoff_state accurately describe the resolved ending state?",
            true_criteria="The handoff is concrete and consistent with the scene outcome.",
            false_criteria="The handoff is vague, contradictory, or unsupported.",
        ),
    }
    questions["next_action"] = choice_question(
        "Choose the safest bounded action after reviewing this scene.",
        {
            "CONTINUE": "The scene is coherent enough to continue.",
            "TARGETED_REPAIR": "A local continuity defect should be repaired in this scene.",
            "ESCALATE": "The scene is broadly ambiguous or risky and requires stronger review.",
        },
    )
    return questions


def evaluate_scene_jev_dynamic(
    *,
    api_key: str,
    scene_index: int,
    story_contract: dict[str, Any],
    scene_contract: dict[str, Any],
    next_scene: dict[str, Any] | None,
    ledger: list[dict[str, Any]],
    envelope: dict[str, Any],
) -> dict[str, Any]:
    questions = dynamic_scene_jev_questions(
        scene_index,
        next_scene is None,
        str(scene_contract.get("narrative_role") or ""),
    )
    body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "English LUMI dynamic-scene continuity evaluation.",
            "story_contract": story_contract,
            "scene_contract": scene_contract,
            "next_scene_contract": next_scene,
            "prior_ledger": ledger,
            "current_scene": envelope,
        },
        questions=questions,
    )
    return pipeline.summarize_jev(
        body,
        question_ids=[key for key in questions if key != "next_action"],
    )


def build_whole_story_jev_questions_dynamic() -> dict[str, dict[str, Any]]:
    checks = {
        "causal_chain": (
            "Does the complete variable-length story form one causal chain from initial goal through the declared PAYOFF and final RESOLUTION?",
            "The full story forms one causal chain.",
            "The story contains disconnected, redundant, or unjustified narrative jumps.",
        ),
        "goal_continuity": (
            "Does the protagonist keep a coherent central goal and motivation across the full story?",
            "The protagonist's goal is coherent throughout.",
            "The protagonist's goal changes or disappears without narrative cause.",
        ),
        "clue_solution_progression": (
            "Is the declared PAYOFF earned by clues, observations, tests, and decisions established earlier?",
            "The payoff is earned by prior evidence.",
            "The payoff depends on coincidence, retroactive explanation, or missing setup.",
        ),
        "no_contradictions": (
            "Using the ContinuityLedger as canonical state, is the assembled story free of direct factual contradictions?",
            "No direct factual contradiction exists.",
            "At least two factual claims cannot both be true or the story conflicts with canonical ledger state.",
        ),
        "no_repeated_event": (
            "Does each scene advance a distinct planned narrative job rather than repeating an event, discovery, or function already completed?",
            "Scenes progress without redundant event repetition.",
            "At least one scene repeats already-completed narrative work.",
        ),
        "ending_consistency": (
            "Does the final RESOLUTION follow from the declared PAYOFF, resolve the central problem, and leave only an allowed bounded hook?",
            "The ending is a coherent consequence of the payoff.",
            "The ending contradicts the payoff, leaves the main problem unresolved, or opens a new main problem.",
        ),
        "decomposition_fitness": (
            "In the completed prose, does the chosen scene decomposition remain justified without obvious fragmentation or overloaded transitions?",
            "The prose validates the chosen decomposition.",
            "The completed story reveals redundant fragmentation or overloaded scene structure.",
        ),
    }
    questions = {
        key: noul_question(instructions, true_criteria=yes, false_criteria=no)
        for key, (instructions, yes, no) in checks.items()
    }
    questions["next_action"] = choice_question(
        "Choose the safest bounded action after reviewing the whole story.",
        {
            "CONTINUE": "The story is coherent enough to proceed to final judgment.",
            "TARGETED_REPAIR": "A bounded local continuity defect should be repaired.",
            "ESCALATE": "The story is broadly ambiguous or risky and needs stronger review.",
        },
    )
    return questions


def evaluate_completed_story_dynamic(
    *,
    api_key: str,
    judge_model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    ledger: list[dict[str, Any]],
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
    story = "\n\n".join(scene["envelope"]["prose"].strip() for scene in scenes)
    total_words = count_words(story)
    minimum_words = round(spec.target_words * pipeline.TOTAL_STORY_MIN_RATIO)
    maximum_words = round(spec.target_words * pipeline.TOTAL_STORY_MAX_RATIO)
    repetition = repeated_ngram_ratio(story, 8)
    deterministic_errors: list[str] = []
    if total_words < minimum_words:
        deterministic_errors.append(f"below_total_word_budget:{total_words}<{minimum_words}")
    if total_words > maximum_words:
        deterministic_errors.append(f"above_total_word_budget:{total_words}>{maximum_words}")
    if repetition > 0.02:
        deterministic_errors.append(f"repeat_8gram_ratio_high:{repetition}>0.02")

    questions = build_whole_story_jev_questions_dynamic()
    whole_body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "Completed English LUMI variable-length SceneGraph story continuity ledger.",
            "story_contract": plan["story_contract"],
            "scene_graph": plan["scenes"],
            "continuity_ledger": ledger,
            "total_word_count": total_words,
            "story": story,
        },
        questions=questions,
    )
    whole_jev = pipeline.summarize_jev(
        whole_body,
        question_ids=[key for key in questions if key != "next_action"],
    )

    final_input = (
        "STORY BRIEF\n"
        + plan_v3.build_labeled_brief(spec)
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nDYNAMIC SCENE GRAPH\n"
        + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
        + "\n\nSCENE COUNT RATIONALE\n"
        + str(plan.get("scene_count_rationale") or "")
        + "\n\nCONTINUITY LEDGER\n"
        + json.dumps(ledger, ensure_ascii=False, indent=2)
        + "\n\nSCENE CONTINUITY EVIDENCE\n"
        + json.dumps(
            [
                {
                    "scene": scene["scene"],
                    "narrative_role": scene["contract"].get("narrative_role"),
                    "jev_history": scene["jev_history"],
                    "semantic_repairs": scene["semantic_repairs"],
                    "continuity_escalation_required": scene["continuity_escalation_required"],
                    "final_polish_repairs": scene.get("final_polish_repairs", []),
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
    payload, body, request, parse_failures = pipeline.call_structured_json_with_retry(
        api_key=api_key,
        model=judge_model,
        system_prompt=FINAL_JUDGE_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=final_input,
        temperature=0.0,
        max_tokens=2500,
        seed=None,
        request_class="judge",
    )
    final_judge = pipeline.validate_final_judge(payload)
    return {
        "story": story,
        "word_count": total_words,
        "repeat_8gram_ratio": repetition,
        "deterministic_errors": deterministic_errors,
        "whole_story_jev": whole_jev,
        "whole_jev_usage": whole_body.get("usage") or {},
        "whole_jev_cost": (whole_body.get("usage") or {}).get("cost"),
        "final_judge": final_judge,
        "final_judge_structured_parse_retries": parse_failures,
        "final_judge_usage": parse_usage(body).model_dump(mode="json"),
        "final_judge_cost": parse_cost(body).model_dump(mode="json"),
        "final_judge_request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
        "accepted": not deterministic_errors and final_judge["accepted"],
    }


def install_experiment_hooks() -> None:
    pipeline.SCENE_WRITER_PROMPT = SCENE_WRITER_PROMPT
    pipeline.PLAN_REPAIR_PROMPT = PLAN_REPAIR_PROMPT
    pipeline.FINAL_JUDGE_PROMPT = FINAL_JUDGE_PROMPT
    pipeline.GENERATION_PROTOCOL_VERSION = "english-story-production.v4-dynamic-scene-experiment"
    pipeline.run_plan_smoke = run_dynamic_plan
    pipeline.evaluate_plan_candidate = evaluate_dynamic_plan
    pipeline.repair_plan_once = repair_dynamic_plan_once
    pipeline.allocate_scene_budgets = allocate_dynamic_scene_budgets
    pipeline.evaluate_scene_jev = evaluate_scene_jev_dynamic
    pipeline.build_whole_story_jev_questions = build_whole_story_jev_questions_dynamic
    pipeline.evaluate_completed_story = evaluate_completed_story_dynamic


def run_experiment(spec_path: Path) -> dict[str, Any]:
    install_experiment_hooks()
    result = pipeline.run(
        model=WRITER_MODEL,
        jev_model=CONTINUITY_MODEL,
        judge_model=JUDGE_MODEL,
        spec_path=spec_path,
    )
    plan = result["plan_result"]["plan"]
    result["pipeline"] = "dynamic_scene_sonnet_architect_luna_writer_v4_experiment"
    result["models"]["planner"] = PLANNER_MODEL
    result["experiment"] = {
        "hypothesis": (
            "A stronger Narrative Architect choosing a variable scene count can reduce "
            "structural/continuity burden while Luna remains the prose writer."
        ),
        "scene_count": len(plan["scenes"]),
        "scene_count_rationale": plan.get("scene_count_rationale"),
        "roles": [scene.get("narrative_role") for scene in plan["scenes"]],
        "relative_weights": [scene.get("relative_weight") for scene in plan["scenes"]],
        "allocated_scene_budgets": result.get("scene_budgets"),
    }
    return result


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument(
        "--output",
        default="runs/dynamic_scene_sonnet_v4/result.json",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        result = run_experiment(Path(args.spec))
    except Exception as exc:
        failure = {
            "pipeline": "dynamic_scene_sonnet_architect_luna_writer_v4_experiment",
            "generation_protocol_version": "english-story-production.v4-dynamic-scene-experiment",
            "models": {
                "planner": PLANNER_MODEL,
                "generator": WRITER_MODEL,
                "continuity_evaluator": CONTINUITY_MODEL,
                "semantic_judge": JUDGE_MODEL,
            },
            "spec": args.spec,
            "accepted": False,
            "terminal_error": {"type": type(exc).__name__, "message": str(exc)},
            "timings": {"total_pipeline_seconds": round(time.perf_counter() - started, 3)},
        }
        failure_path = output.with_name("failure.json")
        failure_path.write_text(
            json.dumps(failure, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(failure, ensure_ascii=False, indent=2), flush=True)
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
    summary = {
        "accepted": result["accepted"],
        "scene_count": result["experiment"]["scene_count"],
        "scene_count_rationale": result["experiment"]["scene_count_rationale"],
        "roles": result["experiment"]["roles"],
        "scene_budgets": result["scene_budgets"],
        "scene_words": [
            {
                "scene": scene["scene"],
                "role": scene["contract"].get("narrative_role"),
                "target": scene["target_words"],
                "actual": scene["word_count"],
                "attempts": len(scene["attempts"]),
                "semantic_repairs": len(scene["semantic_repairs"]),
                "jev_below": scene["jev"].get("below_threshold") or {},
            }
            for scene in result["scenes"]
        ],
        "word_count": result["word_count"],
        "target_words": result["target_words"],
        "repeat_8gram_ratio": result["repeat_8gram_ratio"],
        "deterministic_errors": result["deterministic_errors"],
        "whole_story_jev": result["whole_story_jev"],
        "final_judge": result["final_judge"],
        "timings": result["timings"],
        "costs": result["costs"],
        "output": str(output),
        "story_path": str(story_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    if not result["accepted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
