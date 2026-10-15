"""P2.2: replay the REAL frozen SpineForge deterministic validator, offline.

Only validate_narrative_spine (v19 implementation used by v20) is rerun.
Historical human ACCEPT stays an unauthenticated historical claim. This
does not rerun a model judge, authorize Writer/Q25 or validate story prose.
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

from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_p2 import generate_receipts
from src.story_harness_p21 import _verify_checkout
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA = "lumi.story-harness-p22-real-spine-offline-replay.v1"
CASE_ID = "SPINE-V20-HUMAN-APPROVED"
ARCHIVE_ROLE = "decision"
CONTEXT_PATH = "data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json"
CASES_PATH = "data/specifications/story_lab/spineforge_v20_qualification_cases_v1.json"
VALIDATOR_PATH = "src/spineforge_v19_validator.py"
HASH_PATH = "src/spineforge_v19_human_review.py"
SOURCE_SHA256 = {
    VALIDATOR_PATH: "2c7c4e3f32fcf25755afc2d91c1e1e7e4c3b8dec4224038a6dfab241b0adb34e",
    HASH_PATH: "ce3137d056d12e7faaeea80a061a6f1220f958d356b475c4a9dfa371f80dd63c",
    CONTEXT_PATH: "d3524c41f6c8eeacbf76d881d1ec2d81400bc17d5412f0d68890d67f37f9e80c",
    CASES_PATH: "cbc3ba962005c5938f7948b4b3a9df30fcf059da2287508ac6d8e193e5b007b6",
}

# Code runs with the pinned checkout as cwd. It imports the ACTUAL frozen
# SpineForge module, not a reimplementation in this harness.
_PINNED_LAUNCHER = r"""
import json
from pathlib import Path
import sys
from src.narrative_spine_v1_contract import NarrativeSpineV1
from src.spine_context_pack_v1 import SpineContextPackV1
from src.spineforge_v19_obligations import ReaderStoryObligationsV1
from src.spineforge_v19_validator import validate_narrative_spine
from src.spineforge_v19_human_review import spine_hash

