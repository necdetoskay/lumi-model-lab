from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v18 import run as run_audit
from src.spineforge_v18_case_manifest import load_spineforge_v18_case


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(*, trigger_path: Path, out_dir: Path) -> dict[str, Any]:
    trigger = _read(trigger_path)
    if trigger.get("schema_version") != "spineforge-v18-trigger.v1":
        raise RuntimeError("Unsupported SpineForge v18 trigger schema.")
    if trigger.get("paid_authorized") is not True:
        raise RuntimeError("SpineForge v18 paid strict-audit attempt is not explicitly authorized.")
    if str(trigger.get("scope") or "") != "SPINEFORGE_V18_STRICT_AUDIT_ATTEMPT":
        raise RuntimeError("Trigger scope must be SPINEFORGE_V18_STRICT_AUDIT_ATTEMPT.")

    case_path = Path(str(trigger.get("case_manifest") or ""))
    if not case_path.exists():
        raise RuntimeError("SpineForge v18 case manifest does not exist.")
    case = load_spineforge_v18_case(case_path)

    attempt = int(trigger.get("attempt_index") or 1)
    if attempt != 1 or attempt > case.max_attempts:
        raise RuntimeError("v18 supports only one explicitly authorized paid strict-audit attempt.")

    freeze = verify_spineforge_runtime(Path(case.runtime_profile))
    source_path = Path(case.source_evidence_path)
    if not source_path.exists():
        raise RuntimeError("Frozen v18 source evidence does not exist.")
    source = _read(source_path)

    if source.get("source_context_pack_id") != case.expected_context_pack_id:
        raise RuntimeError("Source ContextPack id differs from v18 case.")
    if source.get("source_context_fingerprint") != case.expected_context_fingerprint:
        raise RuntimeError("Source ContextPack fingerprint differs from v18 case.")

    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / "result.json"
    result = run_audit(source_evidence_path=source_path, out_path=result_path)

    if result.get("source_context_pack_id") != case.expected_context_pack_id:
        raise RuntimeError("v18 result ContextPack id differs from frozen case.")
    if result.get("source_context_fingerprint") != case.expected_context_fingerprint:
        raise RuntimeError("v18 result ContextPack fingerprint differs from frozen case.")

    envelope = {
        "schema_version": "spineforge-v18-stage-envelope.v1",
        "case_id": case.case_id,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "attempt_index": attempt,
        "source_evidence_path": case.source_evidence_path,
        "context_pack_id": case.expected_context_pack_id,
        "context_fingerprint": case.expected_context_fingerprint,
        "result_status": result.get("status"),
        "strict_schema_size_bytes": result.get("strict_schema_size_bytes"),
        "provider_strict_json_schema": True,
        "audit_only": True,
        "architect_recalled": False,
        "repair_called": False,
        "writer_authorized": False,
        "result_path": str(result_path),
    }
    (out_dir / "stage_envelope.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return envelope


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trigger", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(trigger_path=args.trigger, out_dir=args.out_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
