"""P2 typed StageResult and *executed* local source-integrity gate receipts.

The verifier actually replays P1's frozen byte/hash/schema checks in-process.
It does NOT authenticate the original historical human or semantic model gate,
run any providers, prove a story, or grant downstream/production permission.

Only locally derived receipts are emitted. A caller-supplied receipt must be
recomputed and compared against original frozen artifacts before use.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Literal

from src.story_harness_p1 import inspect_historical, PINNED_SOURCE_COMMIT
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

GATE_VERSION = "p2.local-frozen-integrity-gate.v1"
REPORT_SCHEMA = "lumi.story-harness-p2-result-bundle.v1"
STAGE_RESULT_SCHEMA = "lumi.story-harness-stage-result.v1"
RECEIPT_SCHEMA = "lumi.story-harness-local-gate-receipt.v1"
STAGE_TYPE = {
    "SPINE-V20-HUMAN-APPROVED": "spine_human_review",
    "SPINE-V20-AUDIT-REJECTED": "spine_story_audit",
    "Q25-KITE01-CANDIDATES": "q25_paid_extractor",
    "Q25-GREENHOUSE01-REJECTED": "q25_paid_extractor",
}
STOP_CLASS = {
    "SPINE-V20-HUMAN-APPROVED": "HISTORICAL_APPROVAL_UNAUTHENTICATED",
    "SPINE-V20-AUDIT-REJECTED": "HISTORICAL_QUALITY_GATE_FAILED",
    "Q25-KITE01-CANDIDATES": "STATE_CANDIDATES_AWAIT_SEMANTIC_REVIEW",
    "Q25-GREENHOUSE01-REJECTED": "HISTORICAL_EXTRACTOR_GATE_REJECTED",
}
OUTCOME = {
    "SPINE-V20-HUMAN-APPROVED": "ACCEPT",
    "SPINE-V20-AUDIT-REJECTED": "FAIL_KNOWN_DEFECT_MISSED",
    "Q25-KITE01-CANDIDATES": "SOURCE_BOUND_CANDIDATES_ONLY",
    "Q25-GREENHOUSE01-REJECTED": "REJECTED_BY_OFFLINE_GATE",
}


@dataclass(frozen=True)
class StageInput:
    schema: Literal["lumi.story-harness-stage-input.v1"]
    case_id: str
    stage_type: str
    source_commit: str
    input_manifest_sha256: str
    archived_artifact_sha256_by_role: dict[str, str]
    independent_case_only: Literal[True]


@dataclass(frozen=True)
class GateReceipt:
    schema: Literal["lumi.story-harness-local-gate-receipt.v1"]
    gate_id: str
    verifier_source_sha256: str
    input_sha256: str
    artifact_set_sha256: str
    check_executed: Literal[True]
    locally_verified_scope: Literal["FROZEN_ARCHIVE_BYTES_AND_SCHEMA_ONLY"]
    local_integrity_result: Literal["PASS"]
    original_historical_gate_reexecuted: Literal[False]
    original_human_reviewer_authenticated: Literal[False]
    semantic_validity_certified: Literal[False]
    stage_execution_authorized: Literal[False]


@dataclass(frozen=True)
class StageResult:
    schema: Literal["lumi.story-harness-stage-result.v1"]
    case_id: str
    stage_type: str
    input_sha256: str
    gate_receipt_sha256: str
    original_historical_outcome: str
    stop_reason: str
    state: Literal["STOPPED_PENDING_UNVERIFIED_GATE"]
    downstream_execution_authorized: Literal[False]
    semantic_support_certified: Literal[False]
    canonical_state_commit_authorized: Literal[False]
    provider_calls_this_run: Literal[0]
    provider_cost_usd_this_run: Literal["0"]


def _fail(condition, message):
    if not condition:
        raise HarnessStop(message)


def _verifier_source_sha(repo_root: Path) -> str:
    """Bind a local checker implementation by bytes, never call it an identity signature."""
    src = repo_root / "src" / "story_harness_p1.py"
    if src.is_symlink() or not src.is_file() or src.stat().st_size > 1_048_576:
        raise HarnessStop("Unqualified local integrity verifier source")
    return digest(src.read_bytes())


def generate_receipts(*, manifest, repo_root: str | Path):
    """Recompute P1 local checks; NEVER accept receipts as authoritative inputs."""
    root = Path(repo_root).resolve(strict=True)
    # P1 authenticates archived *bytes against our committed pin*, not remote
    # source or a human reviewer. It deliberately raises on all tampering.
    report = inspect_historical(manifest, repo_root=root)
    _fail(report["case_count"] == 4, "P2 requires four pinned frozen historical cases")
    _fail(report["source_commit"] == PINNED_SOURCE_COMMIT,
          "P2 source revision must remain frozen")
    _fail(not report["historical_gate_authenticated_by_harness"] and
          not report["historical_verdicts_rewritten"] and
          not report["spine_and_q25_story_chain_claimed"] and
          report["real_gate_invocations"] == 0 and
          report["new_provider_calls"] == 0 and
          report["state_commit_authorized"] is False,
          "P1 report cannot be promoted into authority")

    source_file_sha = _verifier_source_sha(root)
    manifest_sha = digest(canonical_bytes(manifest))
    inputs, receipts, stages = [], [], []
    for case, checked in zip(manifest["cases"], report["historical_cases"]):
        ident = case["case_id"]
        _fail(ident == checked["case_id"] and
              case["adapter"] == checked["adapter"] == STAGE_TYPE[ident],
              "Stage/case identity does not bind checked evidence")
        original = checked["inspection"]["historical_original_outcome"]
        _fail(original == OUTCOME[ident], "Historical source outcome changed")
        hashes = {
            item["kind"]: item["sha256"]
            for item in case["files"]
        }
        _fail(len(hashes) == len(case["files"]), "Ambiguous artifact role")
        inp = StageInput(
            schema="lumi.story-harness-stage-input.v1",
            case_id=ident,
            stage_type=case["adapter"],
            source_commit=report["source_commit"],
            input_manifest_sha256=manifest_sha,
            archived_artifact_sha256_by_role=hashes,
            independent_case_only=True,
        )
        inp_data = asdict(inp)
        input_sha = digest(canonical_bytes(inp_data))
        receipt = GateReceipt(
            schema="lumi.story-harness-local-gate-receipt.v1",
            gate_id=GATE_VERSION,
            verifier_source_sha256=source_file_sha,
            input_sha256=input_sha,
            artifact_set_sha256=digest(canonical_bytes(hashes)),
            check_executed=True,
            locally_verified_scope="FROZEN_ARCHIVE_BYTES_AND_SCHEMA_ONLY",
            local_integrity_result="PASS",
            original_historical_gate_reexecuted=False,
            original_human_reviewer_authenticated=False,
            semantic_validity_certified=False,
            stage_execution_authorized=False,
        )
        receipt_data = asdict(receipt)
        outcome = StageResult(
            schema=STAGE_RESULT_SCHEMA,
            case_id=ident,
            stage_type=case["adapter"],
            input_sha256=input_sha,
            gate_receipt_sha256=digest(canonical_bytes(receipt_data)),
            original_historical_outcome=original,
            stop_reason=STOP_CLASS[ident],
            state="STOPPED_PENDING_UNVERIFIED_GATE",
            downstream_execution_authorized=False,
            semantic_support_certified=False,
            canonical_state_commit_authorized=False,
            provider_calls_this_run=0,
            provider_cost_usd_this_run="0",
        )
        inputs.append(inp_data)
        receipts.append(receipt_data)
        stages.append(asdict(outcome))

    return {
        "schema": REPORT_SCHEMA,
        "mode": "LOCAL_ARCHIVE_VERIFICATION_ONLY",
        "source_commit": report["source_commit"],
        "historical_import_sha256": manifest_sha,
        "verifier_gate": GATE_VERSION,
        "verifier_module_sha256": source_file_sha,
        "case_count": len(stages),
        "stage_inputs": inputs,
        "gate_receipts": receipts,
        "stage_results": stages,
        "independent_case_records_only": True,
        "actual_local_integrity_checks_executed": len(stages),
        "original_spine_or_q25_gates_reexecuted": False,
        "original_human_review_authenticated": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "downstream_stage_executions_authorized": 0,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "model_execution_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": "0",
    }


def verify_report(candidate: dict, *, manifest, repo_root: Path | str) -> bool:
    """A stored receipt is NOT trusted; recompute full archive checks first."""
    expected = generate_receipts(manifest=manifest, repo_root=repo_root)
    if candidate != expected:
        raise HarnessStop("Submitted StageResult or gate receipt fails independent local recomputation")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default="configs/story_harness_p1_frozen_import.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--verify-report", default=None)
    args = parser.parse_args()
    root = Path(args.repo_root).resolve(strict=True)
    manifest = load_json(secure_artifact(root, args.manifest))
    computed = generate_receipts(manifest=manifest, repo_root=root)
    if args.verify_report is not None:
        candidate = load_json(secure_artifact(root, args.verify_report))
        verify_report(candidate, manifest=manifest, repo_root=root)
    print(json.dumps(computed, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
