from __future__ import annotations

from src.visual_contracts import (
    FailureSeverity,
    ValidationStatus,
    VisualArtifact,
    VisualRequest,
    VisualValidationIssue,
    VisualValidationResult,
)


def validate_visual_result(
    request: VisualRequest,
    artifacts: list[VisualArtifact],
) -> VisualValidationResult:
    issues: list[VisualValidationIssue] = []
    checked: list[str] = []

    if not artifacts:
        issues.append(
            VisualValidationIssue(
                code="NO_ARTIFACT",
                severity=FailureSeverity.CRITICAL,
                message="Provider returned no persisted visual artifact.",
            )
        )

    if request.character_profile:
        checked.extend(request.character_profile.must_keep)
        if not request.character_profile.must_keep:
            issues.append(
                VisualValidationIssue(
                    code="CHARACTER_IDENTITY_CONTRACT_EMPTY",
                    severity=FailureSeverity.MINOR,
                    message="Character request has no must_keep identity constraints.",
                )
            )

    if request.world_profile:
        checked.extend(f"forbid:{item}" for item in request.world_profile.forbidden_visuals)

    # This deterministic validator proves lineage/contract completeness only.
    # Semantic pixels-vs-contract validation is performed by the qualified visual-evaluator lane.
    if any(issue.severity == FailureSeverity.CRITICAL for issue in issues):
        status = ValidationStatus.RETRY
    elif issues:
        status = ValidationStatus.PASS
    else:
        status = ValidationStatus.PASS

    return VisualValidationResult(status=status, issues=issues, checked_constraints=checked)
