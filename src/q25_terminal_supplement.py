"""Q25 read-only supplemental terminal hypotheses for clocks and physical edges.

This is an *annotation* transport boundary for fields the existing extractor
cannot express. No inference from arbitrary prose, automatic truth certification,
model/API call, canonical State write or relaxation of frozen Q25 raw contracts.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import Field, StrictInt

from src.q25_entity_candidates import fingerprint
from src.q25_extractor_adapter import Quote, RawExtractorOutput, materialize_quotes, offline_replay
from src.q25_offline_diagnostic import Span, Strict, digest, valid_span
from src.q25_raw_reconciliation import project_raw


class ClockCandidate(Strict):
    field: str = Field(min_length=1, pattern=r"^minutes_until_[a-z0-9_]+$")
    expected_seed_value: StrictInt
    proposed_terminal_value: StrictInt
    evidence: Quote


class PhysicalEdgeCandidate(Strict):
    subject: str = Field(min_length=5)
    kind: Literal["ATTACHED_TO", "COVERING"]
    target: str = Field(min_length=5)
    evidence: Quote


class TerminalSupplement(Strict):
    schema_name: Literal["q25.terminal-supplement-annotation.v1"]
    source_kind: Literal["AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED"]
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    world_time_claims: list[ClockCandidate]
    physical_relation_claims: list[PhysicalEdgeCandidate]


def _quoted_span(prose: str, source_sha: str, quote: Quote):
    """Resolve a literal citation uniquely; never trust an LLM's supplied offset."""
    candidates = []
    start = prose.find(quote.quote)
    while start >= 0:
        end = start + len(quote.quote)
        if ((quote.context_before is None or prose[:start].endswith(quote.context_before))
                and (quote.context_after is None or prose[end:].startswith(quote.context_after))):
            candidates.append((start, end))
        start = prose.find(quote.quote, start + 1)
    if len(candidates) != 1:
        raise ValueError("Supplement citation absent or ambiguous in frozen story")
    start, end = candidates[0]
    span = Span(start=start, end=end, text=quote.quote)
    if not valid_span(prose, source_sha, span):
        raise ValueError("Invalid supplemental source span")
    return span.model_dump(mode="json")


def _explicit_turkish_minute_anchor(text: str, amount: int) -> bool:
    """Require an actually quoted number + dakika, not an unsupported guess.

    Bounded v1: Turkish 0..99 and plain digits. Semantic understanding,
    terminal relevance and chronology are still reserved for human review.
    """
    words = {"sıfır": 0, "bir": 1, "iki": 2, "üç": 3,
             "dört": 4, "beş": 5, "altı": 6, "yedi": 7,
             "sekiz": 8, "dokuz": 9}
    tens = {"on": 10, "yirmi": 20, "otuz": 30,
            "kırk": 40, "elli": 50, "altmış": 60,
            "yetmiş": 70, "seksen": 80, "doksan": 90}

    def parse_token(token):
        if token.isascii() and token.isdecimal():
            return int(token)
        return words.get(token, tens.get(token))

    lowered = text.lower()
    for match in re.finditer(r"(?<!\w)dakika\b", lowered):
        parts = lowered[:match.start()].strip().split()
        if not parts:
            continue
        last = parts[-1]
        if parse_token(last) == amount:
            return True
        if (len(parts) >= 2 and parts[-2] in tens and last in words
                and tens[parts[-2]] + words[last] == amount):
            return True
    return False


