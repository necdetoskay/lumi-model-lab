from __future__ import annotations

import base64
import json
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.model_registry import normalize_openrouter_request
from src.visual_contracts import (
    CostSource,
    FailureSeverity,
    StrictModel,
    ValidationStatus,
    VisualArtifact,
    VisualRequest,
    VisualValidationIssue,
)
from src.visual_ledger import append_jsonl


class VisualSemanticEvaluation(StrictModel):
    status: ValidationStatus
    identity_consistency: float = 1.0
    style_consistency: float = 1.0
    scene_correctness: float = 1.0
    required_object_correctness: float = 1.0
    issues: list[VisualValidationIssue] = Field(default_factory=list)
    summary: str = ""


class VisualEvaluationRecord(StrictModel):
    evaluation_id: str
    request_id: str
    artifact_id: str
    evaluator_model: str
    provider: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int
    cost_usd: float | None = None
    cost_source: CostSource = CostSource.NONE
    usage: dict[str, Any] = Field(default_factory=dict)
    provider_response_id: str | None = None
    result: VisualSemanticEvaluation


class VisualSemanticEvaluator(ABC):
    model_id: str
    provider: str

    @abstractmethod
    def evaluate(
        self,
        *,
        request: VisualRequest,
        artifact: VisualArtifact,
    ) -> tuple[VisualSemanticEvaluation, dict[str, Any]]:
        raise NotImplementedError


class FixtureVisualSemanticEvaluator(VisualSemanticEvaluator):
    model_id = "fixture/visual-evaluator-v1"
    provider = "fixture"

    def evaluate(
        self,
        *,
        request: VisualRequest,
        artifact: VisualArtifact,
    ) -> tuple[VisualSemanticEvaluation, dict[str, Any]]:
        return (
            VisualSemanticEvaluation(
                status=ValidationStatus.PASS,
                identity_consistency=1.0,
                style_consistency=1.0,
                scene_correctness=1.0,
                required_object_correctness=1.0,
                issues=[],
                summary="Deterministic fixture evaluator pass.",
            ),
            {"usage": {"cost": 0.0}, "response_id": "fixture-evaluation"},
        )


class OpenRouterVisualSemanticEvaluator(VisualSemanticEvaluator):
    provider = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model_id: str = "openai/gpt-5.6-luna",
        timeout_seconds: int = 180,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter visual evaluator requires api_key")
        self.api_key = api_key
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _data_url(artifact: VisualArtifact) -> str:
        raw = Path(artifact.storage_ref).read_bytes()
        return f"data:{artifact.media_type};base64,{base64.b64encode(raw).decode('ascii')}"

    @staticmethod
    def _rubric(request: VisualRequest) -> dict[str, Any]:
        character = request.character_profile.model_dump(mode="json", by_alias=True) if request.character_profile else None
        world = request.world_profile.model_dump(mode="json", by_alias=True) if request.world_profile else None
        state = request.story_visual_state.model_dump(mode="json", by_alias=True) if request.story_visual_state else None
        return {
            "category": request.category.value,
            "style_id": request.style_id,
            "intent": request.intent.model_dump(mode="json"),
            "character_visual_profile": character,
            "world_visual_profile": world,
            "story_visual_state": state,
        }

    def evaluate(
        self,
        *,
        request: VisualRequest,
        artifact: VisualArtifact,
    ) -> tuple[VisualSemanticEvaluation, dict[str, Any]]:
        system = (
            "You are the LUMI visual continuity evaluator. Judge only visible evidence. "
            "Do not reward general beauty when canonical identity or scene requirements are wrong. "
            "Return JSON only with keys: status, identity_consistency, style_consistency, "
            "scene_correctness, required_object_correctness, issues, summary. "
            "Scores are 0..1. status is PASS, RETRY, or FAIL. "
            "Each issue has code, severity (MINOR or CRITICAL), and message. "
            "Use RETRY for repairable critical identity/required-object/scene defects; "
            "FAIL only for an unusable or fundamentally unrelated result."
        )
        rubric = json.dumps(self._rubric(request), ensure_ascii=False)
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Canonical visual contract:\n{rubric}"},
                        {"type": "image_url", "image_url": {"url": self._data_url(artifact)}},
                    ],
                },
            ],
        }
        payload = normalize_openrouter_request(
            self.model_id,
            payload,
            request_class="default",
            structured_output=True,
        )
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
                "X-Title": "LUMI Model Lab Visual Evaluator",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        if not response.ok:
            raise RuntimeError(
                f"OpenRouter visual evaluator HTTP {response.status_code}: {response.text[:2000]}"
            )
        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise RuntimeError("Visual evaluator returned no choices")
        raw_content = (choices[0].get("message") or {}).get("content")
        if isinstance(raw_content, str):
            content = raw_content.strip()
        elif isinstance(raw_content, list):
            parts: list[str] = []
            for item in raw_content:
                if not isinstance(item, dict):
                    continue
                text = item.get("text")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
            content = "\n".join(parts).strip()
        else:
            content = ""
        if not content:
            raise RuntimeError("Visual evaluator returned no JSON content")
        data = json.loads(content)
        evaluation = VisualSemanticEvaluation.model_validate(data)
        return evaluation, {
            "usage": body.get("usage") or {},
            "response_id": body.get("id"),
            "provider": body.get("provider") or "openrouter",
        }


def evaluate_visual_artifact(
    *,
    request: VisualRequest,
    artifact: VisualArtifact,
    evaluator: VisualSemanticEvaluator,
    evidence_dir: Path,
) -> VisualEvaluationRecord:
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    result, meta = evaluator.evaluate(request=request, artifact=artifact)
    completed_at = datetime.now(timezone.utc)
    usage = meta.get("usage") or {}
    raw_cost = usage.get("cost")
    cost_usd: float | None = None
    cost_source = CostSource.NONE
    if raw_cost is not None:
        try:
            cost_usd = float(raw_cost)
            cost_source = CostSource.ACTUAL_PROVIDER
        except (TypeError, ValueError):
            pass
    record = VisualEvaluationRecord(
        evaluation_id=f"viseval_{uuid.uuid4().hex}",
        request_id=request.request_id,
        artifact_id=artifact.artifact_id,
        evaluator_model=evaluator.model_id,
        provider=str(meta.get("provider") or evaluator.provider),
        started_at=started_at,
        completed_at=completed_at,
        latency_ms=round((time.perf_counter() - started) * 1000),
        cost_usd=cost_usd,
        cost_source=cost_source,
        usage=usage,
        provider_response_id=meta.get("response_id"),
        result=result,
    )
    append_jsonl(
        evidence_dir / "visual_evaluations.jsonl",
        record.model_dump(mode="json"),
    )
    return record
