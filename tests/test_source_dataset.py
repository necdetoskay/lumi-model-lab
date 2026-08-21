import unittest

from src.source_dataset import as_runner_config


class SourceDatasetConfigTests(unittest.TestCase):
    def test_source_config_maps_to_single_teacher_runner(self):
        config = {
            "name": "m1",
            "teacher_model": "aion-labs/aion-3.0",
            "specs": ["a.yaml", "b.yaml"],
            "output_dir": "runs/source_dataset",
        }
        result = as_runner_config(config)
        self.assertEqual(result["models"], ["aion-labs/aion-3.0"])
        self.assertEqual(result["specs"], ["a.yaml", "b.yaml"])
        self.assertEqual(result["output_dir"], "runs/source_dataset")

    def test_source_config_requires_teacher(self):
        with self.assertRaises(RuntimeError):
            as_runner_config({"specs": ["a.yaml"]})


if __name__ == "__main__":
    unittest.main()
