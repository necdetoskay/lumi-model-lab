"""P1 read-only historical evidence bridge: real frozen SpineForge/Q25 outputs.

Four *independent* past cases; no implied shared story, sequence or handoff.
Recorded historical gates are not authenticated by this harness. No model calls.
"""
from __future__ import annotations

import argparse
import copy
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

ARCHIVE_SCHEMA = "lumi.story-harness-frozen-import.v1"
REPORT_SCHEMA = "lumi.story-harness-historical-evidence.v1"
SOURCE_REPO = "necdetoskay/lumi-model-lab"
ADAPTERS = frozenset({"spine_human_review", "spine_story_audit", "q25_paid_extractor"})
REQUIRED = {"schema", "source_repository", "source_commit", "source_branch_at_import", "mode", "cases"}
CASE_KEYS = {"case_id", "adapter", "files"}
FILE_KEYS = {"kind", "archive", "source_path", "sha256"}
SHA = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
CASE_ID = re.compile(r"^[A-Z0-9][A-Z0-9_-]{3,79}$")
# P1 is a frozen, independently reviewed import set, NOT an open-ended
# mechanism for relabeling rejected historical runs under a new case name.
PINNED_SOURCE_COMMIT = "2eb3d825b5baf8f0f16ccb23805f619d433c7236"
FROZEN_CASES = {
    "SPINE-V20-HUMAN-APPROVED": {
        "adapter": "spine_human_review",
        "files": {"decision": (
            "spine-v20-approved.json",
            "evidence/spineforge-v20-human-review/36910614976-approved.json",
            "72cd2ecc973884415747aed93e721c2fbb32617901c24884142585b9c54254a3")},
    },
    "SPINE-V20-AUDIT-REJECTED": {
        "adapter": "spine_story_audit",
        "files": {"decision": (
            "spine-v20-audit-rejected.json",
            "evidence/spineforge-v20-paid-story-audit/36969500342/qualification-report.json",
            "eeb20809307a135d725c30d2d2a76209add2e4bae2e2e457526eef7b734edb6c")},
    },
    "Q25-KITE01-CANDIDATES": {
        "adapter": "q25_paid_extractor",
        "files": {
            "ledger": ("kite-q25-ledger.json",
                "evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-03-public-ledger.json",
                "794bdb6807b43bc16807252378f786c87ddfe920063cc7101c9d8def49ae2848"),
            "raw": ("kite-q25-raw.json",
                "evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-03-raw-extraction.json",
                "41581dfc081c41c2fa29007b85ade49902edc222ba4a31ed26168db7773ba2d2"),
        },
    },
    "Q25-GREENHOUSE01-REJECTED": {
        "adapter": "q25_paid_extractor",
        "files": {
            "ledger": ("greenhouse-q25-ledger.json",
                "evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/paid-attempt-01-public-ledger.json",
                "40b844ba3521100b9fd6de86b74a1339e2a40b341170492b4bf5ab3045e2bfa4"),
            "raw": ("greenhouse-q25-raw.json",
                "evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/paid-attempt-01-raw-extraction.json",
                "c551895a16957b0f6e6650e720cd8572dd8260e8a774b52b083bf63eceb770bb"),
        },
    },
}



def _fail_unless(condition, reason):
    if not condition:
        raise HarnessStop(reason)


