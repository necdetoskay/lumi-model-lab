from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.generate import call_openrouter, load_yaml, parse_cost, parse_usage
from src.generator_scene_first_calibration import _brief_text
from src.model_registry import require_judge_runtime_profile, require_qualification_runtime_profile
from src.openrouter_jev import call_openrouter_jev, choice_question, choice_value, load_jev_profile, noul_probability, noul_question
from src.schemas import StorySpec

PLAN_PROMPT = Path("prompts/story_scene_plan_en_v1.md")
HAIKU_PROMPT = Path("prompts/story_scene_plan_judge_en_v1.md")
DEFAULT_SPEC = Path("data/specifications/benchmark_en/01_exploration_mystery.yaml")

HAIKU_CRITERIA = (
    "causal_continuity",
    "protagonist_goal_continuity",
    "constraint_coverage",
    "information_progression",
    "no_unexplained_dependencies",
    "no_early_resolution",
    "ending_coherence",
)

JEV_CHECKS = {
    "causal_continuity": ("Do all six scenes form one causal chain in which each scene follows from prior state and materially enables or constrains the next?", "Scenes form one causal chain.", "One or more transitions are arbitrary or disconnected."),
    "goal_continuity": ("Does the protagonist keep one stable central goal across the six scenes, with scene actions motivated by it?", "The central goal remains stable.", "The goal changes, disappears, or fails to motivate actions."),
    "constraint_coverage": ("Does the plan preserve and schedule every required constraint from the story brief?", "All required constraints are represented.", "At least one required constraint is missing or impossible to satisfy."),
    "information_progression": ("Do clues, observations, decisions, and consequences accumulate without resetting knowledge or repeating the same narrative function?", "Information progresses cumulatively.", "Knowledge resets or narrative functions repeat without progression."),
    "no_unexplained_dependencies": ("Can every important later event be explained using elements established before they are needed?", "Later events depend only on previously established elements.", "A later event requires an unexplained character, object, location, fact, power, or clue."),
    "no_early_resolution": ("Does the plan keep the central problem unresolved through Scene 4 and reserve the decisive solution for Scene 5?", "The decisive solution is reserved for Scene 5.", "The central problem is solved before Scene 5 or later payoff leaks early."),
    "ending_coherence": ("Does Scene 6 resolve consequences from the Scene 5 payoff while leaving at most a small future-discovery hook?", "Scene 6 resolves the main consequences coherently.", "Scene 6 contradicts the payoff, opens a new main problem, or leaves the main thread unresolved."),
}

def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Response did not contain a JSON object.")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise RuntimeError("Response JSON must be an object.")
    return value

def validate_plan(plan: dict[str, Any], spec: StorySpec) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.get("story_title"), str) or not plan["story_title"].strip():
        errors.append("story_title_missing")
    contract = plan.get("story_contract")
    required_fields = ("protagonist_goal", "central_problem", "solution_principle", "theme_thread", "ending_state")
    if not isinstance(contract, dict):
        errors.append("story_contract_missing")
    else:
        for field in required_fields:
            if not isinstance(contract.get(field), str) or not contract[field].strip():
                errors.append(f"story_contract_{field}_missing")
        constraints = contract.get("required_constraints")
        if not isinstance(constraints, list) or len(constraints) < len(spec.constraints):
            errors.append("required_constraints_underrepresented")
        prohibited = contract.get("prohibited_events")
        if not isinstance(prohibited, list) or not prohibited:
            errors.append("prohibited_events_missing")
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or len(scenes) != 6:
        errors.append("scene_count_not_6")
        return errors
    if [s.get("index") if isinstance(s, dict) else None for s in scenes] != list(range(1, 7)):
        errors.append("scene_indexes_not_1_to_6")
    purposes, handoffs = [], []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"scene_{index}_not_object")
            continue
        for field in ("purpose", "entry_state", "handoff"):
            if not isinstance(scene.get(field), str) or not scene[field].strip():
                errors.append(f"scene_{index}_{field}_missing")
        for field in ("beats", "must_include", "must_not_do", "open_threads_after"):
            value = scene.get(field)
            if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
                errors.append(f"scene_{index}_{field}_invalid")
        beats = scene.get("beats")
        if isinstance(beats, list) and not 2 <= len(beats) <= 4:
            errors.append(f"scene_{index}_beats_out_of_range")
        purposes.append(str(scene.get("purpose") or "").strip().casefold())
        handoffs.append(str(scene.get("handoff") or "").strip().casefold())
    if len(purposes) != len(set(purposes)):
        errors.append("duplicate_scene_purpose")
    if len(handoffs) != len(set(handoffs)):
        errors.append("duplicate_scene_handoff")
    return errors

def build_jev_questions() -> dict[str, dict[str, Any]]:
    questions = {}
    for question_id, (instructions, yes, no) in JEV_CHECKS.items():
        questions[question_id] = noul_question(instructions, true_criteria=yes, false_criteria=no)
    questions["next_action"] = choice_question(
        "Choose the safest next bounded action for this scene plan.",
        {
            "CONTINUE": "The plan is coherent enough to proceed.",
            "TARGETED_REPAIR": "A specific local continuity defect should be repaired.",
            "ESCALATE": "The plan is ambiguous or broadly risky and needs a stronger judge.",
        },
    )
    return questions

