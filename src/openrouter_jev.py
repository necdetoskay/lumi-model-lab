from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any

import requests
import yaml

DEFAULT_PROFILE_PATH = "configs/openrouter_jev_continuity.yaml"
JEV_TRANSIENT_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
JEV_RETRY_DELAYS_SECONDS = (2.0, 5.0, 10.0)
JEV_MAX_ATTEMPTS = len(JEV_RETRY_DELAYS_SECONDS) + 1


@dataclass(frozen=True)
class JevProfile:
    model_id: str
    endpoint: str
    positive_probability_threshold: float
    mode: str


def load_jev_profile(path: str = DEFAULT_PROFILE_PATH) -> JevProfile:
    with open(path, "r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
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
    request_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
        "X-Title": "LUMI Model Lab",
    }
    request_payload = {
        "model": profile.model_id,
        "state": state,
        "questions": questions,
    }

    response = None
    transport_error: Exception | None = None
    for attempt in range(JEV_MAX_ATTEMPTS):
        try:
            response = requests.post(
                profile.endpoint,
                headers=request_headers,
                json=request_payload,
                timeout=timeout_seconds,
            )
            transport_error = None
        except (requests.Timeout, requests.ConnectionError) as exc:
            transport_error = exc
            if attempt >= JEV_MAX_ATTEMPTS - 1:
                raise RuntimeError(
                    f"OpenRouter JEV transport failed after {JEV_MAX_ATTEMPTS} "
                    f"attempts: {exc}"
                ) from exc
            time.sleep(JEV_RETRY_DELAYS_SECONDS[attempt])
            continue

        if response.ok:
            break

        try:
            detail: Any = response.json()
        except ValueError:
            detail = response.text[:2000]

        if (
            response.status_code in JEV_TRANSIENT_STATUS_CODES
            and attempt < JEV_MAX_ATTEMPTS - 1
        ):
            retry_after = None
            headers = getattr(response, "headers", {}) or {}
            raw_retry_after = headers.get("Retry-After")
            if raw_retry_after is not None:
                try:
                    retry_after = max(0.0, min(float(raw_retry_after), 30.0))
                except (TypeError, ValueError):
                    retry_after = None
            delay = (
                retry_after
                if retry_after is not None
                else JEV_RETRY_DELAYS_SECONDS[attempt]
            )
            time.sleep(delay)
            continue

        raise RuntimeError(
            f"OpenRouter JEV HTTP {response.status_code}: {detail}"
        )

    if response is None:
        raise RuntimeError(
            "OpenRouter JEV request failed before receiving a response: "
            f"{transport_error}"
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
