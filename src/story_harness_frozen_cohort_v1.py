"""LUMI fixed-ten-cohort policy preflight; READ ONLY, ZERO MODEL CALLS.

An authorized $20 global program ceiling is not a grant. Historical P4.x $10
receipts, caps and committed artifacts remain untouched. The sealed executor
must verify these contracts before every genuine billable attempt.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path

from src.story_harness_p415_benchmark import load_plan, case_fingerprint
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-frozen-cohort-policy.v1"
POLICY_FILE = "configs/story_harness_frozen_cohort_v1.json"
IDS = tuple(f"B{i:02d}" for i in range(1, 11))
AGES = {4: 2, 10: 2, 12: 2, 25: 2, 40: 2}
CAP = Decimal("20.00")
DOCUMENTED_RESERVATION = Decimal("3.249558")
TRIAL_CAP = Decimal("0.440")
STAGES = {"spineforge_writer", "independent_quality", "q25"}
COMPONENTS = {
    "input_contract", "spineforge", "writer", "independent_quality",
    "english_master", "real_q25", "final_read_only_state", "prompt_bundle",
    "model_runtime_profile", "quality_policy", "cost_and_retry_policy"
}
LOCKED_TRUE = (
    "freeze_before_baseline", "baseline_configuration_immutable",
    "no_mid_cohort_quality_fix", "no_per_story_prompt_override",
    "no_manual_prose_edit", "no_failed_story_model_retry",
    "all_ten_attempts_required_for_analysis", "matched_identical_inputs_on_v1_1",
    "blind_quality_review", "separate_unseen_holdout",
    "provider_unknown_charge_fail_closed", "production_state_write_forbidden"
)


def must(ok, reason):
    if not ok:
        raise HarnessStop("FROZEN_COHORT_STOP_" + reason)


def unique_json(pairs):
    out = {}
    for key, value in pairs:
        must(key not in out, "DUPLICATE_JSON_KEY")
        out[key] = value
    return out


def usd(s):
    must(type(s) is str and len(s) <= 24, "INVALID_CURRENCY")
    try:
        n = Decimal(s)
    except InvalidOperation as exc:
        raise HarnessStop("FROZEN_COHORT_STOP_INVALID_CURRENCY") from exc
    must(n.is_finite() and n >= 0 and n.as_tuple().exponent >= -6,
         "INVALID_CURRENCY")
    return n


def digest(data):
    return hashlib.sha256(data).hexdigest()


def preflight(root="."):
    root = Path(root)
    p = root / POLICY_FILE
    must(p.is_file() and not p.is_symlink() and p.stat().st_size < 20000,
         "MISSING_POLICY")
    raw = p.read_bytes()
    policy = json.loads(raw, object_pairs_hook=unique_json)
    must(type(policy) is dict and policy.get("schema") == SCHEMA, "SCHEMA")
    must(policy.get("status") == "PREPARED_NOT_FROZEN", "PREMATURE_FREEZE")
    must(policy.get("source_case_matrix") ==
         "configs/story_harness_p415_benchmark.json", "CHANGED_INPUT_MATRIX")
    must(all(type(policy.get(k)) is int and policy[k] == 10 for k in (
         "baseline_cases", "paired_regression_cases", "unseen_holdout_cases_planned")),
         "CHANGED_COHORT_COUNT")
    must(policy.get("target_success_rate") == "0.90", "LOWERED_TARGET")
    must(all(policy.get(k) is True for k in LOCKED_TRUE), "WEAKENED_FREEZE_RULE")
    must(type(policy.get("paid_calls_authorized")) is int and
         policy["paid_calls_authorized"] == 0, "PAID_GRANT_NOT_AUTHORIZED")
    components = policy.get("required_frozen_components")
    must(type(components) is list and len(components) == 11 and
         set(components) == COMPONENTS, "MISSING_FROZEN_COMPONENT")
    per_stage = policy.get("per_stage_reservation_usd")
    must(type(per_stage) is dict and set(per_stage) == STAGES, "STAGE_POLICY")
    must(usd(policy.get("global_aggregate_budget_usd")) == CAP and
         usd(policy.get("last_documented_prior_conservative_reservation_usd")) ==
         DOCUMENTED_RESERVATION and
         usd(policy.get("indicative_full_trial_reserve_usd")) == TRIAL_CAP and
         sum((usd(x) for x in per_stage.values()), Decimal("0")) ==
         TRIAL_CAP, "BUDGET_POLICY")
    must(DOCUMENTED_RESERVATION + 30 * TRIAL_CAP <= CAP, "ENVELOPE_EXCEEDS_CAP")
    old_plan = load_plan(root)  # Old public benchmark stays $10/unchanged.
    cases = old_plan["cases"]
    must(len(cases) == 10 and tuple(x["id"] for x in cases) == IDS and
         Counter(x["input"]["reader_age"] for x in cases) == AGES,
         "CASE_MATRIX_CHANGED")
    case_sha = {x["id"]: case_fingerprint(x) for x in cases}
    must(len(set(case_sha.values())) == 10, "DUPLICATE_CASE")
    return {
        "schema": SCHEMA,
        "status": "PREPARED_NOT_FROZEN",
        "policy_sha256": digest(raw),
        "case_matrix_sha256": digest((root / policy["source_case_matrix"]).read_bytes()),
        "case_input_sha256": case_sha,
        "baseline_trials": 10,
        "same_input_regression_trials": 10,
        "planned_unseen_holdout_trials": 10,
        "full_new_trial_reserve_usd": str(TRIAL_CAP),
        "global_user_ceiling_usd": str(CAP),
        "historical_reservation_floor_usd": str(DOCUMENTED_RESERVATION),
        "baseline_and_regression_maximum_reserve_usd": str(20 * TRIAL_CAP),
        "holdout_maximum_reserve_usd": str(10 * TRIAL_CAP),
        "illustrative_total_conservative_reserve_usd": str(DOCUMENTED_RESERVATION + 30 * TRIAL_CAP),
        "illustrative_headroom_usd": str(CAP - DOCUMENTED_RESERVATION - 30 * TRIAL_CAP),
        "live_provider_ledger_reconciliation_required": True,
        "paid_calls_authorized": 0,
        "cohort_frozen": False,
        "production_write_authorized": False,
    }


def verify_attempt_seal(lock, attempt, input_sha):
    """Reusable fail-closed contract for future cohort executor.

    BASELINE and PAIRED_REGRESSION require independently sealed locks, pinned
    to separate harness revisions, but the *same input hashes*. A successful
    preflight does not seal them or authorize inference.
    """
    must(type(lock) is dict and type(attempt) is dict and
         type(input_sha) is dict and set(input_sha) == set(IDS), "BAD_LOCK")
    must(lock.get("status") == "SEALED", "UNSEALED")
    sha = lock.get("harness_commit")
    must(type(sha) is str and len(sha) == 40 and
         all(c in "0123456789abcdef" for c in sha), "INVALID_COMMIT")
    expected = lock.get("component_sha256")
    must(type(expected) is dict and set(expected) == COMPONENTS and
         all(type(v) is str and len(v) == 64 and
             all(c in "0123456789abcdef" for c in v) for v in expected.values()),
         "INVALID_COMPONENT_DIGESTS")
    ident = attempt.get("case_id")
    must(ident in IDS, "BAD_CASE_ID")
    must(attempt.get("harness_commit") == sha and
         attempt.get("component_sha256") == expected, "CHANGED_HARNESS")
    must(attempt.get("input_sha256") == input_sha[ident], "CHANGED_INPUT")
    must(attempt.get("round") == lock.get("round") and
         lock.get("round") in ("BASELINE", "PAIRED_REGRESSION"), "CHANGED_ROUND")
    must(type(attempt.get("manual_prose_edits")) is int and
         attempt["manual_prose_edits"] == 0 and
         attempt.get("automatic_quality_retry") is False, "MANUAL_OR_RETRY")


def round_coverage(rows, name):
    """Count attempted cases only, never promote self-reported ACCEPT to truth."""
    must(name in ("BASELINE", "PAIRED_REGRESSION"), "ROUND")
    must(type(rows) is list and len(rows) <= 10, "ROW_COUNT")
    allowed = {"ACCEPT_CLAIMED", "REJECT", "STOP_UNKNOWN_OR_INVALID",
               "OPERATIONAL_STOP"}
    seen = set()
    counts = Counter()
    for row in rows:
        must(type(row) is dict and
             set(row) == {"case_id", "round", "status"}, "BAD_ROW")
        ident = row["case_id"]
        must(ident in IDS and ident not in seen and
             row["round"] == name and row["status"] in allowed,
             "WRONG_ATTEMPT")
        seen.add(ident)
        counts[row["status"]] += 1
    complete = len(seen) == 10
    return {
        "round": name,
        "attempt_records": len(seen),
        "missing_case_ids": [x for x in IDS if x not in seen],
        "all_attempts_recorded": complete,
        "root_cause_review_permitted": complete,
        "unverified_accept_claims": counts["ACCEPT_CLAIMED"],
        "quality_rejections": counts["REJECT"],
        "unknown_or_operational_stops":
            counts["STOP_UNKNOWN_OR_INVALID"] + counts["OPERATIONAL_STOP"],
        "independent_success_rate_certified": False,
    }


if __name__ == "__main__":
    print(json.dumps(preflight(), ensure_ascii=False, sort_keys=True))
