"""Offline-only frozen cohort runner; NO provider invocation, NO fixes.
After the first attempt, B01..B10 must run using exactly the same SHA and
input hashes. Per-case failure never authorizes edits or retries.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

from src.story_harness_frozen_cohort_v1 import (
    IDS, COMPONENTS, preflight, verify_attempt_seal, round_coverage, must
)
from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-frozen-round-offline.v1"
FILES = (
    "configs/story_harness_p415_benchmark.json",
    "configs/story_harness_frozen_cohort_v1.json",
    "configs/story_harness_runtime_v1.json",
    "src/story_harness_p415_benchmark.py",
    "src/story_harness_p416_input_bridge.py",
    "src/story_harness_p417_live_pilot.py",
    "src/story_harness_p422_independent_audit.py",
    "src/story_harness_p423_master.py",
    "src/story_harness_p424_q25_evidence.py",
    "src/story_harness_p425_final_state_draft.py",
    "src/story_harness_cohort_source_v1.py",
    "src/story_harness_cohort_stages_v1.py",
    "src/story_harness_cohort_pipeline_v1.py",
    "src/story_harness_cohort_analysis_v1.py",
    "src/story_harness_frozen_cohort_v1.py",
    "src/story_harness_frozen_round_v1.py",
    "src/story_harness_readiness_v1.py",
    "src/story_harness_runtime_v1.py",
    "src/story_harness_cohort_launch_gate_v1.py",
    "src/story_harness_cohort_provider_observe_v1.py",
    "src/story_harness_cohort_accounting_v1.py",
    "src/story_harness_cohort_generation_receipt_v1.py",
)
# Hash actual immutable bytes for each logical Harness component.
# Unlike SHA(label + commit), this detects any source/config modification.
COMPONENT_FILES = {
    "input_contract": (
        "configs/story_harness_p415_benchmark.json",
        "src/story_harness_p416_input_bridge.py",
    ),
    "spineforge": (
        "src/story_harness_p416_input_bridge.py",
        "src/story_harness_p417_live_pilot.py",
    ),
    "writer": (
        "src/story_harness_p416_input_bridge.py",
        "src/story_harness_p417_live_pilot.py",
    ),
    "independent_quality": (
        "src/story_harness_p422_independent_audit.py",
        "src/story_harness_cohort_stages_v1.py",
    ),
    "english_master": (
        "src/story_harness_p423_master.py",
        "src/story_harness_cohort_stages_v1.py",
    ),
    "real_q25": (
        "src/story_harness_p424_q25_evidence.py",
        "src/story_harness_cohort_stages_v1.py",
    ),
    "final_read_only_state": (
        "src/story_harness_p425_final_state_draft.py",
        "src/story_harness_cohort_stages_v1.py",
    ),
    "prompt_bundle": (
        "src/story_harness_p416_input_bridge.py",
        "src/story_harness_p417_live_pilot.py",
        "src/story_harness_p422_independent_audit.py",
        "src/story_harness_p424_q25_evidence.py",
    ),
    "model_runtime_profile": (
        "configs/story_harness_runtime_v1.json",
        "src/story_harness_runtime_v1.py",
    ),
    "quality_policy": (
        "configs/story_harness_runtime_v1.json",
        "src/story_harness_p422_independent_audit.py",
        "src/story_harness_cohort_analysis_v1.py",
    ),
    "cost_and_retry_policy": (
        "configs/story_harness_frozen_cohort_v1.json",
        "src/story_harness_frozen_cohort_v1.py",
        "src/story_harness_frozen_round_v1.py",
        "src/story_harness_cohort_pipeline_v1.py",
        "src/story_harness_cohort_generation_receipt_v1.py",
    ),
}

def _actual_component_sha256(source_hashes):
    must(set(COMPONENT_FILES) == COMPONENTS,
         "MISSING_OR_UNREGISTERED_HARNESS_COMPONENT")
    values = {}
    for component, paths in COMPONENT_FILES.items():
        must(all(name in source_hashes for name in paths),
             "COMPONENT_HAS_UNPINNED_SOURCE")
        evidence = {
            "component": component,
            "source_file_sha256": {
                name: source_hashes[name] for name in sorted(paths)
            }
        }
        values[component] = hashlib.sha256(canonical_json(evidence)).hexdigest()
    return values

STATUSES = {"REJECT", "ACCEPT_CLAIMED", "STOP_UNKNOWN_OR_INVALID",
            "OPERATIONAL_STOP"}

class GlobalSafetyStop(Exception):
    """Unknown aggregate exposure / unavailable authorization / safety stop."""

def _head(repo):
    result = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=repo,
                            text=True, capture_output=True, timeout=5)
    must(result.returncode == 0 and len(result.stdout.strip()) == 40,
         "GIT_HEAD_UNAVAILABLE")
    return result.stdout.strip()

def _hashes(repo):
    root = Path(repo)
    values = {}
    for name in FILES:
        p = root / name
        must(p.is_file() and not p.is_symlink() and
             0 < p.stat().st_size < 200000, "PINNED_FILE_MISSING")
        values[name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return values

def simulate_seal(repo):
    """Simulation lock is not a billable grant and cannot be promoted to one."""
    p = preflight(repo)
    head = _head(repo)
    return {
        "status": "SEALED", "schema": SCHEMA, "round": "BASELINE",
        "harness_commit": head, "input_sha256": p["case_input_sha256"],
        "policy_sha256": p["policy_sha256"],
        "component_sha256": _actual_component_sha256(_hashes(repo)),
        "files_sha256": _hashes(repo),
        "case_ids": list(IDS), "offline_only": True, "provider_grant": False,
    }

def check_lock(repo, lock):
    p = preflight(repo)
    must(type(lock) is dict and lock.get("schema") == SCHEMA and
         lock.get("status") == "SEALED" and lock.get("round") == "BASELINE" and
         lock.get("case_ids") == list(IDS) and lock.get("offline_only") is True
         and lock.get("provider_grant") is False, "UNSAFE_SEAL")
    must(lock.get("input_sha256") == p["case_input_sha256"] and
         lock.get("policy_sha256") == p["policy_sha256"] and
         type(lock.get("files_sha256")) is dict and
         set(lock["files_sha256"]) == set(FILES), "CHANGED_COHORT_INPUT")
    current = _hashes(repo)
    must(lock.get("harness_commit") == _head(repo) and
         lock["files_sha256"] == current, "MID_COHORT_CODE_CHANGE")
    must(lock.get("component_sha256") == _actual_component_sha256(current),
         "MID_COHORT_COMPONENT_CHANGE")
    return p

def _exclusive(path, data):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(canonical_json(data) + b"\n")
        output.flush()
        os.fsync(output.fileno())

def _read(path):
    p = Path(path)
    must(p.is_file() and not p.is_symlink() and
         0 < p.stat().st_size < 200000, "BAD_RECEIPT")
    return json.loads(p.read_bytes())

def _row(value, case):
    must(type(value) is dict and set(value) == {
        "case_id", "status", "safe_reason", "model_calls",
        "manual_prose_edits"}, "INVALID_ROW_SHAPE")
    must(value["case_id"] == case and value["status"] in STATUSES and
         type(value["model_calls"]) is int and value["model_calls"] == 0 and
         type(value["manual_prose_edits"]) is int and
         value["manual_prose_edits"] == 0 and
         value["safe_reason"] in ("SIMULATED_REJECT", "SIMULATED_ACCEPT",
                                  "NO_RETRY_EXCEPTION", "INTERRUPTED_ATTEMPT",
                                  "GLOBAL_SAFETY_STOP"), "INVALID_ROW")
    return value

def run_frozen_ten_offline(repo, work, callback, *, seal=None):
    """Record each attempt only once. A tiny failure does NOT alter the next."""
    must(callable(callback), "MISSING_CALLBACK")
    repo, work = Path(repo), Path(work)
    must(work.is_dir() and not work.is_symlink() and
         not work.resolve().is_relative_to(repo.resolve()),
         "UNSAFE_LEDGER_ROOT")
    seal = seal if seal is not None else simulate_seal(repo)
    check_lock(repo, seal)
    lock_path = work / "00-seal.json"
    if not lock_path.exists():
        _exclusive(lock_path, seal)
    must(_read(lock_path) == seal, "CHANGED_SEAL")
    results = []
    for case in IDS:
        check_lock(repo, seal)
        folder = work / case
        if not folder.exists():
            folder.mkdir(mode=0o700)
        must(folder.is_dir() and not folder.is_symlink(), "UNSAFE_CASE_DIRECTORY")
        intent, output = folder / "00-intent.json", folder / "01-outcome.json"
        attempt = {"case_id": case, "round": "BASELINE",
                   "harness_commit": seal["harness_commit"],
                   "component_sha256": seal["component_sha256"],
                   "input_sha256": seal["input_sha256"][case],
                   "manual_prose_edits": 0, "automatic_quality_retry": False}
        verify_attempt_seal(seal, attempt, seal["input_sha256"])
        if output.exists():
            must(intent.exists() and _read(intent) == attempt, "TAMPERED_INTENT")
            result = _row(_read(output), case)
        elif intent.exists():
            must(_read(intent) == attempt, "TAMPERED_INTENT")
            # Crash after intent may have incurred a charge; NEVER retry.
            result = dict(case_id=case, status="OPERATIONAL_STOP",
                          safe_reason="INTERRUPTED_ATTEMPT", model_calls=0,
                          manual_prose_edits=0)
            _exclusive(output, result)
        else:
            _exclusive(intent, attempt)
            try:
                result = _row(callback(case, deepcopy(attempt)), case)
            except (GlobalSafetyStop, HarnessStop):
                # Escaped integrity errors and ambiguous provider charges
                # are GLOBAL safety stops, never "minor story formatting".
                # Lower-level per-story validation errors are already
                # classified as OPERATIONAL_STOP within the stage adapter.
                result = dict(case_id=case, status="STOP_UNKNOWN_OR_INVALID",
                              safe_reason="GLOBAL_SAFETY_STOP", model_calls=0,
                              manual_prose_edits=0)
            except Exception:
                result = dict(case_id=case, status="OPERATIONAL_STOP",
                              safe_reason="NO_RETRY_EXCEPTION", model_calls=0,
                              manual_prose_edits=0)
            _exclusive(output, result)
        results.append(result)
        # Do not forge remaining results if budget/integrity can no longer be trusted.
        if result["safe_reason"] == "GLOBAL_SAFETY_STOP":
            break
        check_lock(repo, seal)
    rows = [dict(case_id=x["case_id"], round="BASELINE", status=x["status"])
            for x in results]
    complete = round_coverage(rows, "BASELINE")["all_attempts_recorded"]
    if complete:
        receipt = {"schema": SCHEMA, "complete": True, "attempts": 10,
                   "fixes": 0, "retries": 0, "paid_calls": 0,
                   "quality_certified": False}
        final = work / "11-completion.json"
        if not final.exists():
            _exclusive(final, receipt)
        must(_read(final) == receipt, "CHANGED_COMPLETION")
    return {
        "schema": SCHEMA, "offline_only": True, "complete": complete,
        "attempts": results, "attempt_count": len(results),
        "fix_count": 0, "retry_count": 0, "provider_calls": 0,
        "analysis_allowed": complete, "independent_accepts_certified": False,
    }
