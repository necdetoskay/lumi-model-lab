from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.spine_context_pack_v1 import write_spine_context_pack
from src.spineforge_freeze_verify import verify_spineforge_runtime
from src.spineforge_v5 import run as run_spineforge
from src.spineforge_v5_case_manifest import load_spineforge_v5_case


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run(*, trigger_path: Path, out_dir: Path) -> dict[str, Any]:
    trigger = _read(trigger_path)
    if trigger.get("schema_version") != "spineforge-v5-trigger.v1":
        raise RuntimeError("Unsupported SpineForge v5 trigger schema.")
    if trigger.get("paid_authorized") is not True:
        raise RuntimeError("SpineForge v5 paid attempt is not explicitly authorized.")
    if trigger.get("scope") != "SPINEFORGE_V5_ATTEMPT":
        raise RuntimeError("Trigger scope must be SPINEFORGE_V5_ATTEMPT.")

    case_path = Path(str(trigger.get("case_manifest") or ""))
    case = load_spineforge_v5_case(case_path)
    profile_path = Path(case.runtime_profile)
    freeze = verify_spineforge_runtime(profile_path)
    profile = _read(profile_path)

    attempt = int(trigger.get("attempt_index") or 1)
    if attempt < 1 or attempt > case.max_attempts:
        raise RuntimeError("Trigger attempt index exceeds case bounds.")

    out_dir.mkdir(parents=True, exist_ok=True)
    context_path = out_dir / "spine_context_pack.json"
    pack = write_spine_context_pack(
        source_path=Path(case.canonical_state_source),
        out_path=context_path,
    )
    if pack.context_pack_id != case.expected_context_pack_id:
        raise RuntimeError("Materialized ContextPack id differs from case expectation.")
    if pack.context_fingerprint != case.expected_context_fingerprint:
        raise RuntimeError("Materialized ContextPack fingerprint differs from case expectation.")

    revision_path = None
    if trigger.get("revision_feedback"):
        revision_path = Path(str(trigger["revision_feedback"]))
        if not revision_path.exists():
            raise RuntimeError("SpineForge v5 revision feedback path does not exist.")
        revision = _read(revision_path)
        if revision.get("context_pack_id") != pack.context_pack_id:
            raise RuntimeError("Revision feedback ContextPack id differs from materialized pack.")
        if revision.get("context_fingerprint") != pack.context_fingerprint:
            raise RuntimeError("Revision feedback ContextPack fingerprint differs from materialized pack.")
        if int(revision.get("next_attempt") or 0) != attempt:
            raise RuntimeError("Trigger attempt does not match revision feedback next_attempt.")
    elif attempt != 1:
        raise RuntimeError("Attempt >1 requires context-bound revision feedback.")

    result_path = out_dir / "result.json"
    result = run_spineforge(
        context_pack_path=context_path,
        out_path=result_path,
        creative_prompt_path=Path(profile["runtime"]["creative_prompt"]),
        compiler_prompt_path=Path(profile["runtime"]["compiler_prompt"]),
        gate_prompt_path=Path(profile["runtime"]["product_gate_prompt"]),
        revision_feedback_path=revision_path,
        max_attempts=case.max_attempts,
    )
    if int(result.get("attempt_index") or 0) != attempt:
        raise RuntimeError("Runtime attempt index differs from trigger.")
    if result.get("context_fingerprint") != pack.context_fingerprint:
        raise RuntimeError("Result ContextPack fingerprint differs from materialized pack.")

    envelope = {
        "schema_version": "spineforge-v5-stage-envelope.v1",
        "case_id": case.case_id,
        "runtime_id": profile["runtime_id"],
        "runtime_revision": freeze["runtime_revision"],
        "runtime_verified_files": freeze["verified_files"],
        "attempt_index": attempt,
        "context_pack_id": pack.context_pack_id,
        "context_fingerprint": pack.context_fingerprint,
        "result_status": result.get("status"),
        "writer_authorized": False,
        "result_path": str(result_path),
        "context_pack_path": str(context_path),
    }
    (out_dir / "stage_envelope.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return envelope


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--trigger", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(trigger_path=a.trigger, out_dir=a.out_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