def _validate_import(manifest):
    _fail_unless(isinstance(manifest, dict) and set(manifest) == REQUIRED,
                 "Malformed historical import")
    _fail_unless(
        manifest["schema"] == ARCHIVE_SCHEMA and
        manifest["source_repository"] == SOURCE_REPO and
        manifest["source_branch_at_import"] == "experiment/q25-narrative-memory-intent" and
        isinstance(manifest["source_commit"], str) and COMMIT.fullmatch(manifest["source_commit"]) and
        manifest["mode"] == "HISTORICAL_READ_ONLY" and
        manifest["source_commit"] == PINNED_SOURCE_COMMIT,
        "Historical provenance or execution mode not qualified",
    )
    cases = manifest["cases"]
    _fail_unless(isinstance(cases, list) and 1 <= len(cases) <= 20,
                 "Historical cases must be a bounded list")
    seen_cases, seen_files = set(), set()
    for case in cases:
        _fail_unless(isinstance(case, dict) and set(case) == CASE_KEYS,
                     "Malformed historical case")
        ident, adapter = case["case_id"], case["adapter"]
        _fail_unless(isinstance(ident, str) and CASE_ID.fullmatch(ident)
                     and ident not in seen_cases and adapter in ADAPTERS,
                     "Unqualified historical case or adapter")
        seen_cases.add(ident)
        parts = case["files"]
        expected = {"decision"} if adapter.startswith("spine_") else {"ledger", "raw"}
        _fail_unless(isinstance(parts, list) and len(parts) == len(expected),
                     "Historical file count mismatch")
        kinds = set()
        for item in parts:
            _fail_unless(isinstance(item, dict) and set(item) == FILE_KEYS,
                         "Historical file entry malformed")
            kind, path, source, sha = (
                item["kind"], item["archive"], item["source_path"], item["sha256"])
            _fail_unless(isinstance(path, str) and
                         path.startswith("evidence/story_harness_p1/snapshots/") and
                         isinstance(source, str) and (
                             source.startswith("evidence/spineforge-") or
                             source.startswith("evidence/q25/")) and
                         isinstance(sha, str) and SHA.fullmatch(sha) and
                         path not in seen_files and kind in expected,
                         "Historical file path/kind/hash not qualified")
            seen_files.add(path)
            kinds.add(kind)
            if adapter.startswith("spine_"):
                _fail_unless(source.startswith("evidence/spineforge-"),
                             "Spine adapter bound to wrong source family")
            else:
                _fail_unless(source.startswith("evidence/q25/"),
                             "Q25 adapter bound to wrong source family")
        _fail_unless(kinds == expected, "Missing or repeated historical source role")
        pinned = FROZEN_CASES.get(ident)
        _fail_unless(pinned is not None and adapter == pinned["adapter"],
                     "Historical case identity/adapter is not pinned")
        for item in parts:
            registered = pinned["files"].get(item["kind"])
            _fail_unless(registered is not None and
                         item["archive"] == "evidence/story_harness_p1/snapshots/" + registered[0] and
                         item["source_path"] == registered[1] and
                         item["sha256"] == registered[2],
                         "Historical source path, identity and frozen hash mismatch")


def _q25_record(case, records):
    ledger, raw = records["ledger"], records["raw"]
    _fail_unless(
        ledger.get("schema") == "q25.openrouter-pilot-ledger.v1" and
        raw.get("schema_name") == "q25.extractor-raw-output.v1" and
        ledger.get("source_sha256") == raw.get("source_sha256") and
        ledger.get("seed_sha256") == raw.get("seed_sha256") and
        isinstance(ledger.get("source_sha256"), str) and
        SHA.fullmatch(ledger["source_sha256"]) is not None and
        isinstance(ledger.get("seed_sha256"), str) and
        SHA.fullmatch(ledger["seed_sha256"]) is not None and
        ledger.get("attempted_calls") == ledger.get("provider_calls") == 1 and
        ledger.get("max_calls") == 1 and
        ledger.get("state_commit_authorized") is False and
        ledger.get("billing_status") == "PROVIDER_REPORTED_USAGE" and
        ledger.get("model") == "anthropic/claude-sonnet-5.5",
        "Q25 saved paid ledger/raw bindings or historical authority invalid",
    )
    outcome = ledger.get("outcome")
    _fail_unless(outcome in ("SOURCE_BOUND_CANDIDATES_ONLY", "REJECTED_BY_OFFLINE_GATE"),
                 "Unexpected historical Q25 source outcome")
    _fail_unless(isinstance(ledger.get("usage"), dict), "Missing reported provider usage")
    usage = ledger["usage"]
    _fail_unless(all(type(usage.get(k)) is int and usage[k] >= 0
                      for k in ("prompt_tokens", "completion_tokens", "total_tokens"))
                 and usage["prompt_tokens"] + usage["completion_tokens"] == usage["total_tokens"],
                 "Invalid provider-reported Q25 token counts")
    try:
        cost = Decimal(str(usage["actual_cost_usd"]))
        cap = Decimal(str(ledger["max_cost_usd"]))
    except (ValueError, InvalidOperation, KeyError, TypeError) as exc:
        raise HarnessStop("Missing provider-reported Q25 monetary amount") from exc
    _fail_unless(cost.is_finite() and cap.is_finite()
                 and 0 <= cost <= cap <= Decimal("0.20"),
                 "Historical billed price outside bounded experiment")
    actual_count = sum(len(raw[k]) for k in (
        "objects", "terminal_relations", "character_claims",
        "goal_claims", "obligation_claims", "thread_claims", "property_claims"))
    if outcome == "SOURCE_BOUND_CANDIDATES_ONLY":
        _fail_unless(ledger.get("candidate_count") == actual_count
                     and ledger.get("terminal_state_complete") is False
                     and ledger.get("independent_semantic_review_complete") is False
                     and ledger.get("review_status") == "AWAITING_EXTERNAL_REVIEW",
                     "Passing source-bound Q25 extraction was falsely certified")
    else:
        _fail_unless(ledger.get("gate_failure_type") == "ValueError",
                     "Rejected paid run is not the original preserved failure")
    return {
        "historical_original_outcome": outcome,
        "historical_outcome_class": (
            "SOURCE_BOUND_CANDIDATES_ONLY_NOT_FINAL_STATE"
            if outcome == "SOURCE_BOUND_CANDIDATES_ONLY"
            else "PAID_RUN_REJECTED_DO_NOT_RETROACTIVELY_PASS"),
        "historical_stop_required": True,
        "raw_claim_count": actual_count,
        "model": ledger["model"],
        "historical_provider_calls_reported": 1,
        "historical_provider_cost_usd": str(cost),
        "new_provider_calls": 0,
        "new_provider_cost_usd": "0",
        "semantic_review_required": True,
        "canonical_state_admitted": False,
    }


