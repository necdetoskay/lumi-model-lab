"""P3.0 actual pinned SpineForge -> Writer #3 lineage; STOP at absent same-story Q25.

Reruns authentic P2.2 deterministic SpineForge validation and genuine frozen
SpineForge V20 Writer-manifest validator. Uses source-pinned archived evidence.
Does not call provider or claim human/editor/semantic/audit acceptance.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import subprocess
import sys

from src.story_harness_p1 import PINNED_SOURCE_COMMIT
from src.story_harness_p22 import rerun_spine, _pinned_inputs, _python_runtime_env
from src.story_harness_v1 import HarnessStop, canonical_bytes, digest, load_json, secure_artifact

SCHEMA = "lumi.story-harness-p30-same-story-spine-writer-lineage.v1"
WRITER_CASE = "SPINE-V20-WRITER3-SAME-STORY"
Q25_MISSING = "MISSING_SAME_STORY_Q25_ARTIFACT"
APPROVAL_PATH = "evidence/spineforge-v20-human-review/36910614976-approved.json"
WRITER_DIR = "evidence/spineforge-v20-paid-writer/36965340665"
WRITER_MANIFEST = "evidence/spineforge-v20-writer-product/36965340665/writer-story-artifact.json"
STORY_FILE = WRITER_DIR + "/age12-island-v20-writer3-story.txt"
WRITER_RESULT = WRITER_DIR + "/age12-island-v20-writer3-result.json"
WRITER_ENVELOPE = WRITER_DIR + "/age12-island-v20-writer3-envelope.json"
AUDIT_FILE = "evidence/spineforge-v20-paid-story-audit/36969500342/qualification-report.json"
WRITER_VALIDATOR = "src/spineforge_v20_story_audit_artifact.py"

PINS = {
    APPROVAL_PATH: "72cd2ecc973884415747aed93e721c2fbb32617901c24884142585b9c54254a3",
    WRITER_MANIFEST: "aa78b74d4a2548f46d599aec2ee9abbbfb52aaa18c0bac2d03ed4a5b4f87ea13",
    STORY_FILE: "e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f",
    WRITER_RESULT: "e5245b9cb0d81c6d395aa2cf69c3324f9d65f7df41809b314dfc0175b1094951",
    WRITER_ENVELOPE: "e6f504e26be08325cf304cecfc5f7953d1ca9a494a48c1ff33b048dba5e44cf5",
    AUDIT_FILE: "eeb20809307a135d725c30d2d2a76209add2e4bae2e2e457526eef7b734edb6c",
    WRITER_VALIDATOR: "8e57f788f78d0b16cc121655bfec1b918e560067d746f85732db59418d484414",
}
STORY_SHA = PINS[STORY_FILE]
EXPECTED_ARTIFACT_ID = "writer-story:f1000691c85665ea6894e45e0318faaf5cdf7c1dac91fa453153e392af8192f3"
EXCLUDED_Q25_CASES = ["Q25-KITE01-CANDIDATES", "Q25-GREENHOUSE01-REJECTED"]

# The subprocess invokes the original Writer evidence validator, not a
# simulated verifier or a replacement in the harness. The source is pinned.
_PINNED_LAUNCHER = r"""
import json, sys
from pathlib import Path
from src.spineforge_v20_story_audit_artifact import load_verified_writer_story_artifact
data=load_verified_writer_story_artifact(
    manifest_path=Path(sys.argv[1]), repo_root=Path('.'))
