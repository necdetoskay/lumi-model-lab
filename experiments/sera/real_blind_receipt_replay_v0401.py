"""SERA v0.40.1 — Replay the TWO immutable real-provider v0.40 receipts.

No model calls or repairs to semantic content; only full JSON fence removal
via existing strict v0.11 parser, then original v0.10 source-binder and
partial sweep checks. A structural fix NEVER implies world-fact correctness.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.real_blind_benchmark_v040 import (
    EXPECTED_SHA, MODELS, prepare, _cost,
)
from experiments.sera.sentence_sweep_v010 import (
    bind_batch, summarize_partial,
)
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.real-blind-receipt-replay.v0.40.1"
SOURCE_RUN = 38936451931
ARTIFACT_ID = 12061516509
SHA256_RAW_FILES = {
    "provider_reply_1.json":
        "78dd205010eed4413fdfc92ffa7e2380fc2a676f7f1b07201a37ebb2da937712",
    "provider_reply_2.json":
        "848ca84824346792bb928c5452df10fa94aa18e783bc8ee4438c07ea992142c1",
    "result.json":
        "060f1542fcbea623b4d02788e1b2b222d726470299497be7ec9dec662d4b16c1",
}


def need(ok, code):
    if not ok:
        raise CoverageError(code)


def file_proof(directory):
    """Require every byte to match this run, not a swapped prior model."""
    root = Path(directory)
    result = {}
    for name, expected in SHA256_RAW_FILES.items():
        data = (root / name).read_bytes()
        need(sha256(data).hexdigest() == expected,
             "V0401_REAL_PAID_EVIDENCE_HASH_MISMATCH:" + name)
        result[name] = json.loads(data)
    return result


def replay(directory):
    archived = file_proof(directory)
    header = archived["result.json"]
    source = prepare()
    need(header.get("schema") == "sera.real-blind-benchmark.v0.40" and
         header["source_prose_sha256"] == EXPECTED_SHA and
         header["request_sha256"] == source["batch"]["request_sha256"] and
         header["target_sentence_id"] == source["target_sentence_id"] and
         header["model_ids"] == list(MODELS) and
         header["provider_attempts"] == len(MODELS) and
         len(header["results"]) == len(MODELS) and
         header["canonical_commit_authorized"] is False and
         header["production_db_writes"] == 0,
         "V0401_ARCHIVED_RUN_SCOPE_MISMATCH")
    output = []
    known_spend = 0
    for i, model in enumerate(MODELS, 1):
        receipt = archived[f"provider_reply_{i}.json"]
        need(receipt["model"] == model and
             receipt["request_sha256"] == source["batch"]["request_sha256"] and
             receipt["provider_envelope"]["error"] is None and
             header["results"][i-1]["requested_model"] == model,
             "V0401_PROVIDER_RECEIPT_SCOPE_MISMATCH")
        envelope = receipt["provider_envelope"]["raw"]
        need(isinstance(envelope,dict) and
             envelope.get("model") == header["results"][i-1]["observed_model"] and
             envelope.get("id") == header["results"][i-1]["provider_request_id"] and
             isinstance(envelope.get("choices"),list) and
             len(envelope["choices"]) == 1 and
             envelope["choices"][0]["finish_reason"] == "stop",
             "V0401_PROVIDER_ID_OR_FINISH_MISMATCH")
        measured = _cost(envelope.get("usage"))
        need(measured is not None and
             str(measured) == str(header["results"][i-1]["provider_cost_usd"]),
             "V0401_REAL_PROVIDER_COST_UNVERIFIED")
        known_spend += measured
        content = envelope["choices"][0]["message"]["content"]
        need(isinstance(content,str) and bool(content.strip()),
             "V0401_REAL_MODEL_CONTENT_EMPTY")
        raw_sha = sha256(content.encode("utf-8")).hexdigest()
        row = {
            "model":model,"provider_request_id":envelope["id"],
            "original_response_sha256":raw_sha,
            "source_prose_sha256":EXPECTED_SHA,
            "source_batch_request_sha256":source["batch"]["request_sha256"],
            "cost_usd":str(measured),
            "original_v040_status":header["results"][i-1]["status"],
            "original_target_bench_mentioned":
                header["results"][i-1]["target_bench_mentioned"],
            "repaired_only_json_envelope":False,
            "source_bound":False,"bench_source_mention":False,
            "candidate_mentions":0,"candidate_events":0,
            "status":"HOLD",
            "replay_findings":[],
            "independent_semantic_qualification":False,
        }
        try:
            parsed,envelope_kind = parse_json_model_reply(content)
            row["json_envelope"] = envelope_kind
            row["repaired_only_json_envelope"] = (
                envelope_kind == "FULL_JSON_CODE_FENCE"
            )
            bound = bind_batch(
                plan=source["plan"],batch_id=source["batch"]["batch_id"],
                raw=parsed,prose=source["prose"],
            )
            partial = summarize_partial(
                plan=source["plan"],bound_batches=[bound],
            )
            mentions = [
                (r["sentence_id"],m) for r in bound["rows"]
                for m in r["mentions"]
            ]
            events = [
                (r["sentence_id"],e) for r in bound["rows"]
                for e in r["events"]
            ]
            bench = [
                m for sid,m in mentions
                if sid == source["target_sentence_id"] and
                m["entity_ref"] in ("new:bench","candidate:bench") and
                "bench" in m["quote"].casefold()
            ]
            row.update({
                "status":"SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD",
                "source_bound":True,"bench_source_mention":bool(bench),
                "candidate_mentions":len(mentions),
                "candidate_events":len(events),
                "model_event_kinds_by_sentence":[
                    {
                        "sentence_id":r["sentence_id"],
                        "proposed_disposition":r["disposition"],
                        "kinds":[e["kind"] for e in r["events"]],
                    } for r in bound["rows"]
                ],
                "source_coverage_findings":partial.get("findings",[]),
            })
            # Advisory independent-of-model red flag, NOT automatic removal:
            # "watch open in his palm" denotes an observed state, not
            # evidence someone OPENED/CHANGED the watch during this scene.
            # The reader should inspect before any reducer event can exist.
            target = next(s for s in source["plan"]["source_sentences"]
                          if s["id"] == source["target_sentence_id"])
            if (any(sid == source["target_sentence_id"] and
                    ev["kind"] == "CHANGE_STATE" for sid,ev in events) and
                "pocket watch open" in target["quote"] and
                "opened" not in target["quote"].casefold()):
                row["replay_findings"].append(
                    "V0401_STATIC_WATCH_DESCRIPTION_MAY_BE_FALSE_TRANSITION"
                )
            if row["source_coverage_findings"]:
                row["replay_findings"].append(
                    "V0401_UNRESOLVED_SOURCE_SWEEP_FINDINGS"
                )
        except (CoverageError,ValueError,TypeError,KeyError) as exc:
            row["status"]="REBOUND_SOURCE_OR_ENVELOPE_HOLD"
            row["replay_findings"].append(
                "V0401_REPLAY_BIND_ERROR:" + str(exc)[:180]
            )
        output.append(row)
    need(str(known_spend) == header["observed_spend_usd"],
         "V0401_AGGREGATE_PROVIDER_COST_INCONSISTENT")
    return {
        "schema":SCHEMA,
        "status":"REPLAYED_ACTUAL_MODEL_EVIDENCE_NONCANONICAL",
        "source_run_id":SOURCE_RUN,"source_artifact_id":ARTIFACT_ID,
        "source_sha256":EXPECTED_SHA,
        "total_observed_cost_usd":str(known_spend),
        "provider_calls_during_replay":0,
        "production_db_writes":0,
        "sqlite_lab_writes":0,
        "canonical_commit_authorized":False,
        "independent_semantic_qualification":False,
        "semantic_recall_proven":False,
        "models":output,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipt-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    proof=replay(args.receipt_dir)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(proof,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "status":proof["status"],
        "cost_usd":proof["total_observed_cost_usd"],
        "models":[{
            "model":m["model"],"json_envelope":m.get("json_envelope"),
            "status":m["status"],"bench":m["bench_source_mention"],
            "events":m["candidate_events"],"mentions":m["candidate_mentions"],
            "replay_findings":m["replay_findings"],
        } for m in proof["models"]],
        "provider_calls_during_replay":0,
        "production_db_writes":0,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
