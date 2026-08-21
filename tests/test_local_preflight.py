import unittest

from src.local_preflight import classify


class LocalPreflightTests(unittest.TestCase):
    def test_no_torch_is_not_ready(self) -> None:
        result = {
            "python": "3.12.0",
            "packages": {"torch": None},
            "cuda": {"available": False, "devices": []},
        }
        status, notes = classify(result)
        self.assertEqual(status, "not_ready")
        self.assertTrue(any("torch" in note for note in notes))

    def test_four_gb_gpu_is_constrained(self) -> None:
        result = {
            "python": "3.12.0",
            "packages": {
                "torch": "2.10.0",
                "transformers": None,
                "datasets": None,
                "peft": None,
                "trl": None,
                "bitsandbytes": None,
                "unsloth": None,
            },
            "cuda": {
                "available": True,
                "devices": [{"total_vram_gb": 4.0}],
            },
        }
        status, notes = classify(result)
        self.assertEqual(status, "constrained")
        self.assertTrue(any("below 6 GB" in note for note in notes))

    def test_eight_gb_gpu_with_missing_stack_is_stack_missing(self) -> None:
        result = {
            "python": "3.12.0",
            "packages": {
                "torch": "2.10.0",
                "transformers": None,
                "datasets": None,
                "peft": None,
                "trl": None,
                "bitsandbytes": None,
                "unsloth": None,
            },
            "cuda": {
                "available": True,
                "devices": [{"total_vram_gb": 8.0}],
            },
        }
        status, _ = classify(result)
        self.assertEqual(status, "stack_missing")


if __name__ == "__main__":
    unittest.main()