def project_supplement(*, seed, prose, raw_output, policy, supplement):
    """Derive two kinds of *unverified* terminal observations; leave raw unchanged."""
    inputs = copy.deepcopy((seed, prose, raw_output, policy, supplement))
    annotation = TerminalSupplement.model_validate(supplement)
    replay = offline_replay(seed=seed, prose=prose, raw_output=raw_output, policy=policy)
    if replay["status"] != "SOURCE_BOUND_CANDIDATES_ONLY":
        raise ValueError("Supplement requires source-bound extractor candidates")
    source_sha = digest(prose)
    materialized = materialize_quotes(seed=seed, prose=prose, raw_output=raw_output)
    if (annotation.seed_sha256 != fingerprint(seed)
            or annotation.source_sha256 != source_sha
            or annotation.raw_output_sha256 != materialized["raw_output_sha256"]):
        raise ValueError("Supplement source/raw extraction hashes do not match")
    # Replay the independent read-only candidate bridge. Its graph owns the
    # physical location/containment bookkeeping; sidecar edges never mutate it.
    base = project_raw(seed=seed, prose=prose, raw_output=raw_output, policy=policy)
    existing = {"object:" + name for name in seed["objects"]}
    proposed = {"new:" + item.key for item in RawExtractorOutput.model_validate(raw_output).objects}
    resolved = existing | proposed
    if len(existing) + len(proposed) != len(resolved):
        raise ValueError("Supplement object ID collision")

    clocks = []
    used_fields = set()
    for claim in annotation.world_time_claims:
        if claim.field in used_fields:
            raise ValueError("Duplicate or conflicting terminal clock proposal")
        used_fields.add(claim.field)
        saved = seed.get("world", {}).get("time", {}).get(claim.field)
        if type(saved) is not int or type(claim.expected_seed_value) is not int:
            raise ValueError("Only seeded integer countdowns are qualified")
        if type(claim.proposed_terminal_value) is not int:
            raise ValueError("Countdown candidate must be an integer, not a boolean")
        if claim.expected_seed_value != saved:
            raise ValueError("Countdown proposal rewrites the immutable seed")
        if not (0 <= claim.proposed_terminal_value < saved):
            raise ValueError("Countdown must decrease to a nonnegative explicit candidate")
        if not _explicit_turkish_minute_anchor(
                claim.evidence.quote, claim.proposed_terminal_value):
            raise ValueError("Countdown lacks its explicit numeric minute anchor")
        clocks.append({
            "path": "/world/time/" + claim.field,
            "seed_value": saved,
            "terminal_proposal": claim.proposed_terminal_value,
            "evidence": _quoted_span(prose, source_sha, claim.evidence),
            "authority": "AUTHOR_ANNOTATION_NOT_SEMANTICALLY_VERIFIED",
            "terminal_time_certified": False,
        })

    edges, edge_keys = [], set()
    for claim in annotation.physical_relation_claims:
        if claim.subject not in resolved or claim.target not in resolved:
            raise ValueError("Supplement uses unadmitted object identity")
        if claim.subject == claim.target:
            raise ValueError("Object cannot physically relate to itself")
        key = (claim.kind, claim.subject)
        if key in edge_keys:
            raise ValueError("Duplicate or contradictory physical relation proposal")
        edge_keys.add(key)
        edges.append({
            "subject": claim.subject,
            "kind": claim.kind,
            "target": claim.target,
            "evidence": _quoted_span(prose, source_sha, claim.evidence),
            "authority": "AUTHOR_ANNOTATION_NOT_SEMANTICALLY_VERIFIED",
            "source_binding_only": True,
            "owner_inferred": False,
            "location_inferred": False,
        })

    result = {
        "schema": "q25.terminal-supplement-projection.v1",
        "source_kind": annotation.source_kind,
        "seed_sha256": annotation.seed_sha256,
        "source_sha256": annotation.source_sha256,
        "raw_output_sha256": annotation.raw_output_sha256,
        "annotation_sha256": fingerprint(annotation.model_dump(mode="json")),
        "base_hypothesis_sha256": fingerprint(base),
        "base_hypothesis_status": base["raw_response_trust"],
        "world_time_candidates": clocks,
        "physical_relation_candidates": edges,
        "countdown_candidate_count": len(clocks),
        "physical_relation_candidate_count": len(edges),
        "existing_structural_consistency_preserved": True,
        "supplement_not_in_existing_extractor_contract": True,
        "independently_authenticated_reviewer": False,
        "semantic_support_certified": False,
        "full_story_state_qualified": False,
        "state_commit_authorized": False,
        "production_write_performed": False,
        "provider_calls": 0,
        "provider_cost_usd": 0.0,
    }
    if inputs != (seed, prose, raw_output, policy, supplement):
        raise AssertionError("Supplement projection mutated frozen evidence")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("request-package", "raw-response", "supplement"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    from src.q25_withheld_trial import unpack_request
    read = lambda path: json.loads(path.read_text(encoding="utf8"))
    trial = unpack_request(read(args.request_package))
    print(json.dumps(project_supplement(
        seed=trial["seed"], prose=trial["prose"], policy=trial["policy"],
        raw_output=read(args.raw_response), supplement=read(args.supplement),
    ), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
