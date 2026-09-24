from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_scene_plan_smoke import build_labeled_brief
from src.english_story_pipeline import call_structured_json_with_retry, summarize_jev
from src.generate import call_openrouter, count_words, load_yaml, parse_cost, parse_usage
from src.generator_benchmark_v2 import repeated_ngram_ratio
from src.openrouter_jev import call_openrouter_jev, choice_question, noul_question
from src.schemas import StorySpec

PROTOCOL_VERSION = "english-story-production.v5-whole-draft-prototype"

DEFAULT_ARCHITECT = "openai/gpt-5.6-luna"
DEFAULT_WRITER = "openai/gpt-5.6-luna"
DEFAULT_CONTINUITY = "typesafe/jev-1.13"
DEFAULT_JUDGE = "anthropic/claude-haiku-4.5"
DEFAULT_OUTCOME_EXTRACTOR = "openai/gpt-5.6-luna"

DEFAULT_SPEC: str | None = None

BUILTIN_SPEC = {
    "title_hint": "The Lantern Map",
    "age_min": 9,
    "age_max": 9,
    "language": "en",
    "target_words": 1500,
    "narrative_family": "exploration_mystery",
    "reading_mode": "INDEPENDENT_READER",
    "relative_length_class": "STANDARD",
    "protagonist": "Mira, age 9, observant and curious but not unusually expert",
    "setting": "A small public nature center with a garden trail, map board, labels, notebooks, and ordinary tools.",
    "theme": "Careful observation can turn uncertainty into understanding.",
    "premise": "Before a family nature walk begins, Mira notices that one route marker on the center's map no longer matches the real garden trail. She investigates what changed and must decide how to correct the route before visitors follow it.",
    "constraints": [
        "Use age-appropriate vocabulary, reasoning, pacing, and emotional intensity for an independent 9-year-old reader.",
        "No combat, supernatural powers, or frightening danger.",
        "The solution must emerge from at least two previously established observations.",
        "Include one reasonable false hypothesis that is rejected by evidence.",
        "Do not make an adult solve the central problem for Mira.",
        "Preserve continuity across the complete story and the Narrative Architect's chosen SceneGraph."
    ],
}

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

ARCHITECT_PROMPT = """
You are the Narrative Architect for one LUMI story.

Create an immutable StoryContract and a dynamic SceneGraph. The scene count is not
fixed. Choose the minimum sufficient number of scenes that best protects causal
coherence, pacing, age fit, required length, clue/evidence progression, payoff, and
resolution.

Rules:
- Choose 2-12 scenes.
- Do not prefer six or any other count by default.
- Every scene must have a distinct narrative job.
- Exactly one scene must have role PAYOFF.
- The final scene must have role RESOLUTION.
- PAYOFF must occur before RESOLUTION.
- Do not create micro-scenes merely to increase scene count.
- Do not overload a scene with incompatible narrative jobs merely to reduce scene count.
- Preserve every brief constraint.
- Keep one central protagonist goal and one central problem unless the brief requires otherwise.
- Facts, clues, knowledge and consequences must accumulate rather than reset.
- Each scene must list prior_evidence for any important inference or dependency.
- relative_weight values are positive pacing weights; they need not total 100.

Return JSON only:
{
  "story_title": "",
  "scene_count_rationale": "",
  "story_contract": {
    "protagonist_goal": "",
    "central_problem": "",
    "solution_principle": "",
    "theme_thread": "",
    "ending_state": "",
    "must_preserve": [""],
    "must_not_happen": [""]
  },
  "scenes": [
    {
      "index": 1,
      "role": "SETUP",
      "relative_weight": 20,
      "purpose": "",
      "beats": ["", ""],
      "prior_evidence": [],
      "must_include": [""],
      "must_not_do": [""],
      "handoff": ""
    }
  ]
}
""".strip()

WHOLE_DRAFT_PROMPT = """
You are the Story Writer for LUMI.

Write the complete story in ONE generation from the immutable StoryContract and the
entire dynamic SceneGraph. You are not writing one isolated scene at a time.

Rules:
- Produce one coherent story from beginning to end.
- Follow the SceneGraph exactly enough that every scene has its declared narrative job.
- Preserve all established facts and dependencies.
- Do not reset knowledge between scenes.
- Do not perform PAYOFF work early.
- The final RESOLUTION must follow from the PAYOFF and close the main problem.
- Keep the requested age/reading level natural.
- Reach the target length through meaningful action, observation, dialogue, consequence
  and sensory detail, not filler or recap.
- Avoid re-explaining the same clue or event unless the repetition has a new narrative purpose.
- Scene boundaries are metadata, not chapter headings for the reader. Do not print labels
  like "Scene 1" inside prose.

Return JSON only:
{
  "title": "",
  "scenes": [
    {
      "index": 1,
      "role": "SETUP",
      "prose": ""
    }
  ]
}
""".strip()

