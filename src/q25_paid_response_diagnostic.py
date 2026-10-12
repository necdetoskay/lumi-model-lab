"""Q25 offline diagnostics of an *actual saved* rejected extractor response.

Every raw claim remains untrusted. Identity similarity against authored
provisional labels is not semantic adjudication, acceptance, or state commit.
No model calls, network access, retries, automatic semantic repairs or writes.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.q25_entity_candidates import fingerprint
from src.q25_extraction_benchmark import CLAIM_GROUPS, _claims, _score
from src.q25_extractor_adapter import materialize_quotes, offline_replay
from src.q25_offline_diagnostic import digest
from src.q25_withheld_trial import unpack_request, ReferencePackage


def safe_failure_code(exc):
    """Return only a known error category; never publish raw provider text."""
    message = str(exc)
    if message == "Subject must resolve to an existing or candidate object":
        return "RELATION_SUBJECT_NOT_NAMESPACED_OR_NOT_RESOLVED"
    if message == "Epistemic classification is only for knowledge claims":
        return "EPISTEMIC_CLASSIFICATION_ON_NON_KNOWLEDGE"
    if message == "Ambiguous repeated quote; supply exact context to disambiguate":
        return "AMBIGUOUS_SOURCE_QUOTE"
    if message == "Extractor quote or exact context does not exist in source":
        return "SOURCE_QUOTE_NOT_FOUND"
    return "OTHER_REJECTED_OFFLINE_GATE"


def diagnose(*, request_package, reference_package, raw_response, ledger):
    inputs = copy.deepcopy((request_package, reference_package, raw_response, ledger))
    request = unpack_request(request_package)
    reference = ReferencePackage.model_validate(reference_package)
    if (request["request_id"] != reference.request_id
            or reference.seed_sha256 != fingerprint(request["seed"])
            or reference.source_sha256 != digest(request["prose"])):
        raise ValueError("Provisional reference does not bind to source")
    if not isinstance(raw_response, dict) or not isinstance(ledger, dict):
        raise ValueError("Saved raw extraction and ledger must be objects")
    if (ledger.get("seed_sha256") != reference.seed_sha256
            or ledger.get("source_sha256") != reference.source_sha256
            or ledger.get("model") != "anthropic/claude-sonnet-5.5"
            or ledger.get("attempted_calls") != 1
            or ledger.get("provider_calls") != 1
            or ledger.get("max_calls") != 1
            or ledger.get("state_commit_authorized") is not False
            or ledger.get("outcome") != "REJECTED_BY_OFFLINE_GATE"
            or ledger.get("billing_status") != "PROVIDER_REPORTED_USAGE"):
        raise ValueError("Saved provider ledger not qualified for this analysis")
    usage = ledger.get("usage")
    if not isinstance(usage, dict) or not isinstance(usage.get("actual_cost_usd"), (int, float)):
        raise ValueError("Cannot report unmeasured paid usage")
    if not (0 <= usage["actual_cost_usd"] <= float(ledger.get("max_cost_usd", "0"))):
        raise ValueError("Provider-reported spend exceeds saved cap")
    # The same source-bound materializer checks every source quote, digest and
    # raw schema. We do not loosen the parser to obtain a better score.
    baseline = _claims(materialize_quotes(
        seed=request["seed"], prose=request["prose"],
        raw_output=reference.raw_reference))
    predicted = _claims(materialize_quotes(
        seed=request["seed"], prose=request["prose"], raw_output=raw_response))
    gate = {"result": "BLOCKED", "failure_code": "OTHER_REJECTED_OFFLINE_GATE"}
    try:
        status = offline_replay(
            seed=request["seed"], prose=request["prose"],
            raw_output=raw_response, policy=request["policy"])
    except (ValueError, TypeError, KeyError) as exc:
        gate["failure_code"] = safe_failure_code(exc)
    else:
        gate["result"] = status["status"]
        gate["failure_code"] = None

    per_group = {
        kind: _score(
            {key: val for key, val in baseline.items() if val["group"] == kind},
            {key: val for key, val in predicted.items() if val["group"] == kind},
        )
        for kind in CLAIM_GROUPS
    }
    diagnostics = {
        "unqualified_subject_references": [
            {"group": "terminal_relations", "index": i,
             "subject": r["subject"]}
            for i, r in enumerate(raw_response.get("terminal_relations", []))
            if not r["subject"].startswith(("object:", "new:"))
        ],
        "non_knowledge_epistemic_annotations": [
            {"group": "character_claims", "index": i,
             "actor": claim["actor"], "field": claim["field"],
             "epistemic_type": claim["epistemic_type"]}
            for i, claim in enumerate(raw_response.get("character_claims", []))
            if claim["field"] != "knowledge"
            and claim.get("epistemic_type") is not None
        ],
    }
    result = {
        "schema": "q25.paid-response-diagnostic.v1",
        "request_id": request["request_id"],
        "source_sha256": reference.source_sha256,
        "seed_sha256": reference.seed_sha256,
        "raw_output_sha256": fingerprint(raw_response),
        "ledger_sha256": fingerprint(ledger),
        "model": ledger["model"],
        "model_schema_profile": ledger["model_schema_profile"],
        "provider_reported_cost_usd": usage["actual_cost_usd"],
        "tokens": {
            "prompt": usage["prompt_tokens"],
            "completion": usage["completion_tokens"],
            "total": usage["total_tokens"],
        },
        "source_quote_materialization": "PASS_EXACT_SOURCE_BINDING_ONLY",
        "offline_gate": gate,
        "diagnostics": diagnostics,
        "reference_claim_count": len(baseline),
        "raw_candidate_claim_count": len(predicted),
        "provisional_identity_score": _score(baseline, predicted),
        "by_group": per_group,
        "extra_claims_against_provisional_reference": [
            predicted[k] for k in sorted(set(predicted) - set(baseline))],
        "missed_claims_against_provisional_reference": [
            baseline[k] for k in sorted(set(baseline) - set(predicted))],
        "score_scope": (
            "RAW_IDENTITY_SIMILARITY_DESPITE_REJECTED_GATE"
            if gate["result"] != "SOURCE_BOUND_CANDIDATES_ONLY"
            else "SOURCE_BOUND_ONLY_NO_SEMANTIC_APPROVAL"
        ),
        "reference_independently_adjudicated": False,
        "quoted_evidence_proves_semantic_claim": False,
        "independent_semantic_review_completed": False,
        "actual_accepted_extractor_precision": None,
        "actual_accepted_extractor_recall": None,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "new_provider_calls_by_diagnostic": 0,
        "new_provider_cost_usd": 0.0,
        "retains_raw_unmodified": True,
    }
    if inputs != (request_package, reference_package, raw_response, ledger):
        raise AssertionError("Diagnostics must not change original evidence")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("request-package", "reference-package", "raw-response", "ledger"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    load = lambda path: json.loads(path.read_text(encoding="utf8"))
    result = diagnose(
        request_package=load(args.request_package),
        reference_package=load(args.reference_package),
        raw_response=load(args.raw_response),
        ledger=load(args.ledger),
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
