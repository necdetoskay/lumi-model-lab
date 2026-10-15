"""P4.15 90%-success benchmark and 3-fix diagnosis policy (offline only).

This is NOT a story generator or a substitute for authenticated live evidence.
Offline tests prove metric arithmetic, input coverage and never-self-attest gates.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p415-diverse-e2e-benchmark.v1"
REQUIRED_CHECKS = {
    "model_generated_writer", "spine_state_grounded",
    "blocking_quality_accept", "same_story_english_master",
    "same_story_q25", "state_evidence_support",
    "reader_score_at_least_4_of_5", "no_manual_prose_edit",
}
REQUIRED_AGES = {4, 10, 12, 25, 40}
REQUIRED_AGE_COUNTS = {age: 2 for age in REQUIRED_AGES}
MAX_FIXES = 3
PUBLIC_FIXTURE = "configs/story_harness_p415_benchmark.json"
SHA = re.compile(r"^[a-f0-9]{64}$")


def _must(ok, message):
    if not ok:
        raise HarnessStop(message)


def _money(x):
    _must(type(x) is str and len(x) <= 32, "Budget must be finite decimal text")
    try:
        n = Decimal(x)
    except InvalidOperation as exc:
        raise HarnessStop("Malformed USD budget") from exc
    _must(n.is_finite() and n >= 0 and n <= Decimal("10"),
          "USD amount negative/nonfinite/above user budget")
    return n


def load_plan(repo_root="."):
    root = Path(repo_root).resolve(strict=True)
    path = root / PUBLIC_FIXTURE
    _must(path.is_file() and not path.is_symlink() and path.stat().st_size < 200000,
          "Missing/unsafe benchmark fixture")
    plan = json.loads(path.read_text(encoding="utf-8"))
    return validate_plan(plan)


def validate_plan(plan):
    _must(type(plan) is dict and plan.get("schema") == SCHEMA,
          "Wrong benchmark schema")
    _must(set(plan) == {
        "schema", "description", "target_success_rate", "minimum_pilot_cases",
        "release_holdout_cases", "global_model_budget_usd",
        "per_failure_max_same_method_fixes", "no_automatic_provider_retries",
        "required_distinct_ages", "cases",
    }, "Unexpected benchmark plan fields")
    _must(plan["target_success_rate"] == "0.90"
          and type(plan["minimum_pilot_cases"]) is int
          and plan["minimum_pilot_cases"] == 10
          and type(plan["release_holdout_cases"]) is int
          and plan["release_holdout_cases"] >= 30
          and plan["per_failure_max_same_method_fixes"] == MAX_FIXES
          and plan["no_automatic_provider_retries"] is True
          and _money(plan["global_model_budget_usd"]) == Decimal("10"),
          "Cannot weaken target, budget or no-retry policy")
    _must(type(plan["required_distinct_ages"]) is list
          and set(plan["required_distinct_ages"]) == REQUIRED_AGES
          and len(plan["required_distinct_ages"]) == 5,
          "Required age matrix modified")
    cases = plan["cases"]
    _must(type(cases) is list and len(cases) == 10,
          "Pilot must have exactly ten public diverse cases")
    ids, fingerprints, age_counts, subjects = set(), set(), Counter(), set()
    for case in cases:
        _must(type(case) is dict and set(case) == {
            "id", "split", "input", "acceptance_checks", "forbidden_state_invention"
        }, "Missing/forged case fields")
        _must(type(case["id"]) is str and
              re.fullmatch(r"B\d{2}", case["id"]) is not None and
              case["id"] not in ids and case["split"] == "pilot",
              "Duplicate/invalid pilot case")
        ids.add(case["id"])
        payload = case["input"]
        _must(type(payload) is dict and
              set(payload) == {"topic", "reader_age", "canonical_state"}
              and type(payload["topic"]) is str and
              12 <= len(payload["topic"]) <= 160 and
              payload["topic"] not in subjects,
              "Missing/duplicate creative topic")
        subjects.add(payload["topic"])
        age = payload["reader_age"]
        _must(type(age) is int and age in REQUIRED_AGES,
              "Invalid reader age")
        age_counts[age] += 1
        state = payload["canonical_state"]
        _must(type(state) is dict and
              set(state) == {"version", "world_time", "protagonist", "locations",
                             "objects", "open_obligations", "unknown_facts"}
              and state["version"] == "synthetic-canon.v1"
              and type(state["world_time"]) is int
              and state["world_time"] >= 0
              and type(state["protagonist"]) is dict
              and set(state["protagonist"]) ==
                 {"name", "location", "known_locations"}
              and type(state["locations"]) is list
              and len(state["locations"]) >= 2
              and type(state["protagonist"]["location"]) is str
              and state["protagonist"]["location"] in state["locations"]
              and type(state["open_obligations"]) is list
              and len(state["open_obligations"]) >= 2
              and type(state["objects"]) is list
              and type(state["unknown_facts"]) is list
              and len(state["unknown_facts"]) >= 1,
              "Missing synthetic Canon fields")
        _must(type(case["acceptance_checks"]) is list and
              len(case["acceptance_checks"]) == len(REQUIRED_CHECKS)
              and set(case["acceptance_checks"]) == REQUIRED_CHECKS,
              "Missing a mandatory independent quality/state gate")
        _must(type(case["forbidden_state_invention"]) is str and
              case["forbidden_state_invention"].strip(),
              "Missing non-invention constraint")
        fingerprint = hashlib.sha256(canonical_json(payload)).hexdigest()
        _must(fingerprint not in fingerprints, "Duplicate state/topic fingerprint")
        fingerprints.add(fingerprint)
    _must(age_counts == REQUIRED_AGE_COUNTS,
          "Age coverage is unbalanced")
    return plan


def case_fingerprint(case):
    _must(type(case) is dict and type(case.get("input")) is dict,
          "Missing case input")
    return hashlib.sha256(canonical_json(case["input"])).hexdigest()


def required_passes(n, *, target=Decimal("0.90")):
    _must(type(n) is int and n > 0 and n <= 10000,
          "Invalid benchmark sample size")
    _must(type(target) is Decimal and target == Decimal("0.90"),
          "Do not weaken acceptance threshold")
    return (target * n).to_integral_value(rounding="ROUND_CEILING")


def validate_failure_fix_history(history):
    """Exactly three distinct corrective hypotheses allowed per failure family.

    NOT three free API retries. Each distinct fix needs deterministic regression
    evidence before any separately budgeted model retest. After three, STOP and
    review an alternative. No autonomous strategy-switch or paid retry.
    """
    _must(type(history) is list and len(history) <= MAX_FIXES,
          "More than three same-method correction cycles forbidden")
    hypotheses = set()
    for i, item in enumerate(history, 1):
        _must(type(item) is dict
              and set(item) == {"attempt", "failure_family", "hypothesis",
                                "code_revision", "offline_regression_green",
                                "same_approach", "outcome"},
              "Incomplete fix-cycle evidence")
        h = item["hypothesis"]
        _must(item["attempt"] == i
              and type(item["failure_family"]) is str
              and item["failure_family"].strip()
              and type(h) is str and len(h.strip()) >= 8
              and h not in hypotheses
              and type(item["code_revision"]) is str
              and SHA.fullmatch(item["code_revision"]) is not None
              and item["offline_regression_green"] is True
              and item["same_approach"] is True
              and item["outcome"] in ("FIXED", "STILL_FAILING"),
              "Fix cycle lacks unique tested correction")
        hypotheses.add(h)
        if i < len(history):
            _must(item["outcome"] == "STILL_FAILING",
                  "Successful fix may not be retried")
    if not history:
        next_action = "DIAGNOSE_AND_TRY_FIX_1"
    elif history[-1]["outcome"] == "FIXED":
        next_action = "VERIFY_NO_RETRY_WITH_SEPARATE_GRANT"
    elif len(history) < MAX_FIXES:
        next_action = f"DIAGNOSE_AND_TRY_FIX_{len(history)+1}"
    else:
        next_action = "STOP_AND_REVIEW_ALTERNATIVE_METHOD"
    return {"attempts_used": len(history), "maximum_same_method_fixes": MAX_FIXES,
            "next_action": next_action, "automatic_model_retries_allowed": False}


def evaluate(plan, receipts=None, *, externally_attested=False):
    """Reports pilot coverage, NEVER an authenticated success from fixture alone.

    The future real executor must independently verify immutable artifacts,
    signed grant, provider bill/receipt and external reader assessment before
    it sets externally_attested. This offline module cannot verify those.
    """
    validate_plan(plan)
    rows = [] if receipts is None else receipts
    _must(type(rows) is list and len(rows) <= 10,
          "Invalid candidate quality evidence list")
    allowed = {c["id"]: case_fingerprint(c) for c in plan["cases"]}
    seen, provisional = set(), 0
    claimed_cost = Decimal("0")
    for row in rows:
        _must(type(row) is dict and set(row) == {
            "case_id", "input_sha256", "writer_origin",
            "quality_verdict", "master_sha256", "q25_sha256",
            "story_state_sha256", "reader_score", "manual_prose_edits",
            "actual_model_cost_usd", "evidence_kind",
        }, "Incomplete/bad benchmark receipt")
        i = row["case_id"]
        _must(i in allowed and i not in seen and
              row["input_sha256"] == allowed[i],
              "Duplicate case or state/topic substituted")
        seen.add(i)
        cost = _money(row["actual_model_cost_usd"])
        claimed_cost += cost
        _must(claimed_cost <= Decimal("10"), "User $10 aggregate ceiling crossed")
        qualified = (row["writer_origin"] == "live_model_generation"
                     and row["quality_verdict"] == "ACCEPT"
                     and all(type(row[k]) is str and
                             SHA.fullmatch(row[k]) is not None
                             for k in ("master_sha256", "q25_sha256",
                                       "story_state_sha256"))
                     and type(row["reader_score"]) is int
                     and row["reader_score"] >= 4
                     and row["manual_prose_edits"] == 0
                     and row["evidence_kind"] == "externally_verified_live")
        if qualified:
            provisional += 1
    # Caller booleans are not trusted provider/human attestation.
    # A verified runner must provide a separate cryptographic evidence link.
    return {
        "schema": "lumi.story-harness-p415-benchmark-report.v1",
        "target_success_rate": "0.90",
        "pilot_sample_size": 10,
        "required_pilot_successes": 9,
        "release_holdout_sample_size": 30,
        "required_holdout_successes": 27,
        "submitted_case_count": len(rows),
        "candidate_qualified_claims": provisional,
        "claimed_model_cost_usd": format(claimed_cost, "f"),
        "externally_attested_requested": externally_attested is True,
        "externally_verified_genuine_success_count": None,
        "verified_observed_success_rate": None,
        "ninety_percent_achieved": False,
        "status": "NOT_YET_INDEPENDENTLY_ATTESTED",
        "live_model_calls": 0,
        "actual_model_cost_verified": False,
        "no_background_paid_loop": True,
        "production_admission_authorized": False,
        "warning": "Counts of supplied receipts are claims only. Real provider and reader attestation missing.",
    }


def status(repo_root="."):
    plan = load_plan(repo_root)
    base = evaluate(plan)
    base["case_ids"] = [c["id"] for c in plan["cases"]]
    base["input_fingerprints"] = [
        case_fingerprint(c) for c in plan["cases"]
    ]
    base["frozen_budget_ceiling_usd"] = "10.00"
    base["max_corrective_fixes_per_failure"] = 3
    base["source_production_unchanged"] = True
    return base


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(json.dumps(status(args.repo_root), indent=2, sort_keys=True))