approval = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
pack = SpineContextPackV1.model_validate_json(Path(sys.argv[2]).read_bytes())
qualification = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
assert qualification["schema"] == "spineforge-v20-qualification-cases.v1"
assert len(qualification["cases"]) == 1
case = qualification["cases"][0]
assert case["case_id"] == "spineforge.v20.age12.adventure-exploration.island.01"
assert case["context_fixture_status"] == "FROZEN"
assert case["context_fixture_ref"] == "data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json"
obligations = ReaderStoryObligationsV1.model_validate(case["obligations"])
spine = NarrativeSpineV1.model_validate(approval["approved_spine"])
assert approval["context_pack_id"] == pack.context_pack_id
assert approval["context_fingerprint"] == pack.context_fingerprint
assert spine_hash(spine) == approval["spine_hash"]
report = validate_narrative_spine(spine=spine, pack=pack, obligations=obligations)
data = report.model_dump(mode="json", by_alias=True)
assert data["schema"] == "spineforge-v19-validation.v1"
assert data["context_pack_id"] == pack.context_pack_id
assert data["context_fingerprint"] == pack.context_fingerprint
assert data["authority_valid"] is True
assert data["reveal_safe"] is True
assert data["obligations_valid"] is True
print(json.dumps(data, ensure_ascii=False, sort_keys=True))
"""


def _must(ok, message):
    if not ok:
        raise HarnessStop(message)


def _pinned_inputs(root: Path):
    _verify_checkout(root)
    for path, sha in SOURCE_SHA256.items():
        actual = root / path
        _must(actual.is_file() and not actual.is_symlink() and
              actual.resolve().is_relative_to(root) and digest(actual.read_bytes()) == sha,
              "Pinned SpineForge dependency hash mismatch: " + path)
    return (
        root / CONTEXT_PATH,
        root / CASES_PATH,
    )


def _python_runtime_env(executable: str, temp: Path) -> dict[str, str]:
    # Match P2.1 self-hosted Python shared-library handling but never forward
    # caller environment, model keys, home directory or arbitrary PYTHONPATH.
    runtime = Path(executable).resolve(strict=True).parent.parent
    candidates = [runtime / "lib", Path(sys.prefix) / "lib"]
    compiled = sysconfig.get_config_var("LIBDIR")
    if isinstance(compiled, str) and Path(compiled).is_absolute():
        candidates.append(Path(compiled))
    library = next((
        loc.resolve() for loc in candidates if loc.is_dir()
        and any(loc.glob("libpython%d.%d.so*" % sys.version_info[:2]))
    ), None)
    _must(library is not None, "Python runtime library is unavailable")
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "LD_LIBRARY_PATH": str(library),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "HOME": str(temp),
    }


def _run_spine_validator(*, approval_bytes: bytes, pinned_root: Path,
                         context_path: Path, cases_path: Path,
                         python_executable: str):
    with tempfile.TemporaryDirectory(prefix="story-harness-p22-") as directory:
        temp = Path(directory)
        input_path = temp / "approved-spine.json"
        input_path.write_bytes(approval_bytes)
        argv = [
            python_executable, "-c", _PINNED_LAUNCHER,
            str(input_path), str(context_path), str(cases_path),
        ]
        try:
            proc = subprocess.run(
                argv, cwd=pinned_root,
                env=_python_runtime_env(python_executable, temp),
                capture_output=True, text=True, encoding="utf-8",
                timeout=18, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HarnessStop("Pinned SpineForge validator transport/timeout failure") from exc
        _must(proc.returncode == 0,
              "Pinned SpineForge validator rejected inputs: " + proc.stderr[-500:].replace("\n", " "))
        _must(len(proc.stdout) <= 20_000, "Pinned SpineForge stdout exceeded bounded size")
        try:
            report = json.loads(proc.stdout)
        except (ValueError, TypeError) as exc:
            raise HarnessStop("Pinned SpineForge validator did not return JSON") from exc
    _must(set(report) == {
        "schema", "context_pack_id", "context_fingerprint", "location_sequence",
        "discovery_turns", "real_choice_count", "authority_valid",
        "reveal_safe", "obligations_valid",
    }, "Pinned SpineForge report contains unexpected keys")
    _must(report["schema"] == "spineforge-v19-validation.v1" and
          report["authority_valid"] is True and
          report["reveal_safe"] is True and
          report["obligations_valid"] is True and
          type(report["discovery_turns"]) is int and
          type(report["real_choice_count"]) is int and
          report["discovery_turns"] >= 3 and
          report["real_choice_count"] >= 2 and
          isinstance(report["location_sequence"], list),
          "SpineForge deterministic offline authority validation failed")
    return report


def rerun_spine(*, manifest, repo_root, pinned_spine_root,
                python_executable=sys.executable):
    base = Path(repo_root).resolve(strict=True)
    pinned = Path(pinned_spine_root).resolve(strict=True)
    original_manifest = copy.deepcopy(manifest)
    context_file, cases_file = _pinned_inputs(pinned)
    parent = generate_receipts(manifest=manifest, repo_root=base)
    _must(parent["case_count"] == 4 and
          parent["downstream_stage_executions_authorized"] == 0 and
          parent["provider_calls"] == 0 and
          parent["state_commit_authorized"] is False,
          "P2 archive integrity cannot be promoted to original validator authority")
    stage = next((x for x in parent["stage_results"] if x["case_id"] == CASE_ID), None)
    _must(stage is not None and
          stage["original_historical_outcome"] == "ACCEPT" and
          stage["downstream_execution_authorized"] is False,
          "Original SpineForge case/outcome was changed")
    entry = next((x for x in manifest["cases"] if x["case_id"] == CASE_ID), None)
    _must(entry is not None and entry["adapter"] == "spine_human_review" and
          len(entry["files"]) == 1 and entry["files"][0]["kind"] == ARCHIVE_ROLE,
          "SpineForge historical case is not uniquely pinned")
    file = entry["files"][0]
    archived = secure_artifact(base, file["archive"])
    _must(digest(archived) == file["sha256"] and
          digest(secure_artifact(pinned, file["source_path"])) == file["sha256"],
          "SpineForge approved artifact differs from frozen source")
    record = load_json(archived)
    _must(record["schema"] == "spineforge-v20-human-approved.v1" and
          record["gate_decision"] == "ACCEPT" and
          record["human_review"]["verdict"] == "APPROVE" and
          record["paid_writer_execution_authorized"] is False,
          "Source report cannot be silently promoted to paid Writer authority")
    report = _run_spine_validator(
        approval_bytes=archived, pinned_root=pinned,
        context_path=context_file, cases_path=cases_file,
        python_executable=python_executable,
    )
    _must(report["context_pack_id"] == record["context_pack_id"] and
          report["context_fingerprint"] == record["context_fingerprint"],
          "Original spine/context relationship changed")
    _must(manifest == original_manifest, "SpineForge manifest mutated during replay")
    return {
        "schema": SCHEMA,
        "source_commit": PINNED_SOURCE_COMMIT,
        "p2_receipts_sha256": digest(canonical_bytes(parent)),
        "case_id": CASE_ID,
        "frozen_historical_approval_sha256": file["sha256"],
        "original_historical_gate_claim_immutable": "ACCEPT",
        "validator_name": "src.spineforge_v19_validator.validate_narrative_spine",
        "validator_sha256": SOURCE_SHA256[VALIDATOR_PATH],
        "context_sha256": SOURCE_SHA256[CONTEXT_PATH],
        "obligations_source_sha256": SOURCE_SHA256[CASES_PATH],
        "actual_spine_deterministic_validator_invocations": 1,
        "real_validator_report": report,
        "result_scope": "STRUCTURAL_CONTEXT_AUTHORITY_OBLIGATIONS_ONLY",
        "original_human_review_authenticated": False,
        "original_model_product_gate_reexecuted": False,
        "story_semantic_quality_certified": False,
        "spine_writer_q25_same_story_handoff_verified": False,
        "downstream_execution_authorized": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": "0",
    }


def verify_pinned_report(candidate, *, manifest, repo_root, pinned_spine_root,
                         python_executable=sys.executable):
    regenerated = rerun_spine(
        manifest=manifest, repo_root=repo_root,
        pinned_spine_root=pinned_spine_root, python_executable=python_executable,
    )
    if candidate != regenerated:
        raise HarnessStop("Saved SpineForge receipt diverges from real pinned validator replay")
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pinned-spine-root", required=True)
    parser.add_argument("--manifest", default="configs/story_harness_p1_frozen_import.json")
    parser.add_argument("--verify-report")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve(strict=True)
    manifest = load_json(secure_artifact(root, args.manifest))
    result = rerun_spine(manifest=manifest, repo_root=root,
                         pinned_spine_root=args.pinned_spine_root)
    if args.verify_report:
        candidate = load_json(secure_artifact(root, args.verify_report))
        _must(candidate == result, "Stored P2.2 receipt changed")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

