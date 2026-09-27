from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.visual_contracts import (
    CharacterVisualProfile,
    FailureSeverity,
    ValidationStatus,
    VisualCategory,
    VisualIntent,
    VisualRequest,
    VisualValidationIssue,
    VisualValidationResult,
)
from src.visual_ledger import read_jsonl
from src.visual_provider import FixtureVisualProviderAdapter
from src.visual_retry import generate_visual_with_bounded_validation_retry


def request() -> VisualRequest:
    return VisualRequest(
        request_id="retry-root",
        profile_id="profile-1",
        category=VisualCategory.CHARACTER_PORTRAIT,
        intent=VisualIntent(subject="Elara"),
        style_id="lumi-storybook-soft",
        model_id="fixture/lumi-visual-v1",
        character_profile=CharacterVisualProfile(
            character_id="elara",
            version="1.0.0",
            apparent_age=11,
            eyes="amber brown",
            hair={"color": "dark chestnut"},
            must_keep=["amber brown eyes"],
        ),
    )


class VisualRetryTests(unittest.TestCase):
    def test_critical_semantic_defect_triggers_one_new_invocation(self) -> None:
        validations = iter([
            VisualValidationResult(
                status=ValidationStatus.RETRY,
                issues=[
                    VisualValidationIssue(
                        code="WRONG_EYE_COLOR",
                        severity=FailureSeverity.CRITICAL,
                        message="Preserve amber brown eyes.",
                    )
                ],
            ),
            VisualValidationResult(status=ValidationStatus.PASS),
        ])

        with tempfile.TemporaryDirectory() as tmp:
            result = generate_visual_with_bounded_validation_retry(
                request(),
                adapter_factory=lambda attempt: FixtureVisualProviderAdapter(
                    image_bytes=f"image-{attempt}".encode()
                ),
                semantic_validator=lambda _: next(validations),
                evidence_dir=Path(tmp),
                max_validation_retries=1,
                require_qualified=True,
            )
            self.assertEqual(result.validation.status, ValidationStatus.PASS)
            invocations = read_jsonl(Path(tmp) / "visual_invocations.jsonl")
            self.assertEqual(len(invocations), 2)
            self.assertNotEqual(invocations[0]["request_id"], invocations[1]["request_id"])
            self.assertIn(
                "Correct only these proven visual defects",
                result.compiled_prompt.positive_prompt,
            )


if __name__ == "__main__":
    unittest.main()
