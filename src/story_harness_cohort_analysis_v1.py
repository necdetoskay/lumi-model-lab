"""Batch-complete, offline-only clustering of externally collected findings.

This deliberately does NOT verify upstream quality/provider receipts. It never
promotes a quality claim to independently attested ACCEPT or modifies a story.
"""
from __future__ import annotations

from collections import defaultdict
import re

from src.story_harness_frozen_cohort_v1 import IDS, round_coverage, must

FAMILIES = {
    "physical", "causal", "state", "spatial", "temporal",
    "epistemic", "response", "closure", "canon", "age",
    "spine", "narrative",
}
STAGES = {"SPINEFORGE", "WRITER", "HANDOFF", "QUALITY", "Q25", "FINAL_STATE", "UNKNOWN"}
SHA = re.compile(r"[a-f0-9]{64}\Z")


def cluster_after_full_round(rows, *, round_name):
    """Report repeated suspect causes; no inference, no evidence attestation."""
    must(type(rows) is list and len(rows) <= 10, "INVALID_ROWS")
    simplified = []
    for row in rows:
        must(type(row) is dict and
             set(row) == {"case_id", "round", "status", "findings"},
             "INVALID_ROW_FIELDS")
        simplified.append({k: row[k] for k in ("case_id", "round", "status")})
    coverage = round_coverage(simplified, round_name)
    must(coverage["all_attempts_recorded"], "PREMATURE_ROOT_CAUSE_ANALYSIS")
    clusters = defaultdict(lambda: {"cases": set(), "primary": set(), "blockers": set()})
    rejected_cases = 0
    operational = 0
    unverified_accepts = 0
    for row in rows:
        ident, status = row["case_id"], row["status"]
        findings = row["findings"]
        must(type(findings) is list and len(findings) <= 24, "INVALID_FINDINGS")
        if status == "ACCEPT_CLAIMED":
            unverified_accepts += 1
            must(not findings, "ACCEPT_WITH_FINDINGS")
        if status in ("STOP_UNKNOWN_OR_INVALID", "OPERATIONAL_STOP"):
            operational += 1
            must(not findings, "DO_NOT_MISCLASSIFY_OPERATIONAL_STOP")
        if status == "REJECT":
            rejected_cases += 1
            must(len(findings) >= 1, "UNDIAGNOSED_REJECT")
        seen = set()
        primary_count = 0
        for f in findings:
            must(type(f) is dict and
                 set(f) == {"family", "stage", "severity",
                            "role", "support_sha256"}, "BAD_FINDING")
            family, stage = f["family"], f["stage"]
            must(type(family) is str and family in FAMILIES and
                 type(stage) is str and stage in STAGES and
                 f["severity"] in ("BLOCKER", "ADVISORY") and
                 f["role"] in ("PRIMARY", "CONTRIBUTING") and
                 type(f["support_sha256"]) is str and
                 SHA.fullmatch(f["support_sha256"]) is not None, "BAD_FINDING_VALUE")
            key = (stage, family)
            must((stage, family, f["role"]) not in seen, "DUPLICATE_CAUSE")
            seen.add((stage, family, f["role"]))
            if f["role"] == "PRIMARY":
                primary_count += 1
                must(f["severity"] == "BLOCKER", "PRIMARY_MUST_BLOCK")
            v = clusters[key]
            v["cases"].add(ident)
            if f["role"] == "PRIMARY":
                v["primary"].add(ident)
            if f["severity"] == "BLOCKER":
                v["blockers"].add(ident)
        if status == "REJECT":
            must(primary_count == 1, "PRIMARY_CAUSE_REQUIRED")
        else:
            must(not findings, "FINDINGS_WITHOUT_REJECTION")
    summary = []
    for (stage, family), details in clusters.items():
        summary.append({
            "stage": stage, "family": family,
            "affected_cases": len(details["cases"]),
            "case_ids": sorted(details["cases"]),
            "primary_root_cause_cases": len(details["primary"]),
            "blocking_cases": len(details["blockers"]),
        })
    summary.sort(key=lambda x: (-x["affected_cases"],
                                -x["primary_root_cause_cases"],
                                -x["blocking_cases"],
                                x["stage"], x["family"]))
    return {
        "status": "DIAGNOSTIC_CLUSTERS_UNVERIFIED_NOT_QUALITY_CERTIFICATION",
        "round": round_name,
        "complete_cohort_attempts": 10,
        "real_provider_or_quality_evidence_reverified": False,
        "quality_success_rate_certified": False,
        "independent_passes": None,
        "claimed_accepts_not_certified": unverified_accepts,
        "quality_rejected_cases": rejected_cases,
        "provider_or_operational_stops_not_story_quality": operational,
        "candidate_repeated_root_causes": [x for x in summary if x["affected_cases"] >= 2],
        "single_case_findings": [x for x in summary if x["affected_cases"] < 2],
        "individual_story_rewrite_authorized": False,
        "harness_patch_authorized_by_report": False,
    }
