"""SERA v0.18 unattended semantic probes: synthetic, no paid provider."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.semantic_recovery_v018 import execute
from experiments.sera.tests.test_semantic_risks_v011 import SOURCE, report


MODEL = "anthropic/claude-haiku-4.5"


def reply(content, *, cost=0.001):
    return {"error": None, "raw": {
        "id": "synthetic-provider-receipt", "model": MODEL,
        "usage": {"cost": cost},
        "choices": [{"finish_reason": "stop",
                     "message": {"content": content}}],
    }}


def answer(quote):
    return json.dumps({
        "verdict": "STATE_OBSERVATION",
        "operation_kind": "OBSERVE",
        "effect": "CHARACTER_KNOWLEDGE",
        "evidence_quote": quote,
        "reason": "Independent source-only synthetic advisory, not world truth",
    })


def valid_provider(calls):
    def call(*, model, prepared):
        calls.append(deepcopy(prepared))
        context = json.loads(prepared["request"]["messages"][1]["content"])
        quote = context["exact_chronological_sentences"][-1]["quote"][:12]
        return reply(answer(quote))
    return call


def run(path, provider, **kwargs):
    return execute(
        prose=SOURCE, extraction_report=report(),
        call_model=provider, output_dir=path, **kwargs,
    )


class AutonomousSemanticV018Tests(unittest.TestCase):
    def test_all_semantic_risks_are_auto_probed_and_never_committed(self):
        calls = []
        with TemporaryDirectory() as d:
            root = Path(d) / "stage"
            result = run(root, valid_provider(calls))
            reread = run(root, valid_provider(calls))
        self.assertEqual(result, reread)
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["semantic_risk_count"], 3)
        self.assertEqual(result["completed_advisory_tasks"], 3)
        self.assertEqual(result["status"],
                         "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")
        self.assertEqual(result["next_automatic_action"],
                         "AUTO_EVENT_REEXTRACTION_OR_SCENE_REPLAN")
        self.assertFalse(result["requires_manual_intervention"])
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["world_db_writes"], 0)
        self.assertTrue(all(
            r["status"] == "HOLD_MODEL_RESPONSE_NOT_AUTHORITY"
            for r in result["independent_advisories"]
        ))

    def test_paid_invalid_json_automatically_routes_fallback_model(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            if len(calls) == 1:
                return reply("not json")
            context = json.loads(prepared["request"]["messages"][1]["content"])
            quote = context["exact_chronological_sentences"][-1]["quote"][:10]
            return reply(answer(quote))
        with TemporaryDirectory() as d:
            result = run(Path(d) / "stage", provider)
        self.assertEqual(len(calls), 4)
        self.assertEqual(result["provider_calls"], 4)
        self.assertEqual(result["observed_spend_usd"], "0.004")
        self.assertEqual(result["status"],
                         "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")

    def test_two_forged_source_quotes_fail_closed_not_wait_for_human(self):
        calls = []
        def forged(*, model, prepared):
            calls.append(prepared)
            return reply(answer("physically arrived train never in prose"))
        with TemporaryDirectory() as d:
            result = run(Path(d) / "stage", forged)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(result["failure_code"],
                         "V018_BOTH_RESPONSES_UNQUALIFIED")
        self.assertEqual(result["completed_advisory_tasks"], 0)
        self.assertFalse(result["requires_manual_intervention"])

    def test_lost_provider_reply_does_not_charge_again_automatically(self):
        calls = []
        def unknown(*, model, prepared):
            calls.append(prepared)
            return {"error": "HTTP_502"}
        with TemporaryDirectory() as d:
            root = Path(d) / "stage"
            original = run(root, unknown)
            (root / "final.json").unlink()
            replay = run(root, unknown)
        self.assertEqual(len(calls), 1)
        self.assertEqual(original["status"], "FAILED_SAFE_FINAL")
        self.assertEqual(replay["failure_code"],
                         "V018_UNCONFIRMED_IN_FLIGHT_CALL")
        self.assertFalse(replay["canonical_commit_authorized"])

    def test_replay_counts_previously_paid_fallback_against_call_budget(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            if len(calls) == 1:
                return reply("incomplete json")
            context = json.loads(prepared["request"]["messages"][1]["content"])
            return reply(answer(
                context["exact_chronological_sentences"][-1]["quote"][:10]
            ))
        with TemporaryDirectory() as d:
            root = Path(d) / "stage"
            original = run(root, provider, max_provider_calls=4)
            (root / "final.json").unlink()
            replay = run(root, provider, max_provider_calls=4)
        self.assertEqual(len(calls), 4)
        self.assertEqual(original["provider_calls"], 4)
        self.assertEqual(replay["provider_calls"], 4)
        self.assertEqual(replay["observed_spend_usd"], "0.004")
        self.assertEqual(replay["status"],
                         "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")

    def test_paid_receipt_replayed_without_new_call_after_crash(self):
        calls = []
        with TemporaryDirectory() as d:
            root = Path(d) / "stage"
            original = run(root, valid_provider(calls))
            (root / "final.json").unlink()
            replay = run(root, valid_provider(calls))
        self.assertEqual(len(calls), 3)
        self.assertEqual(replay["status"], original["status"])
        self.assertEqual(replay["observed_spend_usd"], "0.003")

    def test_source_tamper_cannot_start_model_request(self):
        calls = []
        with TemporaryDirectory() as d:
            with self.assertRaisesRegex(
                CoverageError, "SEMANTIC_RISK_SOURCE_OR_AUTHORITY_INVALID"
            ):
                execute(
                    prose=SOURCE + " Unapproved change.",
                    extraction_report=report(), call_model=valid_provider(calls),
                    output_dir=Path(d) / "stage",
                )
        self.assertEqual(calls, [])

    def test_policy_and_source_fingerprint_prevent_wrong_replay(self):
        calls = []
        with TemporaryDirectory() as d:
            root = Path(d) / "stage"
            run(root, valid_provider(calls))
            with self.assertRaisesRegex(
                CoverageError, "V018_INPUT_OR_POLICY_CHANGED"
            ):
                run(root, valid_provider(calls), max_provider_calls=2)
        self.assertEqual(len(calls), 3)

    def test_no_risk_corpus_completes_without_models_or_canon(self):
        simple = report()
        simple["candidate_events"] = []
        simple["targeted_probes"] = []
        calls = []
        with TemporaryDirectory() as d:
            result = execute(
                prose=SOURCE, extraction_report=simple,
                call_model=valid_provider(calls),
                output_dir=Path(d) / "stage",
            )
        self.assertEqual(calls, [])
        self.assertEqual(result["semantic_risk_count"], 0)
        self.assertEqual(result["status"],
                         "NO_TARGETED_RISKS_FOUND_NONCANONICAL")
        self.assertFalse(result["canonical_commit_authorized"])

    def test_single_complete_json_fence_is_recovered_without_fallback(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            context = json.loads(prepared["request"]["messages"][1]["content"])
            quote = context["exact_chronological_sentences"][-1]["quote"][:10]
            return reply("```json\n" + answer(quote) + "\n```")
        with TemporaryDirectory() as d:
            outcome = run(Path(d) / "stage", provider)
        self.assertEqual(len(calls), 3)
        self.assertEqual(outcome["status"],
                         "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")

    def test_fenced_json_with_outside_prose_requires_automatic_fallback(self):
        calls = []
        def provider(*, model, prepared):
            calls.append(prepared)
            context = json.loads(prepared["request"]["messages"][1]["content"])
            quote = context["exact_chronological_sentences"][-1]["quote"][:10]
            if len(calls) == 1:
                return reply("```json\n" + answer(quote) +
                             "\n```\nexternal text")
            return reply(answer(quote))
        with TemporaryDirectory() as d:
            outcome = run(Path(d) / "stage", provider)
        self.assertEqual(len(calls), 4)
        self.assertEqual(outcome["status"],
                         "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL")

    def test_no_application_output_token_ceiling_sent(self):
        calls = []
        with TemporaryDirectory() as d:
            run(Path(d) / "stage", valid_provider(calls))
        outgoing = json.dumps(calls)
        for field in (
            "max_tokens", "max_completion_tokens", "max_output_tokens",
            "max_new_tokens", "num_predict",
        ):
            self.assertNotIn(field, outgoing)


if __name__ == "__main__":
    unittest.main()