def _spine_record(case, records):
    data = records["decision"]
    if case["adapter"] == "spine_human_review":
        _fail_unless(
            data.get("schema") == "spineforge-v20-human-approved.v1" and
            data.get("gate_decision") == "ACCEPT" and
            data.get("human_review", {}).get("verdict") == "APPROVE" and
            data.get("human_review", {}).get("story_writer_authorized") is True and
            data.get("writer_handoff_ready") is True and
            data.get("paid_writer_execution_authorized") is False and
            isinstance(data.get("spine_hash"), str) and SHA.fullmatch(data["spine_hash"]),
            "Spine historical author approval/handoff evidence invalid",
        )
        label = "HUMAN_SPINE_APPROVAL_RECORDED_HARNESS_NOT_AUTHORITY"
        original = data["gate_decision"]
        note = "Original review records writer handoff readiness; no paid writer execution authorized."
    else:
        _fail_unless(
            data.get("schema") == "spineforge-v20-story-audit-qualification-report.v1" and
            data.get("status") == "FAIL_KNOWN_DEFECT_MISSED" and
            data.get("qualification_pass") is False and
            isinstance(data.get("target_count"), int) and data["target_count"] > 0 and
            isinstance(data.get("matched_target_count"), int)
            and data["matched_target_count"] < data["target_count"],
            "Spine historical failed audit was modified or upgraded",
        )
        label = "SPINE_AUDIT_FAILED_HARNESS_MUST_BLOCK"
        original = data["status"]
        note = "Historical detector failed known defect; cannot promote audit or downstream story."
    return {
        "historical_original_outcome": original,
        "historical_outcome_class": label,
        "historical_stop_required": case["adapter"] == "spine_story_audit",
        "reviewer_authenticated_by_harness": False,
        "original_gate_reexecuted": False,
        "model_call_authorized": False,
        "source_note": note,
    }


def inspect_historical(manifest, *, repo_root: Path | str):
    """Verify six original byte-copies and audit *separate* historical cases."""
    original = copy.deepcopy(manifest)
    _validate_import(manifest)
    root = Path(repo_root).resolve(strict=True)
    result = []
    total_historical_cost = Decimal("0")
    for case in manifest["cases"]:
        archive_records, stored = {}, []
        for item in case["files"]:
            bytes_ = secure_artifact(root, item["archive"])
            actual = digest(bytes_)
            _fail_unless(actual == item["sha256"],
                         "Archived historical artifact differs from source hash")
            archive_records[item["kind"]] = load_json(bytes_)
            stored.append({
                "role": item["kind"], "source_repository": manifest["source_repository"],
                "source_commit": manifest["source_commit"],
                "source_path": item["source_path"],
                "archive_path": item["archive"],
                "verified_sha256": actual,
                "source_bytes_rechecked_against_remote_this_run": False,
            })
        assessment = (
            _spine_record(case, archive_records)
            if case["adapter"].startswith("spine_")
            else _q25_record(case, archive_records)
        )
        if case["adapter"] == "q25_paid_extractor":
            total_historical_cost += Decimal(assessment["historical_provider_cost_usd"])
        result.append({
            "case_id": case["case_id"], "adapter": case["adapter"],
            "artifact_inventory": stored, "inspection": assessment,
            "shared_story_dependency_inferred": False,
            "historical_gate_authenticated_by_harness": False,
            "downstream_execution_permitted_by_harness": False,
        })
    _fail_unless(original == manifest, "Historical import mutated source manifest")
    return {
        "schema": REPORT_SCHEMA,
        "import_manifest_sha256": digest(canonical_bytes(manifest)),
        "source_repository": manifest["source_repository"],
        "source_commit": manifest["source_commit"],
        "case_count": len(result),
        "historical_cases": result,
        "sum_historical_provider_reported_cost_usd_for_q25_subset": str(total_historical_cost),
        "new_provider_calls": 0,
        "new_provider_cost_usd": "0",
        "real_gate_invocations": 0,
        "historical_verdicts_rewritten": False,
        "spine_and_q25_story_chain_claimed": False,
        "historical_gate_authenticated_by_harness": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.repo_root.resolve(strict=True)
    manifest = load_json(secure_artifact(root, str(args.manifest)))
    print(json.dumps(inspect_historical(manifest, repo_root=root),
                     sort_keys=True, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
