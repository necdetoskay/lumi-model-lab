from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class VisualCategory(str, Enum):
    CHARACTER_PORTRAIT = "CHARACTER_PORTRAIT"
    CHARACTER_SCENE = "CHARACTER_SCENE"
    ITEM = "ITEM"
    INVENTORY_CARD = "INVENTORY_CARD"
    ENVIRONMENT = "ENVIRONMENT"
    WORLD_KEY_ART = "WORLD_KEY_ART"
    COVER_ART = "COVER_ART"
    MAP_ART = "MAP_ART"


class VisualQualityTier(str, Enum):
    DRAFT = "DRAFT"
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    RETRY = "RETRY"
    FAIL = "FAIL"


class FailureSeverity(str, Enum):
    MINOR = "MINOR"
    CRITICAL = "CRITICAL"


class CostSource(str, Enum):
    ACTUAL_PROVIDER = "ACTUAL_PROVIDER"
    ESTIMATED_PROFILE = "ESTIMATED_PROFILE"
    NONE = "NONE"


class UserVisualPreference(StrictModel):
    schema: Literal["user-visual-preference.v1"] = "user-visual-preference.v1"
    profile_id: str
    preferred_style_id: str
    preferred_style_version: str
    quality_tier: VisualQualityTier = VisualQualityTier.STANDARD
    default_aspect_ratio: str = "3:4"
    allow_automatic_model_routing: bool = True
    custom_style_overrides: list[str] = Field(default_factory=list)
    custom_negative_overrides: list[str] = Field(default_factory=list)
    selection_source: str = "VISUAL_ONBOARDING"
    selected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VisualColorPolicy(StrictModel):
    saturation: str = "MODERATE"
    contrast: str = "SOFT"
    temperature: str = "WARM"


class VisualLightingPolicy(StrictModel):
    preferred: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class VisualStyleProfile(StrictModel):
    schema: Literal["visual-style-profile.v1"] = "visual-style-profile.v1"
    id: str
    version: str
    display_name: str
    status: Literal["ACTIVE", "INACTIVE"] = "ACTIVE"
    base_style_directives: list[str]
    color_policy: VisualColorPolicy = Field(default_factory=VisualColorPolicy)
    lighting_policy: VisualLightingPolicy = Field(default_factory=VisualLightingPolicy)
    global_negative_directives: list[str] = Field(default_factory=list)
    category_overrides: dict[VisualCategory, list[str]] = Field(default_factory=dict)


class VisualModelCapabilities(StrictModel):
    reference_images: bool = False
    negative_prompt: bool = False
    transparent_background: bool = False
    inpainting: bool = False
    image_to_image: bool = False
    max_reference_images: int = Field(default=0, ge=0)
    max_images_per_call: int = Field(default=1, ge=1)
    aspect_ratios: list[str] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)


class VisualPromptPolicy(StrictModel):
    preferred_order: list[str] = Field(default_factory=list)
    detail_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    preferred_prompt_length: Literal["SHORT", "MEDIUM", "LONG"] = "MEDIUM"
    supports_separate_negative_prompt: bool = False
    negative_prompt_parameter: str | None = None
    inline_negative_prefix: str = "Avoid:"


class VisualRuntimePolicy(StrictModel):
    timeout_seconds: int = Field(default=120, ge=1, le=600)
    max_retries: int = Field(default=2, ge=0, le=5)
    transient_status_codes: list[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504, 520, 522, 524, 529]
    )


class VisualPricingPolicy(StrictModel):
    mode: Literal["PROVIDER_USAGE_COST", "PER_IMAGE_HINT", "TOKEN_HINT", "OTHER"] = (
        "PROVIDER_USAGE_COST"
    )
    currency: str = "USD"
    published_hint: float | None = Field(default=None, ge=0)
    published_unit: str | None = None
    actual_cost_field: str = "usage.cost"


class VisualQualification(StrictModel):
    ready: bool = False
    evidence: str | None = None
    qualified_at: datetime | None = None


class VisualModelProfile(StrictModel):
    schema: Literal["visual-model-profile.v1"] = "visual-model-profile.v1"
    model_id: str
    display_name: str
    provider: str = "openrouter"
    endpoint: str = "https://openrouter.ai/api/v1/images"
    profile_version: str
    status: Literal["ACTIVE", "INACTIVE", "DEPRECATED"] = "ACTIVE"
    capabilities: VisualModelCapabilities
    supported_categories: list[VisualCategory]
    supported_styles: list[str]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    prompt_policy: VisualPromptPolicy = Field(default_factory=VisualPromptPolicy)
    runtime_policy: VisualRuntimePolicy = Field(default_factory=VisualRuntimePolicy)
    pricing: VisualPricingPolicy = Field(default_factory=VisualPricingPolicy)
    qualification: VisualQualification = Field(default_factory=VisualQualification)
    sources: list[str] = Field(default_factory=list)


class CharacterVisualProfile(StrictModel):
    schema: Literal["character-visual-profile.v1"] = "character-visual-profile.v1"
    character_id: str
    version: str
    apparent_age: int = Field(ge=0, le=130)
    skin: str | None = None
    eyes: str
    hair: dict[str, str]
    signature_features: list[str] = Field(default_factory=list)
    signature_clothing: list[str] = Field(default_factory=list)
    signature_accessories: list[str] = Field(default_factory=list)
    must_keep: list[str] = Field(default_factory=list)
    soft_flexible: list[str] = Field(default_factory=list)


