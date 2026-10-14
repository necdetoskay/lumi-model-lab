"""P4.24: evidence-only Q25 extraction from immutable PILOT English Master.

A genuine, one-use provider extraction produces PROPOSED state evidence, never
an authorized terminal world-state commit. All changed facts require exact
story quotations. Unknown ownership/time remain unknown.
"""
from __future__ import annotations

from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re

from src.story_harness_p410 import canonical_json
from src.story_harness_p416_input_bridge import sha
from src.story_harness_p417_live_pilot import MODEL, PROVIDER, https_post_once, money
from src.story_harness_p422_independent_audit import load_source
from src.story_harness_p423_master import read_audit, qualify_master
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p424-q25-evidence-proposal.v1"
OUTPUT_CAP = 3500
COST_CAP = Decimal("0.050")
RUN_NAME = "p424-b01-r06-q25-evidence-v01"
R02_RUN_NAME = "p424-b01-r06-q25-evidence-v02"

SAFE_FAILURE_CODE = {
    "Q25 provider model identity wrong": "PROVIDER_MODEL_MISMATCH",
    "Missing actual Q25 model token usage": "PROVIDER_TOKEN_USAGE_INVALID",
    "Q25 observed model stage exceeded allowed cost": "PROVIDER_COST_OVER_STAGE_CAP",
    "Incomplete Q25 generation": "Q25_MODEL_OUTPUT_TRUNCATED",
    "Q25 provider completion missing": "PROVIDER_CONTENT_ABSENT",
    "Q25 provider returned invalid JSON": "PROVIDER_JSON_PARSE_FAILED",
    "Q25 JSON envelope contract mismatch": "PROVIDER_ENVELOPE_SHAPE_INVALID",
    "Cross-story Q25 source identity": "Q25_LINEAGE_MISMATCH",
    "Q25 evidence_json not valid JSON": "Q25_NESTED_JSON_INVALID",
    "Q25 evidence proposal missing exact required fields": "Q25_FIELDS_MISSING_OR_EXTRA",
    "Q25 final location not within canonical locations": "Q25_FINAL_LOCATION_NOT_CANON",
    "Invented or overbroad Q25 prose evidence": "Q25_UNGROUNDED_QUOTE",
    "Final location citation not from story ending": "Q25_FINAL_LOCATION_NOT_END_ANCHORED",
    "Q25 discovered location evidence unbounded": "Q25_LOCATION_COUNT_INVALID",
    "Q25 unknown/duplicate/no-new location": "Q25_DISCOVERY_UNGROUNDED",
    "Q25 final location not previously known or discovered with proof": "Q25_FINAL_LOCATION_UNPROVEN",
    "Q25 object extraction unbounded": "Q25_OBJECT_COUNT_INVALID",
    "Q25 object cannot establish unproven ownership": "Q25_OBJECT_RELATION_OR_OWNER_INVALID",
    "Q25 object is not mentioned in its quoted evidence": "Q25_OBJECT_NAME_NOT_IN_QUOTE",
    "Canonical obligations missing or duplicated": "Q25_OBLIGATION_COUNT_INVALID",
    "Q25 did not account for exact original obligations": "Q25_OBLIGATION_ID_OR_STATUS_INVALID",
    "Unknown ownership/locations cannot be overwritten by Writer inference": "Q25_UNKNOWN_FACTS_NOT_PRESERVED",
    "Unobserved numeric world time must not be invented": "Q25_WORLD_TIME_INVENTED",
    "Missing bounded model extraction explanation": "Q25_EXPLANATION_MISSING",
}

ALLOWED_RELATIONS = {
    "HELD_BY_PROTAGONIST", "AT_HOME", "AT_MEADOW", "WITH_PROTAGONIST",
    "LAST_SEEN_UNKNOWN", "AT_WINDOW",
}
ALLOWED_OBLIGATION_STATUSES = {"SATISFIED","OPEN","UNPROVEN"}

def must(check, message):
    if not check:
        raise HarnessStop(message)


def _read(path):
    must(path.is_file() and not path.is_symlink() and
         0 < path.stat().st_size < 150000,
         "Expected bounded immutable pilot Master source")
    return path.read_bytes()


