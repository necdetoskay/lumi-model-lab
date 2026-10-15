"""P2.1: execute version-pinned REAL Q25 offline validator on original raw bytes.

Only the historical KITE/GREENHOUSE source/structural gate is actually replayed.
GREENHOUSE's old paid REJECT verdict remains immutable, even if later gate
code passes an unmodified raw response after ordered-citation normalization.
No new model call, no original paid gate replay, no semantic or state authority.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig
import tempfile

from src.story_harness_p1 import FROZEN_CASES, PINNED_SOURCE_COMMIT
from src.story_harness_p2 import generate_receipts
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA = "lumi.story-harness-p21-real-q25-offline-replay.v1"
GATE = "q25.offline-extractor-replay.v1"
SOURCE = {
    "Q25-KITE01-CANDIDATES": (
        "evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json",
        "5d8117a47126c9d47ce2e7e1979390c94e8fa9f19272db3523f88397ef907c7d",
        "SOURCE_BOUND_CANDIDATES_ONLY",
    ),
    "Q25-GREENHOUSE01-REJECTED": (
        "evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/request.json",
        "e9005da4042c9b550ec0d22be7b9200f427e4fc8deeb14d60d67c4caa680f2b0",
        "REJECTED_BY_OFFLINE_GATE",
    ),
}
VALIDATOR_PATH = "src/q25_extractor_adapter.py"
VALIDATOR_SHA = "a562d4c96f3c99ee7014f1de5df24765edbb4d223b029ff6a57cdddaf8bce992"
MAX_PROVIDER_CALLS = 0

def _must(condition, reason):
    if not condition:
        raise HarnessStop(reason)

def _git(args, root):
    try:
        p = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True,
            text=True, timeout=12, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise HarnessStop("Cannot verify the pinned offline validator checkout") from exc
    if p.returncode != 0:
        raise HarnessStop("Pinned validator Git checkout verification failed")
    return p.stdout.strip()

def _verify_checkout(root):
    _must(root.is_dir(), "Pinned Q25 checkout absent")
    _must(_git(["rev-parse", "HEAD"], root) == PINNED_SOURCE_COMMIT,
          "Q25 validator checkout is not the original pinned commit")
    _must(Path(_git(["rev-parse", "--show-toplevel"], root)).resolve() == root,
          "Validator root does not match selected Git checkout")
    _must(not _git(["status", "--porcelain", "--untracked-files=no"], root),
          "Pinned offline validator code has tracked modifications")
    source = root / VALIDATOR_PATH
    _must(source.is_file() and not source.is_symlink() and
          digest(source.read_bytes()) == VALIDATOR_SHA,
          "Exact pinned Q25 validator implementation hash mismatch")

def _run_q25_validator(*, case_id, request, raw_bytes, validator_root, python_executable):
    """Use fixed arguments only, no shell/provider environment/auto-retry."""
    _must(set(request) == {"schema_name", "request_id", "model_inputs_only",
                           "labels_included", "seed", "prose_record", "policy"},
          "Q25 source request contains unexpected keys")
    _must(request["labels_included"] is False and
          request["model_inputs_only"] is True and
          set(request["prose_record"]) == {"text"}, "Request contains untrusted answer labels")
    with tempfile.TemporaryDirectory(prefix="story-harness-p21-") as temp:
        tmp = Path(temp)
        for name, payload in (
            ("seed", request["seed"]),
            ("prose-record", request["prose_record"]),
            ("policy", request["policy"]),
        ):
            (tmp / (name + ".json")).write_bytes(canonical_bytes(payload))
        (tmp / "raw.json").write_bytes(raw_bytes)
        # Remove provider credentials and Python user startup; the pinned module
        # executes locally with fixed argv and a total subprocess time bound.
        # setup-python's toolcache interpreter on self-hosted Linux may need
        # its bundled libpython.so at runtime. Pass only its *resolved Python
        # installation library directory*, never inherit the runner's
        # arbitrary LD_LIBRARY_PATH or any model-provider credentials.
        # actions/setup-python may *relocate* its toolcache interpreter.
        # sysconfig's compiled LIBDIR can point to the original machine,
        # so derive the runtime libdir from the actual executing binary first.
        runtime_prefix = Path(python_executable).resolve(strict=True).parent.parent
        candidates = [
            runtime_prefix / "lib",
            Path(sys.prefix) / "lib",
        ]
        compiled_libdir = sysconfig.get_config_var("LIBDIR")
        if isinstance(compiled_libdir, str) and Path(compiled_libdir).is_absolute():
            candidates.append(Path(compiled_libdir))
        python_lib = next((
            loc.resolve() for loc in candidates
            if loc.is_dir() and any(
                loc.glob(f"libpython{sys.version_info.major}.{sys.version_info.minor}.so*")
            )
        ), None)
        _must(python_lib is not None,
              "Python runtime shared library directory is unavailable")
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"),
               "LD_LIBRARY_PATH": str(python_lib),
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
               "HOME": str(tmp)}
        argv = [
            python_executable, "-m", "src.q25_extractor_adapter",
            "--seed", str(tmp / "seed.json"),
            "--prose-record", str(tmp / "prose-record.json"),
            "--raw-response", str(tmp / "raw.json"),
            "--policy", str(tmp / "policy.json"),
        ]
        try:
            response = subprocess.run(
                argv, cwd=validator_root, env=env, capture_output=True,
                text=True, encoding="utf-8", timeout=18, check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            raise HarnessStop("Pinned Q25 validator transport/timeout failure") from exc
        _must(response.returncode == 0,
              "Pinned Q25 validator rejected offline claims: " +
              response.stderr[-400:].replace("\n", " "))
        _must(len(response.stdout) <= 500_000, "Validator output exceeded bounded size")
        try:
            result = json.loads(response.stdout)
        except (ValueError, TypeError) as exc:
            raise HarnessStop("Pinned Q25 validator did not return JSON") from exc
    _must(result.get("schema") == GATE and
          result.get("status") == "SOURCE_BOUND_CANDIDATES_ONLY" and
          result.get("state_commit_authorized") is False and
          result.get("semantic_support_certified") is False and
          result.get("full_story_state_qualified") is False and
          result.get("provider_calls") == 0,
          "Pinned validator tried to claim semantic/canonical authority")
    cov = result["coverage"]
    _must(isinstance(cov.get("blocking_field_count"), int)
          and cov["blocking_field_count"] > 0,
          "Q25 offline gate has no bounded terminal coverage")
    return result

def rerun_q25(*, manifest, repo_root, pinned_q25_root,
              python_executable=sys.executable):
    """Executed version-pinned Q25 gate, preserving paid ledger original verdict."""
    base = Path(repo_root).resolve(strict=True)
    source_root = Path(pinned_q25_root).resolve(strict=True)
    original = copy.deepcopy(manifest)
    _verify_checkout(source_root)
    parent = generate_receipts(manifest=manifest, repo_root=base)
    _must(parent["case_count"] == 4 and parent["provider_calls"] == 0 and
          parent["downstream_stage_executions_authorized"] == 0,
          "Cannot use P2 archive result as semantic authorization")
    by_id = {s["case_id"]: s for s in parent["stage_results"]}
    observations = []
    for case_id, (req_path, req_sha, historical) in SOURCE.items():
        base_result = by_id[case_id]
        _must(base_result["original_historical_outcome"] == historical and
              not base_result["downstream_execution_authorized"],
              "Original Q25 outcome cannot be rewritten")
        original_request = secure_artifact(source_root, req_path)
        _must(digest(original_request) == req_sha,
              "Original source request changed since pinned Q25 commit")
        request = load_json(original_request)
        case = next(x for x in manifest["cases"] if x["case_id"] == case_id)
        raw_item = next(x for x in case["files"] if x["kind"] == "raw")
        raw_bytes = secure_artifact(base, raw_item["archive"])
        _must(digest(raw_bytes) == raw_item["sha256"] and
              digest(secure_artifact(source_root, raw_item["source_path"])) ==
              raw_item["sha256"],
              "Replayed raw text diverged from the original pinned Q25 model output")
        replay = _run_q25_validator(
            case_id=case_id, request=request, raw_bytes=raw_bytes,
            validator_root=source_root, python_executable=python_executable,
        )
        adjustments = replay["evidence_order_adjustments"]
        counts = replay["coverage"]["counts"]
        observations.append({
            "case_id": case_id,
            "original_paid_outcome_immutable": historical,
            "replayed_gate": "EXACT_PINNED_Q25_OFFLINE_VALIDATOR_EXECUTED",
            "validator_git_commit": PINNED_SOURCE_COMMIT,
            "validator_entrypoint_sha256": VALIDATOR_SHA,
            "request_sha256": req_sha,
            "original_raw_sha256": raw_item["sha256"],
            "execution_actual": True,
            "replay_status": replay["status"],
            "replay_status_not_historical_outcome": True,
            "current_offline_source_order_adjustments": adjustments,
            "terminal_field_coverage_count": replay["coverage"]["blocking_field_count"],
            "terminal_field_status_counts": counts,
            "semantic_validity_certified": False,
            "complete_story_state_certified": False,
            "downstream_execution_authorized": False,
            "canonical_state_commit_authorized": False,
            "provider_calls_this_run": 0,
        })
    _must(manifest == original, "Pinned input manifest was mutated")
    _must([o["case_id"] for o in observations] == list(SOURCE),
          "Replay cohort case selection changed")
    return {
        "schema": SCHEMA,
        "p2_receipts_sha256": digest(canonical_bytes(parent)),
        "source_commit": PINNED_SOURCE_COMMIT,
        "source_validator_sha256": VALIDATOR_SHA,
        "cases": observations,
        "actual_q25_offline_gate_invocations": 2,
        "spineforge_gate_invocations": 0,
        "original_human_review_authenticated": False,
        "original_paid_gate_results_modified": False,
        "semantic_support_certified": False,
        "terminal_state_complete": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": "0",
    }

def verify_pinned_report(candidate, *, manifest, repo_root,
                         pinned_q25_root, python_executable=sys.executable):
    """Do not trust a saved offline-stage receipt without executing the real gate."""
    rebuilt = rerun_q25(
        manifest=manifest, repo_root=repo_root,
        pinned_q25_root=pinned_q25_root,
        python_executable=python_executable,
    )
    if candidate != rebuilt:
        raise HarnessStop("Saved Q25 gate replay receipt differs from recomputed real gate")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pinned-q25-root", required=True)
    parser.add_argument("--manifest", default="configs/story_harness_p1_frozen_import.json")
    parser.add_argument("--verify-report", default=None)
    args = parser.parse_args()
    base = Path(args.repo_root).resolve(strict=True)
    manifest = load_json(secure_artifact(base, args.manifest))
    result = rerun_q25(
        manifest=manifest, repo_root=base, pinned_q25_root=args.pinned_q25_root,
    )
    if args.verify_report is not None:
        candidate = load_json(secure_artifact(base, args.verify_report))
        if candidate != result:
            raise HarnessStop("Saved Q25 gate replay receipt differs from recomputed real gate")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))

if __name__ == "__main__":
    main()
