from pathlib import Path
import unittest

import yaml

from src.schemas import StorySpec


BENCHMARK_DIR = Path("data/specifications/benchmark_en")


class EnglishBenchmarkSetTests(unittest.TestCase):
    def test_frozen_english_benchmark_set_has_five_valid_cases(self) -> None:
        paths = sorted(BENCHMARK_DIR.glob("*.yaml"))
        self.assertEqual(
            [path.name for path in paths],
            [
                "01_exploration_mystery.yaml",
                "02_friendship_social.yaml",
                "03_puzzle_problem_solving.yaml",
                "04_fantasy_adventure.yaml",
                "05_emotional_calm.yaml",
            ],
        )
        for path in paths:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
            spec = StorySpec.model_validate(raw)
            self.assertEqual(spec.language, "en", path.name)
            self.assertEqual(spec.target_words, 2000, path.name)
            self.assertEqual((spec.age_min, spec.age_max), (6, 8), path.name)
            self.assertEqual(len(spec.constraints), 5, path.name)
            self.assertTrue(spec.title_hint, path.name)
            self.assertTrue(spec.protagonist, path.name)
            self.assertTrue(spec.setting, path.name)
            self.assertTrue(spec.theme, path.name)
            self.assertTrue(spec.premise, path.name)


if __name__ == "__main__":
    unittest.main()
