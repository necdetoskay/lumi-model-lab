from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.spine_context_pack_v1 import write_spine_context_pack
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v11 import run as run_spineforge
from src.spineforge_v11_case_manifest import load_spineforge_v11_case


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(*, trigger_path: Path, out_dir: Path) -> dict[str, Any]:
    trigger = _read(trigger_path)
    if trigger.get("schema_version") != "spineforge-v11-trigger.v1":
        raise RuntimeError("Unsupported SpineForge v11 trigger schema.")
    if trigger.get("paid_authorized") is not True:
        raise RuntimeError("SpineForge v11 paid attempt is not explicitly authorized.")
    if str(trigger.get("scope") or "") != "SPINEFORGE_V11_ATTEMPT":
        raise RuntimeError("Trigger scope must be SPINEFORGE_V11_ATTEMPT.")

    case_path = Path(str(trigger.get("case_manifest") or ""))
    if not case_path.exists():
        raise RuntimeError("SpineForge v11 case manifest does not exist.")
    case = load_spineforge_v11_case(case_path)

    requested_attempt = int(trigger.get("attempt_index") or 1)
    if requested_attempt != 1:
        raise RuntimeError(
            "SpineForge v11 qualification intentionally supports only Attempt 1. "
            "Repair/retry requires a separately frozen revision."
        )
    if requested_attempt > case.max_attempts:
        raise RuntimeError("Trigger attempt index exceeds case bounds.")

    profile_path = Path(case.runtime_profile)
    freeze = verify_spineforge_runtime(profile_path)
    profile = _read(profile_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    context_pack_path = out_dir / "spine_context_pack.json"
    pack = write_spine_context_pack(
        source_path=Path(case.canonical_state_source),
        out_path=context_pack_path,
    )
    if pack.context_pack_id != case.expected_context_pack_id:
        raise RuntimeError("Materialized ContextPack id differs from qualification case.")
    if pack.context_fingerprint != case.expected_context_fingerprint:
        raise RuntimeError("Materialized ContextPack fingerprint differs from qualification case.")

    result_path = out_dir / "result.json"
    result = run_spineforge(
        context_pack_path=context_pack_path,
        out_path=result_path,
        architect_prompt_path=Path(profile["runtime"]["architect_prompt"]),
        audit_prompt_path=Path(profile["runtime"]["audit_prompt"]),
    )
    if result.get("context_fingerprint") != pack.context_fingerprint:
        raise RuntimeError("Result ContextPack fingerprint differs from materialized pack.")

    envelope = {
        "schema_version": "spineforge-v11-stage-envelope.v1",
        "case_id": case.case_id,
        "runtime_id": profile["runtime_id"],
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "attempt_index": requested_attempt,
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "result_status": result.get("status"),
        "writer_authorized": False,
        "automatic_repair_executed": False,
        "result_path": str(result_path),
        "context_pack_path": str(context_pack_path),
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
