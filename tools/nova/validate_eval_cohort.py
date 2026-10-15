#!/usr/bin/env python3
"""Preflight the 12 NOVA A/B scenario fixtures. NOT a paid generation runner."""
import collections
import json
import sys
from pathlib import Path

from validate_cross_media import check as check_corpus

ROOT = Path(__file__).resolve().parents[2]
COHORT = ROOT / "data/nova/v0.2/EVAL_COHORT_12.json"
MECH = ROOT / "data/nova/v0.2/mechanisms.jsonl"


def validate():
    errors = []
    def must(condition, msg):
        if not condition:
            errors.append(msg)

    corpus = check_corpus()
    must(corpus["status"] == "PASS", "NOVA v0.2 canonical dataset is not green")
    p = json.loads(COHORT.read_text(encoding="utf8"))
    scenario = p.get("scenarios", [])
    ids = {json.loads(line)["mechanic_id"] for line in MECH.read_text(encoding="utf8").splitlines() if line.strip()}
    must(p.get("cohort_id") == "NOVA-CROSSMEDIA-A-B-12", "Cohort ID mismatch")
    must(p.get("status") == "DESIGNED_NOT_EXECUTED", "Unsafe cohort state")
    must(p.get("story_quality_trials_completed") == 0, "No real trials have run")
    must(p.get("planned_story_quality_pairs") == 12, "Expected 12 A/B pairs")
    must(p.get("planned_story_outputs") == 24, "Expected 24 separate stories")
    must(p.get("paid_calls_authorized") is False, "Paid calls not authorized")
    must(p.get("requires_explicit_api_budget_and_freeze_confirmation") is True, "Missing execution freeze boundary")
    must(len(scenario) == 12, "Fixture count != 12")
    must([s.get("scenario_id") for s in scenario] ==
         [f"NOVA-AB-{n:02d}" for n in range(1, 13)], "Scenario IDs not exactly ordered")
    ages = collections.Counter(s.get("target_age_years") for s in scenario)
    must(ages == {4:3, 10:3, 25:3, 40:3}, "Age cohort not balanced")
    for s in scenario:
        ident = s.get("scenario_id", "missing")
        must(s.get("schema_version") == "0.2.0", f"{ident}: version mismatch")
        must(s.get("target_words") in {520, 760, 1000, 1150}, f"{ident}: word range malformed")
        mech_ids = s.get("eligible_mechanic_ids", [])
        must(len(mech_ids) == 2 and len(set(mech_ids)) == 2 and set(mech_ids).issubset(ids),
             f"{ident}: unknown/duplicate mechanic IDs")
        must(s.get("baseline_condition") == "A_NO_NOVA" and
             s.get("experimental_condition") == "B_NOVA_CANDIDATE_ONLY",
             f"{ident}: invalid A/B framing")
        must(s.get("source_copy_prohibited") is True, f"{ident}: source copy firewall")
        must(s.get("model_and_quality_settings_must_be_frozen") is True,
             f"{ident}: model and quality freeze absent")
        must(s.get("paid_execution_status") == "NOT_RUN", f"{ident}: false executed claim")
        must(s.get("no_quality_claim") is True, f"{ident}: fake quality claim")
        for key in ("seed_story_tr", "protagonist_initial_knowledge_tr", "world_truth_tr",
                    "evaluation_focus_tr", "safety_and_continuity_guardrail_tr"):
            must(len(s.get(key, "")) > 60, f"{ident}: missing {key} details")
    return {
        "status": "PASS" if not errors else "FAIL",
        "kind": "OFFLINE_EVAL_COHORT_PREFLIGHT_NOT_A_STORY_TRIAL",
        "scenario_fixtures": len(scenario),
        "age_tiers": dict(sorted(ages.items())),
        "selected_nova_mechanics": len({m for s in scenario for m in s["eligible_mechanic_ids"]}),
        "paired_story_quality_trials_completed": p["story_quality_trials_completed"],
        "paid_api_calls": 0,
        "story_harness_or_production_changes": False,
        "errors": errors,
    }


if __name__ == "__main__":
    try:
        result = validate()
    except Exception as exc:
        result = {"status":"FAIL","fatal":str(exc)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
