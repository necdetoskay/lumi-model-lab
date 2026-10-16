"""SERA v0.7 — provenance-bound sentence review packet for frozen or new scenes.

A packet is a HUMAN REVIEW WORKSHEET, not a gold dataset and not a model
decision. Existing analyst-curated event candidates are included solely as
suggestions with exact source evidence; no label is pre-adjudicated.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.sentence_ledger_v06 import scanner
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.sentence-review-packet.v0.7"
LABELS = frozenset({
    "STATE_EVENT", "KNOWLEDGE_EVENT", "CLAIM_ONLY", "NO_TRACKED_CHANGE",
    "TEXTURE", "AMBIGUOUS",
})


def require(ok, code):
    if not ok:
        raise CoverageError(code)


def build_review_packet(*, prose: str, scene_key: str,
                        registry: dict[str, list[str]],
                        candidate_lexicon: dict[str, list[str]],
                        analyst_candidates: list[dict] | None = None) -> dict:
    """Build 28 source rows for Mara, or N source rows for any other scene."""
    require(isinstance(scene_key, str) and scene_key,
            "REVIEW_PACKET_SCENE_REQUIRED")
    scan = scanner(prose=prose, registry=registry,
                   candidate_lexicon=candidate_lexicon)
    candidates = analyst_candidates or []
    require(isinstance(candidates, list),
            "REVIEW_PACKET_CANDIDATES_INVALID")
    suggestions = []
    identifiers = set()
    rows = scan["sentences"]
    for candidate in candidates:
        require(isinstance(candidate, dict) and
                isinstance(candidate.get("candidate_id"), str) and
                candidate["candidate_id"] not in identifiers,
                "REVIEW_PACKET_EVENT_ID_INVALID")
        identifiers.add(candidate["candidate_id"])
        evidence = candidate.get("evidence")
        require(isinstance(evidence, dict) and
                type(evidence.get("start")) is int and
                type(evidence.get("end")) is int and
                0 <= evidence["start"] < evidence["end"] <= len(prose) and
                evidence.get("quote") ==
                prose[evidence["start"]:evidence["end"]],
                "REVIEW_PACKET_EVENT_EVIDENCE_INVALID")
        overlapping = [
            s["id"] for s in rows
            if s["start"] < evidence["end"] and
            evidence["start"] < s["end"] and
            prose[max(s["start"], evidence["start"]):
                  min(s["end"], evidence["end"])].strip()
        ]
        require(bool(overlapping), "REVIEW_PACKET_EVENT_NOT_IN_SENTENCE")
        suggestions.append({
            "candidate_id": candidate["candidate_id"],
            "event_type": candidate.get("event_type"),
            "epistemic": candidate.get("epistemic"),
            "sentence_ids": overlapping,
            "evidence": evidence,
            "status": "ANALYST_CANDIDATE_NOT_ADJUDICATED",
        })
    worksheet = []
    for s in rows:
        sid = s["id"]
        cues = next(x for x in scan["sentence_cues"]
                    if x["sentence_id"] == sid)
        worksheet.append({
            "sentence_id": sid,
            "start": s["start"], "end": s["end"], "quote": s["quote"],
            "entity_hints": [{
                "ref": h["ref"], "quote": h["quote"],
                "start": h["start"], "end": h["end"], "tier": h["tier"],
            } for h in scan["hints"] if h["sentence_id"] == sid],
            "cue_hints": cues["cues"],
            "time_expressions": cues["time_expressions"],
            "unresolved_pronouns": cues["pronouns"],
            "suggested_event_ids": [
                x["candidate_id"] for x in suggestions
                if sid in x["sentence_ids"]
            ],
            "review": {
                "status": "UNREVIEWED",
                "labels": [],
                "grounded_entity_refs": [],
                "grounded_event_ids": [],
                "unresolved_findings": [],
                "notes": "",
            },
        })
    payload = {
        "schema": SCHEMA,
        "scene_key": scene_key,
        "prose_sha256": prose_hash(prose),
        "source_character_length": len(prose),
        "review_status": "UNREVIEWED",
        "source_prose_unchanged": True,
        "source_type": "CANDIDATE_WORKSHEET_NOT_GOLD",
        "event_suggestions": suggestions,
        "sentences": worksheet,
        "adjudicated_gold": False,
        "canonical_commit_authorized": False,
    }
    payload["packet_sha256"] = sha256(
        canonical(payload).encode("utf-8")
    ).hexdigest()
    return payload


def validate_review_packet(*, prose: str, packet: dict) -> dict:
    """Refuse forged offsets, changed source and gold/self-approval claims."""
    require(isinstance(packet, dict) and packet.get("schema") == SCHEMA and
            packet.get("prose_sha256") == prose_hash(prose) and
            packet.get("source_character_length") == len(prose) and
            packet.get("source_type") == "CANDIDATE_WORKSHEET_NOT_GOLD" and
            packet.get("review_status") == "UNREVIEWED" and
            packet.get("adjudicated_gold") is False and
            packet.get("canonical_commit_authorized") is False,
            "REVIEW_PACKET_SOURCE_OR_AUTHORITY_INVALID")
    digest = packet.get("packet_sha256")
    copy = dict(packet)
    copy.pop("packet_sha256", None)
    require(digest == sha256(canonical(copy).encode("utf-8")).hexdigest(),
            "REVIEW_PACKET_DIGEST_MISMATCH")
    from experiments.sera.sentence_ledger_v06 import sentences
    expected = sentences(prose)
    got = packet.get("sentences")
    require(isinstance(got, list) and len(got) == len(expected),
            "REVIEW_PACKET_SENTENCE_COVERAGE_INVALID")
    for row, sentence in zip(got, expected):
        require(isinstance(row, dict) and
                row.get("sentence_id") == sentence["id"] and
                all(row.get(k) == sentence[k] for k in (
                    "start", "end", "quote"
                )), "REVIEW_PACKET_SENTENCE_MISMATCH")
        decision = row.get("review")
        require(isinstance(decision, dict) and
                decision.get("status") == "UNREVIEWED" and
                decision.get("labels") == [] and
                decision.get("grounded_event_ids") == [] and
                decision.get("grounded_entity_refs") == [],
                "REVIEW_PACKET_PREJUDGED_DECISION")
    for row in packet.get("event_suggestions", []):
        quote = row.get("evidence", {})
        require(isinstance(quote, dict) and
                type(quote.get("start")) is int and
                type(quote.get("end")) is int and
                0 <= quote["start"] < quote["end"] <= len(prose) and
                prose[quote["start"]:quote["end"]] == quote.get("quote") and
                row.get("status") == "ANALYST_CANDIDATE_NOT_ADJUDICATED",
                "REVIEW_PACKET_SUGGESTION_TAMPERED")
    return {
        "schema": "sera.review-packet-validation.v0.7",
        "sentence_count": len(got), "adjudicated": False,
        "status": "PENDING_EXTERNAL_HUMAN_ADJUDICATION",
        "model_calls": 0, "canonical_commit_authorized": False,
    }


def generate_mara_packet() -> dict:
    from experiments.sera.mara_s1_v04_audit import PATH, EXPECTED_SHA
    from experiments.sera.mara_s1_typed_live_v05 import REGISTRY, entry_state
    source = json.loads(PATH.read_text(encoding="utf-8"))
    prose = source["prose"]
    require(prose_hash(prose) == EXPECTED_SHA and
            source["source_prose_sha256"] == EXPECTED_SHA and
            source["production_commit_authorized"] is False,
            "REVIEW_PACKET_MARA_SOURCE_MISMATCH")
    available = entry_state()["entities"]
    registry = {k: v for k, v in REGISTRY.items() if k in available}
    lexicon = json.loads((
        Path(__file__).resolve().parent /
        "fixtures/object_candidate_lexicon_v0.1.json"
    ).read_text(encoding="utf-8"))["candidates"]
    return build_review_packet(
        prose=prose, scene_key=source["scene_id"], registry=registry,
        candidate_lexicon=lexicon,
        analyst_candidates=source["candidates"],
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    packet = generate_mara_packet()
    source = json.loads((
        Path(__file__).resolve().parent /
        "fixtures/mara_s1_real_eventgraph_candidates_v03.json"
    ).read_text(encoding="utf-8"))
    validate_review_packet(prose=source["prose"], packet=packet)
    rendered = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        print("MARA_S1_REVIEW_PACKET_WRITTEN", args.output)
        print("GOLD_STATUS", "UNREVIEWED")
    else:
        print(rendered)
