from __future__ import annotations

import base64
import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.visual_contracts import (
    CostSource,
    VisualArtifact,
    VisualGenerationResult,
    VisualInvocationRecord,
    VisualProviderResult,
    VisualRequest,
)
from src.visual_ledger import append_artifact, append_invocation
from src.visual_model_registry import require_visual_model_profile
from src.visual_prompt_compiler import compile_visual_prompt
from src.visual_provider import FixtureVisualProviderAdapter, VisualProviderAdapter
from src.visual_style_registry import resolve_visual_style_profile
from src.visual_validator import validate_visual_result


DEFAULT_VISUAL_EVIDENCE_DIR = Path("runs/visual")


def _extension(media_type: str) -> str:
    return {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
        "image/svg+xml": ".svg",
    }.get(media_type.lower(), ".bin")


def _cost(result: VisualProviderResult) -> tuple[float | None, CostSource]:
    raw = result.usage.get("cost")
    if raw is None:
        return None, CostSource.NONE
    try:
        return float(raw), CostSource.ACTUAL_PROVIDER
    except (TypeError, ValueError):
        return None, CostSource.NONE


def generate_visual(
    request: VisualRequest,
    *,
    adapter: VisualProviderAdapter | None = None,
    evidence_dir: Path = DEFAULT_VISUAL_EVIDENCE_DIR,
    require_qualified: bool = False,
) -> VisualGenerationResult:
    model_id = request.model_id or "fixture/lumi-visual-v1"
    model = require_visual_model_profile(
        model_id,
        category=request.category,
        style_id=request.style_id,
        require_qualified=require_qualified,
    )
    style = resolve_visual_style_profile(request.style_id, request.style_version)
    compiled = compile_visual_prompt(request, style=style, model=model)
    adapter = adapter or FixtureVisualProviderAdapter()

    invocation_id = f"visinv_{uuid.uuid4().hex}"
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    try:
        provider_result = adapter.generate(model=model, compiled=compiled)
        status = "SUCCESS"
        error_code = None
    except Exception as exc:
        completed_at = datetime.now(timezone.utc)
        invocation = VisualInvocationRecord(
            invocation_id=invocation_id,
            request_id=request.request_id,
            profile_id=request.profile_id,
            category=request.category,
            provider=model.provider,
            model=model.model_id,
            model_profile_sha256=compiled.model_profile_sha256,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=round((time.perf_counter() - started) * 1000),
            image_count=0,
            aspect_ratio=request.aspect_ratio,
            quality_tier=request.quality_tier,
            retry_attempt=0,
            status="ERROR",
            error_code=type(exc).__name__,
        )
        append_invocation(evidence_dir / "visual_invocations.jsonl", invocation)
        raise

    completed_at = datetime.now(timezone.utc)
    cost_usd, cost_source = _cost(provider_result)
    retry_attempt = max(0, int(provider_result.response_meta.get("attempts") or 1) - 1)
    invocation = VisualInvocationRecord(
        invocation_id=invocation_id,
        request_id=request.request_id,
        profile_id=request.profile_id,
        category=request.category,
        provider=provider_result.provider or model.provider,
        model=provider_result.resolved_model or model.model_id,
        model_profile_sha256=compiled.model_profile_sha256,
        started_at=started_at,
        completed_at=completed_at,
        latency_ms=round((time.perf_counter() - started) * 1000),
        image_count=len(provider_result.images),
        aspect_ratio=request.aspect_ratio,
        quality_tier=request.quality_tier,
        cost_usd=cost_usd,
        cost_source=cost_source,
        retry_attempt=retry_attempt,
        status=status,
        provider_response_id=provider_result.response_id,
        error_code=error_code,
    )

    # Persist invocation before artifact bytes so a successful paid call is never retried
    # merely because artifact persistence fails later.
    append_invocation(evidence_dir / "visual_invocations.jsonl", invocation)

    artifacts: list[VisualArtifact] = []
    artifact_dir = evidence_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    for index, image in enumerate(provider_result.images):
        image_bytes = base64.b64decode(image.b64_json)
        content_sha = hashlib.sha256(image_bytes).hexdigest()
        artifact_id = f"visart_{content_sha[:24]}_{index}"
        path = artifact_dir / f"{artifact_id}{_extension(image.media_type)}"
        path.write_bytes(image_bytes)
        artifact = VisualArtifact(
            artifact_id=artifact_id,
            request_id=request.request_id,
            profile_id=request.profile_id,
            category=request.category,
            style_id=style.id,
            style_version=style.version,
            style_profile_sha256=compiled.style_profile_sha256,
            model_id=model.model_id,
            model_profile_sha256=compiled.model_profile_sha256,
            template_id=compiled.template_id,
            template_version=compiled.template_version,
            invocation_id=invocation.invocation_id,
            media_type=image.media_type,
            content_sha256=content_sha,
            storage_ref=str(path),
        )
        append_artifact(evidence_dir / "visual_artifacts.jsonl", artifact)
        artifacts.append(artifact)

    validation = validate_visual_result(request, artifacts)
    return VisualGenerationResult(
        request=request,
        compiled_prompt=compiled,
        invocation=invocation,
        artifacts=artifacts,
        validation=validation,
    )
