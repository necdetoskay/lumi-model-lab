"""Read-only Story Harness V1 full-component readiness certificate.

Checks memory, tools, models, prompts, state, quality, finance, evidence and
ten exact inputs. It has NO provider transport, secrets or payment permissions.
PREPARED != SEALED != LIVE-READY. All flags are explicit, not inferred.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.story_harness_frozen_cohort_v1 import (
    IDS, CAP, preflight as cohort_preflight
)
from src.story_harness_frozen_round_v1 import simulate_seal, check_lock
from src.story_harness_runtime_v1 import (
    create_harness, load_manifest, ROLES, MODULES
)
from src.story_harness_p416_input_bridge import build_spine_request
from src.story_harness_p417_live_pilot import wire
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-preproduction-readiness.v1"

def offline_readiness(repo_root="."):
    root = Path(repo_root)
    policy = cohort_preflight(root)
    config, manifest_sha = load_manifest(root)
    simulated = simulate_seal(root)
    check_lock(root, simulated)
    discovered = {}
    runtime_sha = set()
    for case in IDS:
        runtime = create_harness(root, case)
        runtime.verify_immutable()
        stage = wire("SPINEFORGE",
                     build_spine_request(runtime.pack),
                     simple_envelope=True)
        bound = runtime.authorize_stage("SPINEFORGE", stage)
        if bound["approved_tool"] != "spineforge":
            raise HarnessStop("Unexpected public SpineForge tool")
        if bound["memory_snapshot_sha256"] != runtime.pack["pack_sha256"]:
            raise HarnessStop("Cross-case memory leak")
        discovered[case] = {
            "age": runtime.pack["reader_age"],
            "input_sha256": policy["case_input_sha256"][case],
            "memory_snapshot_sha256": runtime.memory_snapshot_sha256,
            "tools_authorized": len(runtime.contract["tools"]["registry"]),
            "stage_model_count": len(runtime.contract["models"]["stage_roles"]),
            "first_stage_request_sha256": hashlib.sha256(
                json.dumps(stage, sort_keys=True,
                           ensure_ascii=False).encode()).hexdigest(),
        }
        runtime_sha.add(runtime.manifest_sha256)
    if len(discovered) != 10 or len(runtime_sha) != 1:
        raise HarnessStop("Incomplete fixed story cohort or multiple harness configs")
    return {
        "schema": SCHEMA,
        "harness_configuration_status": "PREPARED_NOT_FROZEN",
        "offline_contract_status": "READY_FOR_OFFLINE_REHEARSAL",
        "real_paid_cohort_status": "BLOCKED_NOT_SEALED",
        "harness_module": "src/story_harness_runtime_v1.py",
        "run_commit": simulated["harness_commit"],
        "runtime_manifest_sha256": manifest_sha,
        "frozen_simulation_sha256": hashlib.sha256(
            json.dumps(simulated, sort_keys=True).encode()).hexdigest(),
        "pinned_source_files_count": len(simulated["files_sha256"]),
        "harness_sections": [
            "memory", "tools", "models", "prompts", "quality",
            "state", "finance", "evidence", "lifecycle"
        ],
        "model_stage_names": list(ROLES),
        "tool_names": sorted(MODULES),
        "input_count": len(IDS),
        "inputs": discovered,
        "budget_cap_usd": str(CAP),
        "provider_calls_performed": 0,
        "independent_model_accepts_certified": 0,
        "paid_calls_authorized": 0,
        "full_real_cohort_started": False,
        "missing_live_gates": [
            "seal exact reviewed harness commit and component digests",
            "reconcile actual provider spending/unknown-charge hold under $20 cap",
            "validate dedicated provider key isolation/current limit",
            "validate provider exact model/structured-output route live",
            "authenticate paid grants and provider receipts without mocks",
            "prove no-retry ten-case paid-run dispatch and completion records",
            "preserve independent quality and Q25 provenance for every real case",
        ],
    }

if __name__ == "__main__":
    result = offline_readiness()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
