"""SERA v0.15 forensic offline recovery of ONE already-paid blind model reply.

Only accepts a raw JSON object or one whole JSON code fence. Repairs a
known provider serialization failure: unescaped dialogue double-quotes
inside a SINGLE-LINE support_quote field. Then source-bind each row
individually with the SAME strict v0.15 row validator, restoring source
typographic quotes only on a unique, length-preserving exact match.

An invalid relationship/classification is QUARANTINED, never rewritten
or silently converted into the model's abstention. Other valid rows
remain untrusted advisory proposals, NOT human gold or World authority.
No model/provider requests, no state writes, no paid retries.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import re

from experiments.sera.coverage import CoverageError
from experiments.sera.haiku_evidence_recovery_v011 import (
    parse_json_model_reply,FENCE,
)
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.blind_identity_v015 import (
    make_request,validate_model_row,_input,_check_cycle,
)

ORIGINAL_RUN_ID=38872615837
ORIGINAL_RESPONSE_ID="gen-1792138627-dbcmqQibflV3ANup75VW"
ORIGINAL_LAUNCH_ID="sera-v015-blind-38872615837"
MODEL="anthropic/claude-haiku-4.5"
# Exact historical request + source record binding; never reinterpret new prompt
# as being used to create a previous paid provider result.
ORIGINAL_REQUEST_SHA="089721729d3bc10e0f8e04569269e7857fe5176adc469a4cac2af8191b0d2d89"
ORIGINAL_MENTION_SHA="6778e4811979597b9bbe60ba3d88ad3794371640aa7dd97003550e0956f59077"
SOURCE_QUOTE_LINE=re.compile(
    r'^(?P<prefix>\s*"support_quote"\s*:\s*)"(?P<inner>.*)"(?P<suffix>\s*,?\s*)$'
)

def need(cond,code):
    if not cond:
        raise CoverageError(code)

def digest(raw:str):
    return sha256(raw.encode("utf-8")).hexdigest()

def fold_typography(text:str)->str:
    """Only length-preserving literal apostrophes and quote glyphs."""
    return (text.replace("’","'").replace("‘","'")
            .replace("“",'"').replace("”",'"'))

def recover_literal_json(raw:str)->tuple[dict,dict]:
    try:
        parsed,envelope=parse_json_model_reply(raw)
        return parsed,{
            "envelope":envelope,
            "fixed_support_quote_lines":0,
            "method":"NO_JSON_SERIALIZATION_REPAIR_NEEDED",
        }
    except CoverageError as exc:
        if str(exc)!="PROBE_FENCED_JSON_MALFORMED":
            raise
    match=FENCE.fullmatch(raw)
    need(match is not None,"V015_FORENSIC_ENVELOPE_NOT_WHOLE_FENCE")
    lines=match.group(1).splitlines()
    changed=[]
    out=[]
    for line_number,line in enumerate(lines,start=1):
        m=SOURCE_QUOTE_LINE.fullmatch(line)
        if not m:
            out.append(line)
            continue
        inner=m.group("inner")
        # Restrict repair to a single JSON string containing raw, not
        # backslash-escaped, double quotes. No general JSON5 or eval.
        if '"' not in inner:
            out.append(line)
            continue
        need("\\" not in inner,
             "V015_FORENSIC_COMPLEX_ESCAPES_NOT_REPAIRED")
        new=m.group("prefix")+json.dumps(
            inner,ensure_ascii=False
        )+m.group("suffix")
        changed.append({
            "source_response_line":line_number,
            "original_field_line_sha256":digest(line),
            "repaired_field_line_sha256":digest(new),
            "operation":"ESCAPE_UNESCAPED_JSON_DOUBLE_QUOTES_IN_SUPPORT_QUOTE_ONLY",
        })
        out.append(new)
    need(changed,"V015_FORENSIC_UNRECOGNIZED_JSON_FAILURE")
    try:
        parsed=json.loads("\n".join(out))
    except ValueError:
        raise CoverageError("V015_FORENSIC_JSON_STILL_INVALID") from None
    need(isinstance(parsed,dict),
         "V015_FORENSIC_JSON_ROOT_NOT_OBJECT")
    return parsed,{
        "envelope":"FULL_JSON_CODE_FENCE",
        "fixed_support_quote_lines":len(changed),
        "fixed_fields":changed,
        "method":"LOSSLESS_SUPPORT_QUOTE_JSON_STRING_ESCAPING_ONLY",
    }

def exact_source_quote(*,prose:str,source_map:dict,
                       mentions:dict,ref:str,row:dict)->tuple[str,str]:
    sent=source_map.get(row.get("support_sentence_id"))
    need(sent is not None and isinstance(row.get("support_quote"),str),
         "V015_FORENSIC_SUPPORT_SENTENCE_INVALID")
    need(sent["id"] in {
        h["sentence_id"] for h in mentions[ref]["source_evidence"]
    },"V015_FORENSIC_SUPPORT_NOT_MENTION_SENTENCE")
    quote=row["support_quote"]
    if quote in sent["quote"]:
        return quote,"EXACT_SOURCE_QUOTE"
    folded=fold_typography(quote)
    need(folded!=quote,
         "V015_FORENSIC_QUOTE_NOT_EXACT_OR_TYPOGRAPHIC")
    source_fold=fold_typography(sent["quote"])
    matching=[]
    start=0
    while True:
        index=source_fold.find(folded,start)
        if index<0:
            break
        original=sent["quote"][index:index+len(quote)]
        if original!=quote and fold_typography(original)==folded:
            matching.append(original)
        start=index+1
    need(len(matching)==1,
         "V015_FORENSIC_TYPOGRAPHY_NOT_UNIQUE_OR_SOURCE_MATCH")
    return matching[0],"UNIQUE_TYPOGRAPHIC_QUOTE_EQUIVALENCE_UNVERIFIED"

def verify_paid_provenance(*,evidence:dict,request:dict):
    need(isinstance(evidence,dict) and
         evidence.get("schema")==
             "sera.mara-s1-blind-identity-paid-pilot.v0.15" and
         evidence.get("launch_id")==ORIGINAL_LAUNCH_ID and
         evidence.get("provider_response_id")==ORIGINAL_RESPONSE_ID and
         evidence.get("model_requested")==MODEL and
         evidence.get("observed_model")==MODEL and
         evidence.get("request_sha256")==ORIGINAL_REQUEST_SHA and
         evidence.get("source_mentions_sha256")==ORIGINAL_MENTION_SHA and
         evidence.get("provider_attempts")==1 and
         evidence.get("finish_reason")=="stop" and
         evidence.get("provider_reported_cost")==0.015781 and
         evidence.get("status")=="IDENTITY_PROVIDER_OR_CONTRACT_HOLD" and
         evidence.get("error_code")=="PROBE_FENCED_JSON_MALFORMED" and
         evidence.get("output_token_limit_configured") is False and
         evidence.get("canonical_commit_authorized") is False and
         evidence.get("world_db_writes")==0 and
         evidence.get("new_entities_created")==0 and
         evidence.get("new_relationship_links")==0 and
         evidence.get("request_sha256")==request["request_sha256"] and
         request["census_sha256"]==ORIGINAL_MENTION_SHA,
         "V015_HISTORICAL_PAID_PROVENANCE_NOT_PINNED")

def forensic_rebind(*,prose:str,world:dict,census:dict,
                    evidence:dict)->dict:
    _source,unknown=_input(prose=prose,world=world,census=census)
    request=make_request(prose=prose,world=world,census=census)
    verify_paid_provenance(evidence=evidence,request=request)
    content=evidence.get("raw_provider_content")
    need(isinstance(content,str) and content,
         "V015_HISTORICAL_PROVIDER_CONTENT_MISSING")
    raw,syntax=recover_literal_json(content)
    need(set(raw)=={"rows"} and isinstance(raw["rows"],list),
         "V015_FORENSIC_RESPONSE_SCHEMA_INVALID")
    rows=raw["rows"]
    ids=[r.get("entity_ref") if isinstance(r,dict) else None for r in rows]
    need(len(rows)==len(unknown) and len(set(ids))==len(ids) and
         set(ids)==unknown,"V015_FORENSIC_MISSING_OR_EXTRA_MODEL_ROWS")
    source_map={s["id"]:s for s in sentences(prose)}
    mentions={i["entity_ref"]:i for i in census["items"]}
    accepted=[]
    quarantine=[]
    typography=[]
    source_bound_row_map={}
    for row in rows:
        ref=row["entity_ref"]
        repaired=deepcopy(row)
        if row.get("decision")=="PROPOSE" and isinstance(
            row.get("support_quote"),str
        ):
            try:
                exact,method=exact_source_quote(
                    prose=prose,source_map=source_map,
                    mentions=mentions,ref=ref,row=row)
                repaired["support_quote"]=exact
                if method!="EXACT_SOURCE_QUOTE":
                    typography.append({
                        "entity_ref":ref,
                        "raw_model_support_quote":row["support_quote"],
                        "exact_source_support_quote":exact,
                        "method":method,
                    })
            except CoverageError as exc:
                quarantine.append({
                    "entity_ref":ref,"model_row_unmodified":row,
                    "error_code":str(exc),
                    "status":"MODEL_ROW_QUARANTINED_NOT_ABSTAIN",
                })
                continue
        try:
            checked=validate_model_row(
                ref=ref,row=repaired,world=world,request=request,
                mentions=mentions,source_map=source_map,
            )
            accepted.append(checked)
            source_bound_row_map[ref]=repaired
        except CoverageError as exc:
            quarantine.append({
                "entity_ref":ref,"model_row_unmodified":row,
                "error_code":str(exc),
                "status":"MODEL_ROW_QUARANTINED_NOT_ABSTAIN",
            })
    # All source-bound valid subset rows must also form an acyclic
    # prospective graph; otherwise quarantine all group-level evidence.
    try:
        _check_cycle(source_bound_row_map)
    except CoverageError as exc:
        quarantine.extend({
            "entity_ref":v["entity_ref"],
            "model_row_unmodified":next(x for x in rows
                                         if x["entity_ref"]==v["entity_ref"]),
            "error_code":str(exc),
            "status":"MODEL_ROW_QUARANTINED_NOT_ABSTAIN",
        } for v in accepted)
        accepted=[]
    need(len(accepted)+len(quarantine)==len(unknown),
         "V015_FORENSIC_LOST_MODEL_ROW")
    return {
        "schema":"sera.paid-blind-identity-forensic-recovery.v0.15.1",
        "source_run_id":ORIGINAL_RUN_ID,
        "source_model":MODEL,
        "provider_reported_cost_original":0.015781,
        "original_paid_request_sha256":ORIGINAL_REQUEST_SHA,
        "source_prose_sha256":request["source_prose_sha256"],
        "source_mentions_sha256":ORIGINAL_MENTION_SHA,
        "raw_provider_content_sha256":digest(content),
        "syntax_repair_audit":syntax,
        "typographic_source_quote_mapping":typography,
        "all_original_model_rows_returned":len(rows),
        "source_bound_model_proposals":accepted,
        "quarantined_original_model_rows":quarantine,
        "source_bound_count":len(accepted),
        "quarantine_count":len(quarantine),
        "independent_model_abstained_count":sum(
            x["decision"]=="ABSTAIN" for x in accepted),
        "paid_model_calls_during_recovery":0,
        "new_entity_creations":0,
        "new_relation_attachments":0,
        "world_db_writes":0,
        "canonical_commit_authorized":False,
        "human_gold_adjudicated":False,
        "status":(
            "PARTIALLY_RECOVERED_SOURCE_BOUND_PROPOSALS_SEMANTIC_HOLD"
            if quarantine else
            "ALL_RECOVERED_SOURCE_BOUND_MODEL_OPINIONS_SEMANTIC_HOLD"
        ),
    }
