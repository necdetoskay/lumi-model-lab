from __future__ import annotations

from collections.abc import Callable

from src.visual_contracts import (
    CharacterVisualProfile,
    CompiledPromptPackage,
    StoryVisualState,
    VisualCategory,
    VisualIntent,
    VisualModelProfile,
    VisualRequest,
    VisualStyleProfile,
    WorldVisualProfile,
)
from src.visual_model_registry import visual_model_profile_identity
from src.visual_style_registry import visual_style_profile_identity


TEMPLATE_VERSIONS = {
    VisualCategory.CHARACTER_PORTRAIT: "character-portrait.v1",
    VisualCategory.CHARACTER_SCENE: "character-scene.v1",
    VisualCategory.ITEM: "item.v1",
    VisualCategory.INVENTORY_CARD: "inventory-card.v1",
    VisualCategory.ENVIRONMENT: "environment.v1",
    VisualCategory.WORLD_KEY_ART: "world-key-art.v1",
    VisualCategory.COVER_ART: "cover-art.v1",
    VisualCategory.MAP_ART: "map-art.v1",
}


def _join(label: str, values: list[str]) -> str | None:
    clean = [str(value).strip() for value in values if str(value).strip()]
    return f"{label}: " + "; ".join(clean) if clean else None


def _character_lines(profile: CharacterVisualProfile) -> list[str]:
    lines = [
        f"Character identity: {profile.character_id}.",
        f"Apparent age: {profile.apparent_age}.",
        f"Eyes: {profile.eyes}.",
        "Hair: " + ", ".join(f"{key}={value}" for key, value in profile.hair.items()) + ".",
    ]
    if profile.skin:
        lines.append(f"Skin: {profile.skin}.")
    for label, values in (
        ("Signature features", profile.signature_features),
        ("Signature clothing", profile.signature_clothing),
        ("Signature accessories", profile.signature_accessories),
        ("Must preserve", profile.must_keep),
    ):
        value = _join(label, values)
        if value:
            lines.append(value + ".")
    return lines


def _world_lines(profile: WorldVisualProfile) -> list[str]:
    lines = [f"World identity: {profile.world_id}.", f"Biome: {profile.biome}."]
    if profile.architecture:
        lines.append(f"Architecture: {profile.architecture}.")
    if profile.technology_level:
        lines.append(f"Technology level: {profile.technology_level}.")
    for label, values in (
        ("Dominant materials", profile.dominant_materials),
        ("World palette", profile.palette),
        ("Recurring motifs", profile.recurring_motifs),
    ):
        value = _join(label, values)
        if value:
            lines.append(value + ".")
    return lines


def _state_lines(state: StoryVisualState | None, character_id: str | None = None) -> list[str]:
    if state is None:
        return []
    lines: list[str] = []
    if character_id and character_id in state.character_states:
        cstate = state.character_states[character_id]
        for label, values in (
            ("Current clothing state", cstate.clothing_changes),
            ("Currently visible inventory", cstate.inventory_visible),
            ("Temporary character state", cstate.temporary_state),
        ):
            value = _join(label, values)
            if value:
                lines.append(value + ".")
    if state.weather:
        lines.append(f"Weather: {state.weather}.")
    if state.time_of_day:
        lines.append(f"Time of day: {state.time_of_day}.")
    value = _join("Temporary environment changes", state.environment_changes)
    if value:
        lines.append(value + ".")
    return lines


def _intent_lines(intent: VisualIntent, *fields: str) -> list[str]:
    result = [f"Subject: {intent.subject}."]
    for field in fields:
        value = getattr(intent, field)
        if value:
            result.append(f"{field.replace('_', ' ').title()}: {value}.")
    if intent.required_objects:
        result.append("Required objects: " + "; ".join(intent.required_objects) + ".")
    if intent.extra_directives:
        result.extend(f"Directive: {item}." for item in intent.extra_directives)
    return result


