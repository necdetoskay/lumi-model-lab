from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE = Path("experiments/fixtures/story_context_selection_proof_20260926.json")
RAW = Path("experiments/fixtures/story_context_selection_hybrid_raw_evidence_36264952721.json")
OUT = Path("runs/story-context-selection-hybrid-policy-proof/result.json")


def relation_entity(fid: str) -> str | None:
    if not fid.startswith("relationship."):
        return None
    suffix = fid.split(".", 1)[1]
    return suffix.split("_", 1)[0]


def apply_policy(intent: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    refs = intent["story_intent"]["references"]
    direct_ids = set(refs["required_fact_ids"]) | set(refs["hard_guard_fact_ids"])
    direct_relation_entities = {
        relation_entity(fid)
        for fid in direct_ids
        if relation_entity(fid) is not None
    }

    raw_selected = list(run["selected_enrichment_ids"])
    review = set(run["review_enrichment_ids"])
    auto = []
    demoted = []

    for fid in raw_selected:
        entity = relation_entity(fid)
        if entity is not None and entity not in direct_relation_entities:
            demoted.append(fid)
            review.add(fid)
        else:
            auto.append(fid)

    return {
        "deterministic_core_ids": run["deterministic_core_ids"],
        "raw_selected_enrichment_ids": sorted(raw_selected),
        "policy_demoted_ids": sorted(demoted),
        "selected_enrichment_ids": sorted(auto),
        "review_enrichment_ids": sorted(review),
    }


def score(fixture: dict[str, Any], intent: dict[str, Any], run: dict[str, Any]) -> dict[str, Any]:
    gold = intent["gold"]
    final_ids = set(run["deterministic_core_ids"]) | set(run["selected_enrichment_ids"])
    selected = set(run["selected_enrichment_ids"])
    forbidden = {x["id"] for x in fixture["forbidden"]}

    missing_must = sorted(set(gold["must_select"]) - final_ids)
    selected_must_not = sorted(set(gold["must_not_select"]) & selected)
    forbidden_leak = sorted(forbidden & final_ids)
    useful_hits = sorted(set(gold["useful_select_any"]) & selected)

    return {
        "missing_must_select": missing_must,
        "selected_must_not_select": selected_must_not,
        "forbidden_leak": forbidden_leak,
        "useful_auto_hits": useful_hits,
        "pass": not missing_must and not selected_must_not and not forbidden_leak,
    }


def main():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    intent_map = {x["id"]: x for x in fixture["intents"]}

    results = []
    for source in raw["results"]:
        intent = intent_map[source["intent_id"]]
        run_1 = apply_policy(intent, source["run_1"])
        run_2 = apply_policy(intent, source["run_2"])
        score_1 = score(fixture, intent, run_1)
        score_2 = score(fixture, intent, run_2)
        stable = run_1["selected_enrichment_ids"] == run_2["selected_enrichment_ids"]

        results.append({
            "intent_id": source["intent_id"],
            "run_1": run_1,
            "run_2": run_2,
            "run_1_score": score_1,
            "run_2_score": score_2,
            "same_selected_enrichment": stable,
            "pass": score_1["pass"] and score_2["pass"] and stable,
        })

    packets = {
        row["intent_id"]: tuple(row["run_1"]["deterministic_core_ids"] + row["run_1"]["selected_enrichment_ids"])
        for row in results
    }
    differentiated = len(set(packets.values())) == len(packets)
    qualification_pass = all(x["pass"] for x in results) and differentiated

    result = {
        "schema_version": "story-context-selection-hybrid-policy-proof-result.v1",
        "source_run_id": raw["source_run_id"],
        "model_calls": 0,
        "policy": {
            "always_required": "deterministic",
            "direct_story_refs": "deterministic",
            "hard_guards": "deterministic",
            "forbidden": "removed before JEV",
            "soft_enrichment": "JEV advisory",
            "relationship_entity_expansion": "AUTO only if that relationship entity is directly referenced; otherwise demote to REVIEW",
            "review_sent_to_planner": False,
        },
        "summary": {
            "intent_count": len(results),
            "passes": sum(1 for x in results if x["pass"]),
            "failures": sum(1 for x in results if not x["pass"]),
            "packets_differentiated": differentiated,
            "qualification_pass": qualification_pass,
        },
        "results": results,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
