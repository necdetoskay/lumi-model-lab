"""v0.25 composed lab worker: independent source extraction and app fact policy."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.composed_scene_runner_v023 import run
from experiments.sera.coverage import prose_hash
from experiments.sera.tests.test_relation_knowledge_v025 import (
    SOURCE, ALIASES, FACTS,
)
from experiments.sera.tests.test_world_state_v02 import base

SCENE = "transfer-and-verified-fact-v025"
POLICY = "trusted-fact-and-identity-registry-v1"


def trusted_builder(*, prose, world, extraction_report, facts=None):
    events = sorted(extraction_report["candidate_events"],
                    key=lambda e: e["start"])
    specs = []
    for row in events:
        if row["kind"] == "TRANSFER":
            specs.append({
                "source_event_id": row["event_id"],
                "operation": "TRANSFER_HOLDER",
                "object_id": "vane_watch", "from_id": "vane",
                "to_id": "mara", "fact_id": None,
            })
        if row["kind"] == "KNOWLEDGE_UPDATE":
            specs.append({
                "source_event_id": row["event_id"],
                "operation": "LEARN_FACT",
                "object_id": None, "from_id": None,
                "to_id": "mara", "fact_id": "station_clock_stopped",
            })
    return {
        "entry": deepcopy(world), "policy_id": POLICY,
        "registered_aliases": deepcopy(ALIASES),
        "verified_fact_registry": deepcopy(FACTS if facts is None else facts),
        "transitions": specs,
    }


def provider_fixture(log):
    def provider(*, key, model, prepared):
        request=prepared["request"]
        for limit in ("max_tokens", "max_output_tokens",
                      "max_completion_tokens", "max_new_tokens"):
            assert limit not in json.dumps(request)
        packet=json.loads(request["messages"][1]["content"])
        log.append((model,deepcopy(packet)))
        if "target_sentences" in packet:
            rows=[]
            for sentence in packet["target_sentences"]:
                first="handed" in sentence["quote"]
                if first:
                    mentions = [
                        {"entity_ref": "vane", "role": "PRESENT",
                         "evidence_quote": "Vane", "occurrence": 0},
                        {"entity_ref": "mara", "role": "PRESENT",
                         "evidence_quote": "Mara", "occurrence": 0},
                        {"entity_ref": "vane_watch", "role": "PRESENT",
                         "evidence_quote": "watch", "occurrence": 0},
                    ]
                    kind,effect,quote = "TRANSFER","OBJECT","handed the watch"
                    refs=["vane","vane_watch","mara"]
                else:
                    mentions = [{"entity_ref":"mara","role":"PRESENT",
                                 "evidence_quote":"Mara","occurrence":0}]
                    kind,effect,quote = (
                        "KNOWLEDGE_UPDATE","CHARACTER_KNOWLEDGE",
                        "learned the station clock stopped",
                    )
                    refs=["mara"]
                rows.append({
                    "sentence_id": sentence["id"], "disposition":"STATE_EVENT",
                    "reason":"Independent source-grounded synthetic event",
                    "mentions":mentions,
                    "events":[{"kind":kind,"effect":effect,
                               "epistemic":"OBSERVED_ACTION",
                               "evidence_quote":quote,"occurrence":0,
                               "entity_refs":refs,
                               "reason":"source grounded synthetic"}],
                })
            payload={"rows":rows}
        elif "original_prose" in packet:
            payload={"typed_candidates":[]}
        else:
            # Conservative, independent semantic probe (only when requested).
            lines=packet.get("exact_chronological_sentences",[])
            payload={"verdict":"STATE_OBSERVATION",
                     "operation_kind":"OBSERVE","effect":"UNKNOWN",
                     "evidence_quote":lines[0]["quote"] if lines else SOURCE[:8],
                     "reason":"synthetic uncertainty"}
        return {"error":None,"raw":{
            "id":f"v025-{len(log)}","model":model,
            "usage":{"cost":"0.001"},
            "choices":[{"finish_reason":"stop",
                        "message":{"content":json.dumps(payload)}}],
        }}
    return provider


def invoke(root, provider, *, facts=None, policy_id=POLICY):
    def builder(**kwargs):
        return trusted_builder(**kwargs, facts=facts)
    return run(
        prose=SOURCE, world=base(), scene_key=SCENE, work_root=root,
        api_key="synthetic", provider_call=provider,
        registry={"vane":["Vane"],"mara":["Mara"],
                  "vane_watch":["watch"]},
        candidate_lexicon={},
        typed_registry={"openables":[],"documents":[]},
        writer_model="synthetic/unused-writer",
        sweep_model="synthetic/source-sweep",
        semantic_model="synthetic/independent-risk",
        facet_model="synthetic/typed-facet",
        max_rewrites=0,
        trusted_relation_builder=builder, relation_policy_id=policy_id,
    )


class ComposedTransferKnowledgeV025Tests(unittest.TestCase):
    def test_automatic_end_to_end_sweep_full_gate_for_registered_relation_and_fact(self):
        log=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"story"
            answer=invoke(root,provider_fixture(log))
            evidence_path=root/"evidence"/(prose_hash(SOURCE)+".json")
            evidence=json.loads(evidence_path.read_text(encoding="utf-8"))
            replay=invoke(root,lambda **kwargs:self.fail("duplicate charge"))
        self.assertEqual(answer, replay)
        self.assertEqual(answer["status"],
                         "SCENE_CANDIDATE_READY_NONCANONICAL", answer)
        self.assertEqual(answer["rewrite_count"],0)
        self.assertEqual(len(evidence["typed_candidates"]),0)
        self.assertEqual(len(evidence["extraction_report"]["candidate_events"]),2)
        self.assertEqual(evidence["relation_case"]["policy_id"],POLICY)
        self.assertGreaterEqual(len(log),2)
        self.assertFalse(answer["canonical_commit_authorized"])
        self.assertEqual(answer["world_db_writes"],0)

    def test_rumored_fact_yields_safe_failure_even_with_sourced_extraction(self):
        catalog=deepcopy(FACTS)
        catalog["station_clock_stopped"]["truth_status"]="RUMORED"
        with TemporaryDirectory() as d:
            answer=invoke(Path(d)/"story",provider_fixture([]),facts=catalog)
        self.assertEqual(answer["status"],"FAILED_SAFE_FINAL")
        self.assertFalse(answer["canonical_commit_authorized"])
        self.assertFalse(answer["requires_manual_intervention"])

    def test_relation_policy_id_is_immutable_on_durable_replay(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)/"story"
            invoke(root,provider_fixture(calls))
            from experiments.sera.coverage import CoverageError
            with self.assertRaisesRegex(
                CoverageError,"V020_REWRITE_RESUME_CONTRACT_MISMATCH"
            ):
                invoke(root,provider_fixture(calls),
                       policy_id="another-policy")
        self.assertGreaterEqual(len(calls),2)


if __name__=="__main__":
    unittest.main()