def load_pilot_source(repo_root, claims_root, quality_root, master_root):
    source = load_source(repo_root, claims_root)
    audit = read_audit(source, quality_root)
    expected = qualify_master(source, audit)
    root = Path(master_root)
    must(root.is_dir() and not root.is_symlink(),
         "Sealed English Master root missing")
    folder = root / ("b01-"+expected["story_sha256"][:16])
    must(folder.is_dir() and not folder.is_symlink(),
         "Missing accepted same-story master")
    manifest = json.loads(_read(folder/"master-manifest.json"))
    raw_text = _read(folder/"ENGLISH_MASTER.txt")
    must(manifest.get("schema")=="lumi.story-harness-p423-pilot-english-master.v1"
         and manifest.get("artifact_type")=="PILOT_ONLY_IMMUTABLE_ENGLISH_MASTER"
         and manifest.get("source_story_sha256")==expected["story_sha256"]
         and manifest.get("accepted_story_sha256")==expected["story_sha256"]
         and manifest.get("source_pack_sha256")==expected["source_pack_sha256"]
         and manifest.get("approved_spine_sha256")==expected["spine_sha256"]
         and manifest.get("independent_auditor_generation_id")==
             expected["auditor_generation_id"]
         and manifest.get("manual_text_edits")==0
         and manifest.get("independent_initial_audit_verdict")=="ACCEPT"
         and manifest.get("q25_read_only_extraction_allowed") is True
         and manifest.get("production_master_published") is False
         and manifest.get("production_state_write_authorized") is False
         and manifest.get("full_original_frozen_v21_4_production_quality_accepted") is False,
         "Pilot-only master not strictly source matched")
    must(hashlib.sha256(raw_text).hexdigest()==expected["story_sha256"]
         and raw_text.decode("utf-8")==source["story"]["story_text"],
         "Pilot Master does not contain exact accepted Writer bytes")
    return {"source":source, "audit":audit, "master":manifest,
            "english_master_text":raw_text.decode("utf-8")}


def allowed_relations_for_canon(canon):
    # Do not ask Q25 to locate B02's cloud in B01 HOME/MEADOW.
    locations=canon["locations"]
    must(type(locations) is list and len(locations)>0,
         "Q25 original canonical locations missing")
    values={"HELD_BY_PROTAGONIST","WITH_PROTAGONIST","LAST_SEEN_UNKNOWN"}
    values.update("AT_"+place for place in locations
                  if type(place) is str and
                  re.fullmatch(r"[A-Z_]{2,32}",place))
    if "HOME" in locations:
        values.add("AT_WINDOW")
    return values


def extraction_wire(bundle):
    source=bundle["source"]
    pack, spine=source["pack"],source["spine"]
    canon=pack["canonical_state"]
    allowed=allowed_relations_for_canon(canon)
    system=(
        "You are an evidence-only read-only post-story State Extractor (Q25). "
        "Return a structured PROPOSAL, not a canonical state commit. This is "
        "an actual English children's story and approved source Spine. Use "
        "only quotes occurring VERBATIM in English_Master_Text. Do not "
        "reinterpret an ambiguous quote as a certain physical fact. "
        "Differentiate possession from ownership: carrying an object does "
        "NOT establish its owner. Names and properties of unobserved objects "
        "and locations must not be invented. Preserve unknown_facts. "
        "Give final_location as one of canonical_state.locations, plus a "
        "quote from the final 40 percent of the story proving location. "
        "Give discovered_locations only from canon locations not initially "
        "known, each with a verbatim quote showing actual discovery. "
        "Give at most six object_observations, each with a brief object name "
        "that appears in its quoted text, a last_seen_relation and an "
        "ownership field ALWAYS set to the exact string UNKNOWN. Do not "
        "infer ownership even if possession or affection is shown; later "
        "validation may determine an owner. Choose last_seen_relation from "
        "EXACT allowed enum: "+", ".join(sorted(allowed))+
        ". No other values. "
        "The evidence_json must encode an object with EXACT fields: "
        "final_location {location_id, quote}, discovered_locations "
        "list of {location_id, quote}, object_observations list of "
        "{object_name, last_seen_relation, ownership, quote}, "
        "open_obligation_outcomes list of {obligation, status, quote}, "
        "unknown_facts_retained copied verbatim as an array and "
        "world_time_delta JSON null. Quotes must match case and punctuation "
        "in English_Master_Text, with no paraphrasing. "
        "Each canonical open_obligation MUST have exactly one "
        "entry with its exact obligation text, a SATISFIED/OPEN/UNPROVEN "
        "status, and a short supporting verbatim quote. Numeric elapsed "
        "world time must stay unknown; no fabricated timestamps. "
        "Use flat JSON fields: source_pack_sha256, story_sha256, "
        "spine_sha256, evidence_json (a JSON-ENCODED STRING containing the "
        "structured observations), and explanation. This stage is NOT a "
        "final quality gate and CANNOT authorize production state writes."
    )
    payload={
        "case_id":source.get("case_id","B01"),
        "source_pack_sha256":pack["pack_sha256"],
        "story_sha256":source["story"]["story_sha256"],
        "spine_sha256":spine["spine_sha256"],
        "reader_age":pack["reader_age"],
        "original_canonical_state":canon,
        "required_open_obligations":pack["open_obligations"],
        "unknown_facts_to_preserve":pack["unknown_facts"],
        "approved_story_spine":spine["spine"],
        "English_Master_Text":bundle["english_master_text"],
    }
    response_schema={
        "type":"object","additionalProperties":False,
        "properties":{
            "source_pack_sha256":{"type":"string"},
            "story_sha256":{"type":"string"},
            "spine_sha256":{"type":"string"},
            "evidence_json":{"type":"string"},
            "explanation":{"type":"string"},
        },
        "required":["source_pack_sha256","story_sha256","spine_sha256",
                    "evidence_json","explanation"],
    }
    body={
        "model":MODEL,
        "messages":[{"role":"system","content":system},
                    {"role":"user","content":canonical_json(payload).decode()}],
        "max_tokens":OUTPUT_CAP, "stream":False,
        "usage":{"include":True},
        "provider":{"only":[PROVIDER],"allow_fallbacks":False,
                    "require_parameters":True,
                    "max_price":{"prompt":2,"completion":10}},
        "response_format":{"type":"json_schema","json_schema":{
            "name":"lumi_"+source.get("case_id","B01").lower()+
                   "_q25_evidence_proposal_v1",
            "strict":True,"schema":response_schema}},
    }
    must(len(canonical_json(body))<24000,"Q25 prompt exceeds bounded size")
    return body


