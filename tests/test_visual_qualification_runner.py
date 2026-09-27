from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.visual_qualification_runner import run_visual_qualification


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "visual_qualification_fixture.yaml"


class VisualQualificationRunnerTests(unittest.TestCase):
    def test_full_fixture_matrix_is_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = run_visual_qualification(CONFIG, evidence_dir=Path(tmp))
            self.assertEqual(report["total_rows"], 40)
            self.assertEqual(report["qualified_rows"], 40)
            self.assertEqual(len(report["routes"]), 40)
            self.assertEqual(len(report["observations"]), 120)
            self.assertTrue((Path(tmp) / "qualification_report.json").exists())


if __name__ == "__main__":
    unittest.main()
