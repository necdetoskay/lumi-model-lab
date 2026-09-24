from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

import yaml

from src.capability_cube import (
    narrative_age_tier_for_range,
    resolve_relative_length_class,
)
from src.schemas import StorySpec

BASE = Path(
    "data/specifications/waves/age-relative-standard-v2/"
    "adult--puzzle-problem-solving.yaml"
)
VARIANT_B = Path(
    "data/specifications/diagnostics/"
    "adult-puzzle-problem-solving-variant-b-v1.yaml"
)


def load_spec(path: Path) -> StorySpec:
    return StorySpec.model_validate(
        yaml.safe_load(path.read_text(encoding="utf-8"))
    )


class DiagnosticFixtureTests(unittest.TestCase):
    def test_adult_puzzle_variant_b_preserves_controlled_axes(self) -> None:
        base = load_spec(BASE)
        variant = load_spec(VARIANT_B)

        controlled = (
            "age_min",
            "age_max",
            "language",
            "target_words",
            "narrative_family",
            "reading_mode",
            "relative_length_class",
            "protagonist",
            "theme",
            "constraints",
        )
        for field in controlled:
            with self.subTest(field=field):
                self.assertEqual(
                    getattr(variant, field),
                    getattr(base, field),
                )

        self.assertNotEqual(variant.title_hint, base.title_hint)
        self.assertNotEqual(variant.setting, base.setting)
        self.assertNotEqual(variant.premise, base.premise)

    def test_adult_puzzle_variant_b_has_distinct_spec_fingerprint(self) -> None:
        base_sha = hashlib.sha256(BASE.read_bytes()).hexdigest()
        variant_sha = hashlib.sha256(VARIANT_B.read_bytes()).hexdigest()
        self.assertNotEqual(base_sha, variant_sha)

    def test_adult_puzzle_variant_b_resolves_same_capability_cell(self) -> None:
        base = load_spec(BASE)
        variant = load_spec(VARIANT_B)

        for spec in (base, variant):
            self.assertEqual(
                narrative_age_tier_for_range(spec.age_min, spec.age_max),
                "ADULT",
            )
            mode, relative_class = resolve_relative_length_class(
                age_min=spec.age_min,
                age_max=spec.age_max,
                target_words=spec.target_words,
                reading_mode=spec.reading_mode,
            )
            self.assertEqual(mode, "INDEPENDENT_READER")
            self.assertEqual(relative_class, "STANDARD")
            self.assertEqual(spec.narrative_family, "puzzle_problem_solving")


if __name__ == "__main__":
    unittest.main()
