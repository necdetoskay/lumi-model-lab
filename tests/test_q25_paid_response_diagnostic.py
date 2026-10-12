"""Replay authenticated provider-style evidence offline: rejected stays rejected."""
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.q25_paid_response_diagnostic import diagnose

EVIDENCE = Path("evidence/q25/Q25-WITHHELD-TRIAL-20261012")


def read(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf8"))


def inputs():
    return {
        "request_package": read("request.json"),
        "reference_package": read("provisional-reference.json"),
        "raw_response": read("paid-attempt-02-raw-extraction.json"),
        "ledger": read("paid-attempt-02-public-ledger.json"),
    }


def test_real_saved_model_response_scores_without_forging_offline_acceptance():
    data = inputs()
    original = copy.deepcopy(data)
    result = diagnose(**data)
    assert result["schema"] == "q25.paid-response-diagnostic.v1"
    assert result["request_id"] == "KITE-01"
    assert result["model"] == "anthropic/claude-sonnet-5.5"
    assert result["model_schema_profile"] == "ANTHROPIC_STRICT_V1"
    assert result["provider_reported_cost_usd"] == 0.04313
    assert result["tokens"] == {
        "prompt": 6270, "completion": 3059, "total": 9329}
    assert result["source_quote_materialization"] == (
        "PASS_EXACT_SOURCE_BINDING_ONLY")
    assert result["offline_gate"] == {
        "result": "BLOCKED",
        "failure_code": "RELATION_SUBJECT_NOT_NAMESPACED_OR_NOT_RESOLVED"}
    assert result["reference_claim_count"] == 16
    assert result["raw_candidate_claim_count"] == 18
    assert result["provisional_identity_score"] == {
        "true_positive": 13, "false_positive": 5, "false_negative": 3,
        "precision": pytest.approx(13/18),
        "recall": pytest.approx(13/16),
        "f1": pytest.approx(26/34),
        "reference_quote_exact_matches": 3,
    }
    assert sum(r["true_positive"] for r in result["by_group"].values()) == 13
    assert sum(r["false_positive"] for r in result["by_group"].values()) == 5
    assert sum(r["false_negative"] for r in result["by_group"].values()) == 3
    assert result["by_group"]["character_claims"]["true_positive"] == 0
    assert result["by_group"]["property_claims"]["true_positive"] == 4
    assert result["diagnostics"]["unqualified_subject_references"] == [{
        "group": "terminal_relations", "index": 0, "subject": "blue_string"}]
    tags = result["diagnostics"]["non_knowledge_epistemic_annotations"]
    assert len(tags) == 2
    assert {tag["field"] for tag in tags} == {"emotion", "relationship_trust"}
    assert result["score_scope"] == "RAW_IDENTITY_SIMILARITY_DESPITE_REJECTED_GATE"
    assert result["reference_independently_adjudicated"] is False
    assert result["independent_semantic_review_completed"] is False
    assert result["actual_accepted_extractor_precision"] is None
    assert result["actual_accepted_extractor_recall"] is None
    assert result["full_story_state_qualified"] is False
    assert result["state_commit_authorized"] is False
    assert result["production_write_performed"] is False
    assert result["new_provider_calls_by_diagnostic"] == 0
    assert result["new_provider_cost_usd"] == 0
    assert data == original
    assert diagnose(**data) == result


def test_raw_model_claims_remain_distinct_from_source_quite_and_semantic_truth():
    result = diagnose(**inputs())
    extra = result["extra_claims_against_provisional_reference"]
    missed = result["missed_claims_against_provisional_reference"]
    assert len(extra) == 5
    assert len(missed) == 3
    assert any(x["group"] == "terminal_relations" and
               x["identity"][0] == "blue_string" for x in extra)
    assert any(x["group"] == "property_claims" and
               x["identity"][0:2] == ["wooden_box", "lid_closed"] for x in extra)
    assert any(x["group"] == "terminal_relations" and
               x["identity"][0] == "object:blue_string" for x in missed)
    assert any(x["group"] == "character_claims" and
               x["identity"][0:2] == ["Bora", "knowledge"] for x in missed)
    assert result["quoted_evidence_proves_semantic_claim"] is False


@pytest.mark.parametrize("tamper", [
    "source_seed", "source_prose", "raw_quote", "raw_source_digest",
    "ledger_model", "ledger_usage", "ledger_cost", "ledger_call_count",
    "ledger_promotion", "reference_id", "reference_origin",
])
def test_tampering_never_produces_fake_paid_or_accepted_diagnostic(tamper):
    kw = inputs()
    if tamper == "source_seed":
        kw["request_package"]["seed"]["objects"]["red_kite"]["state"]["ready"] = True
    elif tamper == "source_prose":
        kw["request_package"]["prose_record"]["text"] += " fabricated"
    elif tamper == "raw_quote":
        kw["raw_response"]["objects"][0]["mention"]["quote"] = "nonexistent magic"
    elif tamper == "raw_source_digest":
        kw["raw_response"]["source_sha256"] = "0" * 64
    elif tamper == "ledger_model":
        kw["ledger"]["model"] = "unknown/model"
    elif tamper == "ledger_usage":
        kw["ledger"]["usage"]["actual_cost_usd"] = None
    elif tamper == "ledger_cost":
        kw["ledger"]["usage"]["actual_cost_usd"] = 0.25
    elif tamper == "ledger_call_count":
        kw["ledger"]["provider_calls"] = 2
    elif tamper == "ledger_promotion":
        kw["ledger"]["state_commit_authorized"] = True
    elif tamper == "reference_id":
        kw["reference_package"]["request_id"] = "DIFFERENT"
    elif tamper == "reference_origin":
        kw["reference_package"]["review_status"] = "ACCEPTED"
    with pytest.raises(ValueError):
        diagnose(**kw)


def test_same_saved_evidence_reproduces_via_cli_without_touching_source_files():
    paths = [
        EVIDENCE / name for name in (
            "request.json", "provisional-reference.json",
            "paid-attempt-02-raw-extraction.json",
            "paid-attempt-02-public-ledger.json",
        )
    ]
    before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
    cmd = [sys.executable, "-X", "utf8", "-m",
           "src.q25_paid_response_diagnostic"]
    for label, path in zip(
        ("--request-package", "--reference-package", "--raw-response", "--ledger"),
        paths,
    ):
        cmd.extend([label, str(path)])
    result = json.loads(subprocess.check_output(cmd, text=True, encoding="utf8"))
    assert result == diagnose(**inputs())
    assert before == [hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in paths]
