"""Forensic zero-cost and fail-closed identity row quarantine regressions."""
from __future__ import annotations

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from experiments.sera.coverage import CoverageError
from experiments.sera.tests.test_blind_identity_v015 import (
    synthetic_model_rows,preflight,
)
from experiments.sera.paid_blind_identity_forensics_v015 import (
    recover_literal_json,exact_source_quote,forensic_rebind,
    verify_paid_provenance,
)
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.tests.test_identity_resolution_v014 import PROSE

def evidence(raw):
    return {"raw_provider_content":raw}

class PaidIdentityForensicsV015Tests(unittest.TestCase):
    def test_three_literal_unescaped_dialogue_quote_lines_repair_only_support_field(self):
        source=(
            '"rows": [\n {"support_quote": ""I waited on the platform," he said.",\n '
            '"reason":"quoted sentence"},\n '
            '{"support_quote": ""I saw no train at 02:10."",\n '
            '"reason":"reported topic"},\n '
            '{"support_quote": ""What the sources say," she replied.",\n '
            '"reason":"a statement"}\n ]'
        )
        bad=chr(96)*3+"json\n{\n "+source+"\n}\n"+chr(96)*3
        result,changes=recover_literal_json(bad)
        self.assertEqual(changes["fixed_support_quote_lines"],3)
        self.assertEqual(result["rows"][0]["support_quote"],
                         '"I waited on the platform," he said.')
        self.assertEqual(result["rows"][1]["support_quote"],
                         '"I saw no train at 02:10."')
        self.assertEqual(result["rows"][2]["support_quote"],
                         '"What the sources say," she replied.')
        self.assertTrue(all(
            x["operation"]==
            "ESCAPE_UNESCAPED_JSON_DOUBLE_QUOTES_IN_SUPPORT_QUOTE_ONLY"
            for x in changes["fixed_fields"]))

    def test_no_general_json_repair_or_fake_output_interpreted(self):
        invalid=(chr(96)*3+"json\n"+
                 '{"rows":[], "decision":"PROPOSE" extra garbage}\n'+chr(96)*3)
        with self.assertRaisesRegex(
            CoverageError,"V015_FORENSIC_UNRECOGNIZED_JSON_FAILURE"
        ):
            recover_literal_json(invalid)

    def test_punctuation_recovery_must_be_unique_and_source_exact(self):
        m={"new:platform":{"source_evidence":[{
            "sentence_id":"s005",
        }]}}
        sources={x["id"]:x for x in sentences(PROSE)}
        recovered,how=exact_source_quote(
            prose=PROSE,source_map=sources,mentions=m,ref="new:platform",
            row={"support_sentence_id":"s005",
                 "support_quote":'"I waited on the platform," he said.'})
        self.assertEqual(recovered,'“I waited on the platform,” he said.')
        self.assertEqual(how,"UNIQUE_TYPOGRAPHIC_QUOTE_EQUIVALENCE_UNVERIFIED")
        with self.assertRaises(CoverageError):
            exact_source_quote(
                prose=PROSE,source_map=sources,mentions=m,ref="new:platform",
                row={"support_sentence_id":"s005",
                     "support_quote":'"I visited a different station," he said.'})

    def test_valid_candidates_retained_invalid_relations_quarantined_not_abstained(self):
        world,census,request=preflight()
        original=synthetic_model_rows()
        wrong=next(x for x in original["rows"] if x["entity_ref"]=="new:bench")
        wrong["relation"]="POTENTIAL_LOCATION_WITHIN"
        wrong["relation_target"]="north_quay_station"
        report=json.dumps(original,ensure_ascii=False)
        with patch(
            "experiments.sera.paid_blind_identity_forensics_v015.verify_paid_provenance"
        ):
            out=forensic_rebind(
                prose=PROSE,world=world,census=census,evidence=evidence(report))
        self.assertEqual(out["source_bound_count"],15)
        self.assertEqual(out["quarantine_count"],1)
        self.assertEqual(out["all_original_model_rows_returned"],16)
        self.assertEqual(out["quarantined_original_model_rows"][0]
                         ["entity_ref"],"new:bench")
        self.assertIn("V015_RELATION_UNGROUNDED",
                      out["quarantined_original_model_rows"][0]["error_code"])
        self.assertEqual(out["independent_model_abstained_count"],0)
        self.assertEqual(out["paid_model_calls_during_recovery"],0)
        self.assertFalse(out["canonical_commit_authorized"])
        self.assertEqual(out["new_entity_creations"],0)
        self.assertEqual(out["new_relation_attachments"],0)
        self.assertEqual(out["status"],
            "PARTIALLY_RECOVERED_SOURCE_BOUND_PROPOSALS_SEMANTIC_HOLD")

    def test_provenance_pin_refuses_fake_paid_response(self):
        world,census,request=preflight()
        with self.assertRaisesRegex(
            CoverageError,"V015_HISTORICAL_PAID_PROVENANCE_NOT_PINNED"
        ):
            verify_paid_provenance(evidence={
                "schema":"sera.mara-s1-blind-identity-paid-pilot.v0.15",
                "provider_attempts":2,
            },request=request)

    def test_invalid_quote_quarantined_without_rewriting_world(self):
        world,census,request=preflight()
        original=deepcopy(world)
        rows=synthetic_model_rows()
        candidate=next(x for x in rows["rows"] if x["entity_ref"]=="new:train")
        candidate["support_quote"]="Train 41 visibly arrived at North Quay"
        with patch(
            "experiments.sera.paid_blind_identity_forensics_v015.verify_paid_provenance"
        ):
            out=forensic_rebind(
                prose=PROSE,world=world,census=census,
                evidence=evidence(json.dumps(rows)))
        self.assertEqual(out["quarantine_count"],1)
        self.assertEqual(world,original)
        self.assertFalse(out["canonical_commit_authorized"])

if __name__=="__main__":
    unittest.main()
