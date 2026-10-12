"""Read-only review queue for differently worded *source-bound* story claims.

Pairs comparable character knowledge slots without declaring paraphrases equal.
An independently authenticated semantic reviewer is required for judgments.
No model call, automatic acceptance, canonical commit or cost.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from src.q25_extraction_benchmark import _claims
from src.q25_extractor_adapter import materialize_quotes, offline_replay
from src.q25_entity_candidates import fingerprint
from src.q25_offline_diagnostic import digest
from src.q25_withheld_trial import ReferencePackage, unpack_request


def _slot(claim):
    group, identity = claim["group"], claim["identity"]
    if group == "character_claims":
        return ["character_claims", identity[0], identity[1], identity[4]]
    if group == "terminal_relations":
        return [group, identity[0], identity[1]]
    if group == "property_claims":
        return [group, identity[0], identity[1]]
    if group == "goal_claims":
        return [group, identity[0], identity[1]]
    if group in ("obligation_claims", "thread_claims"):
        return [group, identity[0]]
    if group == "objects":
        return [group, identity[0]]
    raise ValueError("Unsupported review claim group")


def make_queue(*, request_package, reference_package, raw_response):
    original = copy.deepcopy((request_package, reference_package, raw_response))
    trial = unpack_request(request_package)
    reference = ReferencePackage.model_validate(reference_package)
    if (reference.request_id != trial["request_id"] or
            reference.seed_sha256 != fingerprint(trial["seed"]) or
            reference.source_sha256 != digest(trial["prose"])):
        raise ValueError("Unrelated evidence and reference package")
    for raw in (reference.raw_reference, raw_response):
        replay = offline_replay(
            seed=trial["seed"], prose=trial["prose"],
            raw_output=raw, policy=trial["policy"])
        if replay["status"] != "SOURCE_BOUND_CANDIDATES_ONLY":
            raise ValueError("A structurally rejected raw response cannot form this queue")
    materialize = lambda raw: _claims(materialize_quotes(
        seed=trial["seed"], prose=trial["prose"], raw_output=raw))
    labels = materialize(reference.raw_reference)
    predictions = materialize(raw_response)
    same = set(labels) & set(predictions)
    extras = {key: predictions[key] for key in sorted(set(predictions) - same)}
    missed = {key: labels[key] for key in sorted(set(labels) - same)}

    def by_slot(entries):
        indexed = {}
        for key, claim in entries.items():
            slot = fingerprint(_slot(claim))
            indexed.setdefault(slot, []).append((key, claim))
        return indexed

    extra_slots, missed_slots = by_slot(extras), by_slot(missed)
    paired = []
    paired_extra, paired_missed = set(), set()
    for slot in sorted(set(extra_slots) & set(missed_slots)):
        outgoing, incoming = extra_slots[slot], missed_slots[slot]
        # Multiple claims in a slot require a human, not arbitrary greedy pairing.
        if len(outgoing) != 1 or len(incoming) != 1:
            continue
        xkey, x = outgoing[0]
        ykey, y = incoming[0]
        paired_extra.add(xkey)
        paired_missed.add(ykey)
        paired.append({
            "group": x["group"], "semantic_slot": _slot(x),
            "candidate_identity": x["identity"],
            "reference_identity": y["identity"],
            "candidate_quotes": x["quotes"],
            "reference_quotes": y["quotes"],
            "disposition": "REVIEW_MEANING_EQUIVALENCE_NOT_AUTO_MATCHED",
            "decision_options": [
                "SEMANTICALLY_EQUIVALENT", "CANDIDATE_MORE_GENERAL",
                "CANDIDATE_UNSUPPORTED", "REFERENCE_INCOMPLETE",
                "DIFFERENT_FACTS", "UNDECIDED",
            ],
            "independent_decision": None,
        })
    quote_differences = [
        {"group": predictions[key]["group"],
         "identity": predictions[key]["identity"],
         "candidate_quotes": predictions[key]["quotes"],
         "reference_quotes": labels[key]["quotes"],
         "status": "DIFFERENT_EXCERPTS_NOT_AUTOMATIC_SEMANTIC_ERROR"}
        for key in sorted(same)
        if not set(labels[key]["quotes"]).issubset(set(predictions[key]["quotes"]))
    ]
    output = {
        "schema": "q25.semantic-gap-queue.v1",
        "request_id": trial["request_id"],
        "seed_sha256": reference.seed_sha256,
        "source_sha256": reference.source_sha256,
        "reference_sha256": fingerprint(reference.raw_reference),
        "raw_response_sha256": fingerprint(raw_response),
        "paired_meaning_review": paired,
        "unpaired_extra_claims": [
            extras[key] for key in sorted(set(extras) - paired_extra)],
        "unpaired_missing_claims": [
            missed[key] for key in sorted(set(missed) - paired_missed)],
        "matching_identity_different_excerpt": quote_differences,
        "raw_identity_overlap": len(same),
        "meaning_pairs_not_decided": len(paired),
        "independently_authenticated_reviewer": False,
        "semantic_equivalence_certified": False,
        "complete_state_certified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": 0.0,
    }
    if original != (request_package, reference_package, raw_response):
        raise AssertionError("Read-only review builder mutated evidence")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for part in ("request-package", "reference-package", "raw-response"):
        parser.add_argument("--" + part, type=Path, required=True)
    a = parser.parse_args()
    read = lambda file: json.loads(file.read_text(encoding="utf8"))
    print(json.dumps(make_queue(
        request_package=read(a.request_package),
        reference_package=read(a.reference_package),
        raw_response=read(a.raw_response),
    ), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