def summarize_jev(body: dict[str, Any]) -> dict[str, Any]:
    profile = load_jev_profile()
    answers = body["answers"]
    probabilities = {key: noul_probability(answers[key]) for key in JEV_CHECKS}
    below = {key: value for key, value in probabilities.items() if value < profile.positive_probability_threshold}
    next_action, confidence = choice_value(answers["next_action"])
    signal = "CONTINUE" if not below and next_action == "CONTINUE" else "REVIEW"
    return {
        "mode": profile.mode,
        "threshold": profile.positive_probability_threshold,
        "positive_probabilities": probabilities,
        "below_threshold": below,
        "next_action": next_action,
        "next_action_confidence": confidence,
        "shadow_signal": signal,
        "resolved_model": body.get("model"),
        "provider": body.get("provider"),
        "usage": body.get("usage") or {},
    }

def validate_haiku(payload: dict[str, Any]) -> dict[str, Any]:
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("Haiku plan judge scores missing.")
    normalized = {}
    for criterion in HAIKU_CRITERIA:
        score = scores.get(criterion)
        if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 5:
            raise RuntimeError(f"Invalid Haiku score for {criterion}: {score!r}")
        normalized[criterion] = score
    critical = payload.get("critical_failures")
    risks = payload.get("scene_risks")
    if not isinstance(critical, list) or not isinstance(risks, list):
        raise RuntimeError("Haiku plan judge returned invalid failure/risk arrays.")
    average = round(sum(normalized.values()) / len(normalized), 3)
    minimum = min(normalized.values())
    return {
        "scores": normalized, "average": average, "minimum": minimum,
        "critical_failures": critical, "scene_risks": risks,
        "summary": str(payload.get("summary") or ""),
        "accepted": average >= 4.0 and minimum >= 3 and not critical,
    }

def run(planner_model: str, jev_model: str, judge_model: str, spec_path: Path) -> dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")
    require_qualification_runtime_profile(planner_model)
    require_judge_runtime_profile(judge_model)
    jev_profile = load_jev_profile()
    if jev_model != jev_profile.model_id:
        raise RuntimeError(f"JEV model mismatch: expected {jev_profile.model_id}, got {jev_model}")
    spec = StorySpec.model_validate(load_yaml(spec_path))
    if spec.language.lower() != "en":
        raise RuntimeError("English-first scene-plan smoke requires language=en.")
    brief = _brief_text(spec)
    plan_text, plan_body, plan_request = call_openrouter(
        api_key=api_key, model=planner_model,
        system_prompt=PLAN_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=f"Create the immutable six-scene story plan.\n\nSTORY BRIEF\n{brief}",
        temperature=0.2, max_tokens=2500, seed=42,
        request_class="story_plan", structured_output=True,
    )
    plan = parse_json_object(plan_text)
    deterministic_errors = validate_plan(plan, spec)
    jev_body = call_openrouter_jev(
        api_key=api_key,
        state={
            "description": "English LUMI story brief, immutable StoryContract, and six-scene plan. Judge continuity only.",
            "story_brief": {"protagonist": spec.protagonist, "setting": spec.setting, "theme": spec.theme, "premise": spec.premise, "constraints": spec.constraints},
            "story_contract": plan.get("story_contract"),
            "scenes": plan.get("scenes"),
        },
        questions=build_jev_questions(),
    )
    jev = summarize_jev(jev_body)
    haiku_input = "STORY BRIEF\n" + brief + "\n\nPLAN\n" + json.dumps(plan, ensure_ascii=False, indent=2) + "\n\nJEV SHADOW SIGNAL\n" + json.dumps(jev, ensure_ascii=False, indent=2)
    haiku_text, haiku_body, haiku_request = call_openrouter(
        api_key=api_key, model=judge_model,
        system_prompt=HAIKU_PROMPT.read_text(encoding="utf-8").strip(),
        user_prompt=haiku_input, temperature=0.0, max_tokens=1800, seed=None,
        request_class="scene_plan_judge", structured_output=True,
    )
    haiku = validate_haiku(parse_json_object(haiku_text))
    accepted = not deterministic_errors and haiku["accepted"]
    return {
        "pipeline": "english_scene_plan_smoke_v1",
        "planner_model": planner_model, "jev_model": jev_model, "judge_model": judge_model,
        "spec": str(spec_path), "accepted": accepted, "deterministic_errors": deterministic_errors,
        "plan": plan, "jev": jev, "haiku": haiku,
        "costs": {"planner": parse_cost(plan_body).model_dump(mode="json"), "jev": (jev_body.get("usage") or {}).get("cost"), "haiku": parse_cost(haiku_body).model_dump(mode="json")},
        "usage": {"planner": parse_usage(plan_body).model_dump(mode="json"), "jev": jev_body.get("usage") or {}, "haiku": parse_usage(haiku_body).model_dump(mode="json")},
        "request_evidence": {"planner": {"reasoning": plan_request.get("reasoning"), "response_format": plan_request.get("response_format")}, "haiku": {"reasoning": haiku_request.get("reasoning"), "response_format": haiku_request.get("response_format")}},
    }

def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="English-first LUMI StoryContract and SceneGraph smoke.")
    parser.add_argument("--planner-model", default="qwen/qwen3.8-flash")
    parser.add_argument("--jev-model", default="typesafe/jev-1.13")
    parser.add_argument("--judge-model", default="anthropic/claude-haiku-4.5")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--output", default="runs/english_scene_plan_smoke/result.json")
    args = parser.parse_args()
    result = run(args.planner_model, args.jev_model, args.judge_model, Path(args.spec))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"accepted": result["accepted"], "deterministic_errors": result["deterministic_errors"], "jev": result["jev"], "haiku": result["haiku"], "costs": result["costs"], "output": str(output)}, ensure_ascii=False, indent=2))
    if not result["accepted"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()