FINAL_JUDGE_PROMPT = """
You are the final production gate for a complete LUMI story.

Judge ONLY the CURRENT final story against its immutable StoryContract, SceneGraph and
original brief. Historical repair attempts are intentionally not supplied. Do not invent
a defect from earlier versions.

Score each criterion 1-5:
- instruction_following
- coherence
- character_consistency
- age_appropriateness
- creativity
- style_quality
- continuity
- ending_quality

A 4 means solid production quality. A 5 means exceptional.

Acceptance:
- average >= 4.0
- every criterion >= 3
- no critical failure

If rejected, identify the smallest repairable defect and its owner:
- PLAN: StoryContract or SceneGraph itself is defective
- PROSE: plan is sound but current prose is defective
- STATE: proposed canonical state would be unsupported or contradictory

Return JSON only:
{
  "scores": {
    "instruction_following": 1,
    "coherence": 1,
    "character_consistency": 1,
    "age_appropriateness": 1,
    "creativity": 1,
    "style_quality": 1,
    "continuity": 1,
    "ending_quality": 1
  },
  "critical_failures": [],
  "repair_targets": [
    {
      "owner": "PROSE",
      "scene": 1,
      "issue": ""
    }
  ],
  "summary": ""
}
""".strip()

PROSE_REPAIR_PROMPT = """
You are repairing one already-generated whole LUMI story.

The StoryContract and SceneGraph are immutable for this repair. Repair only the prose
defects listed by the final judge. Do not change scene roles, facts, clue ordering,
canonical outcomes, protagonist goal, or ending state.

Return the complete current draft again as JSON:
{
  "title": "",
  "scenes": [
    {"index": 1, "role": "SETUP", "prose": ""}
  ]
}
""".strip()

OUTCOME_PROMPT = """
You are the LUMI typed StateMutationProposal extractor.

Read the ACCEPTED final story and the APPLICATION-OWNED STATE AUTHORITY contract.
You may propose only mutations that exactly match one allowed tuple:
(mutation_type, entity_ref, field_key).

Rules:
- Never invent a database field, entity, operation, persistence class, or mutation type.
- Every proposal must cite one or more supporting scene indexes.
- Evidence support is necessary but not sufficient: emit a mutation only when the story
  establishes an end-of-story state that the authority explicitly allows to persist.
- Do NOT persist transient emotions, temporary current activity, brief handling of an item,
  generic supportive behavior, descriptive details, or intermediate hypotheses unless an
  allowed mutation explicitly represents them.
- Do not infer secret knowledge for a character that the character never learned.
- Do not turn unresolved possibilities into facts.
- Do not write to a database.
- Keep proposals minimal. Omit an allowed mutation when the story does not establish it.

Return JSON only:
{
  "authority_revision": "",
  "mutations": [
    {
      "mutation_type": "",
      "entity_ref": "",
      "field_key": "",
      "value": null,
      "evidence_scenes": [1],
      "reason": ""
    }
  ]
}
""".strip()


