from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests
import yaml

DEFAULT_PROFILE_PATH = "configs/openrouter_jev_continuity.yaml"


@dataclass(frozen=True)
class JevProfile:
    model_id: str
    endpoint: str
    positive_probability_threshold: float
    mode: str


def load_jev_profile(path: str = DEFAULT_PROFILE_PATH) -> JevProfile:
    payload = yaml.safe_load(open(path, "r", encoding="utf-8")) or {}
    if payload.get("schema_version") != "openrouter-jev-profile.v1":
        raise RuntimeError("Unsupported OpenRouter JEV profile schema.")
    model_id = str(payload.get("model_id") or "")
    if model_id != "typesafe/jev-1.13":
        raise RuntimeError(
            "JEV profile must pin the exact qualified model slug typesafe/jev-1.13."
        )
    transport = payload.get("transport") or {}
    workload = payload.get("workload") or {}
    endpoint = str(transport.get("endpoint") or "")
    if endpoint != "https://openrouter.ai/api/alpha/decisions":
        raise RuntimeError("JEV profile must use the OpenRouter Decisions API endpoint.")
    return JevProfile(
        model_id=model_id,
        endpoint=endpoint,
        positive_probability_threshold=float(
            workload.get("positive_probability_threshold", 0.80)
        ),
        mode=str(workload.get("mode") or "shadow"),
    )


def noul_question(
    instructions: str,
    *,
    true_criteria: str,
    false_criteria: str,
) -> dict[str, Any]:
    return {
        "type": "noul",
        "instructions": instructions,
        "criteria": {
            "true": true_criteria,
            "false": false_criteria,
        },
    }


def choice_question(
    instructions: str,
    criteria: dict[str, str],
) -> dict[str, Any]:
    if len(criteria) < 2:
        raise ValueError("choice question requires at least two criteria.")
    return {
        "type": "choice",
        "instructions": instructions,
        "criteria": dict(criteria),
    }


def call_openrouter_jev(
    *,
    api_key: str,
    state: dict[str, Any],
    questions: dict[str, dict[str, Any]],
    profile_path: str = DEFAULT_PROFILE_PATH,
    timeout_seconds: float = 60.0,
) -> dict[str, Any]:
    profile = load_jev_profile(profile_path)
    if not questions:
        raise ValueError("JEV request requires at least one question.")
    response = requests.post(
        profile.endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "LUMI Model Lab",
        },
        json={
            "model": profile.model_id,
            "state": state,
            "questions": questions,
        },
        timeout=timeout_seconds,
    )
    if not response.ok:
        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text[:2000]
        raise RuntimeError(
            f"OpenRouter JEV HTTP {response.status_code}: {detail}"
        )
    body = response.json()
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise RuntimeError(f"OpenRouter JEV response missing answers: {body}")
    missing = sorted(set(questions) - set(answers))
    if missing:
        raise RuntimeError(
            "OpenRouter JEV response missing answers: " + ", ".join(missing)
        )
    return body


def noul_probability(answer: dict[str, Any]) -> float:
    value = answer.get("noul")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise RuntimeError(f"Invalid JEV noul answer: {answer}")
    probability = float(value)
    if not 0.0 <= probability <= 1.0:
        raise RuntimeError(f"JEV noul probability outside [0,1]: {probability}")
    return probability


def choice_value(answer: dict[str, Any]) -> tuple[str, float | None]:
    value = answer.get("choice")
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"Invalid JEV choice answer: {answer}")
    confidence = answer.get("confidence")
    if confidence is not None:
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise RuntimeError(f"Invalid JEV choice confidence: {answer}")
        confidence = float(confidence)
    return value, confidence
