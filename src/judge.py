from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
import yaml
from dotenv import load_dotenv
from rich.console import Console

from src.generate import OPENROUTER_URL, parse_cost, parse_usage
from src.model_registry import normalize_openrouter_request, require_judge_runtime_profile
from src.schemas import (
    GenerationRecord,
    JUDGE_CRITERIA,
    JudgeDecision,
    JudgePayload,
    JudgeRecord,
)

console = Console()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_generation(path: Path) -> GenerationRecord:
    with path.open("r", encoding="utf-8") as handle:
        return GenerationRecord.model_validate(json.load(handle))


def build_judge_input(record: GenerationRecord) -> str:
    spec = record.spec
    constraints = "\n".join(f"- {item}" for item in spec.constraints) or "- None"
    return f"""Evaluate this candidate story against the brief.

BRIEF
Language: {spec.language}
Age range: {spec.age_min}-{spec.age_max}
Target words: {spec.target_words}
Title hint: {spec.title_hint or 'None'}
Protagonist: {spec.protagonist}
Setting: {spec.setting}
Theme: {spec.theme}
Premise: {spec.premise}
Constraints:
{constraints}

CANDIDATE STORY
{record.story}
"""


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("Judge response did not contain a JSON object.")
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise RuntimeError("Judge response JSON must be an object.")
    return parsed


def validate_judge_payload(payload: dict[str, Any]) -> JudgePayload:
    result = JudgePayload.model_validate(payload)
    missing_scores = [criterion for criterion in JUDGE_CRITERIA if criterion not in result.scores]
    missing_reasons = [criterion for criterion in JUDGE_CRITERIA if criterion not in result.reasons]
    if missing_scores or missing_reasons:
        raise RuntimeError(
            f"Judge response is missing criteria. scores={missing_scores}, reasons={missing_reasons}"
        )
    for criterion in JUDGE_CRITERIA:
        score = result.scores[criterion]
        if not 1 <= score <= 5:
            raise RuntimeError(f"Judge score for {criterion} must be between 1 and 5; got {score}.")
        if not result.reasons[criterion].strip():
            raise RuntimeError(f"Judge reason for {criterion} is empty.")
    return result


def make_decision(
    result: JudgePayload,
    *,
    acceptance_threshold: float,
    minimum_criterion_score: int,
) -> JudgeDecision:
    scores = [result.scores[criterion] for criterion in JUDGE_CRITERIA]
    average_score = sum(scores) / len(scores)
    minimum_score = min(scores)
    reasons: list[str] = []
    if average_score < acceptance_threshold:
        reasons.append("average_score_below_threshold")
    if minimum_score < minimum_criterion_score:
        reasons.append("criterion_score_below_minimum")
    if result.critical_failures:
        reasons.append("critical_failures_present")
    return JudgeDecision(
        accepted=not reasons,
        average_score=round(average_score, 3),
        minimum_score=minimum_score,
        acceptance_threshold=acceptance_threshold,
        minimum_criterion_score=minimum_criterion_score,
        reasons=reasons,
    )


def call_judge(
    *,
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    reasoning: dict[str, Any] | None = None,
    response_format: dict[str, Any] | None = None,
) -> tuple[JudgePayload, dict[str, Any]]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if reasoning is not None:
        payload["reasoning"] = reasoning
    if response_format is not None:
        payload["response_format"] = response_format

    require_judge_runtime_profile(model)
    payload = normalize_openrouter_request(
        model,
        payload,
        request_class="judge",
        structured_output=response_format is not None,
    )

    response = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "LUMI Model Lab",
        },
        json=payload,
        timeout=240,
    )
    if not response.ok:
        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text[:2000]
        raise RuntimeError(f"OpenRouter judge HTTP {response.status_code}: {detail}")

    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"OpenRouter judge response contains no choices: {body}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        finish_reason = choices[0].get("finish_reason")
        raise RuntimeError(
            f"OpenRouter judge response did not contain text content (finish_reason={finish_reason})."
        )

    result = validate_judge_payload(extract_json_object(content))
    return result, body


def save_judgment(record: JudgeRecord, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{record.source_story_id}.judge.json"
    path.write_text(
        json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def judge_story(input_path: Path, config_path: Path) -> tuple[Path, JudgeRecord]:
    config = load_yaml(config_path)
    judge_config = config.get("judge") or {}
    record = load_generation(input_path)
    if not record.technical_validation.eligible_for_judge:
        raise RuntimeError(
            f"{record.id} is not eligible for judge: {record.technical_validation.reasons}"
        )

    model_env = judge_config.get("model_env", "JUDGE_MODEL")
    model = os.getenv(model_env)
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not model:
        raise RuntimeError(f"Missing judge model in environment variable {model_env}.")
    if not api_key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    prompt_version = str(judge_config.get("prompt_version", "story_judge_v0.1"))
    system_prompt = Path("prompts/story_judge.md").read_text(encoding="utf-8").strip()
    result, body = call_judge(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        user_prompt=build_judge_input(record),
        temperature=float(judge_config.get("temperature", 0.0)),
        max_tokens=int(judge_config.get("max_tokens", 1800)),
        reasoning=judge_config.get("reasoning"),
        response_format=judge_config.get("response_format"),
    )
    decision = make_decision(
        result,
        acceptance_threshold=float(judge_config.get("acceptance_threshold", 4.0)),
        minimum_criterion_score=int(judge_config.get("minimum_criterion_score", 3)),
    )

    choice = (body.get("choices") or [{}])[0]
    judge_record = JudgeRecord(
        id=f"judge_{record.id}",
        created_at=datetime.now(timezone.utc),
        source_story_id=record.id,
        source_path=str(input_path),
        teacher_model=record.teacher_model,
        judge_model=model,
        judge_prompt_version=prompt_version,
        result=result,
        decision=decision,
        usage=parse_usage(body),
        cost=parse_cost(body),
        response_meta={
            "openrouter_id": body.get("id"),
            "model": body.get("model"),
            "provider": body.get("provider"),
            "finish_reason": choice.get("finish_reason"),
        },
    )
    output_dir = Path(judge_config.get("output_dir", "runs/judgments"))
    return save_judgment(judge_record, output_dir), judge_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge one technically valid LUMI teacher story.")
    parser.add_argument("--input", required=True, help="Path to data/raw/story_XXXX.json")
    parser.add_argument("--config", default="configs/evaluation.yaml")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    output_path, record = judge_story(Path(args.input), Path(args.config))
    style = "green" if record.decision.accepted else "yellow"
    console.print(f"[{style}]Judged[/{style}] {record.source_story_id} -> {output_path}")
    console.print(
        f"Decision: [{style}]{'ACCEPTED' if record.decision.accepted else 'REJECTED'}[/{style}] | "
        f"average={record.decision.average_score:.2f}/5 | minimum={record.decision.minimum_score}/5"
    )
    for criterion in JUDGE_CRITERIA:
        console.print(f"  {criterion}: {record.result.scores[criterion]}/5")
    if record.result.critical_failures:
        console.print(f"Critical failures: {record.result.critical_failures}")
    if record.decision.reasons:
        console.print(f"Gate reasons: {', '.join(record.decision.reasons)}")
    if record.cost.usd is not None:
        console.print(f"Judge cost: ${record.cost.usd:.6f}")


if __name__ == "__main__":
    main()
