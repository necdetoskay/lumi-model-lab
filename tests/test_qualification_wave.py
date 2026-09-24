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

WAVE = Path("configs/qualification_waves/age-relative-standard-v2.yaml")
OLD_WAVE = Path("configs/qualification_waves/age-standard-v1.yaml")


class QualificationWaveTests(unittest.TestCase):
    def test_age_relative_standard_wave_has_24_cases(self) -> None:
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

    def test_age_cases_use_age_appropriate_standard_targets(self) -> None:
        rows = matrix_payload(WAVE)["include"]
        expected = {
            "EARLY_CHILD": (4, 500, "READ_ALOUD"),
            "CHILD": (7, 1500, "EARLY_READER"),
            "MIDDLE_CHILD": (10, 2800, "INDEPENDENT_READER"),
            "TEEN": (15, 3800, "INDEPENDENT_READER"),
            "YOUNG_ADULT": (21, 4200, "INDEPENDENT_READER"),
            "ADULT": (32, 4200, "INDEPENDENT_READER"),
            "MATURE_ADULT": (50, 4200, "INDEPENDENT_READER"),
            "SENIOR": (70, 4200, "INDEPENDENT_READER"),
        }
        for tier, (age, words, mode) in expected.items():
            tier_rows = [row for row in rows if row["age_tier"] == tier]
            self.assertEqual(len(tier_rows), 3)
            self.assertTrue(all(row["exact_age"] == age for row in tier_rows))
            self.assertTrue(all(row["target_words"] == words for row in tier_rows))
            self.assertTrue(all(row["reading_mode"] == mode for row in tier_rows))
            self.assertTrue(
                all(row["relative_length_class"] == "STANDARD" for row in tier_rows)
            )

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
                self.assertEqual(spec.language, "en")
                self.assertTrue(spec.narrative_family)
                self.assertTrue(spec.reading_mode)
                self.assertEqual(spec.relative_length_class, "STANDARD")

    def test_wave_fails_if_representative_age_is_in_wrong_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = load_wave(WAVE)
            bad = copy.deepcopy(source)
            bad["age_cases"]["CHILD"]["exact_age"] = 10
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                yaml.safe_dump(bad, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "maps to MIDDLE_CHILD"):
                load_wave(path)

    def test_wave_fails_if_age_target_uses_wrong_standard_length(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = load_wave(WAVE)
            bad = copy.deepcopy(source)
            bad["age_cases"]["EARLY_CHILD"]["target_words"] = 2000
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                yaml.safe_dump(bad, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be 500"):
                load_wave(path)

    def test_wave_fails_if_reading_mode_is_wrong_for_tier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = load_wave(WAVE)
            bad = copy.deepcopy(source)
            bad["age_cases"]["EARLY_CHILD"]["reading_mode"] = "INDEPENDENT_READER"
            path = Path(tmp) / "bad.yaml"
            path.write_text(
                yaml.safe_dump(bad, sort_keys=False),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "must be READ_ALOUD"):
                load_wave(path)

    def test_superseded_global_2000_word_wave_is_not_executable(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Unsupported qualification wave schema"):
            load_wave(OLD_WAVE)

    def test_case_ids_are_unique_and_paths_are_stable(self) -> None:
        rows = matrix_payload(WAVE)["include"]
        case_ids = [row["case_id"] for row in rows]
        paths = [row["spec_path"] for row in rows]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertTrue(
            all(
                path.startswith(
                    "data/specifications/waves/age-relative-standard-v2/"
                )
                for path in paths
            )
        )


if __name__ == "__main__":
    unittest.main()