def validate_plan(plan: dict[str, Any], spec: StorySpec) -> list[str]:
    errors: list[str] = []
    contract = plan.get("story_contract")
    scenes = plan.get("scenes")

    if not isinstance(contract, dict):
        errors.append("story_contract_missing")
    if not isinstance(scenes, list):
        return errors + ["scenes_missing"]
    if not 2 <= len(scenes) <= 12:
        errors.append(f"scene_count_out_of_range:{len(scenes)}")

    expected_indexes = list(range(1, len(scenes) + 1))
    actual_indexes = [s.get("index") if isinstance(s, dict) else None for s in scenes]
    if actual_indexes != expected_indexes:
        errors.append("scene_indexes_not_contiguous")

    roles: list[str] = []
    purposes: set[str] = set()
    total_weight = 0

    for i, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"scene_{i}_not_object")
            continue
        role = str(scene.get("role") or "").strip().upper()
        roles.append(role)
        purpose = str(scene.get("purpose") or "").strip()
        if not purpose:
            errors.append(f"scene_{i}_purpose_missing")
        elif purpose.casefold() in purposes:
            errors.append(f"scene_{i}_duplicate_purpose")
        purposes.add(purpose.casefold())

        weight = scene.get("relative_weight")
        if not isinstance(weight, int) or isinstance(weight, bool) or weight <= 0:
            errors.append(f"scene_{i}_relative_weight_invalid")
        else:
            total_weight += weight

        beats = scene.get("beats")
        if not isinstance(beats, list) or not 1 <= len(beats) <= 5:
            errors.append(f"scene_{i}_beats_invalid")

        prior = scene.get("prior_evidence")
        if not isinstance(prior, list):
            errors.append(f"scene_{i}_prior_evidence_invalid")

    if roles.count("PAYOFF") != 1:
        errors.append(f"payoff_role_count_invalid:{roles.count('PAYOFF')}")
    if not roles or roles[-1] != "RESOLUTION":
        errors.append("final_scene_not_resolution")
    if "PAYOFF" in roles and roles.index("PAYOFF") >= len(roles) - 1:
        errors.append("payoff_must_precede_resolution")
    if total_weight <= 0:
        errors.append("relative_weight_sum_invalid")

    if not isinstance(plan.get("scene_count_rationale"), str) or not plan["scene_count_rationale"].strip():
        errors.append("scene_count_rationale_missing")

    if spec.target_words < 300 and len(scenes) > 6:
        errors.append("implausible_fragmentation_for_very_short_story")

    return errors


def validate_draft(draft: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scenes = draft.get("scenes")
    planned = plan["scenes"]
    if not isinstance(scenes, list):
        return ["draft_scenes_missing"]
    if len(scenes) != len(planned):
        errors.append(f"draft_scene_count_mismatch:{len(scenes)}!={len(planned)}")
        return errors

    for expected, actual in zip(planned, scenes):
        if not isinstance(actual, dict):
            errors.append(f"draft_scene_{expected['index']}_not_object")
            continue
        if actual.get("index") != expected.get("index"):
            errors.append(f"draft_scene_index_mismatch:{actual.get('index')}!={expected.get('index')}")
        if str(actual.get("role") or "").upper() != str(expected.get("role") or "").upper():
            errors.append(f"draft_scene_{expected['index']}_role_mismatch")
        if not isinstance(actual.get("prose"), str) or not actual["prose"].strip():
            errors.append(f"draft_scene_{expected['index']}_prose_missing")
    return errors


def assemble_story(draft: dict[str, Any]) -> str:
    return "\n\n".join(str(s["prose"]).strip() for s in draft["scenes"])


def allocate_scene_word_targets(plan: dict[str, Any], target_words: int) -> list[dict[str, int]]:
    scenes = plan["scenes"]
    weights = [int(scene["relative_weight"]) for scene in scenes]
    total_weight = sum(weights)
    if total_weight <= 0:
        raise RuntimeError("scene_weight_sum_invalid")
    exact = [target_words * weight / total_weight for weight in weights]
    targets = [int(value) for value in exact]
    remainder = target_words - sum(targets)
    order = sorted(
        range(len(exact)),
        key=lambda index: exact[index] - int(exact[index]),
        reverse=True,
    )
    for index in range(remainder):
        targets[order[index % len(order)]] += 1
    return [
        {"scene": scene["index"], "target_words": targets[index]}
        for index, scene in enumerate(scenes)
    ]


def whole_story_questions() -> dict[str, dict[str, Any]]:
    checks = {
        "causal_chain": (
            "Does the complete story form one causal chain in which each scene materially enables, constrains, advances, or resolves later work?",
            "The full story forms one causal chain.",
            "The story contains disconnected, redundant, or unjustified narrative jumps.",
        ),
        "goal_continuity": (
            "Does the protagonist keep one coherent central goal and motivation throughout the story?",
            "The central goal remains coherent throughout.",
            "The goal disappears or changes without narrative cause.",
        ),
        "evidence_progression": (
            "Are clues, observations, decisions and consequences established before they are used, with knowledge accumulating rather than resetting?",
            "Information progresses cumulatively and dependencies are established before use.",
            "The story uses unexplained dependencies, future leakage, or resets established knowledge.",
        ),
        "no_contradictions": (
            "Is the final current story free of material factual contradictions?",
            "No material factual contradiction exists.",
            "At least two material claims cannot both be true.",
        ),
        "no_redundant_events": (
            "Does each scene perform a distinct narrative job rather than repeating already-completed events or discoveries?",
            "Scenes advance distinct narrative work.",
            "One or more scenes repeat already-completed narrative work without a new purpose.",
        ),
        "payoff_resolution": (
            "Is the PAYOFF earned by prior setup, and does the final RESOLUTION coherently close the main problem?",
            "The payoff is earned and the resolution follows from it.",
            "The payoff is unearned, premature, contradictory, or the main problem remains unresolved.",
        ),
        "decomposition_fitness": (
            "Does the chosen scene decomposition fit the completed story without obvious fragmentation or overloaded transitions?",
            "The decomposition remains structurally justified in prose.",
            "The prose reveals redundant fragmentation, an overloaded scene, or a missing causal step.",
        ),
    }
    questions = {
        key: noul_question(instructions, true_criteria=yes, false_criteria=no)
        for key, (instructions, yes, no) in checks.items()
    }
    questions["next_action"] = choice_question(
        "Choose the safest action after reviewing the complete current story.",
        {
            "CONTINUE": "The story is coherent enough for final semantic judgment.",
            "TARGETED_REPAIR": "A bounded prose defect should be repaired.",
            "ESCALATE": "The defect belongs to the plan/state layer or is too broad for prose-only repair.",
        },
    )
    return questions


def run_jev(
    api_key: str,
    spec: StorySpec,
    plan: dict[str, Any],
    draft: dict[str, Any],
) -> dict[str, Any]:
    questions = whole_story_questions()
    story = assemble_story(draft)
    body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "Complete current LUMI whole-draft story.",
            "story_brief": build_labeled_brief(spec),
            "story_contract": plan["story_contract"],
            "scene_graph": plan["scenes"],
            "story": story,
        },
        questions=questions,
    )
    return summarize_jev(
        body,
        question_ids=[key for key in questions if key != "next_action"],
    )


