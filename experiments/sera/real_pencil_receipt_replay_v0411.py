"""SERA v0.41.1: Rebind immutable REAL pencil-model replies, ZERO new calls.

Only accept exact complete JSON/code-fence and discard one documented
NONSEMANTIC extra field: mention.reason (never event.reason). Original
response and every stripped value remain referenced by immutable SHA-256.
No model-proposed physical motion is canonical; observer != mover.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import argparse
import json
from pathlib import Path

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import parse_json_model_reply
from experiments.sera.real_blind_benchmark_v040 import MODELS, EXPECTED_SHA, _cost
from experiments.sera.real_pencil_benchmark_v041 import prepare
from experiments.sera.sentence_sweep_v010 import bind_batch, summarize_partial
from experiments.sera.world_state_v02 import canonical

SCHEMA = "sera.real-pencil-receipt-replay.v0.41.1"
EVIDENCE_RUN = 38938438488
EVIDENCE_ARTIFACT = 12061129188
IMMUTABLE_SHA = {
    "provider_reply_1.json":
        "1cf73a0d155d442985466d535193e533e28c1206a5b9fa7c3a4654c4d02ba60a",
    "provider_reply_2.json":
        "d6f0636dd73cf9b5e3612be7fedd34cdf86f8ee9f7944ce60a9b990c7ff0f214",
    "result.json":
        "e27da5e9b780f51167e4eae28e01791e248450e91bbedad943f7fc1e116a98fb",
}
MENTION_FIELDS = frozenset({
    "entity_ref","role","evidence_quote","occurrence",
})


def require(ok,code):
    if not ok:
        raise CoverageError(code)


def load_archived(directory):
    root=Path(directory)
    result={}
    for file,expected in IMMUTABLE_SHA.items():
        data=(root/file).read_bytes()
        require(sha256(data).hexdigest()==expected,
                "V0411_RECEIPT_HASH_MISMATCH:"+file)
        result[file]=json.loads(data)
    return result


def normalize_only_safe_advisory_fields(raw):
    """This never edits a model's actor, quote, epistemic, kind or event."""
    parsed=deepcopy(raw)
    repairs=[]
    require(isinstance(parsed,dict) and set(parsed)=={"rows"} and
            isinstance(parsed["rows"],list),
            "V0411_SOURCE_REPLY_SCHEMA_INVALID")
    for row in parsed["rows"]:
        require(isinstance(row,dict) and
                isinstance(row.get("mentions"),list),
                "V0411_MENTION_LIST_INVALID")
        for mention in row["mentions"]:
            require(isinstance(mention,dict),"V0411_MENTION_NOT_OBJECT")
            extras=set(mention)-MENTION_FIELDS
            if extras=={"reason"} and isinstance(mention["reason"],str):
                repairs.append({
                    "sentence_id":row.get("sentence_id"),
                    "entity_ref":mention.get("entity_ref"),
                    "operation":"REMOVE_UNSUPPORTED_ADVISORY_MENTION_REASON",
                    "old_value_sha256":sha256(
                        mention["reason"].encode("utf-8")
                    ).hexdigest(),
                })
                del mention["reason"]
            else:
                require(not extras, "V0411_UNSAFE_EXTRA_MENTION_FIELD")
    return parsed,repairs


