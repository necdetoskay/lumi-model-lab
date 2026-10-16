"""SERA v0.10: forensic offline replay of one *already paid* provider artifact.

An actual completed model response can fail due to a strict JSON label
mismatch. Replay lets a repaired deterministic contract recover source-bound
candidates WITHOUT another API call. The original request SHA is preserved
even when subsequent extractor SYSTEM wording changes; the binder MUST NOT
pretend new prompt instructions were part of the original paid request.

Input is the exact JSON evidence or its GitHub Actions ZIP (result.json).
No network, model calls, approved state writes or gold metric generation.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import zipfile

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_sweep_pilot_v010 import (
    prepare, TARGET_QUOTE,
)
from experiments.sera.sentence_sweep_v010 import (
    bind_batch, summarize_partial,
)

PILOT_LAUNCH_ID = "sera-mara-v010-once-38860727745"
PILOT_REQUEST_SHA = (
    "137b7f4c44557f6507eaba6012ac0f6c8b5344b5d322de7a8082fdec391b3094"
)
PILOT_MODEL = "google/gemini-3.7-flash"
PILOT_BATCH = "batch_003"

def read_evidence(path: Path) -> dict:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            if archive.namelist() != ["result.json"]:
                raise CoverageError("V010_FORENSIC_ZIP_CONTENT_INVALID")
            return json.loads(archive.read("result.json"))
    return json.loads(path.read_text(encoding="utf-8"))


def replay(*, evidence: dict) -> dict:
    """Reinterpret only whitelisted grammatical role labels, no other repair."""
    plan_input = prepare()
    plan = plan_input["plan"]
    batch = plan_input["batch"]
    required = {
        "schema": "sera.mara-s1-sweep-paid-pilot.v0.10",
        "launch_id": PILOT_LAUNCH_ID,
        "model_requested": PILOT_MODEL,
        "observed_model": PILOT_MODEL,
        "source_prose_sha256": plan["source_prose_sha256"],
        "batch_id": PILOT_BATCH,
        "target_sentence_ids": batch["sentence_ids"],
        "request_sha256": PILOT_REQUEST_SHA,
        "provider_attempts": 1,
        "finish_reason": "stop",
        "status": "DIAGNOSTIC_INCOMPLETE_HOLD",
        "error_code": "SWEEP_MENTION_SCHEMA_INVALID",
        "max_model_output_tokens_configured": False,
        "semantic_completeness_proven": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
    }
    if not isinstance(evidence, dict) or any(
        evidence.get(k) != v for k, v in required.items()
    ):
        raise CoverageError("V010_FORENSIC_EVIDENCE_NOT_PINNED")
    raw = evidence.get("raw_extraction")
    if not isinstance(raw, dict):
        raise CoverageError("V010_FORENSIC_NO_COMPLETED_MODEL_CONTENT")
    # Verify raw text byte-for-byte round trips into the saved JSON output:
    # the JSON decode itself is the last non-semantic provider acceptance.
    content = evidence.get("provider_raw_content")
    try:
        parsed = json.loads(content)
    except (TypeError, ValueError):
        raise CoverageError("V010_FORENSIC_PROVIDER_CONTENT_INVALID") from None
    if parsed != raw:
        raise CoverageError("V010_FORENSIC_PROVIDER_RAW_CONFLICT")
    # A NEW prompt was authored to constrain mention-role labels after the
    # real paid call. Preserve the two distinct request fingerprints.
    bound = bind_batch(
        plan=plan, batch_id=PILOT_BATCH, raw=raw,
        prose=plan_input["prose"],
    )
    recovery = summarize_partial(plan=plan, bound_batches=[bound])
    events = [{
        "sentence_id": row["sentence_id"],
        **event,
    } for row in bound["rows"] for event in row["events"]]
    mentions = [{
        "sentence_id": row["sentence_id"],
        **mention,
    } for row in bound["rows"] for mention in row["mentions"]]
    preserved_claims = [
        e for e in events if e["kind"]=="CLAIM_MENTION" and
        e["epistemic"]=="REPORTED_CLAIM" and e["effect"]=="NONE"
    ]
    closing = [e for e in events if e["kind"]=="CLOSE" and
               e["quote"]=="closed" and
               e["epistemic"]=="OBSERVED_ACTION" and
               "new:watch_case" in e["entity_refs"]]
    if not closing:
        raise CoverageError("V010_FORENSIC_CLOSE_EVENT_NOT_RECOVERED")
    if not preserved_claims:
        raise CoverageError("V010_FORENSIC_REPORTED_CLAIMS_NOT_RECOVERED")
    unknown_body_part = [
        m["entity_ref"] for m in mentions
        if m["entity_ref"].startswith("new:") and
        m["quote"].casefold()=="thumb"
    ]
    return {
        "schema": "sera.mara-s1-v010-forensic-replay.v0.1",
        "source_launch_id": PILOT_LAUNCH_ID,
        "source_provider_response_id": evidence["provider_response_id"],
        "original_provider_request_sha256": PILOT_REQUEST_SHA,
        "replay_binder_request_sha256": batch["request_sha256"],
        "request_prompt_changed_since_paid_call":
            batch["request_sha256"] != PILOT_REQUEST_SHA,
        "raw_provider_content_sha256": sha256(
            content.encode("utf-8")
        ).hexdigest(),
        "source_prose_sha256": plan["source_prose_sha256"],
        "total_source_sentences": plan["sentence_count"],
        "model_returned_sentences": len(bound["rows"]),
        "recovered_candidate_mentions": len(mentions),
        "recovered_candidate_events": len(events),
        "lexical_role_aliases_mapped_to_only_mentioned": [
            {"sentence_id": m["sentence_id"],
             "raw_model_role": m["raw_model_role"],
             "entity_ref": m["entity_ref"]}
            for m in mentions
            if m["role_binding"] != "EXACT"
        ],
        "watch_case_closure_candidate_found": bool(closing),
        "provisional_watch_case_found": any(
            m["entity_ref"]=="new:watch_case" for m in mentions
        ),
        "body_part_candidates_must_not_auto_create_entity": unknown_body_part,
        "reported_claim_candidate_count": len(preserved_claims),
        "recovery_queue": recovery,
        "remaining_source_batches": len(recovery["pending_batch_ids"]),
        "provider_reported_cost_original": evidence.get("provider_reported_cost"),
        "paid_model_calls_during_replay": 0,
        "human_adjudicated": False,
        "canonical_commit_authorized": False,
        "world_db_writes": 0,
        "status": "RECOVERED_MODEL_CANDIDATES_ONLY_S1_HOLD",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("evidence",type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result=replay(evidence=read_evidence(args.evidence))
    output=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        if args.output.exists():
            raise CoverageError("V010_FORENSIC_OUTPUT_EXISTS")
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding="utf-8")
    print(output)


if __name__=="__main__":
    main()
