"""P4.57 B07 explicit-grant offline gate. No provider network operations."""
from __future__ import annotations
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from src.story_harness_p454_b07_age25 import SOURCE_SHA, PRIOR_CONSERVATIVE, source_case
from src.story_harness_p417_live_pilot import MODEL, USD_CAP, GLOBAL_USER_CAP, STAGE_MAX_USD, OUTPUT_CAPS
from src.story_harness_v1 import HarnessStop

RECEIPT_SHA = "c1532871bdea9b114aa5c09c2d25a5014ff2f97d3e8f980683369213c6331309"
LABEL = "b07-" + SOURCE_SHA[:16] + "-r06"
OLD_CLAIM_ROOTS = ("_lumi_p454_b07_story_claims", "_lumi_p455_b07_story_claims")
EXPECTED_GRANT = {
    "schema": "lumi.story-harness-p457-B07-paid-original-single-grant.v1",
    "case_id": "B07",
    "run_variant": "r06",
    "source_pack_sha256": SOURCE_SHA,
    "reader_age": 25,
    "minimum_words": 1800,
    "maximum_words": 2800,
    "model": MODEL,
    "max_model_posts": 2,
    "maximum_new_cost_usd": "0.35",
    "previous_conservative_budget_reserved_usd": "2.859558",
    "user_aggregate_approved_usd": "10.00",
    "automatic_retries": False,
    "production_write": False,
    "previous_p455_skip_run_id": 38605301285,
    "previous_p455_model_posts": 0,
    "grant_id": "p457-b07-original-r06-once",
}

def require(ok, reason):
    if not ok:
        raise HarnessStop("P457_STOP_" + reason)

def check_claims(workspace):
    root = Path(workspace)
    require(root.is_dir() and not root.is_symlink(), "WORKSPACE_UNTRUSTED")
    for name in OLD_CLAIM_ROOTS:
        claim_root = root / name
        require(not claim_root.is_symlink(), "CLAIM_ROOT_SYMLINK")
        claim = claim_root / LABEL
        require(not claim.exists() and not claim.is_symlink(), "PREVIOUS_B07_ATTEMPT")
    return True

def check_grant(grant):
    require(type(grant) is dict and grant == EXPECTED_GRANT, "GRANT_MISMATCH")
    require(PRIOR_CONSERVATIVE == Decimal(grant["previous_conservative_budget_reserved_usd"]), "PRIOR_BUDGET")
    require(USD_CAP == Decimal(grant["maximum_new_cost_usd"]), "RUN_BUDGET")
    require(GLOBAL_USER_CAP == Decimal(grant["user_aggregate_approved_usd"]), "GLOBAL_BUDGET")
    require(PRIOR_CONSERVATIVE + USD_CAP <= GLOBAL_USER_CAP, "CAP_EXCEEDED")
    require(sum(STAGE_MAX_USD.values()) <= USD_CAP, "STAGE_CAP_EXCEEDED")
    require(OUTPUT_CAPS == {"SPINEFORGE": 5500, "WRITER": 6500}, "OUTPUT_CAP_CHANGED")
    return True

def preflight(repo_root, workspace, grant_path):
    _, pack = source_case(repo_root)
    require(pack["pack_sha256"] == SOURCE_SHA and pack["reader_age"] == 25, "SOURCE_CHANGED")
    receipt = Path(repo_root) / "evidence/story_harness_p444/b05-r06-original-quality-stop.json"
    require(hashlib.sha256(receipt.read_bytes()).hexdigest() == RECEIPT_SHA, "B05_STOP_TAMPER")
    stop = json.loads(receipt.read_bytes())
    require(stop["case_id"] == "B05"
            and stop["quality_initial_verdict"] == "STOP_UNKNOWN_OR_INVALID"
            and stop["english_master_authorized"] is False, "B05_STOP_VIOLATED")
    check_grant(json.loads(Path(grant_path).read_bytes()))
    check_claims(workspace)
    return {"case_id": "B07", "offline_preflight": "READY_NO_MODEL_POST",
            "prior_reservation_usd": str(PRIOR_CONSERVATIVE),
            "maximum_new_spend_usd": str(USD_CAP), "provider_calls": 0}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo-root", default=".")
    p.add_argument("--workspace", required=True)
    p.add_argument("--grant", required=True)
    args = p.parse_args()
    print(json.dumps(preflight(args.repo_root, args.workspace, args.grant), sort_keys=True))

if __name__ == "__main__":
    main()
