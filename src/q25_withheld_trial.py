"""Q25 answer-withheld trial package and offline scoring boundary.

The reference is deliberately NOT an independent human-adjudicated truth set.
Only seed + prose are sent on the provider wire. No dispatch in this module.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Literal

from pydantic import Field

from src.q25_entity_candidates import fingerprint
from src.q25_extraction_benchmark import calibrate
from src.q25_offline_diagnostic import Strict, digest
from src.q25_openrouter_pilot import build_wire_request, MODEL_ALLOWLIST


class RequestPackage(Strict):
    schema_name: Literal["q25.withheld-request.v1"]
    request_id: str = Field(min_length=3, max_length=100, pattern=r"^[A-Z0-9_-]+$")
    model_inputs_only: Literal[True]
    labels_included: Literal[False]
    seed: dict
    prose_record: dict
    policy: dict


class ReferencePackage(Strict):
    schema_name: Literal["q25.withheld-provisional-reference.v1"]
    request_id: str
    seed_sha256: str
    source_sha256: str
    reference_origin: Literal["AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED"]
    never_include_in_model_request: Literal[True]
    review_status: Literal["PROVISIONAL"]
    raw_reference: dict
    cautions: list[str]


def unpack_request(package):
    validated = RequestPackage.model_validate(package)
    if set(validated.prose_record) != {"text"}:
        raise ValueError("Story record must contain only text, no hidden labels")
    prose = validated.prose_record["text"]
    if not isinstance(prose, str) or len(prose) < 500:
        raise ValueError("Trial prose is not a complete story")
    policy = validated.policy
    if (policy.get("scope") != "EXPERIMENTAL_DRAFT_ONLY" or
            policy.get("schema_name") != "q25.object-admission-policy.v1"):
        raise ValueError("Trial must be experimental and explicitly admitted")
    return {
        "request_id": validated.request_id,
        "seed": copy.deepcopy(validated.seed),
        "prose": prose,
        "policy": copy.deepcopy(policy),
    }


def preflight(*, request_package, model, max_tokens=3500):
    """Compile the actual provider wire *without ever loading the label file*."""
    if model not in MODEL_ALLOWLIST:
        raise ValueError("Unqualified model outside one-shot pilot allowlist")
    case = unpack_request(request_package)
    wire = build_wire_request(
        seed=case["seed"], prose=case["prose"],
        model=model, max_tokens=max_tokens)
    wire_serialized = json.dumps(
        wire, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if "withheld-provisional-reference" in wire_serialized or (
            "AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED" in wire_serialized):
        raise ValueError("Reference labels contaminated the provider wire")
    return {
        "schema": "q25.withheld-trial-preflight.v1",
        "request_id": case["request_id"],
        "seed_sha256": fingerprint(case["seed"]),
        "source_sha256": digest(case["prose"]),
        "wire_sha256": fingerprint(wire),
        "model": model,
        "max_tokens": max_tokens,
        "max_calls": 1,
        "max_cost_usd": "0.20",
        "provider_dispatch_performed": False,
        "provider_calls": 0,
        "reference_labels_loaded": False,
        "reference_labels_sent_to_model": False,
        "model_accuracy_measured": False,
        "state_commit_authorized": False,
    }


def evaluate(*, request_package, reference_package, raw_response,
             origin="UNAUTHENTICATED_SAVED_RESPONSE"):
    """Score a saved envelope; independently establishing provenance is separate."""
    case = unpack_request(request_package)
    ref = ReferencePackage.model_validate(reference_package)
    if ref.request_id != case["request_id"] or (
            ref.seed_sha256 != fingerprint(case["seed"])) or (
            ref.source_sha256 != digest(case["prose"])):
        raise ValueError("Withheld reference does not match frozen trial request")
    if not isinstance(raw_response, dict):
        raise ValueError("Raw candidate response must be JSON object")
    report = calibrate(
        seed=case["seed"], prose=case["prose"], policy=case["policy"],
        gold_raw_output=ref.raw_reference, candidate_raw_output=raw_response,
    )
    report.update(
        schema="q25.withheld-trial-evaluation.v1",
        request_id=case["request_id"],
        reference_label_origin=ref.reference_origin,
        candidate_origin=origin,
        evaluation_scope="ANSWER_WITHHELD_FROM_WIRE_REFERENCE_NOT_INDEPENDENTLY_CERTIFIED",
        reference_labels_sent_to_model=False,
        independent_human_adjudication_complete=False,
        real_model_success_measured=False,
        state_commit_authorized=False,
        provider_calls=0,
        provider_cost_usd=0.0,
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-package", required=True, type=Path)
    parser.add_argument("--model", default="anthropic/claude-sonnet-5.5",
                        choices=sorted(MODEL_ALLOWLIST))
    parser.add_argument("--max-tokens", type=int, default=3500)
    parser.add_argument("--reference-package", type=Path)
    parser.add_argument("--raw-response", type=Path)
    args = parser.parse_args()
    read = lambda x: json.loads(x.read_text(encoding="utf8"))
    request = read(args.request_package)
    if args.reference_package or args.raw_response:
        if not (args.reference_package and args.raw_response):
            parser.error("Both reference and response are required for offline scoring")
        result = evaluate(
            request_package=request,
            reference_package=read(args.reference_package),
            raw_response=read(args.raw_response),
        )
    else:
        result = preflight(request_package=request, model=args.model,
                           max_tokens=args.max_tokens)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
