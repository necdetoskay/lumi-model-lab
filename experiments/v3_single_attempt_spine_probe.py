"""Manually authorized, fail-closed, frozen Final V3 Spine probe.

Do not invoke without a fresh, explicit, case-scoped human paid grant. This
wrapper leaves all V3 frozen source/prompt files unchanged. A successful
architect and gate are two distinct charged POSTs; Writer is never started.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.frozen_lane_stage import run as frozen_stage_run
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SPINE_MODELS, SafetyStop, SingleAttemptSpineGuard

PROFILE = Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
CASE = Path("data/specifications/story_lab/age18_forbidden_cartographer_frozen_case_v1.json")


def enforce_spine_gate(*, envelope: dict, evidence_dir: Path,
                       post_count: int, event):
    """Interpret a real frozen Spine result without changing V3 semantics."""
    if not isinstance(envelope, dict) or envelope.get("stage") != "SPINE":
        raise SafetyStop("SPINE_STAGE_ENVELOPE_INVALID")
    if envelope.get("result_status") != "awaiting_human_review":
        raise SafetyStop("SPINE_STAGE_NOT_READY_FOR_REVIEW")
    expected = (evidence_dir / "stage-output" / "result.json").resolve()
    given = Path(str(envelope.get("result_path") or "")).resolve()
    if given != expected or not expected.is_file():
        raise SafetyStop("SPINE_STAGE_EVIDENCE_PATH_INVALID")
    if post_count != 2:
        raise SafetyStop("SPINE_TWO_MODEL_POSTS_NOT_OBSERVED")
    payload = json.loads(expected.read_text(encoding="utf-8"))
    if payload.get("status") != "awaiting_human_review":
        raise SafetyStop("SPINE_RESULT_STATUS_INVALID")
    gate = payload.get("gate") or {}
    decision = gate.get("decision")
    event("GATE_VERDICT_OBSERVED", decision=decision,
          architect_post_count=1, gate_post_count=1)
    if decision == "REPLAN":
        raise SafetyStop("SPINE_GATE_REPLAN_STOP")
    if decision != "ACCEPT":
        raise SafetyStop("SPINE_GATE_DECISION_INVALID")
    review = payload.get("human_review") or {}
    if payload.get("episode_writer_authorized") is not False:
        raise SafetyStop("SPINE_WRITER_AUTHORITY_LEAK")
    if review.get("verdict") is not None or review.get("episode_writer_authorized") is not False:
        raise SafetyStop("SPINE_HUMAN_APPROVAL_NOT_PENDING")
    return "ACCEPT_AWAITING_HUMAN_APPROVAL"


def run(*, grant_file: Path, evidence_dir: Path, claim_dir: Path | None = None):
    # An unapproved call is refused without touching provider or output state.
    grant = json.loads(grant_file.read_text(encoding="utf-8"))
    required = {
        "schema": "lumi.v3-single-attempt-paid-grant.v1",
        "authorized": True,
        "stage": "SPINE",
        "case_id": "age18.forbidden-cartographer.fantasy.frozen-01",
        "frozen_runtime_sha": FROZEN_V3_SHA,
        "models": list(SPINE_MODELS),
    }
    if any(grant.get(k) != v for k, v in required.items()):
        raise SafetyStop("PAID_GRANT_SCOPE_MISMATCH")
    if not isinstance(grant.get("human_approval_reference"), str) or not grant["human_approval_reference"].strip():
        raise SafetyStop("EXPLICIT_HUMAN_APPROVAL_REFERENCE_MISSING")
    try:
        ceiling = Decimal(str(grant["max_total_usd"]))
    except (InvalidOperation, KeyError, TypeError):
        raise SafetyStop("GRANT_COST_CEILING_MISSING_OR_INVALID")
    if not ceiling.is_finite() or ceiling <= 0 or ceiling > Decimal("0.50"):
        raise SafetyStop("GRANT_CEILING_OUTSIDE_PROBE_LIMIT")
    # Compare an exact, user-approved wrapper HEAD, not HEAD^ (which breaks
    # when a safe follow-up commit is added to the isolated test branch).
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if grant.get("guard_commit_sha") != head:
        raise SafetyStop("GUARD_COMMIT_NOT_EXACTLY_APPROVED")
    if subprocess.run(["git", "merge-base", "--is-ancestor", FROZEN_V3_SHA, head],
                      check=False).returncode != 0:
        raise SafetyStop("FROZEN_V3_NOT_ANCESTOR")
    # No runtime edits even outside the 43 SHA-locked files. The only allowed
    # additions are the small qualification guard itself and its evidence.
    changes = set(subprocess.check_output(
        ["git", "diff", "--name-only", FROZEN_V3_SHA, head],
        text=True).splitlines())
    permitted = {
        "src/v3_single_attempt_guard.py",
        "experiments/v3_single_attempt_spine_probe.py",
        "tests/test_v3_single_attempt_guard.py",
        "docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_GUARD_V1.md",
    }
    if not changes or not changes.issubset(permitted):
        raise SafetyStop("NON_GUARD_SOURCE_CHANGE_DETECTED")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"],
        text=True).strip():
        raise SafetyStop("DIRTY_CHECKOUT_BLOCKED")
    if claim_dir is None:
        raise SafetyStop("PERSISTENT_CLAIM_DIRECTORY_REQUIRED")
    if not claim_dir.is_absolute():
        raise SafetyStop("CLAIM_DIRECTORY_MUST_BE_ABSOLUTE")
    claim_identifier = grant.get("grant_id")
    if not isinstance(claim_identifier, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}", claim_identifier):
        raise SafetyStop("UNIQUE_GRANT_ID_REQUIRED")
    verified = verify_frozen_lane(PROFILE)
    case = load_case_manifest(CASE)
    if case["case_id"] != required["case_id"]:
        raise SafetyStop("CASE_CHANGED")
    if os.environ.get("OPENROUTER_API_KEY") is None:
        raise SafetyStop("API_KEY_MISSING")
    if evidence_dir.exists():
        raise SafetyStop("EVIDENCE_DIR_ALREADY_EXISTS_NO_REUSE")
    if not evidence_dir.is_absolute():
        raise SafetyStop("EVIDENCE_DIRECTORY_MUST_BE_ABSOLUTE")
    # Each grant is consumed atomically across all trial output locations.
    # A crash, timeout, invalid response or failed evidence write also consumes
    # it: fail-closed, with no implicit request replay after an uncertain charge.
    claim_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    grant_digest = hashlib.sha256(claim_identifier.encode("utf-8")).hexdigest()
    claim_path = claim_dir / (grant_digest + ".json")
    claim_data = json.dumps({
        "schema": "v3-single-attempt-claim.v1",
        "grant_sha256": grant_digest,
        "source_sha": head,
        "case_id": case["case_id"],
    }, sort_keys=True).encode("utf-8") + b"\n"
    try:
        fd = os.open(claim_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SafetyStop("PAID_GRANT_ALREADY_CLAIMED") from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write(claim_data)
        stream.flush()
        os.fsync(stream.fileno())
    evidence_dir.mkdir(parents=True, mode=0o700)
    guard = SingleAttemptSpineGuard(evidence_dir, ceiling)
    trigger = evidence_dir / "stage-trigger.json"
    # A local data-only trigger, not a change to the frozen stage runner.
    trigger.write_text(json.dumps({
        "schema_version": "frozen-lane-stage-trigger.v1",
        "stage": "SPINE", "paid_authorized": True,
        "case_manifest": str(CASE)
    }, indent=2) + "\n")
    guard.event("GRANT_VERIFIED", case_id=case["case_id"], max_cost_usd=str(ceiling),
                frozen_files=verified["verified_files"],
                approval_reference_sha256=hashlib.sha256(grant["human_approval_reference"].encode()).hexdigest())
    try:
        with guard.installed():
            result = frozen_stage_run(trigger_path=trigger,
                                      out_dir=evidence_dir / "stage-output")
        gate_status = enforce_spine_gate(
            envelope=result, evidence_dir=evidence_dir,
            post_count=guard.calls, event=guard.event,
        )
        guard.event("STAGE_FINISHED", result_status=gate_status,
                    post_count=guard.calls, accounted_cost_usd=str(guard.spent),
                    human_approval_still_required=True,
                    writer_authorized=False)
        return {**result, "qualification_verdict": gate_status,
                "writer_authorized": False}
    except BaseException as exc:
        try:
            trace = getattr(exc, "trace", None)
            code = trace.get("status_code") if isinstance(trace, dict) else None
            guard.event("STAGE_STOP", reason_type=type(exc).__name__,
                        http_status=code if isinstance(code, int) else None,
                        post_count=guard.calls,
                        accounted_cost_usd=str(guard.spent))
        except Exception:
            pass
        raise


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grant", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--claim-dir", type=Path, required=True)
    a = p.parse_args()
    result = run(grant_file=a.grant, evidence_dir=a.evidence_dir, claim_dir=a.claim_dir)
    print(json.dumps({"stage": result.get("stage"), "status": result.get("result_status"),
                      "human_approval_required": True}, sort_keys=True))


if __name__ == "__main__":
    main()
