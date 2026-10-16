"""v0.27 real composed lab pipeline (synthetic billable transport)."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import prose_hash
from experiments.sera.tests.test_ordered_facets_v027 import (
    SOURCE, SCENE, KINDS, EFFECTS, NAMES, material,
)
from experiments.sera.tests.test_world_state_v02 import base
from experiments.sera.tests.test_relation_knowledge_v025 import ALIASES, FACTS


def model(calls):
    typed = material()[4]
    def call(*, key, model, prepared):
        req = prepared["request"]
        assert all(x not in json.dumps(req) for x in (
            "max_tokens", "max_output_tokens", "max_completion_tokens",
            "max_new_tokens",
        ))
        user = json.loads(req["messages"][1]["content"])
        calls.append(model)
        if "target_sentences" in user:
            rows = []
            for s in user["target_sentences"]:
                n = next(i for i, part in enumerate(SOURCE.split(". "))
                         if s["quote"].startswith(part.rstrip(".")))
                quote = s["quote"]
                if n in (0,1):
                    refs = [NAMES[n]]
                    aliases = [(NAMES[n], "Vane" if n == 0 else "Mara")]
                elif n == 2:
                    refs = ["vane", "mara", "vane_watch"]
                    aliases = [("vane","Vane"),("mara","Mara"),
                               ("vane_watch","watch")]
                elif n in (3,4):
                    refs = ["mara", "vane_watch"]
                    aliases = [("mara","Mara"),("vane_watch","watch")]
                elif n == 5:
                    refs = ["mara", "mara_notebook"]
                    aliases = [("mara","Mara"),
                               ("mara_notebook","notebook")]
                else:
                    refs = ["mara"]
                    aliases = [("mara","Mara")]
                rows.append({
                    "sentence_id": s["id"],
                    "disposition": "STATE_EVENT",
                    "reason": "Independent original source binding",
                    "mentions": [{
                        "entity_ref": eid, "role": "PRESENT",
                        "evidence_quote": name, "occurrence": 0,
                    } for eid, name in aliases],
                    "events": [{
                        "kind": KINDS[n], "epistemic": "OBSERVED_ACTION",
                        "effect": EFFECTS[n],
                        "evidence_quote": quote.rstrip("."),
                        "occurrence": 0, "entity_refs": refs,
                        "reason": "Source-grounded unverified candidate",
                    }],
                })
            body = {"rows": rows}
        elif "original_prose" in user:
            body = {"typed_candidates": deepcopy(typed)}
        else:
            source = user.get("exact_chronological_sentences") or []
            body = {
                "verdict": "STATE_OBSERVATION", "operation_kind": "OBSERVE",
                "effect": "UNKNOWN",
                "evidence_quote": source[0]["quote"] if source else SOURCE[:4],
                "reason": "Independent conservative risk reply",
            }
        return {"error": None, "raw": {
            "id": f"fake-v027-{len(calls)}", "model": model,
            "usage": {"cost": "0.001"},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(body)},
            }],
        }}
    return call


def clock(*, prose, world, extraction_report):
    rows = sorted(extraction_report["candidate_events"],
                  key=lambda r: r["start"])
    return {
        "entry": deepcopy(world), "scene_key": SCENE,
        "scene_window": {
            "scene_key": SCENE, "entry_revision": world["revision"],
            "earliest_minute": 135, "latest_minute": 175,
        },
        "events": [{
            "event_id": row["event_id"], "ordinal": idx+1,
            "actor_id": (
                "vane" if row["kind"] == "TRANSFER"
                else "vane" if row["quote"].startswith("Vane")
                else "mara"
            ),
            "kind": "MOVEMENT" if row["kind"] == "MOVE" else "ACTION",
            "to_location": "archive" if row["kind"] == "MOVE" else None,
            "earliest_minute": None, "latest_minute": None,
            "exact_minute": None, "depends_on": [],
        } for idx,row in enumerate(rows)],
        "travel_minutes": {"station->archive": 10},
    }


def relations(*, prose, world, extraction_report, verified=True):
    events = sorted(extraction_report["candidate_events"],
                    key=lambda row: row["start"])
    specs = []
    for e in events:
        if e["kind"] == "TRANSFER":
            specs.append({
                "source_event_id": e["event_id"],
                "operation": "TRANSFER_HOLDER",
                "object_id": "vane_watch", "from_id": "vane",
                "to_id": "mara", "fact_id": None,
            })
        elif e["kind"] == "KNOWLEDGE_UPDATE":
            specs.append({
                "source_event_id": e["event_id"],
                "operation": "LEARN_FACT", "object_id": None,
                "from_id": None, "to_id": "mara",
                "fact_id": "station_clock_stopped",
            })
    facts = deepcopy(FACTS)
    if not verified:
        facts["station_clock_stopped"]["truth_status"] = "RUMORED"
    return {
        "entry": deepcopy(world), "policy_id": "application-facts-v027",
        "registered_aliases": deepcopy(ALIASES),
        "verified_fact_registry": facts, "transitions": specs,
    }


def invoke(root, provider, *, verified=True):
    def knowledge(**kwargs):
        return relations(**kwargs, verified=verified)
    return run(
        prose=SOURCE, world=base(), scene_key=SCENE, work_root=root,
        api_key="synthetic", provider_call=provider, max_rewrites=0,
        registry={
            "vane": ["Vane"], "mara": ["Mara"],
            "vane_watch": ["watch"], "mara_notebook": ["notebook"],
        }, candidate_lexicon={},
        typed_registry={
            "openables": ["vane_watch"],
            "documents": ["mara_notebook"],
        },
        writer_model="synthetic/unused-writer",
        sweep_model="synthetic/source-blind",
        semantic_model="synthetic/risk-blind",
        facet_model="synthetic/facet-blind",
        trusted_temporal_builder=clock,
        temporal_policy_id="app-station-archive-v027",
        trusted_relation_builder=knowledge,
        relation_policy_id="application-facts-v027",
    )


class FullStagedV027Tests(unittest.TestCase):
    def test_model_to_evidence_to_ordered_facets_with_durable_restart(self):
        calls = []
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "job"
            first = invoke(root, model(calls))
            evidence = list((root/"evidence").glob("*.json"))
            cached = invoke(root, lambda **kw: self.fail(
                "Already receipted model invoked twice"
            ))
        self.assertEqual(first, cached)
        self.assertEqual(first["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL", first)
        self.assertEqual(first["rewrite_count"], 0)
        self.assertEqual(len(evidence), 1)
        self.assertGreaterEqual(len(calls), 3)
        self.assertFalse(first["canonical_commit_authorized"])
        self.assertEqual(first["world_db_writes"], 0)

    def test_unverified_application_fact_cannot_become_known_world_truth(self):
        with TemporaryDirectory() as tmp:
            result = invoke(Path(tmp)/"job", model([]), verified=False)
        self.assertEqual(result["status"], "FAILED_SAFE_FINAL")
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertFalse(result["requires_manual_intervention"])


if __name__ == "__main__":
    unittest.main()
