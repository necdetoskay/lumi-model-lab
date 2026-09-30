from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v14 import run as run_repair
from src.spineforge_v14_case_manifest import load_spineforge_v14_case


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(*, trigger_path: Path, out_dir: Path) -> dict[str, Any]:
    trigger = _read(trigger_path)
    if trigger.get("schema_version") != "spineforge-v14-trigger.v1":
        raise RuntimeError("Unsupported SpineForge v14 trigger schema.")
    if trigger.get("paid_authorized") is not True:
        raise RuntimeError("SpineForge v14 paid repair attempt is not explicitly authorized.")
    if str(trigger.get("scope") or "") != "SPINEFORGE_V14_REPAIR_ATTEMPT":
        raise RuntimeError("Trigger scope must be SPINEFORGE_V14_REPAIR_ATTEMPT.")

    case_path = Path(str(trigger.get("case_manifest") or ""))
    if not case_path.exists():
        raise RuntimeError("SpineForge v14 case manifest does not exist.")
    case = load_spineforge_v14_case(case_path)

    requested_attempt = int(trigger.get("attempt_index") or 1)
    if requested_attempt != 1:
        raise RuntimeError(
            "SpineForge v14 qualification supports only Repair Attempt 1. "
            "Another repair requires a separately frozen revision."
        )
    if requested_attempt > case.max_attempts:
        raise RuntimeError("Trigger attempt index exceeds case bounds.")

    freeze = verify_spineforge_runtime(Path(case.runtime_profile))
    result_path = out_dir / "result.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    result = run_repair(
        source_evidence_path=Path(case.source_evidence_path),
        out_path=result_path,
    )
    if result.get("source_context_pack_id") != case.expected_context_pack_id:
        raise RuntimeError("Repair result ContextPack id differs from qualification case.")
    if result.get("source_context_fingerprint") != case.expected_context_fingerprint:
        raise RuntimeError("Repair result ContextPack fingerprint differs from qualification case.")

    envelope = {
        "schema_version": "spineforge-v14-stage-envelope.v1",
        "case_id": case.case_id,
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "attempt_index": requested_attempt,
        "source_evidence_path": case.source_evidence_path,
        "context_pack_id": case.expected_context_pack_id,
        "context_fingerprint": case.expected_context_fingerprint,
        "result_status": result.get("status"),
        "writer_authorized": False,
        "automatic_repair_loop_executed": False,
        "result_path": str(result_path),
    }
    (out_dir / "stage_envelope.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
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