def validate_judge(payload: dict[str, Any], scene_count: int) -> dict[str, Any]:
    raw = payload.get("scores")
    if not isinstance(raw, dict):
        raise RuntimeError("judge_scores_missing")
    scores: dict[str, int] = {}
    for key in FINAL_CRITERIA:
        value = raw.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise RuntimeError(f"judge_score_invalid:{key}:{value!r}")
        scores[key] = value

    critical = payload.get("critical_failures")
    targets = payload.get("repair_targets")
    if not isinstance(critical, list):
        raise RuntimeError("judge_critical_failures_invalid")
    if not isinstance(targets, list):
        raise RuntimeError("judge_repair_targets_invalid")

    normalized_targets: list[dict[str, Any]] = []
    for target in targets:
        if not isinstance(target, dict):
            raise RuntimeError("judge_repair_target_not_object")
        owner = str(target.get("owner") or "").upper()
        if owner not in {"PLAN", "PROSE", "STATE"}:
            raise RuntimeError(f"judge_repair_owner_invalid:{owner}")
        scene = target.get("scene")
        if scene is not None and (
            not isinstance(scene, int)
            or isinstance(scene, bool)
            or not 1 <= scene <= scene_count
        ):
            raise RuntimeError(f"judge_repair_scene_invalid:{scene!r}")
        issue = str(target.get("issue") or "").strip()
        if not issue:
            raise RuntimeError("judge_repair_issue_missing")
        normalized_targets.append({"owner": owner, "scene": scene, "issue": issue})

    average = round(sum(scores.values()) / len(scores), 3)
    minimum = min(scores.values())
    return {
        "scores": scores,
        "average": average,
        "minimum": minimum,
        "critical_failures": critical,
        "repair_targets": normalized_targets,
        "summary": str(payload.get("summary") or ""),
        "accepted": average >= 4.0 and minimum >= 3 and not critical,
    }


