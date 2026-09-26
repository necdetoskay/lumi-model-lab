import unittest

from src.story_defect_mutation_protocol import (
    apply_single_patch,
    validate_author_pack,
    validate_validator_verdict,
)


class StoryDefectMutationProtocolTests(unittest.TestCase):
    def setUp(self):
        self.story = "Deniz taşı gördü. Taşı cebine koydu. Eve döndü."
        self.recipe = {
            "id": "state_object_reset",
            "family": "state_continuity",
            "severity": "serious",
            "repair_scope": "LOCAL_REPAIR",
        }

    def test_single_patch_requires_unique_exact_source_span(self):
        out = apply_single_patch(
            self.story,
            "Taşı cebine koydu.",
            "Taşı cebine koydu ama taş bir anda yeniden yerdeydi.",
        )
        self.assertIn("yeniden yerdeydi", out)
        with self.assertRaises(ValueError):
            apply_single_patch(self.story, ".", "!")

    def test_corrupt_pack_rejects_full_story_rewrite(self):
        variant = {
            "recipe_id": "state_object_reset",
            "family": "state_continuity",
            "severity": "serious",
            "repair_scope": "LOCAL_REPAIR",
            "before_text": "Taşı cebine koydu.",
            "after_text": "Taşı cebine koydu ama taş bir anda yeniden yerdeydi.",
            "story": "Tamamen başka bir hikâye.",
            "defect_reason": "Committed state açıklamasız resetleniyor.",
        }
        errors = validate_author_pack(
            source_story=self.story,
            recipes=[self.recipe],
            payload={"variants": [variant]},
        )
        self.assertIn(
            "variant_0:variant_story_is_not_exact_single_patch",
            errors,
        )

    def test_valid_corrupt_pack_preserves_all_unrelated_text(self):
        after = "Taşı cebine koydu ama taş bir anda yeniden yerdeydi."
        variant_story = apply_single_patch(
            self.story,
            "Taşı cebine koydu.",
            after,
        )
        variant = {
            "recipe_id": "state_object_reset",
            "family": "state_continuity",
            "severity": "serious",
            "repair_scope": "LOCAL_REPAIR",
            "before_text": "Taşı cebine koydu.",
            "after_text": after,
            "story": variant_story,
            "defect_reason": "Committed state açıklamasız resetleniyor.",
        }
        self.assertEqual(
            validate_author_pack(
                source_story=self.story,
                recipes=[self.recipe],
                payload={"variants": [variant]},
            ),
            [],
        )

    def test_validator_must_confirm_intended_blocking_defect_and_no_second(self):
        verdict = {
            "recipe_id": "state_object_reset",
            "accept_gold": True,
            "blocking_defect_present": True,
            "confirmed_family": "state_continuity",
            "confirmed_severity": "serious",
            "second_blocking_defects": [],
        }
        self.assertEqual(
            validate_validator_verdict(recipe=self.recipe, verdict=verdict),
            [],
        )
        bad = dict(verdict)
        bad["confirmed_family"] = "causal_logic"
        self.assertIn(
            "validator_family_mismatch",
            validate_validator_verdict(recipe=self.recipe, verdict=bad),
        )

    def test_benign_variant_requires_zero_blocking_defect(self):
        benign_recipe = {
            "id": "perception_response_separated",
            "challenge_family": "response_causality",
        }
        verdict = {
            "recipe_id": "perception_response_separated",
            "accept_gold": True,
            "blocking_defect_present": False,
        }
        self.assertEqual(
            validate_validator_verdict(
                recipe=benign_recipe,
                verdict=verdict,
                benign=True,
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
