"""No-network strict forensic recovery contract; synthetic providers only."""
from __future__ import annotations

import json
import unittest

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import (
    parse_json_model_reply,source_quote_repair,recover_model_task,
)
from experiments.sera.tests.test_mara_s1_haiku_probes_v011 import evidence

class HistoricalHaikuRecoveryTests(unittest.TestCase):
    def test_entire_fenced_json_is_parsed_without_other_text(self):
        sample={"verdict":"STATE_OBSERVATION","operation_kind":"OBSERVE",
                "effect":"CHARACTER_KNOWLEDGE","evidence_quote":"turned",
                "reason":"Attention to the clock"}
        parsed,fmt=parse_json_model_reply(
            chr(96)*3+"json\n"+json.dumps(sample)+"\n"+chr(96)*3)
        self.assertEqual(parsed,sample)
        self.assertEqual(fmt,"FULL_JSON_CODE_FENCE")
        raw,typ=parse_json_model_reply(json.dumps(sample))
        self.assertEqual(raw,sample)
        self.assertEqual(typ,"RAW_JSON")

    def test_wrapped_json_plus_chatty_prose_is_not_accepted(self):
        contents=chr(96)*3+"json\n{}\n"+chr(96)*3
        for sample in ("My opinion:\n"+contents,contents+"\nExtra thoughts",
                       chr(96)*3+"json\n{BROKEN}\n"+chr(96)*3):
            with self.assertRaises(CoverageError):
                parse_json_model_reply(sample)

    def test_curly_vs_ascii_apostrophe_exact_unique_quote(self):
        task={"exact_source_context":[{"quote":
            "She turned to the platform clock’s strike record and traced the entry."}]}
        quote="She turned to the platform clock's strike record and traced the entry."
        actual,how=source_quote_repair(task=task,proposed_quote=quote)
        self.assertEqual(actual,task["exact_source_context"][0]["quote"])
        self.assertEqual(how,"TYPOGRAPHIC_APOSTROPHE_EQUIVALENCE_UNVERIFIED")
        self.assertEqual(len(actual),len(quote))

    def test_repair_cannot_invent_or_fuzzy_match_other_words(self):
        task={"exact_source_context":[{"quote":"Mara’s watch was open."}]}
        for quote in ("Mara's watch was closed.","The clock was open.",
                      "Mara's watch said the train arrived"):
            with self.assertRaisesRegex(CoverageError,
                                        "PROBE_TYPOGRAPHIC_MATCH_NOT_UNIQUE"):
                source_quote_repair(task=task,proposed_quote=quote)

    def test_curly_double_quotes_bind_only_exact_source_punctuation(self):
        task={"exact_source_context":[{"quote":
            "She paused, then added, “Discrepancy documented; explanation unknown.”"}]}
        proposed='She paused, then added, "Discrepancy documented; explanation unknown."'
        actual,method=source_quote_repair(task=task,proposed_quote=proposed)
        self.assertEqual(actual,task["exact_source_context"][0]["quote"])
        self.assertEqual(method,"TYPOGRAPHIC_DOUBLE_QUOTES_EQUIVALENCE_UNVERIFIED")

    def test_ambiguous_apostrophe_equivalence_stays_hold(self):
        task={"exact_source_context":[{"quote":"Mara’s watch. Mara’s watch."}]}
        with self.assertRaisesRegex(CoverageError,
                                    "PROBE_TYPOGRAPHIC_MATCH_NOT_UNIQUE"):
            source_quote_repair(task=task,proposed_quote="Mara's watch")

    def test_recovered_advisory_cannot_authorize_truth_or_rewrite_semantics(self):
        audit=evidence()
        reply={
            "verdict":"STATE_OBSERVATION",
            "operation_kind":"OBSERVE",
            "effect":"CHARACTER_KNOWLEDGE",
            "evidence_quote":"turned",
            "reason":"This is attentional shift, not locational move"
        }
        wrapped=chr(96)*3+"json\n"+json.dumps(reply)+"\n"+chr(96)*3
        result=recover_model_task(
            risk_audit=audit,task_id="task_001",raw_provider_content=wrapped)
        self.assertEqual(result["model_calls_during_recovery"],0)
        self.assertFalse(result["canonical_commit_authorized"])
        self.assertEqual(result["unmodified_proposed_semantics"]["verdict"],
                         "STATE_OBSERVATION")
        self.assertEqual(result["bound_advisory"]["verdict_model_proposed"],
                         "STATE_OBSERVATION")
        self.assertEqual(result["exact_source_evidence_quote"],"turned")

if __name__=="__main__":
    unittest.main()
