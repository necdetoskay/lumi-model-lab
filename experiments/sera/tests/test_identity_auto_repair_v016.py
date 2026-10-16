"""SERA v0.16 self-healing identity test fixtures, no paid provider."""
from __future__ import annotations
from copy import deepcopy
import json
import unittest
from experiments.sera.identity_auto_repair_v016 import repair
from experiments.sera.mara_s1_typed_live_v05 import entry_state
from experiments.sera.tests.test_blind_identity_v015 import synthetic_model_rows
from experiments.sera.tests.test_identity_resolution_v014 import PROSE,synthetic_mention_census

def problem_response():
    rows=synthetic_model_rows()
    mapping={r["entity_ref"]:r for r in rows["rows"]}
    for ref in ("new:bench","new:pencil"):
        mapping[ref]["relation"]="POTENTIAL_LOCATION_WITHIN"
        mapping[ref]["relation_target"]="north_quay_station"
    mapping["new:north_quay_station"]["relation"]="POTENTIAL_ALIAS_OF"
    mapping["new:strike_record"]["relation"]="POTENTIAL_DOCUMENT_ENTRY_OF"
    return rows

def run(raw,model_repair=None,checkpoints=None,max_targeted_calls=4):
    return repair(
        prose=PROSE,world=entry_state(),census=synthetic_mention_census(),
        raw_provider_content=raw,model_repair=model_repair,
        checkpoints=checkpoints,max_targeted_calls=max_targeted_calls,
    )

