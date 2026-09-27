from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from src.visual_contracts import (
    ValidationStatus,
    VisualGenerationResult,
    VisualRequest,
    VisualValidationResult,
)
from src.visual_generation import generate_visual
from src.visual_provider import VisualProviderAdapter


SemanticValidator = Callable[[VisualGenerationResult], VisualValidationResult]
AdapterFactory = Callable[[int], VisualProviderAdapter]


def generate_visual_with_bounded_validation_retry(
    request: VisualRequest,
    *,
    adapter_factory: AdapterFactory,
    semantic_validator: SemanticValidator,
    evidence_dir: Path,
    max_validation_retries: int = 1,
    require_qualified: bool = False,
) -> VisualGenerationResult:
    if max_validation_retries < 0:
        raise ValueError("max_validation_retries must be >= 0")

    current = request
    last: VisualGenerationResult | None = None
    for attempt in range(max_validation_retries + 1):
        result = generate_visual(
            current,
            adapter=adapter_factory(attempt),
            evidence_dir=evidence_dir,
            require_qualified=require_qualified,
        )
        semantic = semantic_validator(result)
        result = result.model_copy(update={"validation": semantic})
        last = result
        if semantic.status == ValidationStatus.PASS:
            return result
        if semantic.status == ValidationStatus.FAIL:
            return result
        if attempt >= max_validation_retries:
            return result

        repair_messages = [
            issue.message for issue in semantic.issues
            if issue.severity.value == "CRITICAL"
        ]
        payload = current.model_dump(mode="python")
        intent = current.intent.model_copy(deep=True)
        if repair_messages:
            intent.extra_directives.append(
                "Correct only these proven visual defects: " + " | ".join(repair_messages)
            )
        payload["intent"] = intent
        payload["request_id"] = f"{request.request_id}:validation-retry:{attempt + 1}"
        current = VisualRequest.model_validate(payload)

    assert last is not None
    return last