def build_character_portrait_prompt(request: VisualRequest) -> list[str]:
    assert request.character_profile is not None
    return [
        "Draw one coherent character portrait.",
        *_character_lines(request.character_profile),
        *_intent_lines(request.intent, "pose", "expression", "composition", "mood"),
        "Keep the character visually readable; environment is secondary.",
    ]


def build_character_scene_prompt(request: VisualRequest) -> list[str]:
    assert request.character_profile is not None
    return [
        "Draw one story scene with the canonical character acting inside the environment.",
        *_character_lines(request.character_profile),
        *_state_lines(request.story_visual_state, request.character_profile.character_id),
        *_intent_lines(
            request.intent, "scene_summary", "action", "environment", "mood", "lighting", "composition"
        ),
    ]


def build_item_prompt(request: VisualRequest) -> list[str]:
    return [
        "Draw one clearly identifiable object.",
        *_intent_lines(request.intent, "composition", "lighting", "mood"),
        "Prioritize shape, material, functional details, condition, and readable silhouette.",
    ]


def build_inventory_card_prompt(request: VisualRequest) -> list[str]:
    return [
        "Draw one inventory-card asset containing a single object.",
        *_intent_lines(request.intent, "composition", "lighting"),
        "Use a clean centered silhouette, controlled shadow, minimal background, and UI-readable scale.",
    ]


def build_environment_prompt(request: VisualRequest) -> list[str]:
    assert request.world_profile is not None
    return [
        "Draw one environment establishing shot.",
        *_world_lines(request.world_profile),
        *_state_lines(request.story_visual_state),
        *_intent_lines(request.intent, "environment", "mood", "lighting", "composition"),
        "The location, not a character, is the primary subject.",
    ]


def build_world_prompt(request: VisualRequest) -> list[str]:
    assert request.world_profile is not None
    return [
        "Draw world key art that communicates the world's large-scale visual identity.",
        *_world_lines(request.world_profile),
        *_intent_lines(request.intent, "environment", "mood", "lighting", "composition"),
        "Show strong scale cues, macro landmarks, habitat identity, and narrative atmosphere.",
    ]


def build_cover_prompt(request: VisualRequest) -> list[str]:
    lines = ["Draw polished story cover art."]
    if request.character_profile:
        lines.extend(_character_lines(request.character_profile))
    if request.world_profile:
        lines.extend(_world_lines(request.world_profile))
    lines.extend(_state_lines(request.story_visual_state, request.character_profile.character_id if request.character_profile else None))
    lines.extend(_intent_lines(request.intent, "scene_summary", "action", "environment", "mood", "lighting", "composition"))
    lines.append("Use one strong focal composition and preserve title-safe negative space.")
    return lines


def build_map_prompt(request: VisualRequest) -> list[str]:
    assert request.world_profile is not None
    return [
        "Draw one readable illustrated map.",
        *_world_lines(request.world_profile),
        *_intent_lines(request.intent, "environment", "composition", "mood"),
        "Prioritize geographic hierarchy, routes, known landmarks, exploration state, and label-safe areas.",
    ]


BUILDERS: dict[VisualCategory, Callable[[VisualRequest], list[str]]] = {
    VisualCategory.CHARACTER_PORTRAIT: build_character_portrait_prompt,
    VisualCategory.CHARACTER_SCENE: build_character_scene_prompt,
    VisualCategory.ITEM: build_item_prompt,
    VisualCategory.INVENTORY_CARD: build_inventory_card_prompt,
    VisualCategory.ENVIRONMENT: build_environment_prompt,
    VisualCategory.WORLD_KEY_ART: build_world_prompt,
    VisualCategory.COVER_ART: build_cover_prompt,
    VisualCategory.MAP_ART: build_map_prompt,
}


