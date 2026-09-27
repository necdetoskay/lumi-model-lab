from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from pydantic import Field

from src.visual_contracts import StrictModel, UserVisualPreference, VisualRequest
from src.visual_style_registry import resolve_visual_style_profile


class VisualOnboardingCandidate(StrictModel):
    candidate_id: str
    style_id: str
    style_version: str
    model_id: str
    artifact_id: str | None = None


def build_onboarding_requests(
    base_request: VisualRequest,
    *,
    style_ids: Iterable[str],
    model_id: str = "fixture/lumi-visual-v1",
) -> list[VisualRequest]:
    requests: list[VisualRequest] = []
    for index, style_id in enumerate(style_ids, start=1):
        style = resolve_visual_style_profile(style_id)
        payload = base_request.model_dump(mode="python")
        payload.update(
            {
                "request_id": f"{base_request.request_id}:onboarding:{index}",
                "style_id": style.id,
                "style_version": style.version,
                "model_id": model_id,
            }
        )
        requests.append(VisualRequest.model_validate(payload))
    return requests


def select_visual_preference(
    *,
    profile_id: str,
    candidate: VisualOnboardingCandidate,
    default_aspect_ratio: str = "3:4",
    allow_automatic_model_routing: bool = True,
) -> UserVisualPreference:
    # The selected candidate records the model as evidence, but the user preference
    # intentionally persists only the style identity.
    return UserVisualPreference(
        profile_id=profile_id,
        preferred_style_id=candidate.style_id,
        preferred_style_version=candidate.style_version,
        default_aspect_ratio=default_aspect_ratio,
        allow_automatic_model_routing=allow_automatic_model_routing,
        selection_source=f"VISUAL_ONBOARDING:{candidate.candidate_id}",
        selected_at=datetime.now(timezone.utc),
    )
