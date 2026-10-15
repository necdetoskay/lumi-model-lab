"""Manually authorized, fail-closed, frozen Final V3 Spine probe.

Do not invoke without a fresh, explicit, case-scoped human paid grant. This
wrapper leaves all V3 frozen source/prompt files unchanged. A successful
architect and gate are two distinct charged POSTs; Writer is never started.
"""
import argparse
import hashlib
import json
import os
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.frozen_lane_stage import run as frozen_stage_run
from src.frozen_lane_verify import verify_frozen_lane
from src.story_lane_case_manifest import load_case_manifest
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SPINE_MODELS, SafetyStop, SingleAttemptSpineGuard

PROFILE = Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
CASE = Path("data/specifications/story_lab/age18_forbidden_cartographer_frozen_case_v1.json")


def run(*, grant_file: Path, evidence_dir: Path):
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
    if subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() != FROZEN_V3_SHA:
        # On a new non-frozen wrapper branch, the original parent must equal
        # exactly the authoritative V3 source, with no change to frozen files.
        parent = subprocess.check_output(["git", "rev-parse", "HEAD^"], text=True).strip()
        if parent != FROZEN_V3_SHA:
            raise SafetyStop("V3_RUNTIME_BASE_CHANGED")
    verified = verify_frozen_lane(PROFILE)
    case = load_case_manifest(CASE)
    if case["case_id"] != required["case_id"]:
        raise SafetyStop("CASE_CHANGED")
    if os.environ.get("OPENROUTER_API_KEY") is None:
        raise SafetyStop("API_KEY_MISSING")
    if evidence_dir.exists():
        raise SafetyStop("EVIDENCE_DIR_ALREADY_EXISTS_NO_REUSE")
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
        guard.event("STAGE_FINISHED", result_status=result.get("result_status"),
                    post_count=guard.calls, accounted_cost_usd=str(guard.spent),
                    human_approval_still_required=True)
        return result
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
    a = p.parse_args()
    result = run(grant_file=a.grant, evidence_dir=a.evidence_dir)
    print(json.dumps({"stage": result.get("stage"), "status": result.get("result_status"),
                      "human_approval_required": True}, sort_keys=True))


if __name__ == "__main__":
    main()