def run_judge(
    api_key: str,
    judge_model: str,
    spec: StorySpec,
    plan: dict[str, Any],
    draft: dict[str, Any],
    jev: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    user = (
        "ORIGINAL BRIEF\n"
        + build_labeled_brief(spec)
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nDYNAMIC SCENE GRAPH\n"
        + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
        + "\n\nCURRENT WHOLE-STORY JEV EVIDENCE\n"
        + json.dumps(jev, ensure_ascii=False, indent=2)
        + "\n\nCURRENT FINAL STORY\n"
        + assemble_story(draft)
    )
    payload, body, _, parse_failures = call_structured_json_with_retry(
        api_key=api_key,
        model=judge_model,
        system_prompt=FINAL_JUDGE_PROMPT,
        user_prompt=user,
        temperature=0.0,
        max_tokens=2500,
        seed=None,
        request_class="judge",
    )
    result = validate_judge(payload, len(plan["scenes"]))
    return result, {
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "parse_failures": parse_failures,
    }


def validate_outcome(
    outcome: dict[str, Any],
    scene_count: int,
    authority: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    expected_revision = str(authority.get("revision") or "")
    if outcome.get("authority_revision") != expected_revision:
        errors.append("outcome_authority_revision_mismatch")

    allowed_rows = authority.get("allowed_mutations")
    if not isinstance(allowed_rows, list) or not allowed_rows:
        return errors + ["state_authority_allowed_mutations_missing"]

    allowed: set[tuple[str, str, str]] = set()
    for index, row in enumerate(allowed_rows):
        if not isinstance(row, dict):
            errors.append(f"state_authority_row_{index}_not_object")
            continue
        key = (
            str(row.get("mutation_type") or ""),
            str(row.get("entity_ref") or ""),
            str(row.get("field_key") or ""),
        )
        if not all(key):
            errors.append(f"state_authority_row_{index}_invalid")
            continue
        allowed.add(key)

    mutations = outcome.get("mutations")
    if not isinstance(mutations, list):
        return errors + ["outcome_mutations_not_list"]

    seen: set[tuple[str, str, str, str]] = set()
    for index, row in enumerate(mutations):
        if not isinstance(row, dict):
            errors.append(f"mutation_{index}_not_object")
            continue

        key = (
            str(row.get("mutation_type") or ""),
            str(row.get("entity_ref") or ""),
            str(row.get("field_key") or ""),
        )
        if key not in allowed:
            errors.append(
                "mutation_not_authorized:"
                + "|".join(key)
            )

        scenes = row.get("evidence_scenes")
        if not isinstance(scenes, list) or not scenes:
            errors.append(f"mutation_{index}_evidence_missing")
        else:
            for scene in scenes:
                if (
                    not isinstance(scene, int)
                    or isinstance(scene, bool)
                    or not 1 <= scene <= scene_count
                ):
                    errors.append(f"mutation_{index}_invalid_evidence_scene:{scene!r}")

        reason = row.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"mutation_{index}_reason_missing")

        value_identity = json.dumps(
            row.get("value"),
            sort_keys=True,
            ensure_ascii=False,
        )
        duplicate_key = (*key, value_identity)
        if duplicate_key in seen:
            errors.append(f"mutation_{index}_duplicate")
        seen.add(duplicate_key)

    return errors


def sum_costs(*costs: Any) -> float:
    total = 0.0
    for cost in costs:
        if isinstance(cost, (int, float)):
            total += float(cost)
        elif isinstance(cost, dict) and isinstance(cost.get("usd"), (int, float)):
            total += float(cost["usd"])
    return total


def load_story_spec(path: str | None) -> tuple[StorySpec, str]:
    if path:
        return StorySpec.model_validate(load_yaml(Path(path))), path
    return StorySpec.model_validate(BUILTIN_SPEC), "<builtin-v5-prototype-spec>"


def load_state_authority(path: str | None) -> tuple[dict[str, Any], str]:
    if path:
        authority_path = Path(path)
        authority = json.loads(authority_path.read_text(encoding="utf-8"))
        return authority, path

    authority = {
        "schema_version": "state-mutation-authority.v1",
        "revision": "prototype-minimal-safe-r1",
        "entities": [
            {"entity_ref": "CHARACTER:PROTAGONIST", "entity_kind": "CHARACTER"},
            {"entity_ref": "SAGA:CURRENT", "entity_kind": "SAGA"},
            {"entity_ref": "OPPORTUNITY:CURRENT", "entity_kind": "OPPORTUNITY"},
        ],
        "allowed_mutations": [
            {
                "mutation_type": "CHARACTER_KNOWLEDGE_ADD",
                "entity_ref": "CHARACTER:PROTAGONIST",
                "field_key": "knowledge.discoveries",
                "persistence": "PERSISTENT",
            },
            {
                "mutation_type": "THREAD_RESOLVE",
                "entity_ref": "SAGA:CURRENT",
                "field_key": "threads.resolved",
                "persistence": "PERSISTENT",
            },
            {
                "mutation_type": "THREAD_OPEN",
                "entity_ref": "SAGA:CURRENT",
                "field_key": "threads.open",
                "persistence": "PERSISTENT",
            },
            {
                "mutation_type": "MEMORY_CANDIDATE_ADD",
                "entity_ref": "CHARACTER:PROTAGONIST",
                "field_key": "memory.candidates",
                "persistence": "REVIEWABLE",
            },
            {
                "mutation_type": "OPPORTUNITY_CONSUME",
                "entity_ref": "OPPORTUNITY:CURRENT",
                "field_key": "status",
                "persistence": "PERSISTENT",
            },
        ],
    }
    return authority, "<builtin-minimal-safe-state-authority>"


def run(args: argparse.Namespace) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY")

    spec, spec_source = load_story_spec(args.spec)
    state_authority, state_authority_source = load_state_authority(args.state_authority)
    brief = build_labeled_brief(spec)
    started = time.perf_counter()

    plan, plan_body, _, plan_parse = call_structured_json_with_retry(
        api_key=api_key,
        model=args.architect,
        system_prompt=ARCHITECT_PROMPT,
        user_prompt="Create the story architecture.\n\nSTORY BRIEF\n" + brief,
        temperature=0.2,
        max_tokens=None,
        seed=41,
        request_class="story_plan",
    )
    plan_errors = validate_plan(plan, spec)
    if plan_errors:
        raise RuntimeError("PLAN_INVALID:" + ",".join(plan_errors))

    min_words = round(spec.target_words * 0.75)
    max_words = round(spec.target_words * 1.25)
    scene_word_targets = allocate_scene_word_targets(plan, spec.target_words)
    draft_user = (
        "STORY BRIEF\n"
        + brief
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nDYNAMIC SCENE GRAPH\n"
        + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
        + "\n\nNORMALIZED SCENE WORD TARGETS\n"
        + json.dumps(scene_word_targets, ensure_ascii=False, indent=2)
        + f"\n\nTARGET TOTAL WORDS: {spec.target_words}"
        + f"\nHARD ACCEPTABLE TOTAL RANGE: {min_words}-{max_words} words."
        + "\nStay close to each scene target and DO NOT exceed the hard total maximum."
    )
    draft, draft_body, _, draft_parse = call_structured_json_with_retry(
        api_key=api_key,
        model=args.writer,
        system_prompt=WHOLE_DRAFT_PROMPT,
        user_prompt=draft_user,
        temperature=0.6,
        max_tokens=None,
        seed=42,
        request_class="scene_story",
    )
    draft_errors = validate_draft(draft, plan)
    if draft_errors:
        raise RuntimeError("DRAFT_INVALID:" + ",".join(draft_errors))

    story = assemble_story(draft)
    word_count = count_words(story)
    repeat_ratio = repeated_ngram_ratio(story, 8)
    deterministic_errors: list[str] = []
    if word_count < min_words:
        deterministic_errors.append(f"below_total_word_budget:{word_count}<{min_words}")
    if word_count > max_words:
        deterministic_errors.append(f"above_total_word_budget:{word_count}>{max_words}")
    if repeat_ratio > 0.02:
        deterministic_errors.append(f"repeat_8gram_ratio_high:{repeat_ratio}>0.02")

    length_normalization = None
    only_length_error = bool(deterministic_errors) and all(
        error.startswith("below_total_word_budget:")
        or error.startswith("above_total_word_budget:")
        for error in deterministic_errors
    )
    if only_length_error:
        normalize_user = (
            "The current whole draft is structurally valid but outside the application-owned word range. "
            "Normalize LENGTH ONLY. Preserve the same title, scene count, roles, facts, clue order, "
            "character decisions, payoff, resolution, and ending state. Remove redundant description, "
            "recap, and repeated explanation before removing causal content. Do not add new events.\n\n"
            + f"TARGET TOTAL WORDS: {spec.target_words}\n"
            + f"HARD ACCEPTABLE TOTAL RANGE: {min_words}-{max_words}\n"
            + "NORMALIZED SCENE WORD TARGETS:\n"
            + json.dumps(scene_word_targets, ensure_ascii=False, indent=2)
            + "\n\nCURRENT DRAFT JSON:\n"
            + json.dumps(draft, ensure_ascii=False, indent=2)
        )
        normalized, normalize_body, _, normalize_parse = call_structured_json_with_retry(
            api_key=api_key,
            model=args.writer,
            system_prompt=WHOLE_DRAFT_PROMPT,
            user_prompt=normalize_user,
            temperature=0.2,
            max_tokens=None,
            seed=4201,
            request_class="scene_repair",
        )
        normalize_schema_errors = validate_draft(normalized, plan)
        normalized_story = assemble_story(normalized) if not normalize_schema_errors else ""
        normalized_words = count_words(normalized_story) if normalized_story else 0
        normalized_repeat = repeated_ngram_ratio(normalized_story, 8) if normalized_story else 0.0
        normalized_deterministic: list[str] = []
        if not normalize_schema_errors:
            if normalized_words < min_words:
                normalized_deterministic.append(
                    f"below_total_word_budget:{normalized_words}<{min_words}"
                )
            if normalized_words > max_words:
                normalized_deterministic.append(
                    f"above_total_word_budget:{normalized_words}>{max_words}"
                )
            if normalized_repeat > 0.02:
                normalized_deterministic.append(
                    f"repeat_8gram_ratio_high:{normalized_repeat}>0.02"
                )
        length_normalization = {
            "attempted": True,
            "before_words": word_count,
            "after_words": normalized_words,
            "schema_errors": normalize_schema_errors,
            "deterministic_errors_after": normalized_deterministic,
            "usage": parse_usage(normalize_body).model_dump(mode="json"),
            "cost": parse_cost(normalize_body).model_dump(mode="json"),
            "parse_failures": normalize_parse,
        }
        if not normalize_schema_errors and not normalized_deterministic:
            draft = normalized
            story = normalized_story
            word_count = normalized_words
            repeat_ratio = normalized_repeat
            deterministic_errors = []

    jev = run_jev(api_key, spec, plan, draft)
    judge, judge_meta = run_judge(api_key, args.judge, spec, plan, draft, jev)

    repair = None
    if not deterministic_errors and not judge["accepted"]:
        owners = {target["owner"] for target in judge["repair_targets"]}
        if owners and owners <= {"PROSE"}:
            repair_input = (
                "IMMUTABLE STORY CONTRACT\n"
                + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
                + "\n\nIMMUTABLE SCENE GRAPH\n"
                + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
                + "\n\nCURRENT DRAFT\n"
                + json.dumps(draft, ensure_ascii=False, indent=2)
                + "\n\nPROSE DEFECTS\n"
                + json.dumps(judge["repair_targets"], ensure_ascii=False, indent=2)
            )
            repaired, repair_body, _, repair_parse = call_structured_json_with_retry(
                api_key=api_key,
                model=args.writer,
                system_prompt=PROSE_REPAIR_PROMPT,
                user_prompt=repair_input,
                temperature=0.2,
                max_tokens=None,
                seed=43,
                request_class="scene_repair",
            )
            repair_errors = validate_draft(repaired, plan)
            if not repair_errors:
                repaired_jev = run_jev(api_key, spec, plan, repaired)
                repaired_judge, repaired_judge_meta = run_judge(
                    api_key, args.judge, spec, plan, repaired, repaired_jev
                )
                repair = {
                    "attempted": True,
                    "parse_failures": repair_parse,
                    "cost": parse_cost(repair_body).model_dump(mode="json"),
                    "usage": parse_usage(repair_body).model_dump(mode="json"),
                    "jev": repaired_jev,
                    "judge": repaired_judge,
                    "judge_meta": repaired_judge_meta,
                }
                if repaired_judge["accepted"]:
                    draft = repaired
                    story = assemble_story(draft)
                    word_count = count_words(story)
                    repeat_ratio = repeated_ngram_ratio(story, 8)
                    jev = repaired_jev
                    judge = repaired_judge
                    judge_meta = repaired_judge_meta

    accepted = not deterministic_errors and judge["accepted"] and not jev.get("below_threshold")

    outcome = None
    outcome_errors: list[str] = []
    outcome_meta: dict[str, Any] | None = None
    if accepted:
        outcome_user = (
            "APPLICATION-OWNED STATE AUTHORITY\n"
            + json.dumps(state_authority, ensure_ascii=False, indent=2)
            + "\n\nIMMUTABLE STORY CONTRACT\n"
            + json.dumps(plan["story_contract"], ensure_ascii=False, indent=2)
            + "\n\nSCENE GRAPH\n"
            + json.dumps(plan["scenes"], ensure_ascii=False, indent=2)
            + "\n\nACCEPTED FINAL STORY BY SCENE\n"
            + json.dumps(draft["scenes"], ensure_ascii=False, indent=2)
        )
        outcome, outcome_body, _, outcome_parse = call_structured_json_with_retry(
            api_key=api_key,
            model=args.outcome_extractor,
            system_prompt=OUTCOME_PROMPT,
            user_prompt=outcome_user,
            temperature=0.0,
            max_tokens=3500,
            seed=44,
            request_class="structured_large",
        )
        outcome_errors = validate_outcome(
            outcome,
            len(plan["scenes"]),
            state_authority,
        )
        outcome_meta = {
            "parse_failures": outcome_parse,
            "usage": parse_usage(outcome_body).model_dump(mode="json"),
            "cost": parse_cost(outcome_body).model_dump(mode="json"),
            "commit_ready": not outcome_errors,
            "database_written": False,
        }
        accepted = accepted and not outcome_errors

    plan_cost = parse_cost(plan_body).model_dump(mode="json")
    draft_cost = parse_cost(draft_body).model_dump(mode="json")
    total_cost = sum_costs(
        plan_cost,
        draft_cost,
        judge_meta["cost"],
        outcome_meta["cost"] if outcome_meta else None,
        repair["cost"] if repair else None,
        length_normalization["cost"] if length_normalization else None,
    )

    result = {
        "protocol_version": PROTOCOL_VERSION,
        "accepted": accepted,
        "models": {
            "architect": args.architect,
            "writer": args.writer,
            "continuity_evaluator": DEFAULT_CONTINUITY,
            "semantic_judge": args.judge,
            "outcome_extractor": args.outcome_extractor,
        },
        "spec": spec_source,
        "state_authority_source": state_authority_source,
        "state_authority": state_authority,
        "plan": plan,
        "plan_parse_failures": plan_parse,
        "draft": draft,
        "draft_parse_failures": draft_parse,
        "story": story,
        "metrics": {
            "scene_count": len(plan["scenes"]),
            "word_count": word_count,
            "target_words": spec.target_words,
            "scene_word_targets": scene_word_targets,
            "repeat_8gram_ratio": repeat_ratio,
            "deterministic_errors": deterministic_errors,
        },
        "whole_story_jev": jev,
        "final_judge": judge,
        "repair": repair,
        "length_normalization": length_normalization,
        "story_outcome": outcome,
        "story_outcome_validation_errors": outcome_errors,
        "story_outcome_meta": outcome_meta,
        "database_commit": {
            "mode": "DRY_RUN_ONLY",
            "attempted": False,
            "reason": "Prototype emits validated StoryOutcome proposal; real LUMI application owns atomic/idempotent DB commit.",
        },
        "costs": {
            "plan": plan_cost,
            "whole_draft": draft_cost,
            "final_judge": judge_meta["cost"],
            "outcome_extraction": outcome_meta["cost"] if outcome_meta else None,
            "repair": repair["cost"] if repair else None,
            "length_normalization": (
                length_normalization["cost"] if length_normalization else None
            ),
            "known_usd_total_excluding_jev_if_unreported": round(total_cost, 9),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    return result


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="LUMI v5 whole-draft story prototype: Architect -> Whole Draft -> JEV -> Judge -> Outcome."
    )
    parser.add_argument("--spec", default=DEFAULT_SPEC)
    parser.add_argument("--architect", default=DEFAULT_ARCHITECT)
    parser.add_argument("--writer", default=DEFAULT_WRITER)
    parser.add_argument("--judge", default=DEFAULT_JUDGE)
    parser.add_argument("--outcome-extractor", default=DEFAULT_OUTCOME_EXTRACTOR)
    parser.add_argument("--state-authority", default=None)
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()

    result = run(args)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    story_path = output.with_suffix(".story.txt")
    story_path.write_text(
        str(result["draft"].get("title") or result["plan"].get("story_title") or "LUMI Story")
        + "\n\n"
        + result["story"],
        encoding="utf-8",
    )
    outcome_path = output.with_suffix(".outcome.json")
    outcome_path.write_text(
        json.dumps(result.get("story_outcome"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "accepted": result["accepted"],
                "scene_count": result["metrics"]["scene_count"],
                "word_count": result["metrics"]["word_count"],
                "target_words": result["metrics"]["target_words"],
                "repeat_8gram_ratio": result["metrics"]["repeat_8gram_ratio"],
                "jev_below_threshold": result["whole_story_jev"].get("below_threshold"),
                "judge_average": result["final_judge"]["average"],
                "judge_minimum": result["final_judge"]["minimum"],
                "outcome_commit_ready": (
                    result["story_outcome_meta"]["commit_ready"]
                    if result["story_outcome_meta"]
                    else False
                ),
                "database_written": False,
                "costs": result["costs"],
                "elapsed_seconds": result["elapsed_seconds"],
                "result_path": str(output),
                "story_path": str(story_path),
                "outcome_path": str(outcome_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        flush=True,
    )

    if not result["accepted"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