def _anchored(text, quote, *, final=False):
    must(type(quote) is str and
         7<=len(quote)<=500 and
         quote in text,
         "Invented or overbroad Q25 prose evidence")
    if final:
        must(text.rfind(quote)>=int(len(text)*0.60),
             "Final location citation not from story ending")


def verify_candidate(bundle, answer):
    source=bundle["source"]
    story=source["story"]
    pack=source["pack"]
    canon=pack["canonical_state"]
    must(type(answer) is dict and set(answer)=={
        "source_pack_sha256","story_sha256","spine_sha256",
        "evidence_json","explanation"},
        "Q25 JSON envelope contract mismatch")
    must(answer["source_pack_sha256"]==pack["pack_sha256"]
         and answer["story_sha256"]==story["story_sha256"]
         and answer["spine_sha256"]==source["spine"]["spine_sha256"],
         "Cross-story Q25 source identity")
    try:
        obs=json.loads(answer["evidence_json"])
    except (TypeError, ValueError):
        raise HarnessStop("Q25 evidence_json not valid JSON") from None
    must(type(obs) is dict and set(obs)=={
        "final_location","discovered_locations","object_observations",
        "open_obligation_outcomes","unknown_facts_retained",
        "world_time_delta"},
        "Q25 evidence proposal missing exact required fields")
    master=bundle["english_master_text"]
    fl=obs["final_location"]
    must(type(fl) is dict and set(fl)=={"location_id","quote"}
         and fl["location_id"] in canon["locations"],
         "Q25 final location not within canonical locations")
    _anchored(master,fl["quote"],final=True)
    discoveries=obs["discovered_locations"]
    must(type(discoveries) is list and
         len(discoveries)<=len(canon["locations"]),
         "Q25 discovered location evidence unbounded")
    known=set(canon["protagonist"]["known_locations"])
    found=set()
    for loc in discoveries:
        must(type(loc) is dict and set(loc)=={"location_id","quote"}
             and loc["location_id"] in canon["locations"]
             and loc["location_id"] not in known
             and loc["location_id"] not in found,
             "Q25 unknown/duplicate/no-new location")
        _anchored(master,loc["quote"])
        found.add(loc["location_id"])
    must(fl["location_id"] in known | found,
         "Q25 final location not previously known or discovered with proof")
    obj=obs["object_observations"]
    must(type(obj) is list and len(obj)<=6,
         "Q25 object extraction unbounded")
    for o in obj:
        must(type(o) is dict and set(o)=={
            "object_name","last_seen_relation","ownership","quote"}
            and type(o["object_name"]) is str
            and 3<=len(o["object_name"])<=80
            and type(o["last_seen_relation"]) is str
            and o["last_seen_relation"] in allowed_relations_for_canon(canon)
            and o["ownership"]=="UNKNOWN",
            "Q25 object cannot establish unproven ownership")
        _anchored(master,o["quote"])
        must(o["object_name"].lower() in o["quote"].lower(),
             "Q25 object is not mentioned in its quoted evidence")
    obligations=obs["open_obligation_outcomes"]
    must(type(obligations) is list and
         len(obligations)==len(pack["open_obligations"]),
         "Canonical obligations missing or duplicated")
    seen=set()
    for item in obligations:
        must(type(item) is dict and set(item)=={"obligation","status","quote"}
             and item["obligation"] in pack["open_obligations"]
             and item["obligation"] not in seen
             and item["status"] in ALLOWED_OBLIGATION_STATUSES,
             "Q25 did not account for exact original obligations")
        _anchored(master,item["quote"])
        seen.add(item["obligation"])
    must(obs["unknown_facts_retained"]==pack["unknown_facts"],
         "Unknown ownership/locations cannot be overwritten by Writer inference")
    must(obs["world_time_delta"] is None,
         "Unobserved numeric world time must not be invented")
    must(type(answer["explanation"]) is str and
         12<=len(answer["explanation"])<=2500,
         "Missing bounded model extraction explanation")
    return obs


