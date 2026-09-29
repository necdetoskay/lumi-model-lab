from __future__ import annotations

import unittest

from src.translation_fidelity_recovery import _apply_repairs, _blocking


class TranslationFidelityRecoveryTests(unittest.TestCase):
    def test_apply_repairs_is_exact_and_bounded(self):
        text, applied = _apply_repairs(
            "Önce A oldu. Sonra B oldu.",
            {"repairs": [{"old": "A oldu", "new": "A gerçekleşti", "why": "fidelity"}]},
        )
        self.assertEqual(text, "Önce A gerçekleşti. Sonra B oldu.")
        self.assertEqual(len(applied), 1)

    def test_apply_repairs_rejects_ambiguous_target(self):
        with self.assertRaises(RuntimeError):
            _apply_repairs(
                "aynı aynı",
                {"repairs": [{"old": "aynı", "new": "farklı", "why": "x"}]},
            )

    def test_blocking_filters_only_serious_critical(self):
        rows = _blocking(
            [
                {"severity": "minor"},
                {"severity": "serious", "class": "omission"},
                {"severity": "critical", "class": "ending_shift"},
            ]
        )
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
