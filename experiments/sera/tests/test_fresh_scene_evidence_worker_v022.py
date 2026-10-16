"""SERA v0.22 end-to-end fresh-source evidence worker — zero real billing."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.artifact_scene_checker_v021 import create_checker
from experiments.sera.coverage import prose_hash
from experiments.sera.fresh_scene_evidence_worker_v022 import create_preparer
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.unattended_scene_rewrite_v020 import execute as scene_loop
from experiments.sera.world_state_v02 import (
    entity_template, environment_template, initial_state,
)

SOURCE_1 = "Ari looked at the box. Ari closed the box."
SOURCE_2 = "Ari saw the box open. Ari closed the box."
EXTRACT = "synthetic/sweep-independent"
SEMANTIC = "synthetic/semantic-independent"
TYPED = "synthetic/typed-independent"
MODELS = [EXTRACT, SEMANTIC, TYPED]


def entry():
    return initial_state(
        minute=0,
        entities={
            "ari": entity_template("ari", "CHARACTER", "hall"),
            "box": entity_template("box", "OBJECT", "hall"),
        },
        regions={"hall": environment_template(
            "UNKNOWN", last_change_minute=0,
        )},
    )


def fake_model(calls, *, tamper_typed=False, error_mode=False):
    def provider(*, key, model, prepared):
        req = prepared["request"]
        for forbidden in (
            "max_tokens", "max_output_tokens", "max_completion_tokens",
            "max_generation_tokens", "max_new_tokens",
        ):
            assert forbidden not in json.dumps(req)
        user = json.loads(req["messages"][1]["content"])
        calls.append((model, deepcopy(user)))
        if error_mode:
            return {"error": "HTTP_502", "raw": None}
        if "target_sentences" in user:
            rows = []
            for s in user["target_sentences"]:
                sentence = s["quote"]
                mentions = [
                    {"entity_ref": "ari", "role": "PRESENT",
                     "evidence_quote": "Ari", "occurrence": 0},
                    {"entity_ref": "box", "role": "PRESENT",
                     "evidence_quote": "box", "occurrence": 0},
                ]
                if "closed" in sentence:
                    kind, effect, quote = "CLOSE", "OBJECT", "closed the box"
                elif "box open" in sentence:
                    kind, effect, quote = "OBSERVE", "NONE", "box open"
                else:
                    kind, effect, quote = None, None, None
                events = ([{
                    "kind": kind, "epistemic": "OBSERVED_ACTION",
                    "effect": effect, "evidence_quote": quote, "occurrence": 0,
                    "entity_refs": ["box"],
                    "reason": "Synthetic blinded source event",
                }] if kind else [])
                rows.append({
                    "sentence_id": s["id"],
                    "disposition": "STATE_EVENT" if events else
                                   "NO_TRACKED_CHANGE",
                    "reason": "Complete source-independent sentence row",
                    "mentions": mentions, "events": events,
                })
            content = {"rows": rows}
        elif "original_prose" in user:
            prose = user["original_prose"]
            source_sentences = sentences(prose)
            candidates = []
            if "box open" in prose:
                i = prose.index("box open")
                candidates.append({
                    "event_id": "obs-box-open", "type": "OBSERVE_OPENABLE",
                    "actor_id": "ari", "object_id": "box",
                    "sentence_id": source_sentences[0]["id"],
                    "evidence": {
                        "start": i, "end": i+len("box open"),
                        "quote": "box open",
                    },
                    "payload": {"expected": "UNKNOWN", "observed": "OPEN"},
                })
            i = prose.index("closed the box")
            candidates.append({
                "event_id": "close-box", "type": "SET_OPENABLE",
                "actor_id": "ari", "object_id": "box",
                "sentence_id": source_sentences[1]["id"],
                "evidence": {
                    "start": i, "end": i+len("closed the box"),
                    "quote": ("fake forged quote" if tamper_typed
                              else "closed the box"),
                },
                "payload": {"expected": "OPEN", "next": "CLOSED"},
            })
            content = {"typed_candidates": candidates}
        else:
            # If any semantic finding actually needs a probe, answer from
            # exact source only; no previous extractor answer is fed back.
            content = {
                "verdict": "STATE_OBSERVATION",
                "operation_kind": "OBSERVE",
                "effect": "UNKNOWN",
                "evidence_quote": user["exact_chronological_sentences"][-1]
                                      ["quote"][:8],
                "reason": "Synthetic independent conservative uncertainty",
            }
        reply = {
            "id": f"mock-{len(calls)}", "model": model,
            "usage": {"cost": "0.001"},
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps(content)},
            }],
        }
        return {"error": None, "raw": reply}
    return provider


def preparer(root, provider, *, spend="0.30", scene="simple"):
    return create_preparer(
        evidence_root=root/"evidence", work_root=root/"jobs",
        scene_key=scene, registry={"ari": ["Ari"], "box": ["box"]},
        candidate_lexicon={},
        typed_registry={"openables": ["box"], "documents": []},
        api_key="fake-key", extraction_model=EXTRACT,
        semantic_model=SEMANTIC, typed_model=TYPED,
        provider_call=provider, observed_spend_guard_usd=spend,
    )


class FreshEvidenceWorkerV022Tests(unittest.TestCase):
    def test_two_revisions_generate_distinct_source_and_world_bound_evidence(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            calls = []
            prepare = preparer(root, fake_model(calls))
            first = prepare(prose=SOURCE_1, world=entry())
            second = prepare(prose=SOURCE_2, world=entry())
            self.assertEqual(first["status"], "EVIDENCE_READY_NONCANONICAL")
            self.assertEqual(second["status"], "EVIDENCE_READY_NONCANONICAL")
            self.assertNotEqual(first["prose_sha256"], second["prose_sha256"])
            self.assertTrue((root/"evidence"/
                             (prose_hash(SOURCE_1)+".json")).exists())
            self.assertTrue((root/"evidence"/
                             (prose_hash(SOURCE_2)+".json")).exists())
            self.assertFalse(first["canonical_commit_authorized"])
            self.assertEqual(second["world_db_writes"], 0)

    def test_v020_loop_autonomously_rewrites_then_reextracts_and_validates(self):
        calls = []
        edits = []
        def rewrite(*, source, defects):
            edits.append(deepcopy(defects))
            return {
                "prose": SOURCE_2,
                "receipt": {
                    "source_prose_sha256": prose_hash(source),
                    "response_id": "mock-paid-writer", "model": "mock-writer",
                    "finish_reason": "stop", "cost_usd": "0.001",
                },
            }
        with TemporaryDirectory() as d:
            root = Path(d)
            prepare = preparer(root, fake_model(calls))
            out = scene_loop(
                prose=SOURCE_1, world=entry(),
                prepare_evidence=prepare,
                evidence_policy_id="v022-synthetic-integration-1",
                check_scene=create_checker(evidence_root=root/"evidence"),
                rewrite_scene=rewrite, output_dir=root/"scene",
                max_rewrites=2,
            )
            replay = scene_loop(
                prose=SOURCE_1, world=entry(),
                prepare_evidence=prepare,
                evidence_policy_id="v022-synthetic-integration-1",
                check_scene=create_checker(evidence_root=root/"evidence"),
                rewrite_scene=rewrite, output_dir=root/"scene",
                max_rewrites=2,
            )
            evidence_files = list((root/"evidence").glob("*.json"))
        self.assertEqual(replay, out)
        self.assertEqual(out["status"], "SCENE_CANDIDATE_READY_NONCANONICAL")
        self.assertEqual(out["rewrite_count"], 1)
        self.assertEqual(len(edits), 1)
        self.assertEqual(len(evidence_files), 2)
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["world_db_writes"], 0)

    def test_replay_completed_paid_responses_without_any_new_api_calls(self):
        calls = []
        with TemporaryDirectory() as d:
            root=Path(d)
            first=preparer(root,fake_model(calls))(
                prose=SOURCE_2,world=entry())
            count=len(calls)
            second=preparer(root,lambda **kwargs: self.fail(
                "Provider should not be contacted on replay"
            ))(prose=SOURCE_2,world=entry())
        self.assertEqual(first,second)
        self.assertGreater(count,0)

    def test_unreceived_provider_charge_blocks_a_second_request(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)
            prepare=preparer(root,fake_model(calls,error_mode=True))
            first=prepare(prose=SOURCE_1,world=entry())
            self.assertEqual(first["status"],"FAILED_SAFE_FINAL")
            # Even after an interrupted final outcome, the started receipt
            # is intact: no second possibly billed request is initiated.
            list((root/"jobs").glob("*/final.json"))[0].unlink()
            again=prepare(prose=SOURCE_1,world=entry())
            self.assertEqual(again["status"],"FAILED_SAFE_FINAL")
        self.assertEqual(len(calls),1)
        self.assertIn("V021_UNCONFIRMED_IN_FLIGHT_PROVIDER_CALL",
                      again["failure_code"])

    def test_model_forged_exact_quote_fails_without_world_write(self):
        calls=[]
        with TemporaryDirectory() as d:
            out=preparer(Path(d),fake_model(calls,tamper_typed=True))(
                prose=SOURCE_2,world=entry())
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertIn("V022_TYPED_EVENT_SOURCE_INVALID",out["failure_code"])
        self.assertEqual(out["world_db_writes"],0)

    def test_world_revision_source_registry_are_not_reused_as_old_proof(self):
        calls=[]
        with TemporaryDirectory() as d:
            root=Path(d)
            worker=preparer(root,fake_model(calls))
            first=worker(prose=SOURCE_2,world=entry())
            changed=entry()
            changed["revision"]=1
            other=worker(prose=SOURCE_2,world=changed)
        self.assertEqual(first["status"],"EVIDENCE_READY_NONCANONICAL")
        self.assertEqual(other["status"],"FAILED_SAFE_FINAL")
        self.assertIn("V022_DIFFERENT_PROOF_FOR_SAME_SOURCE",
                      other["failure_code"])

    def test_no_output_token_cap_and_usd_guard_prevents_second_paid_call(self):
        calls=[]
        with TemporaryDirectory() as d:
            out=preparer(Path(d),fake_model(calls),spend="0.0005")(
                prose=SOURCE_2,world=entry())
        self.assertEqual(len(calls),1)
        self.assertEqual(out["status"],"FAILED_SAFE_FINAL")
        self.assertIn("V022_CALL_OR_SPEND_GUARD",out["failure_code"])


if __name__=="__main__":
    unittest.main()