def verify_model_response(bundle,response):
    must(type(response) is dict and response.get("model")==MODEL,
         "Q25 provider model identity wrong")
    usage=response.get("usage")
    must(type(usage) is dict and
         type(usage.get("prompt_tokens")) is int and
         type(usage.get("completion_tokens")) is int and
         usage["prompt_tokens"]>=0 and
         0<=usage["completion_tokens"]<=OUTPUT_CAP,
         "Missing actual Q25 model token usage")
    cost=money(usage.get("cost"))
    must(cost<=COST_CAP,"Q25 observed model stage exceeded allowed cost")
    choices=response.get("choices")
    must(type(choices) is list and len(choices)==1
         and choices[0].get("finish_reason")=="stop",
         "Incomplete Q25 generation")
    content=choices[0].get("message",{}).get("content")
    must(type(content) is str and len(content)<=45000,
         "Q25 provider completion missing")
    try:
        answer=json.loads(content)
    except (TypeError,ValueError):
        raise HarnessStop("Q25 provider returned invalid JSON") from None
    observations=verify_candidate(bundle,answer)
    gid=response.get("id")
    must(type(gid) is str and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",gid),
         "Missing actual Q25 generation identity")
    source=bundle["source"]
    return {
        "schema":SCHEMA,
        "case_id":source.get("case_id","B01"),
        "source_pack_sha256":source["pack"]["pack_sha256"],
        "spine_sha256":source["spine"]["spine_sha256"],
        "story_sha256":source["story"]["story_sha256"],
        "model":MODEL, "generation_id":gid,
        "evidence_proposal":observations,
        "provenance_verified":True,
        "quote_matching_verified":True,
        "semantic_state_fully_certified":False,
        "final_story_state_committed":False,
        "production_state_write_authorized":False,
        "prior_english_master_unchanged":True,
        "provider_usage":{
            "prompt_tokens":usage["prompt_tokens"],
            "completion_tokens":usage["completion_tokens"]},
        "provider_reported_cost_usd":format(cost,"f"),
    }


def _write_once(path,data):
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,"wb") as file:
        file.write(canonical_json(data)+b"\n")
        file.flush()
        os.fsync(file.fileno())


