from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {
    "minor": 1,
    "moderate": 2,
    "serious": 3,
    "critical": 4,
}


def evaluate_story_audit_qualification(
    *,
    result_path: Path,
    gold_path: Path,
) -> dict[str, Any]:
    result = json.loads(result_path.read_text(encoding="utf-8"))
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    if result.get("schema") != "spineforge-v20-story-audit-execution.v1":
        raise RuntimeError("Story Audit qualification result schema mismatch.")
    if result.get("status") not in {
        "audit_completed",
        "audit_reprocessed_zero_cost",
        "audit_contract_failure",
    }:
        raise RuntimeError(
            "Story Audit qualification requires completed, contract-failure, "
            "or zero-cost reprocessed audit evidence."
        )
    if gold.get("schema") != "spineforge-v20-story-audit-qualification-gold.v1":
        raise RuntimeError("Story Audit qualification gold schema mismatch.")
    if result.get("source_story_sha256") != gold.get("source_story_sha256"):
        raise RuntimeError("Story Audit qualification source story SHA mismatch.")
    if result.get("source_artifact_id") != gold.get("source_artifact_id"):
        raise RuntimeError("Story Audit qualification source artifact mismatch.")

    artifact = result.get("audit_artifact") or {}
    if artifact.get("findings") is not None:
        findings = list(artifact.get("findings") or [])
        findings_source = "audit_artifact"
    else:
        findings = list(result.get("merged_findings_before_artifact") or [])
        findings_source = "merged_findings_before_artifact"
    targets = list(gold.get("targets") or [])

    target_results: list[dict[str, Any]] = []
    matched_count = 0
    for target in targets:
        target_family = str(target["family"])
        anchor = str(target["anchor"])
        required_scope = str(target["required_repair_scope"])
        minimum = str(target["minimum_severity"]).lower()
        minimum_rank = SEVERITY_ORDER[minimum]

        matches = []
        for index, finding in enumerate(findings):
            severity = str(finding.get("severity") or "").lower()
            exact_text = str(finding.get("exact_text") or "")
            if (
                finding.get("family") == target_family
                and finding.get("repair_scope") == required_scope
                and anchor in exact_text
                and SEVERITY_ORDER.get(severity, 0) >= minimum_rank
            ):
                matches.append(index)

        matched = bool(matches)
        if matched:
            matched_count += 1
        target_results.append({
            "target_id": target["id"],
            "matched": matched,
            "matching_finding_indexes": matches,
        })

    target_count = len(targets)
    recall = matched_count / target_count if target_count else 1.0
    passed = recall == 1.0

    return {
        "schema": "spineforge-v20-story-audit-qualification-report.v1",
        "source_story_sha256": gold["source_story_sha256"],
        "source_artifact_id": gold["source_artifact_id"],
        "target_count": target_count,
        "matched_target_count": matched_count,
        "target_recall": recall,
        "target_results": target_results,
        "findings_source": findings_source,
        "qualification_pass": passed,
        "status": "PASS" if passed else "FAIL_KNOWN_DEFECT_MISSED",
    }
