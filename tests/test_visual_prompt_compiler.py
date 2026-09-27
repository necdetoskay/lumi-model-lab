from __future__ import annotations

import unittest

from src.visual_contracts import (
    CharacterVisualProfile,
    StoryVisualState,
    CharacterSceneVisualState,
    VisualCategory,
    VisualIntent,
    VisualRequest,
    WorldVisualProfile,
)
from src.visual_model_registry import require_visual_model_profile
from src.visual_prompt_compiler import BUILDERS, compile_visual_prompt
from src.visual_style_registry import resolve_visual_style_profile


def character() -> CharacterVisualProfile:
    return CharacterVisualProfile(
        character_id="elara",
        version="1.0.0",
        apparent_age=11,
        skin="light wheat",
        eyes="amber brown",
        hair={"color": "dark chestnut", "length": "shoulder", "texture": "wavy"},
        signature_features=["left braid with turquoise bead"],
        signature_clothing=["moss green explorer jacket"],
        signature_accessories=["brass compass necklace"],
        must_keep=["amber brown eyes", "left braid with turquoise bead"],
    )


def world() -> WorldVisualProfile:
    return WorldVisualProfile(
        world_id="forest-habitat",
        version="1.0.0",
        biome="temperate forest",
        architecture="weathered stone and timber",
        technology_level="low fantasy",
        palette=["moss green", "warm earth", "aged brass"],
        forbidden_visuals=["cars", "neon signs"],
    )


def request_for(category: VisualCategory) -> VisualRequest:
    kwargs = {}
    if category in {VisualCategory.CHARACTER_PORTRAIT, VisualCategory.CHARACTER_SCENE}:
        kwargs["character_profile"] = character()
    if category in {VisualCategory.ENVIRONMENT, VisualCategory.WORLD_KEY_ART, VisualCategory.MAP_ART}:
        kwargs["world_profile"] = world()
    if category == VisualCategory.COVER_ART:
        kwargs["character_profile"] = character()
        kwargs["world_profile"] = world()
    if category == VisualCategory.CHARACTER_SCENE:
        kwargs["story_visual_state"] = StoryVisualState(
            story_id="s1",
            scene_id="scene5",
            character_states={
                "elara": CharacterSceneVisualState(
                    clothing_changes=["right sleeve muddy"],
                    inventory_visible=["silver key"],
                )
            },
            weather="light rain",
        )
    return VisualRequest(
        request_id=f"req-{category.value}",
        profile_id="profile-1",
        category=category,
        intent=VisualIntent(
            subject="Elara or the canonical requested subject",
            scene_summary="A quiet discovery",
            action="examining a clue",
            environment="forest clearing",
            mood="curious",
            lighting="warm morning light",
            composition="clear focal point",
            pose="relaxed",
            expression="observant",
            required_objects=["silver key"] if category == VisualCategory.CHARACTER_SCENE else [],
        ),
        style_id="lumi-storybook-soft",
        **kwargs,
    )


class VisualPromptCompilerTests(unittest.TestCase):
    def test_every_canonical_category_has_distinct_builder(self) -> None:
        self.assertEqual(set(BUILDERS), set(VisualCategory))
        self.assertEqual(len({id(fn) for fn in BUILDERS.values()}), len(VisualCategory))

    def test_all_categories_compile_with_fixture_model(self) -> None:
        style = resolve_visual_style_profile("lumi-storybook-soft")
        model = require_visual_model_profile("fixture/lumi-visual-v1")
        prompts = {}
        for category in VisualCategory:
            package = compile_visual_prompt(request_for(category), style=style, model=model)
            prompts[category] = package.positive_prompt
            self.assertEqual(package.template_version, "1.0.0")
            self.assertEqual(len(package.style_profile_sha256), 64)
            self.assertEqual(len(package.model_profile_sha256), 64)
        self.assertEqual(len(set(prompts.values())), len(VisualCategory))

    def test_character_scene_carries_temporary_state_and_identity(self) -> None:
        style = resolve_visual_style_profile("lumi-storybook-soft")
        model = require_visual_model_profile("fixture/lumi-visual-v1")
        package = compile_visual_prompt(
            request_for(VisualCategory.CHARACTER_SCENE), style=style, model=model
        )
        self.assertIn("right sleeve muddy", package.positive_prompt)
        self.assertIn("silver key", package.positive_prompt)
        self.assertIn("amber brown eyes", package.positive_prompt)

    def test_negative_layers_use_separate_field_when_model_supports_it(self) -> None:
        style = resolve_visual_style_profile("lumi-storybook-soft")
        model = require_visual_model_profile("fixture/lumi-visual-v1")
        request = request_for(VisualCategory.CHARACTER_PORTRAIT)
        request.user_negative_overrides.append("no hat")
        package = compile_visual_prompt(request, style=style, model=model)
        self.assertIn("no hat", package.negative_prompt or "")
        self.assertIn("identity drift", package.negative_prompt or "")
        self.assertEqual(package.provider_options["negative_prompt"], package.negative_prompt)


if __name__ == "__main__":
    unittest.main()