def replay(directory):
    archives=load_archived(directory)
    plan=prepare()
    header=archives["result.json"]
    require(header.get("schema")=="sera.real-pencil-blind-benchmark.v0.41" and
            header["source_prose_sha256"]==EXPECTED_SHA and
            header["request_sha256"]==plan["batch"]["request_sha256"] and
            header["target_sentence_id"]==plan["target_sentence_id"] and
            header["model_ids"]==list(MODELS) and
            header["provider_attempts"]==len(MODELS) and
            len(header["results"])==len(MODELS) and
            header["canonical_commit_authorized"] is False and
            header["production_db_writes"]==0,
            "V0411_ORIGINAL_LIVE_RUN_SCOPE_MISMATCH")
    rows=[]
    total_cost=0
    for i,model in enumerate(MODELS,1):
        provider=archives[f"provider_reply_{i}.json"]
        require(provider["model"]==model and
                provider["request_sha256"]==plan["batch"]["request_sha256"] and
                provider["provider_envelope"]["error"] is None,
                "V0411_PROVIDER_RECEIPT_SCOPE_MISMATCH")
        raw=provider["provider_envelope"]["raw"]
        original=header["results"][i-1]
        require(raw.get("model")==original.get("observed_model") and
                raw.get("id")==original.get("provider_request_id") and
                isinstance(raw.get("choices"),list) and
                len(raw["choices"])==1 and
                raw["choices"][0].get("finish_reason")=="stop",
                "V0411_PROVIDER_RECEIPT_ID_OR_FINISH_MISMATCH")
        cost=_cost(raw.get("usage"))
        require(cost is not None and
                str(cost)==str(original["provider_cost_usd"]),
                "V0411_PROVIDER_COST_INCONSISTENT")
        total_cost+=cost
        content=raw["choices"][0]["message"]["content"]
        require(isinstance(content,str) and bool(content.strip()),
                "V0411_EMPTY_REAL_MODEL_RESPONSE")
        row={
            "model":model,
            "provider_request_id":raw["id"],
            "original_content_sha256":sha256(content.encode()).hexdigest(),
            "original_status":original["status"],
            "cost_usd":str(cost),
            "json_envelope":None,
            "source_bound":False,
            "pencil_source_mention":False,
            "event_count":0,
            "mention_count":0,
            "structural_repairs":[],
            "semantic_faults_or_unknowns":[],
            "status":"HOLD",
            "canonical_commit_authorized":False,
            "production_db_writes":0,
        }
        try:
            parsed,envelope=parse_json_model_reply(content)
            parsed,repairs=normalize_only_safe_advisory_fields(parsed)
            row["json_envelope"]=envelope
            row["structural_repairs"]=repairs
            bound=bind_batch(
                plan=plan["plan"],batch_id=plan["batch"]["batch_id"],
                raw=parsed,prose=plan["prose"],
            )
            partial=summarize_partial(
                plan=plan["plan"],bound_batches=[bound],
            )
            mentions=[(r["sentence_id"],m) for r in bound["rows"]
                      for m in r["mentions"]]
            events=[(r["sentence_id"],e) for r in bound["rows"]
                    for e in r["events"]]
            row["source_bound"]=True
            row["mention_count"]=len(mentions)
            row["event_count"]=len(events)
            row["status"]="SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD"
            row["pencil_source_mention"]=any(
                sid==plan["target_sentence_id"] and
                m["entity_ref"] in ("new:pencil","candidate:pencil") and
                "pencil" in m["quote"].casefold()
                for sid,m in mentions
            )
            row["model_event_summaries"]=[{
                "sentence_id":r["sentence_id"],
                "disposition":r["disposition"],
                "kinds":[e["kind"] for e in r["events"]],
                "epistemic":[e["epistemic"] for e in r["events"]],
            } for r in bound["rows"]]
            if any(e["kind"]=="MOVE" for sid,e in events
                   if sid==plan["target_sentence_id"]):
                row["semantic_faults_or_unknowns"].append(
                    "V0411_PENCIL_MOVE_CAUSAL_AGENT_NOT_ESTABLISHED"
                )
            if any(
                m["entity_ref"]=="new:unidentified_female"
                for _,m in mentions
            ):
                row["semantic_faults_or_unknowns"].append(
                    "V0411_NEW_UNIDENTIFIED_CHARACTER_NOT_EVIDENCED"
                )
            if partial.get("findings"):
                row["semantic_faults_or_unknowns"].append(
                    "V0411_UNRESOLVED_PARTIAL_SWEEP_FINDINGS"
                )
        except (CoverageError,ValueError,KeyError,TypeError) as exc:
            row["status"]="STRUCTURAL_OR_SOURCE_BIND_HOLD"
            row["semantic_faults_or_unknowns"].append(
                "V0411_BIND_ERROR:"+str(exc)[:180]
            )
        rows.append(row)
    require(str(total_cost)==header["observed_spend_usd"],
            "V0411_PROVIDER_SPEND_LEDGER_MISMATCH")
    return {
        "schema":SCHEMA,"source_run_id":EVIDENCE_RUN,
        "source_artifact_id":EVIDENCE_ARTIFACT,
        "original_scene_sha256":EXPECTED_SHA,
        "status":"REAL_PENCIL_RECEIPTS_REBOUND_NONCANONICAL",
        "models":rows,"provider_reported_total_cost_usd":str(total_cost),
        "additional_provider_calls":0,
        "semantic_completeness_proven":False,
        "canonical_commit_authorized":False,
        "production_db_writes":0,"sqlite_lab_writes":0,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--receipt-dir",type=Path,required=True)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    report=replay(args.receipt_dir)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(
            json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
            encoding="utf-8",
        )
    print(json.dumps({
        "status":report["status"],
        "new_provider_calls":0,
        "total_cost_usd":report["provider_reported_total_cost_usd"],
        "models":[{
            "model":x["model"],"source_bound":x["source_bound"],
            "pencil":x["pencil_source_mention"],
            "events":x["event_count"],
            "structural_repairs":len(x["structural_repairs"]),
            "findings":x["semantic_faults_or_unknowns"],
        } for x in report["models"]],
    },ensure_ascii=False))


if __name__=="__main__":
    main()
