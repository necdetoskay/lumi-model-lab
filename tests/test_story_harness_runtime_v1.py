"""Strict Harness registry and cross-case drift adversarial tests."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.story_harness_runtime_v1 import (
    create_harness, load_manifest, RuntimeHarness, PATH
)
from src.story_harness_v1 import HarnessStop
from src.story_harness_p415_benchmark import load_plan
from src.story_harness_p416_input_bridge import compile_case, build_spine_request
from src.story_harness_p417_live_pilot import wire

class HarnessRegistryTests(unittest.TestCase):
    def test_all_ten_mandatory_harness_roles_and_isolated_memory(self):
        manifests = set()
        for n in range(1, 11):
            case=f"B{n:02d}"
            run=create_harness(".",case)
            self.assertEqual(run.case_id,case)
            manifests.add(run.manifest_sha256)
            memory=run.memory_view()
            self.assertEqual(memory["canonical_state"],
                             run.pack["canonical_state"])
            memory["canonical_state"]["protagonist"]["name"]="TAMPERED"
            self.assertNotEqual(memory["canonical_state"],run.memory_view()["canonical_state"])
            self.assertEqual(run.receipt()["paid_calls_authorized"],0)
            self.assertEqual(run.invoked,[])
        self.assertEqual(len(manifests),1)

    def test_no_dynamic_tools_or_generic_model_fallback(self):
        contract,_=load_manifest()
        names={x["name"] for x in contract["tools"]["registry"]}
        self.assertEqual(len(names),9)
        self.assertFalse(contract["memory"]["cross_story_retrieval"])
        self.assertFalse(contract["tools"]["dynamic_tool_invocation"])
        self.assertFalse(contract["models"]["allow_fallbacks"])
        self.assertFalse(contract["finance"]["payment_authorized"])
        self.assertEqual(contract["models"]["exact_model_id"],
                         "anthropic/claude-sonnet-5.5")

    def test_pipeline_stage_source_uses_exact_case_memory(self):
        run=create_harness(".","B01")
        prompt=build_spine_request(run.pack)
        good=wire("SPINEFORGE", prompt,simple_envelope=True)
        run.authorize_stage("SPINEFORGE",good)
        self.assertEqual(run.invoked,["SPINEFORGE"])
        with self.assertRaises(HarnessStop):
            run.authorize_stage("SPINEFORGE",good)
        bad=copy.deepcopy(good)
        bad["model"]="different/model"
        other=create_harness(".","B01")
        with self.assertRaises(HarnessStop):
            other.authorize_stage("SPINEFORGE",bad)
        bad=copy.deepcopy(good)
        bad["provider"]["allow_fallbacks"]=True
        other=create_harness(".","B01")
        with self.assertRaises(HarnessStop):
            other.authorize_stage("SPINEFORGE",bad)
        bad=copy.deepcopy(good)
        payload=json.loads(bad["messages"][1]["content"])
        payload["canonical_state"]["protagonist"]["name"]="OtherStory"
        bad["messages"][1]["content"]=json.dumps(payload)
        other=create_harness(".","B01")
        with self.assertRaises(HarnessStop):
            other.authorize_stage("SPINEFORGE",bad)

    def test_reject_changed_memory_tool_model_ledger_policy(self):
        data=json.loads(Path(PATH).read_text())
        for section,key,value in (
            ("memory","cross_story_retrieval",True),
            ("tools","external_shell",True),
            ("models","allow_fallbacks",True),
            ("models","exact_model_id","other/model"),
            ("quality","minimum_reader_score",3),
            ("finance","aggregate_limit_usd","999.00"),
            ("evidence","reported_accept_is_not_certified",False),
            ("lifecycle","zero_change_during_round",False),
        ):
            with self.subTest(section=section,key=key),tempfile.TemporaryDirectory() as d:
                root=Path(d)/"configs"
                root.mkdir()
                other=copy.deepcopy(data)
                other[section][key]=value
                (root/"story_harness_runtime_v1.json").write_text(json.dumps(other))
                with self.assertRaises(HarnessStop):
                    load_manifest(d)

    def test_no_quality_can_be_written_as_a_new_canonical_memory(self):
        run=create_harness(".","B01")
        with self.assertRaises(HarnessStop):
            run.bind_story({
                "case_id":"B02","pack":{"pack_sha256":run.pack["pack_sha256"]},
                "story":{"story_sha256":"f"*64,"quality_accepted":False}
            })
        self.assertIsNone(run.story_sha256)

    def test_runner_rejects_missing_harness_even_when_mock_transport_passed(self):
        from src.story_harness_cohort_pipeline_v1 import run_one_case_with_injected_transport
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(TypeError):
                run_one_case_with_injected_transport(".", "B01", td,
                                                     transport=lambda body:{})