class WorldVisualProfile(StrictModel):
    schema: Literal["world-visual-profile.v1"] = "world-visual-profile.v1"
    world_id: str
    version: str
    biome: str
    architecture: str | None = None
    technology_level: str | None = None
    dominant_materials: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    recurring_motifs: list[str] = Field(default_factory=list)
    forbidden_visuals: list[str] = Field(default_factory=list)


class CharacterSceneVisualState(StrictModel):
    clothing_changes: list[str] = Field(default_factory=list)
    inventory_visible: list[str] = Field(default_factory=list)
    temporary_state: list[str] = Field(default_factory=list)


class StoryVisualState(StrictModel):
    schema: Literal["story-visual-state.v1"] = "story-visual-state.v1"
    story_id: str
    scene_id: str | None = None
    character_states: dict[str, CharacterSceneVisualState] = Field(default_factory=dict)
    weather: str | None = None
    time_of_day: str | None = None
    environment_changes: list[str] = Field(default_factory=list)


class VisualIntent(StrictModel):
    subject: str
    scene_summary: str | None = None
    action: str | None = None
    environment: str | None = None
    mood: str | None = None
    lighting: str | None = None
    composition: str | None = None
    pose: str | None = None
    expression: str | None = None
    required_objects: list[str] = Field(default_factory=list)
    extra_directives: list[str] = Field(default_factory=list)


class VisualRequest(StrictModel):
    schema: Literal["visual-request.v1"] = "visual-request.v1"
    request_id: str
    profile_id: str
    category: VisualCategory
    intent: VisualIntent
    style_id: str
    style_version: str | None = None
    model_id: str | None = None
    quality_tier: VisualQualityTier = VisualQualityTier.STANDARD
    aspect_ratio: str = "3:4"
    image_count: int = Field(default=1, ge=1, le=10)
    character_profile: CharacterVisualProfile | None = None
    world_profile: WorldVisualProfile | None = None
    story_visual_state: StoryVisualState | None = None
    user_style_overrides: list[str] = Field(default_factory=list)
    user_negative_overrides: list[str] = Field(default_factory=list)
    input_references: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_context(self) -> "VisualRequest":
        if self.category in {VisualCategory.CHARACTER_PORTRAIT, VisualCategory.CHARACTER_SCENE}:
            if self.character_profile is None:
                raise ValueError(f"{self.category.value} requires character_profile")
        if self.category in {VisualCategory.ENVIRONMENT, VisualCategory.WORLD_KEY_ART, VisualCategory.MAP_ART}:
            if self.world_profile is None:
                raise ValueError(f"{self.category.value} requires world_profile")
        return self


class CompiledPromptPackage(StrictModel):
    schema: Literal["compiled-visual-prompt.v1"] = "compiled-visual-prompt.v1"
    positive_prompt: str
    negative_prompt: str | None = None
    provider_options: dict[str, Any] = Field(default_factory=dict)
    input_references: list[str] = Field(default_factory=list)
    continuity_constraints: list[str] = Field(default_factory=list)
    style_profile_sha256: str
    model_profile_sha256: str
    template_id: str
    template_version: str


class VisualProviderImage(StrictModel):
    b64_json: str
    media_type: str = "image/png"


class VisualProviderResult(StrictModel):
    images: list[VisualProviderImage]
    usage: dict[str, Any] = Field(default_factory=dict)
    response_id: str | None = None
    resolved_model: str | None = None
    provider: str | None = None
    response_meta: dict[str, Any] = Field(default_factory=dict)


class VisualInvocationRecord(StrictModel):
    schema: Literal["visual-invocation.v1"] = "visual-invocation.v1"
    invocation_id: str
    request_id: str
    profile_id: str
    category: VisualCategory
    provider: str
    model: str
    model_profile_sha256: str
    started_at: datetime
    completed_at: datetime
    latency_ms: int = Field(ge=0)
    image_count: int = Field(ge=0)
    aspect_ratio: str
    quality_tier: VisualQualityTier
    cost_usd: float | None = Field(default=None, ge=0)
    cost_source: CostSource = CostSource.NONE
    retry_attempt: int = Field(default=0, ge=0)
    status: Literal["SUCCESS", "ERROR"]
    provider_response_id: str | None = None
    error_code: str | None = None


class VisualArtifact(StrictModel):
    schema: Literal["visual-artifact.v1"] = "visual-artifact.v1"
    artifact_id: str
    request_id: str
    profile_id: str
    category: VisualCategory
    style_id: str
    style_version: str
    style_profile_sha256: str
    model_id: str
    model_profile_sha256: str
    template_id: str
    template_version: str
    invocation_id: str
    media_type: str
    content_sha256: str
    storage_ref: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VisualValidationIssue(StrictModel):
    code: str
    severity: FailureSeverity
    message: str


class VisualValidationResult(StrictModel):
    status: ValidationStatus
    issues: list[VisualValidationIssue] = Field(default_factory=list)
    checked_constraints: list[str] = Field(default_factory=list)


class VisualGenerationResult(StrictModel):
    request: VisualRequest
    compiled_prompt: CompiledPromptPackage
    invocation: VisualInvocationRecord
    artifacts: list[VisualArtifact]
    validation: VisualValidationResult


def canonical_sha256(payload: BaseModel | dict[str, Any]) -> str:
    if isinstance(payload, BaseModel):
        value = payload.model_dump(mode="json")
    else:
        value = payload
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
