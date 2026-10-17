"""Aion 3.5 Mini high/max one-use transport and story-input contract tests."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import patch

from experiments.prototypes import aion35_mini_reasoning_high_max_once_20261017 as ab


def fake_provider(request, key):
    effort=request["reasoning"]["effort"]
    assert key=="sk-test-not-a-real-api-key"
    assert "max_tokens" not in request
    assert "max_tokens" not in request["reasoning"]
    return {
        "generation_id":"mock-"+effort,
        "returned_model":ab.MODEL,
        "finish_reason":"stop",
        "story":"Deniz heard a tick. " * (100 if effort=="high" else 110),
        "usage":{
            "prompt_tokens":300,
            "completion_tokens":2000 if effort=="high" else 2600,
            "completion_tokens_details":{
                "reasoning_tokens":1700 if effort=="high" else 2200
            },
            "cost":"0.004"
        },
        "event_count":222, "elapsed_seconds":1.5,
    }


class AionHighMaxTests(unittest.TestCase):
    def test_frozen_original_spine_and_only_effort_changes(self):
        packet=ab.verify_equal_experiment()
        self.assertEqual(packet["model"],ab.MODEL)
        self.assertEqual(packet["efforts"],["high","max"])
        self.assertNotEqual(packet["high_request_sha256"],
                            packet["max_request_sha256"])
        h=ab.make_request("high")
        m=ab.make_request("max")
        self.assertEqual(h["messages"],m["messages"])
        self.assertEqual(h["temperature"],m["temperature"])
        self.assertEqual(h["reasoning"]["exclude"],True)
        self.assertEqual(h["reasoning"]["effort"],"high")
        self.assertEqual(m["reasoning"]["effort"],"max")
        self.assertEqual(h["stream"],True)
        self.assertEqual(h["stream_options"]["include_usage"],True)
        self.assertNotIn("seed",h)
        for keyword in ("max_tokens","max_output_tokens",
                        "max_completion_tokens","reasoning_effort"):
            self.assertNotIn(keyword,h)
            self.assertNotIn(keyword,m)
        self.assertIn("Deniz",h["messages"][1]["content"])
        self.assertIn("metal rings",h["messages"][0]["content"])

    def test_two_real_shape_responses_saved_unedited_and_no_world_writes(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(ab,"validate_one_use_launch",
                              return_value=ab.verify_equal_experiment()), \
                 patch.object(ab,"real_stream_call",
                              side_effect=fake_provider) as calls:
                answer=ab.run_live(
                    output_root=root/"run",claim_root=root/"claims",
                    api_key="sk-test-not-a-real-api-key",grant={
                        "launch_id":"aion35mini-deniz-high-max-20261017-once",
                    },
                )
            self.assertEqual(calls.call_count,2)
            self.assertEqual(answer["completed_real_provider_replies"],2)
            self.assertEqual(answer["real_paid_posts_started"],2)
            self.assertEqual(answer["status"],
                             "TWO_GENUINE_PROVIDER_ANSWERS_COMPARABLE")
            self.assertFalse(answer["model_output_token_limit_set"])
            self.assertEqual(answer["manual_story_repairs"],0)
            self.assertEqual(answer["editor_or_judge_provider_calls"],0)
            self.assertEqual(answer["production_db_writes"],0)
            for effort in ab.EFFORTS:
                summary=json.loads((root/"run"/
                                   f"{effort}.summary.json").read_text())
                self.assertEqual(summary["effort"],effort)
                self.assertIsNotNone(summary["usage"]["reasoning_tokens"])
                self.assertEqual((root/"run"/f"{effort}.txt").read_text(),
                                 fake_provider(ab.make_request(effort),
                                               "sk-test-not-a-real-api-key")["story"]+"\n")
                self.assertTrue((root/"run"/f"{effort}.receipt.json").exists())
                self.assertTrue((root/"run"/f"{effort}.started.json").exists())

    def test_unreceived_first_reply_stops_both_and_is_not_reused(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(ab,"validate_one_use_launch",
                              return_value=ab.verify_equal_experiment()), \
                 patch.object(ab,"real_stream_call",
                              side_effect=TimeoutError("unknown billable")) as call:
                result=ab.run_live(
                    output_root=root/"out",claim_root=root/"claims",
                    api_key="sk-test-not-a-real-api-key",grant={
                        "launch_id":"aion35mini-deniz-high-max-20261017-once"
                    },
                )
            self.assertEqual(call.call_count,1)
            self.assertEqual(result["real_paid_posts_started"],1)
            self.assertEqual(result["completed_real_provider_replies"],0)
            self.assertEqual(result["status"],
                             "PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND")
            failure=json.loads((root/"out"/"high.failure.json").read_text())
            self.assertEqual(failure["possibly_billed"],True)
            self.assertTrue(failure["safe_no_retry"])
            self.assertFalse((root/"out"/"max.started.json").exists())
            self.assertEqual(len(list((root/"claims").glob("*.claimed.json"))),1)
            with self.assertRaises(FileExistsError):
                ab.claim_one_use({
                    "launch_id":"aion35mini-deniz-high-max-20261017-once",
                },root/"claims")

    def test_complete_provider_sse_requires_done_and_final_finish_reason(self):
        from unittest.mock import MagicMock
        def packet(content="",finish=None,usage=None):
            body={
                "id":"gen-1","model":ab.MODEL,
                "choices":[{"delta":{"content":content},"finish_reason":finish}],
            }
            if usage is not None:
                body["usage"]=usage
            return "data: "+json.dumps(body)
        def stubbed(lines):
            response=MagicMock()
            response.__enter__.return_value=response
            response.iter_lines.return_value=lines
            response.raise_for_status.return_value=None
            return response
        request=ab.make_request("high")
        events=[
            packet("Deniz heard a tick. "),
            packet("He looked up.",finish="stop",
                   usage={"prompt_tokens":661,"completion_tokens":3000,
                          "cost":0.01}),
            "data: [DONE]",
        ]
        with patch("requests.post",return_value=stubbed(events)):
            receipt=ab.real_stream_call(request,"sk-test")
        self.assertEqual(receipt["generation_id"],"gen-1")
        self.assertEqual(receipt["finish_reason"],"stop")
        self.assertEqual(receipt["story"],
                         "Deniz heard a tick. He looked up.")
        self.assertEqual(receipt["usage"]["cost"],0.01)
        for bad in [events[:-1],
                    [events[0],packet("end",finish=None),"data: [DONE]"]]:
            with patch("requests.post",return_value=stubbed(bad)):
                with self.assertRaisesRegex(
                    RuntimeError,"PROVIDER_STREAM_TRUNCATED_OR_NO_DONE",
                ):
                    ab.real_stream_call(request,"sk-test")

    def test_consumed_global_one_use_claim_prevents_second_paid_run(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)
            grant={"launch_id":"aion35mini-deniz-high-max-20261017-once"}
            with patch.object(ab,"validate_one_use_launch",
                              return_value=ab.verify_equal_experiment()), \
                 patch.object(ab,"real_stream_call",
                              side_effect=fake_provider) as provider:
                ab.run_live(output_root=root/"run-1",
                            claim_root=root/"claims",
                            api_key="sk-test-not-a-real-api-key",grant=grant)
                self.assertEqual(provider.call_count,2)
                with self.assertRaises(FileExistsError):
                    ab.run_live(output_root=root/"run-2",
                                claim_root=root/"claims",
                                api_key="sk-test-not-a-real-api-key",grant=grant)
                self.assertEqual(provider.call_count,2)

    def test_grant_must_solely_modify_exact_launch_file(self):
        grant={
            "schema":ab.SCHEMA,
            "launch_id":"aion35mini-deniz-high-max-20261017-once",
            "base_commit":"parent123","model":ab.MODEL,
            "efforts":["high","max"],"max_provider_posts":2,
            "source_blob":ab.OLD_BLOB,
            "grant_policy":"PAID_TWO_CALLS_HIGH_AND_MAX_EXPLICIT_USER_APPROVAL"
        }
        with patch.object(ab,"_git",
                          side_effect=["parent123",
                                       "experiments/triggers/unexpected.txt"]):
            with self.assertRaisesRegex(
                RuntimeError,"PAID_LAUNCH_CHANGED_CODE",
            ):
                ab.validate_one_use_launch(grant)

    def test_ambiguous_output_does_not_count_as_acceptable_story(self):
        payload=ab.make_request("max")
        bad=fake_provider(payload,"sk-test-not-a-real-api-key")
        bad["finish_reason"]="length"
        result=ab.summarize("max",bad,payload)
        self.assertEqual(result["finish_reason"],"length")
        self.assertFalse(result["story_quality_semantically_judged"])


if __name__=="__main__":
    unittest.main()
