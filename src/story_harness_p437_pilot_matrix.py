"""P4.37 — Budgeted, evidence-disciplined ten-case / 10x3 pilot scheduler.

READ-ONLY, zero model calls, not a production release or 90% certificate.
It never promotes historical initial audits into final quality/holdout PASS.
Uses the unchanged frozen P4.15 age/topic matrix and real receipt links.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal
import json
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p437-evidence-budget-pilot-matrix.v1"
CAP = Decimal("10.00")
# Prior conservative $1.449558 incl B03 original writer; $0.040 audit
# and $0.050 genuine Q25 reserved; the actual charges were lower.
RESERVED = Decimal("1.539558")
KNOWN_ACTUAL_REPORTED = Decimal("0.378446")
UNKNOWN_CHARGE_HOLD = Decimal("1.130000")
UNUSED_STAGE_RESERVE = Decimal("0.031112")
GENERATION_CAP = Decimal("0.350")
INITIAL_AUDIT_CAP = Decimal("0.040")
Q25_CAP = Decimal("0.050")
FULL_TRIAL_CAP = GENERATION_CAP + INITIAL_AUDIT_CAP + Q25_CAP
AGES = {4:2, 10:2, 12:2, 25:2, 40:2}
VALID_IDS = tuple(f"B{i:02d}" for i in range(1,11))
# Historical initial pilot runs: evidence is authentic, but these are NOT
# preregistered independent holdout trials or frozen v21 final audit passes.
FROZEN = {
    "B01": {
        "story_sha256":"cbbf3ba8cb3a9ec5d19ed51238bc3b9a0259237cdb7896b75dcdd0584adca912",
        "source_sha256":"91854710f46db13ee2599d567ca2fcbbcd945af50515a779ddee58211ee050dc",
        "audit":"evidence/story_harness_p422/b01-r06-independent-quality-accept.json",
        "master":"evidence/story_harness_p423/b01-r06-pilot-master-manifest.json",
        "q25":"evidence/story_harness_p424/b01-r06-q25-r02-real-evidence.json",
        "final":"evidence/story_harness_p425/b01-r06-real-read-only-final-state-draft.json",
    },
    "B02": {
        "story_sha256":"7712f1561881ba50544857bc1d384eba163691c6a1e1bf65b295d90f86e5955d",
        "source_sha256":"95397810d5a20c9c7f4a4185f914bf73bf84179ddc5a495c62db84c1fcdac2b8",
        "audit":"evidence/story_harness_p427/b02-r06-independent-quality-accept.json",
        "master":"evidence/story_harness_p428/b02-r06-pilot-master-manifest.json",
        "q25":"evidence/story_harness_p429/b02-r06-original-q25-evidence.json",
        "final":"evidence/story_harness_p430/b02-r06-real-read-only-final-state-draft.json",
    },
    "B03": {
        "story_sha256":"80fa8224c78c494b13bc347ecabdfff75fd5c9e1638ad88ee9ba47c6986643f9",
        "source_sha256":"b55ba5c57a3abda0a1b4ef18fe98284f4fea7511b1b82281585ac9da77a205c0",
        "audit":"evidence/story_harness_p433/b03-r06-original-independent-quality-accept.json",
        "master":"evidence/story_harness_p434/b03-r06-pilot-master-manifest.json",
        "q25":"evidence/story_harness_p435/b03-r06-original-q25-evidence.json",
        "final":"evidence/story_harness_p436/b03-r06-real-read-only-final-state-draft.json",
    },
}

def require(ok, reason):
    if not ok:
        raise HarnessStop(reason)

def _receipt(root, relative):
    p = Path(root) / relative
    require(p.is_file() and not p.is_symlink() and 0 < p.stat().st_size < 100000,
            "Historical evidence missing or path unsafe: " + relative)
    return json.loads(p.read_bytes())

def verify_historical(root, case_id):
    record = FROZEN[case_id]
    story_sha, source_sha = record["story_sha256"], record["source_sha256"]
    quality = _receipt(root, record["audit"])
    master = _receipt(root, record["master"])
    q25 = _receipt(root, record["q25"])
    state = _receipt(root, record["final"])
    require(quality.get("case_id") in (case_id, None)  # B01 v1 omits case_id
            and quality.get("source_pack_sha256") == source_sha
            and quality.get("story_sha256") == story_sha
            and quality.get("quality_initial_verdict") == "ACCEPT"
            and quality.get("quality_initial_audit_accepted") is True
            and quality.get("reader_score", 0) >= 4
            and quality.get("blocking_findings") == []
            and quality.get("full_original_v21_final_audit_completed") is False,
            case_id + " initial quality is not genuinely original ACCEPT")
    require(master.get("case_id") == case_id
            and master.get("accepted_story_sha256") == story_sha
            and master.get("source_story_sha256") == story_sha
            and master.get("source_pack_sha256") == source_sha
            and master.get("q25_read_only_extraction_allowed") is True
            and master.get("manual_text_edits") == 0
            and master.get("full_original_frozen_v21_4_production_quality_accepted") is False
            and master.get("production_state_write_authorized") is False,
            case_id + " immutable pilot Master not verified")
    require(q25.get("case_id") == case_id
            and q25.get("source_pack_sha256") == source_sha
            and q25.get("story_sha256") == story_sha
            and q25.get("provenance_verified") is True
            and q25.get("quote_matching_verified") is True
            and q25.get("final_story_state_committed") is False
            and q25.get("production_state_write_authorized") is False,
            case_id + " Q25 receipt cannot certify downstream production")
    require(state.get("case_id") == case_id
            and state.get("english_master_sha256") == story_sha
            and state.get("artifact_classification") == "READ_ONLY_FINAL_STORY_STATE_DRAFT_NOT_CANON"
            and state.get("world_time_final") is None
            and state.get("production_change") is False,
            case_id + " Final StoryState must stay a read-only proposal")
    return {
        "case_id": case_id,
        "stage_status": "INITIAL_PIPELINE_ARTIFACTS_VERIFIED_NOT_RELEASE_CERTIFIED",
        "story_sha256": story_sha,
        "reader_score": quality["reader_score"],
        "q25_generation_id": q25.get("generation_id"),
        "original_state_receipt_path": record["final"],
        "independent_holdout_count": 0,
        "frozen_v21_final_quality_certified": False,
    }

def build_report(repo_root="."):
    plan = load_plan(repo_root)
    cases = plan["cases"]
    require(len(cases) == 10
            and tuple(c["id"] for c in cases) == VALID_IDS
            and Counter(c["input"]["reader_age"] for c in cases) == AGES
            and all(c.get("split") == "pilot" for c in cases),
            "Frozen ten-case pilot distribution changed")
    require(RESERVED == KNOWN_ACTUAL_REPORTED + UNKNOWN_CHARGE_HOLD + UNUSED_STAGE_RESERVE
            and RESERVED <= CAP
            and FULL_TRIAL_CAP == Decimal("0.440"),
            "Conservative inference budget ledger inconsistent")
    proofs = {name: verify_historical(repo_root, name) for name in FROZEN}
    remaining = CAP - RESERVED
    fresh_limit = int(remaining // FULL_TRIAL_CAP)
    not_generated = len(cases) - len(proofs)
    proposed_pilot_reserve = FULL_TRIAL_CAP * not_generated
    require(RESERVED + proposed_pilot_reserve <= CAP, "Cannot pre-reserve seven new pilot stories")
    targets = []
    for c in cases:
        name = c["id"]
        targets.append({
            "case_id": name,
            "reader_age": c["input"]["reader_age"],
            "topic": c["input"]["topic"],
            "historical_initial_pipeline": proofs.get(name),
            "new_pilot_generation_status": (
                "ORIGINAL_INITIAL_CHAIN_ONLY" if name in proofs else "NOT_GENERATED"
            ),
            "frozen_v21_final_quality_certified": False,
        })
    trials = [
        {"case_id": c["id"], "independent_run": f"holdout-{index:02d}",
         "status": "NOT_RUN_NOT_ACCEPTED", "generation_id": None, "cost_usd": None}
        for c in cases for index in (1,2,3)
    ]
    return {
        "schema": SCHEMA,
        "paid_execution_authorized_by_this_report": False,
        "new_model_calls": 0,
        "production_changes": False,
        "approved_cap_usd": format(CAP,"f"),
        "known_provider_reported_total_usd": format(KNOWN_ACTUAL_REPORTED,"f"),
        "unknown_charge_reservation_usd": format(UNKNOWN_CHARGE_HOLD,"f"),
        "unused_stage_reservation_usd": format(UNUSED_STAGE_RESERVE,"f"),
        "total_conservative_reserved_usd": format(RESERVED,"f"),
        "remaining_conservative_budget_usd": format(remaining,"f"),
        "new_full_trial_worst_case_usd": format(FULL_TRIAL_CAP,"f"),
        "max_new_full_trials_current_budget": fresh_limit,
        "pilot_missing_generations": not_generated,
        "pilot_new_run_worst_case_reserve_usd": format(proposed_pilot_reserve,"f"),
        "conservative_budget_after_seven_case_pilot_usd": format(
            RESERVED + proposed_pilot_reserve,"f"),
        "new_full_trials_after_seven_case_pilot": int(
            (CAP-RESERVED-proposed_pilot_reserve)//FULL_TRIAL_CAP),
        "historical_initial_pipeline_evidence_cases": len(proofs),
        "release_certified_cases": 0,
        "holdout_real_independent_trials": 0,
        "holdout_required_trials": len(trials),
        "holdout_tranche_fully_preapproved": False,
        "cases": targets,
        "holdout": trials,
        "next_candidate_case": "B04",
    }

def main():
    print(json.dumps(build_report(), ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
