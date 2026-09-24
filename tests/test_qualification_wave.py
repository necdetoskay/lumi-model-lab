from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

import yaml

from src.qualification_wave import (
    load_wave,
    materialize_wave,
    matrix_payload,
    validate_materialized_wave,
)
from src.schemas import StorySpec

WAVE = Path("configs/qualification_waves/age-standard-v1.yaml")


class QualificationWaveTests(unittest.TestCase):
    def test_age_standard_wave_has_24_cases(self) -> None:
        matrix = matrix_payload(WAVE)
        rows = matrix["include"]
        self.assertEqual(len(rows), 24)
        self.assertEqual(
            {row["age_tier"] for row in rows},
            {
                "EARLY_CHILD",
                "CHILD",
                "MIDDLE_CHILD",
                "TEEN",
                "YOUNG_ADULT",
                "ADULT",
                "MATURE_ADULT",
                "SENIOR",
            },
        )
        self.assertEqual(
            {row["narrative_family"] for row in rows},
            {
                "exploration_mystery",
                "emotional_development",
                "puzzle_problem_solving",
            },
        )

    def test_representative_ages_are_exact_and_cover_every_tier(self) -> None:
        rows = matrix_payload(WAVE)["include"]
        expected = {
            "EARLY_CHILD": 4,
            "CHILD": 7,
            "MIDDLE_CHILD": 10,
            "TEEN": 15,
            "YOUNG_ADULT": 21,
            "ADULT": 32,
            "MATURE_ADULT": 50,
            "SENIOR": 70,
        }
        for tier, age in expected.items():
            tier_rows = [row for row in rows if row["age_tier"] == tier]
            self.assertEqual(len(tier_rows), 3)
            self.assertTrue(all(row["exact_age"] == age for row in tier_rows))

    def test_materialized_specs_are_deterministic_and_valid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            materialize_wave(WAVE, output_root=root)
            first = {
                path.relative_to(root): path.read_bytes()
                for path in sorted(root.rglob("*.yaml"))
            }
            self.assertEqual(len(first), 24)
            materialize_wave(WAVE, output_root=root)
            second = {
                path.relative_to(root): path.read_bytes()
                for path in sorted(root.rglob("*.yaml"))
            }
            self.assertEqual(first, second)
            self.assertEqual(validate_materialized_wave(WAVE, output_root=root), [])

            for path in root.rglob("*.yaml"):
                spec = StorySpec.model_validate(
                    yaml.safe_load(path.read_text(encoding="utf-8"))
                )
                self.assertEqual(spec.age_min, spec.age_max)
                self.assertEqual(spec.target_words, 2000)
                self.assertEqual(spec.language, "en")
                self.assertTrue(spec.narrative_family)

    def test_wave_fails_if_representative_age_is_in_wrong_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = load_wave(WAVE)
            bad = copy.deepcopy(source)
            bad["representative_ages"]["CHILD"] = 10
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                yaml.safe_dump(bad, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "maps to MIDDLE_CHILD"):
                load_wave(path)

    def test_wave_fails_if_target_is_not_standard_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = load_wave(WAVE)
            bad = copy.deepcopy(source)
            bad["target_words"] = 1000
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                yaml.safe_dump(bad, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "STANDARD"):
                load_wave(path)

    def test_case_ids_are_unique_and_paths_are_stable(self) -> None:
        rows = matrix_payload(WAVE)["include"]
        case_ids = [row["case_id"] for row in rows]
        paths = [row["spec_path"] for row in rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(
            all(
                path.startswith("data/specifications/waves/age-standard-v1/")
                for path in paths
            )
        )


if __name__ == "__main__":
    unittest.main()