class AutomaticIdentityRepairTests(unittest.TestCase):
    def test_three_schema_errors_fixed_one_quarantined_automatically(self):
        log=[]
        res=run(json.dumps(problem_response()),checkpoints=log.append)
        self.assertEqual(res["requested_entity_count"],16)
        self.assertEqual(res["accepted_source_bound_count"],15)
        self.assertEqual(res["automatic_abstain_count"],1)
        self.assertEqual(res["deterministically_repaired_count"],3)
        self.assertEqual(res["additional_model_calls"],0)
        self.assertEqual(res["quarantined_proposals"][0]["entity_ref"],"new:strike_record")
        self.assertEqual(res["quarantined_proposals"][0]["system_disposition"],
                         "ABSTAIN_UNRESOLVED_AUTOMATIC")
        known={x["entity_ref"]:x for x in res["accepted_proposals"]}
        for ref in ("new:bench","new:pencil"):
            self.assertEqual(known[ref]["proposed_relation"],"NONE")
            self.assertIsNone(known[ref]["proposed_relation_target"])
            self.assertFalse(known[ref]["physical_presence_confirmed"])
        self.assertEqual(known["new:north_quay_station"]["proposed_relation"],
                         "EXISTING_REGION_NAME_CANDIDATE")
        self.assertEqual(res["world_db_writes"],0)
        self.assertEqual(res["auto_entity_creations"],0)
        self.assertFalse(res["canonical_commit_authorized"])
        self.assertEqual(log[-1]["stage"],"AUTO_REPAIR_TERMINATED")

    def test_targeted_model_only_bad_ref_revalidated_and_still_noncanonical(self):
        tasks=[]
        def model_repair(prompt):
            tasks.append(prompt)
            self.assertEqual(prompt["target_ref"],"new:strike_record")
            self.assertNotIn("max_tokens",str(prompt))
            original=next(r for r in problem_response()["rows"]
                          if r["entity_ref"]=="new:strike_record")
            original["relation"]="POTENTIAL_PART_OF"
            return json.dumps({"rows":[original]})
        result=run(json.dumps(problem_response()),model_repair=model_repair)
        self.assertEqual(len(tasks),1)
        self.assertEqual(result["additional_model_calls"],1)
        self.assertEqual(result["model_targeted_repaired_count"],1)
        self.assertEqual(result["accepted_source_bound_count"],16)
        self.assertEqual(result["automatic_abstain_count"],0)
        self.assertEqual(result["status"],"AUTOMATIC_IDENTITY_SOURCE_BOUND_HOLD")
        self.assertEqual(result["auto_relation_attachments"],0)

    def test_model_cannot_fabricate_source_quote_or_parent(self):
        def malicious(task):
            row=next(x for x in problem_response()["rows"]
                     if x["entity_ref"]=="new:strike_record")
            row["relation"]="POTENTIAL_PART_OF"
            row["relation_target"]="new:fabricated_train"
            row["support_quote"]="invented physical arrival"
            return json.dumps({"rows":[row]})
        res=run(json.dumps(problem_response()),model_repair=malicious)
        self.assertEqual(res["accepted_source_bound_count"],15)
        self.assertEqual(res["automatic_abstain_count"],1)
        self.assertEqual(res["additional_model_calls"],1)
        self.assertTrue(res["quarantined_proposals"][0]["error_code"].startswith(
            "V016_TARGETED_REPAIR_UNRESOLVED:"
        ))
        self.assertFalse(res["canonical_commit_authorized"])

    def test_missing_or_duplicate_row_held_not_whole_batch(self):
        no_last=synthetic_model_rows();no_last["rows"].pop()
        result=run(json.dumps(no_last))
        self.assertEqual(result["accepted_source_bound_count"],15)
        self.assertEqual(result["quarantined_proposals"][0]["error_code"],
                         "V016_MISSING_ROW")
        duplicate=synthetic_model_rows()
        duplicate["rows"].append(deepcopy(duplicate["rows"][0]))
        result=run(json.dumps(duplicate))
        self.assertEqual(result["accepted_source_bound_count"],15)
        self.assertEqual(result["automatic_abstain_count"],1)
        self.assertEqual(result["unexpected_response_rows"][0]["code"],
                         "V016_UNKNOWN_OR_DUPLICATE_REF")

    def test_no_retry_budget_still_deterministically_resolves_three(self):
        calls=[]
        res=run(json.dumps(problem_response()),model_repair=calls.append,
                max_targeted_calls=0)
        self.assertEqual(calls,[])
        self.assertEqual(res["accepted_source_bound_count"],15)
        self.assertEqual(res["additional_model_calls"],0)

    def test_unparseable_raw_becomes_complete_automatic_abstention(self):
        invalid=chr(96)*3+'json\n{"rows":[\nINVALID\n'+chr(96)*3
        res=run(invalid,max_targeted_calls=0)
        self.assertEqual(res["accepted_source_bound_count"],0)
        self.assertEqual(res["automatic_abstain_count"],16)
        self.assertTrue(res["syntax_error"])
        self.assertTrue(res["all_reference_slots_accounted_for"])

    def test_model_repair_invalid_schema_auto_abstains(self):
        calls=[]
        def invalid(t):
            calls.append(t["target_ref"])
            return '{"rows": 17}'
        res=run(json.dumps(problem_response()),model_repair=invalid)
        self.assertEqual(calls,["new:strike_record"])
        self.assertEqual(res["additional_model_calls"],1)
        self.assertEqual(res["accepted_source_bound_count"],15)
        self.assertIn("V016_TARGETED_REPAIR_RESPONSE_INVALID",
                      res["quarantined_proposals"][0]["error_code"])

    def test_network_failure_is_automatic_abstention_for_only_one_identity(self):
        calls=[]
        def provider_failure(task):
            calls.append(task["target_ref"])
            raise ConnectionError("synthetic provider unreachable")
        output=run(json.dumps(problem_response()),model_repair=provider_failure)
        self.assertEqual(calls,["new:strike_record"])
        self.assertEqual(output["accepted_source_bound_count"],15)
        self.assertEqual(output["automatic_abstain_count"],1)
        self.assertEqual(output["additional_model_calls"],1)
        self.assertIn("provider unreachable",
                      output["quarantined_proposals"][0]["error_code"])
        self.assertFalse(output["canonical_commit_authorized"])

    def test_durable_checkpoint_each_step_before_and_after_model(self):
        checkpoints=[]
        def one(t):
            row=next(x for x in problem_response()["rows"]
                     if x["entity_ref"]=="new:strike_record")
            row["relation"]="POTENTIAL_PART_OF"
            return json.dumps({"rows":[row]})
        out=run(json.dumps(problem_response()),model_repair=one,
                checkpoints=checkpoints.append)
        stages=[x["stage"] for x in checkpoints]
        self.assertEqual(stages.count("TARGETED_REPAIR_STARTED"),1)
        self.assertEqual(stages.count("TARGETED_REPAIR_RAW_RETURNED"),1)
        self.assertEqual(stages[-1],"AUTO_REPAIR_TERMINATED")
        self.assertEqual(out["original_response_sha256"],
                         out["journal"][0]["raw_sha256"])

if __name__=="__main__":
    unittest.main()