m=data["manifest"]
r=data["result"]
e=data["envelope"]
out={
  "validated_original_writer_artifact": bool(data["input_verified"]),
  "writer_manifest": m,
  "writer_result_status": r["status"],
  "writer_envelope_status": e["result_status"],
  "writer_result_lineage": {
    "approval_id": r["approval_id"], "context_fingerprint": r["context_fingerprint"],
    "context_pack_id": r["context_pack_id"], "spine_hash": r["spine_hash"],
  },
  "writer_result_story_sha256": __import__("hashlib").sha256(
    (data["story"]+"\n").encode("utf-8")).hexdigest()
}
print(json.dumps(out, sort_keys=True, ensure_ascii=False))
"""


def _must(condition, reason):
    if not condition:
        raise HarnessStop(reason)


def _pin_source(root: Path):
    _pinned_inputs(root)  # Exact clean Git commit and P2.2 SpineForge gate source identity.
    for path, sha in PINS.items():
        p = root / path
        rel = Path(path)
        _must(not rel.is_absolute() and ".." not in rel.parts,
              "Unsafe same-story source path")
        current = root
        for component in rel.parts:
            current = current / component
            _must(not current.is_symlink(), "Source path crosses symlink: " + path)
        _must(p.is_file() and p.resolve().is_relative_to(root)
              and p.stat().st_size <= 500_000
              and digest(p.read_bytes()) == sha,
              "Same-story source artifact or validator not version-pinned: " + path)


def _run_original_writer_checker(*, pinned_root: Path, python_executable: str):
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix="story-harness-p30-") as name:
        env = _python_runtime_env(python_executable, Path(name))
        argv = [
            python_executable, "-c", _PINNED_LAUNCHER,
            WRITER_MANIFEST,
        ]
        try:
            result = subprocess.run(
                argv, cwd=pinned_root, env=env, capture_output=True,
                text=True, encoding="utf-8", timeout=18, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise HarnessStop("Original Writer validator subprocess failed or timed out") from exc
        _must(result.returncode == 0,
              "Original Writer validator rejected immutable artifact: " +
              result.stderr[-300:].replace("\n", " "))
        _must(len(result.stdout) <= 25_000, "Writer validator stdout too large")
        try:
            record = json.loads(result.stdout)
        except (ValueError, TypeError) as exc:
            raise HarnessStop("Original Writer validator output is not JSON") from exc
    _must(set(record) == {
        "validated_original_writer_artifact", "writer_manifest",
        "writer_result_status", "writer_envelope_status",
        "writer_result_lineage", "writer_result_story_sha256",
    }, "Unexpected original Writer verifier output")
    return record


def _validate_chain(*, spine_record, writer, audit):
    """Strict local identity checks; cannot authorize downstream execution."""
    manifest = writer["writer_manifest"]
    _must(writer["validated_original_writer_artifact"] is True
          and writer["writer_result_status"] == "writer_generated"
          and writer["writer_envelope_status"] == "writer_generated",
          "Writer product did not pass the original frozen file/lineage check")
    _must(set(manifest) == {
        "schema", "artifact_type", "stage", "status", "artifact_id",
        "immutable", "source_run_id", "attempt_index", "story_path",
        "story_sha256", "result_path", "result_sha256", "envelope_path",
        "envelope_sha256", "context_pack_id", "context_fingerprint",
        "spine_hash", "approval_id", "writer_model", "word_count",
        "writer_status", "next_stage",
    }, "Writer manifest keys diverge from frozen schema")
    _must(manifest["schema"] == "spineforge-v20-writer-story-artifact.v1"
          and manifest["artifact_type"] == "IMMUTABLE_ENGLISH_WRITER_STORY"
          and manifest["stage"] == 4 and manifest["status"] == "FROZEN"
          and manifest["immutable"] is True
          and manifest["source_run_id"] == 36965340665
          and manifest["attempt_index"] == 3
          and manifest["next_stage"] == "STORY_AUDIT"
          and manifest["writer_status"] == "writer_generated"
          and manifest["artifact_id"] == EXPECTED_ARTIFACT_ID
          and manifest["story_path"] == STORY_FILE
          and manifest["result_path"] == WRITER_RESULT
          and manifest["envelope_path"] == WRITER_ENVELOPE
          and manifest["story_sha256"] == STORY_SHA
          and manifest["result_sha256"] == PINS[WRITER_RESULT]
          and manifest["envelope_sha256"] == PINS[WRITER_ENVELOPE]
          and writer["writer_result_story_sha256"] == STORY_SHA,
          "Writer product identity, location or frozen hashes changed")
    _must(manifest["word_count"] == 2324 and manifest["writer_model"] == "aion-labs/aion-3.5-mini",
          "Writer run facts changed")
    expected = {key: spine_record[key] for key in (
        "approval_id", "context_pack_id", "context_fingerprint", "spine_hash")}
    _must({key: manifest[key] for key in expected} == expected
          and writer["writer_result_lineage"] == expected,
          "SpineForge and Writer are NOT the same story")
    _must(audit["schema"] == "spineforge-v20-story-audit-qualification-report.v1"
          and audit["source_story_sha256"] == STORY_SHA
          and audit["source_artifact_id"] == EXPECTED_ARTIFACT_ID
          and audit["status"] == "FAIL_KNOWN_DEFECT_MISSED"
          and audit["qualification_pass"] is False
          and audit["target_count"] == 1
          and audit["matched_target_count"] == 0,
          "Original same-story failed audit qualification was changed")
    return expected


def qualify(*, manifest, repo_root, pinned_source_root, python_executable=sys.executable):
    base = Path(repo_root).resolve(strict=True)
    source = Path(pinned_source_root).resolve(strict=True)
    frozen_manifest = copy.deepcopy(manifest)
    _pin_source(source)
    spine = rerun_spine(
        manifest=manifest, repo_root=base, pinned_spine_root=source,
        python_executable=python_executable,
    )
    _must(spine["actual_spine_deterministic_validator_invocations"] == 1
          and spine["downstream_execution_authorized"] is False
          and spine["provider_calls"] == 0, "P2.2 gate authority was altered")
    spine_case = next(c for c in manifest["cases"] if c["case_id"] == "SPINE-V20-HUMAN-APPROVED")
    approval = load_json(secure_artifact(base, spine_case["files"][0]["archive"]))
    _must(digest(secure_artifact(source, APPROVAL_PATH)) == PINS[APPROVAL_PATH],
          "Historical approved source bytes are not authentic")
    writer = _run_original_writer_checker(pinned_root=source, python_executable=python_executable)
    audit = load_json(secure_artifact(source, AUDIT_FILE))
    binding = _validate_chain(spine_record=approval, writer=writer, audit=audit)
    _must(manifest == frozen_manifest, "Input manifest was mutated")
    return {
        "schema": SCHEMA,
        "mode": "READ_ONLY_REAL_HISTORY_SAME_STORY_LINEAGE",
        "source_commit": PINNED_SOURCE_COMMIT,
        "p22_reexecuted_spine_receipt_sha256": digest(canonical_bytes(spine)),
        "writer_original_validator_executed": True,
        "writer_original_validator_sha256": PINS[WRITER_VALIDATOR],
        "historical_spine_case": "SPINE-V20-HUMAN-APPROVED",
        "historical_writer_case": WRITER_CASE,
        "same_story_spine_to_writer_confirmed": True,
        "identity": binding,
        "source_sha256_by_path": dict(PINS),
        "writer_story_sha256": STORY_SHA,
        "writer_manifest_artifact_id": EXPECTED_ARTIFACT_ID,
        "writer_word_count": 2324,
        "original_story_audit_qualification": audit["status"],
        "original_story_audit_qualification_pass": False,
        "original_story_audit_reexecuted": False,
        "q25_considered_but_unrelated_frozen_cases": EXCLUDED_Q25_CASES,
        "same_story_q25_evidence_present": False,
        "same_story_q25_handoff_verified": False,
        "stop_reason": Q25_MISSING,
        "state": "STOPPED_MISSING_SAME_STORY_Q25",
        "historical_human_approval_authenticated": False,
        "model_story_quality_certified": False,
        "writer_execution_authorized": False,
        "q25_execution_authorized": False,
        "downstream_execution_authorized": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": "0",
    }


def verify_report(candidate, *, manifest, repo_root, pinned_source_root,
                  python_executable=sys.executable):
    actual = qualify(manifest=manifest, repo_root=repo_root,
                     pinned_source_root=pinned_source_root,
                     python_executable=python_executable)
    _must(candidate == actual, "P3 stored lineage receipt differs from actual verified source")
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--pinned-source-root", required=True)
    p.add_argument("--manifest", default="configs/story_harness_p1_frozen_import.json")
    p.add_argument("--verify-report")
    args = p.parse_args()
    root = Path(args.repo_root).resolve(strict=True)
    historical = load_json(secure_artifact(root, args.manifest))
    outcome = qualify(manifest=historical, repo_root=root,
                      pinned_source_root=args.pinned_source_root)
    if args.verify_report:
        candidate = load_json(secure_artifact(root, args.verify_report))
        _must(candidate == outcome, "Stored P3 receipt was altered")
    print(json.dumps(outcome, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

