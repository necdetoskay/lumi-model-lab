"""Isolated Aion Mini Writer probe; no paid grant is bundled."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from decimal import Decimal
from pathlib import Path

from src.episode_writer_v2_generate import _validate_source, generate, WRITER_MODEL
from src.frozen_lane_verify import verify_frozen_lane
from src.v3_single_attempt_aion_writer_guard import SingleAttemptAionWriterGuard
from src.v3_single_attempt_guard import FROZEN_V3_SHA, SafetyStop

APPROVED = Path("data/specifications/story_lab/age18_cross_age_c11_approved.json")
PROFILE = Path("data/specifications/story_lab/age18_story_lane_profile_v2_frozen.json")
PROMPT = Path("prompts/episode_writer_v3_generic.md")
APPROVED_SHA = "75087c11a286f01ba8d2190083011fd3afed94b2e6faebd74d1eca8b4e4e10ad"
CASE_ID = "age18.a1.beacon-ridge.approved-control"
ALLOWED_FILES = {
    "src/v3_single_attempt_guard.py",
    "src/v3_single_attempt_aion_writer_guard.py",
    "experiments/v3_single_attempt_spine_probe.py",
    "experiments/v3_aion_writer_single_attempt_probe.py",
    "tests/test_v3_single_attempt_guard.py",
    "tests/test_v3_single_attempt_aion_writer_guard.py",
    "docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_GUARD_V1.md",
    "docs/qualifications/V3_SINGLE_ATTEMPT_SPINE_LIVE_WORKFLOW_TEMPLATE.yml",
    "docs/qualifications/V3_AION_MINI_WRITER_SINGLE_ATTEMPT.md",
}


def run(*, grant_file: Path, evidence_dir: Path, claim_dir: Path):
    grant = json.loads(grant_file.read_text(encoding="utf-8"))
    required = {
        "schema": "lumi.v3-aion-mini-writer-paid-grant.v1",
        "authorized": True,
        "stage": "WRITER",
        "case_id": CASE_ID,
        "model": WRITER_MODEL,
        "frozen_runtime_sha": FROZEN_V3_SHA,
        "approved_spine_sha256": APPROVED_SHA,
    }
    if any(grant.get(k) != val for k, val in required.items()):
        raise SafetyStop("WRITER_GRANT_SCOPE_MISMATCH")
    ref = grant.get("human_paid_authorization_reference")
    if not isinstance(ref, str) or not ref.strip():
        raise SafetyStop("WRITER_SPECIFIC_PAID_AUTHORIZATION_REQUIRED")
    uid = grant.get("grant_id")
    if not isinstance(uid, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}", uid):
        raise SafetyStop("WRITER_UNIQUE_GRANT_ID_REQUIRED")
    try:
        ceiling = Decimal(str(grant["max_total_usd"]))
    except (KeyError, ValueError, TypeError) as exc:
        raise SafetyStop("WRITER_COST_CEILING_INVALID") from exc
    if not ceiling.is_finite() or not Decimal("0") < ceiling <= Decimal("0.50"):
        raise SafetyStop("WRITER_COST_CEILING_INVALID")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if grant.get("guard_commit_sha") != head:
        raise SafetyStop("WRITER_GUARD_COMMIT_NOT_APPROVED")
    if subprocess.run(["git", "merge-base", "--is-ancestor", FROZEN_V3_SHA, head]).returncode:
        raise SafetyStop("FROZEN_V3_NOT_ANCESTOR")
    changes = set(subprocess.check_output(
        ["git", "diff", "--name-only", FROZEN_V3_SHA, head], text=True
    ).splitlines())
    if not changes or not changes.issubset(ALLOWED_FILES):
        raise SafetyStop("NON_GUARD_SOURCE_CHANGE_DETECTED")
    if subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=normal"], text=True
    ).strip():
        raise SafetyStop("DIRTY_CHECKOUT_BLOCKED")
    verify_frozen_lane(PROFILE)
    if hashlib.sha256(APPROVED.read_bytes()).hexdigest() != APPROVED_SHA:
        raise SafetyStop("APPROVED_SPINE_CHANGED")
    _validate_source(json.loads(APPROVED.read_text(encoding="utf-8")))
    if WRITER_MODEL != json.loads(PROFILE.read_text())["runtime"]["writer"]["model"]:
        raise SafetyStop("WRITER_MODEL_MISMATCH")
    if not (claim_dir.is_absolute() and evidence_dir.is_absolute()):
        raise SafetyStop("ABSOLUTE_EVIDENCE_AND_CLAIM_DIR_REQUIRED")
    if evidence_dir.exists():
        raise SafetyStop("EVIDENCE_DIR_ALREADY_EXISTS")
    if not os.getenv("OPENROUTER_API_KEY"):
        raise SafetyStop("GITHUB_ACTIONS_OPENROUTER_SECRET_NOT_AVAILABLE")

    # Exclusively claim before any possible billable POST.
    claim_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    claim_hash = hashlib.sha256(("writer:" + uid).encode()).hexdigest()
    try:
        fd = os.open(claim_dir / (claim_hash + ".json"),
                     os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SafetyStop("WRITER_GRANT_ALREADY_CONSUMED") from exc
    with os.fdopen(fd, "wb") as stream:
        stream.write((json.dumps({"stage": "WRITER", "commit": head,
                                  "claim_hash": claim_hash}) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())
    evidence_dir.mkdir(parents=True, mode=0o700)

    guard = SingleAttemptAionWriterGuard(evidence_dir, ceiling)
    guard.event("WRITER_GRANT_VERIFIED", case_id=CASE_ID, model=WRITER_MODEL)
    try:
        with guard.installed_writer():
            result = generate(
                approved_path=APPROVED, prompt_path=PROMPT,
                out_path=evidence_dir / "writer-result.json",
                story_out_path=evidence_dir / "story-en.txt",
                api_key=os.environ["OPENROUTER_API_KEY"],
                authority_packet_version="v2",
            )
        guard.event("STAGE_FINISHED", status=result["status"],
                    post_count=guard.calls, observed_usd=str(guard.spent),
                    next_stage_authorized=False)
        if result["status"] != "writer_generated":
            raise SafetyStop("WRITER_DETERMINISTIC_CHECK_FAILED")
        return result
    except BaseException as exc:
        guard.event("STAGE_STOP", reason_type=type(exc).__name__,
                    post_count=guard.calls, observed_usd=str(guard.spent))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--grant", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, required=True)
    p.add_argument("--claim-dir", type=Path, required=True)
    a = p.parse_args()
    r = run(grant_file=a.grant, evidence_dir=a.evidence_dir,
            claim_dir=a.claim_dir)
    print(json.dumps({"model": WRITER_MODEL, "status": r["status"],
                      "next_stage_authorized": False}))