def extract_once(bundle, root, *, transport, run_variant="r01"):
    base=Path(root)
    must(base.is_dir() and not base.is_symlink(),
         "Protected Q25 evidence-only ledger root absent")
    must(run_variant in ("r01","r02"), "Disallowed Q25 one-use variant")
    folder=base/(RUN_NAME if run_variant=="r01" else R02_RUN_NAME)
    folder.mkdir(mode=0o700,exist_ok=False)
    body=extraction_wire(bundle)
    _write_once(folder/"00-intent.json",{
        "schema":SCHEMA, "run_variant":run_variant,
        "story_sha256":bundle["source"]["story"]["story_sha256"],
        "spine_sha256":bundle["source"]["spine"]["spine_sha256"],
        "request_sha256":hashlib.sha256(canonical_json(body)).hexdigest(),
        "maximum_model_posts":1,
        "stage_cost_cap_usd":format(COST_CAP,"f"),
        "automatic_retry":False,
        "state_write_authorized":False,
    })
    provider_response=None
    try:
        provider_response=transport(body)
        result=verify_model_response(bundle,provider_response)
        _write_once(folder/"01-q25-proposal.json",result)
        return result
    except Exception as exc:
        # Record only typed model envelope metadata, SHA and bounded safe reason.
        # Never copy untrusted model prose, provider errors or credentials.
        usage=(provider_response.get("usage")
               if type(provider_response) is dict else None)
        charge=None
        usage_counts=None
        if type(usage) is dict:
            try:
                charge=money(usage.get("cost"))
            except HarnessStop:
                pass
            if (type(usage.get("prompt_tokens")) is int and
                type(usage.get("completion_tokens")) is int and
                usage["prompt_tokens"]>=0 and
                usage["completion_tokens"]>=0):
                usage_counts={
                    "prompt_tokens":usage["prompt_tokens"],
                    "completion_tokens":usage["completion_tokens"]}
        gid=(provider_response.get("id") if
             type(provider_response) is dict else None)
        if not (type(gid) is str and
                re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",gid)):
            gid=None
        completion=None
        choices=(provider_response.get("choices") if
                 type(provider_response) is dict else None)
        finish_reason=None
        if type(choices) is list and len(choices)==1 and type(choices[0]) is dict:
            finish_reason=choices[0].get("finish_reason")
            message=choices[0].get("message")
            if type(message) is dict and type(message.get("content")) is str:
                completion=message["content"]
        if isinstance(exc,HarnessStop):
            why=SAFE_FAILURE_CODE.get(str(exc),"UNKNOWN_SAFE_CONTRACT_FAILURE")
        elif isinstance(exc,(ValueError,TypeError,KeyError)):
            why="Q25_RESPONSE_RUNTIME_SHAPE_ERROR"
        else:
            why="PROVIDER_POST_OR_UNKNOWN_EXCEPTION"
        if not (folder/"01-q25-proposal.json").exists():
            _write_once(folder/"01-q25-proposal.json",{
                "schema":SCHEMA,"case_id":"B01",
                "status":"STOP_UNKNOWN_OR_INVALID",
                "safe_failure_code":why,
                "provider_response_received":provider_response is not None,
                "provider_generation_id":gid,
                "provider_model_matched":
                    (provider_response.get("model")==MODEL
                     if type(provider_response) is dict else None),
                "finish_reason":
                    (finish_reason if finish_reason in
                     ("stop","length","content_filter") else "OTHER_OR_MISSING"),
                "provider_completion_sha256":
                    (hashlib.sha256(completion.encode("utf-8")).hexdigest()
                     if completion is not None else None),
                "billed_cost_usd":format(charge,"f") if charge is not None else None,
                "provider_usage":usage_counts,
                "state_write_authorized":False,"retry_allowed":False,
            })
        raise HarnessStop("Q25 consumed without retry; safe reason="+why) from None


def main():
    import argparse
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--repo-root",default=".")
    cli.add_argument("--producer-claims")
    cli.add_argument("--quality-claims")
    cli.add_argument("--master-root")
    cli.add_argument("--evidence-root")
    cli.add_argument("--paid-once",action="store_true")
    cli.add_argument("--run-variant",choices=("r01","r02"),default="r01")
    args=cli.parse_args()
    if not args.paid_once:
        print(json.dumps({"schema":SCHEMA,"model_calls":0,
                          "q25_candidate_authorized":False,
                          "production_state_write_authorized":False,
                          "stage_cap_usd":format(COST_CAP,"f")},sort_keys=True))
        return
    must(os.getenv("LUMI_P424_Q25_ENABLE")=="ONE_EVIDENCE_ONLY_B01_Q25"
         and args.run_variant=="r02",
         "Only corrected r02 Q25 attempt may send a provider request")
    must(args.producer_claims and args.quality_claims and args.master_root
         and args.evidence_root,
         "Q25 claim paths missing")
    bundle=load_pilot_source(args.repo_root,args.producer_claims,
                             args.quality_claims,args.master_root)
    result=extract_once(bundle,args.evidence_root,run_variant=args.run_variant,
        transport=lambda body:https_post_once(
            os.getenv("OPENROUTER_API_KEY",""),body))
    print(json.dumps({
        "schema":SCHEMA,
        "story_sha256":result["story_sha256"],
        "q25_evidence_observations":len(result["evidence_proposal"]["object_observations"]),
        "evidence_quote_matching_verified":result["quote_matching_verified"],
        "cost_usd":result["provider_reported_cost_usd"],
        "semantic_state_fully_certified":False,
        "production_state_write_authorized":False,
    },sort_keys=True))


if __name__=="__main__":
    main()