def _negative_constraints(
    request: VisualRequest,
    style: VisualStyleProfile,
    model: VisualModelProfile,
) -> list[str]:
    category_negative = {
        VisualCategory.CHARACTER_PORTRAIT: [
            "extra limbs", "duplicate accessories", "adult proportions for a child",
            "wrong canonical eye or hair color", "identity drift",
        ],
        VisualCategory.CHARACTER_SCENE: [
            "extra limbs", "duplicate characters", "missing required objects", "identity drift",
        ],
        VisualCategory.ITEM: [
            "duplicate objects", "busy background", "unclear silhouette", "unrequested hands",
        ],
        VisualCategory.INVENTORY_CARD: [
            "multiple objects", "busy scene", "cropped object", "unclear silhouette",
        ],
        VisualCategory.ENVIRONMENT: [
            "random foreground crowds", "forbidden modern objects", "incorrect architecture",
        ],
        VisualCategory.WORLD_KEY_ART: [
            "generic unrelated biome", "forbidden technology", "inconsistent world palette",
        ],
        VisualCategory.COVER_ART: [
            "cluttered composition", "unreadable focal point", "identity drift",
        ],
        VisualCategory.MAP_ART: [
            "photorealistic satellite map", "illegible hierarchy", "random unlabeled clutter",
        ],
    }[request.category]
    values = [
        *style.global_negative_directives,
        *category_negative,
        *request.user_negative_overrides,
    ]
    if request.world_profile:
        values.extend(request.world_profile.forbidden_visuals)
    # Model-specific negative behavior lives in the model profile; content stays shared/style/category.
    return list(dict.fromkeys(value.strip() for value in values if value.strip()))


def compile_visual_prompt(
    request: VisualRequest,
    *,
    style: VisualStyleProfile,
    model: VisualModelProfile,
) -> CompiledPromptPackage:
    if request.category not in model.supported_categories:
        raise ValueError(f"Model {model.model_id} does not support {request.category.value}")
    if model.supported_styles and style.id not in model.supported_styles:
        raise ValueError(f"Model {model.model_id} does not support style {style.id}")

    lines = BUILDERS[request.category](request)
    lines.append("Style: " + "; ".join(style.base_style_directives) + ".")
    category_style = style.category_overrides.get(request.category, [])
    if category_style:
        lines.append("Category style: " + "; ".join(category_style) + ".")
    lines.append(
        "Color policy: "
        f"{style.color_policy.saturation} saturation, "
        f"{style.color_policy.contrast} contrast, "
        f"{style.color_policy.temperature} temperature."
    )
    if style.lighting_policy.preferred:
        lines.append("Preferred lighting: " + "; ".join(style.lighting_policy.preferred) + ".")
    if request.user_style_overrides:
        lines.append("User style refinements: " + "; ".join(request.user_style_overrides) + ".")

    negatives = _negative_constraints(request, style, model)
    negative_prompt: str | None
    if model.prompt_policy.supports_separate_negative_prompt:
        negative_prompt = ", ".join(negatives) or None
    else:
        negative_prompt = None
        if negatives:
            lines.append(model.prompt_policy.inline_negative_prefix + " " + "; ".join(negatives) + ".")

    continuity: list[str] = []
    if request.character_profile:
        continuity.extend(request.character_profile.must_keep)
    if request.world_profile:
        continuity.extend(f"forbid: {item}" for item in request.world_profile.forbidden_visuals)

    provider_options = {
        "aspect_ratio": request.aspect_ratio,
        "n": request.image_count,
        "quality_tier": request.quality_tier.value,
    }
    if negative_prompt and model.prompt_policy.negative_prompt_parameter:
        provider_options[model.prompt_policy.negative_prompt_parameter] = negative_prompt

    style_identity = visual_style_profile_identity(style.id, style.version)
    model_identity = visual_model_profile_identity(model.model_id)
    return CompiledPromptPackage(
        positive_prompt="\n".join(line for line in lines if line),
        negative_prompt=negative_prompt,
        provider_options=provider_options,
        input_references=list(request.input_references),
        continuity_constraints=list(dict.fromkeys(continuity)),
        style_profile_sha256=style_identity["profile_sha256"],
        model_profile_sha256=model_identity["profile_sha256"],
        template_id=TEMPLATE_VERSIONS[request.category],
        template_version="1.0.0",
    )
