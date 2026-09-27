from __future__ import annotations

from pathlib import Path

from src.visual_contracts import VisualGenerationResult, VisualRequest
from src.visual_generation import DEFAULT_VISUAL_EVIDENCE_DIR, generate_visual
from src.visual_provider import VisualProviderAdapter
from src.visual_routing_evidence import select_visual_route_lineage
from src.visual_router import VisualRoutingPolicy


def generate_routed_visual(
    request: VisualRequest,
    *,
    routing_registry_path: Path,
    adapter: VisualProviderAdapter,
    evidence_dir: Path = DEFAULT_VISUAL_EVIDENCE_DIR,
    routing_policy: VisualRoutingPolicy | None = None,
) -> VisualGenerationResult:
    if request.model_id is not None:
        raise RuntimeError(
            "VISUAL_PRODUCTION_MODEL_LOCK_FORBIDDEN: "
            "production visual requests must route from evidence"
        )

    lineage = select_visual_route_lineage(
        routing_registry_path,
        request,
        policy=routing_policy,
    )
    routed = request.model_copy(
        update={
            "model_id": lineage.model_id,
            "style_version": lineage.style_version,
        }
    )
    return generate_visual(
        routed,
        adapter=adapter,
        evidence_dir=evidence_dir,
        require_qualified=False,
        route_lineage=lineage,
    )
