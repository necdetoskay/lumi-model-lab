"""Experimental v21.5 failure-only diagnostic quarantine for frozen v21.4 adapter.

Does not mutate frozen source, retry, authorize paid calls, or persist raw
provider/prompt material. Keeps SHA of original raw bytes and typed safe
structure, allowlisted validation path, usage with explicit missing fields.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re

SCHEMA="lumi.v21-p42-redacted-failure-diagnostic.v1"
SAFE_PHASES={"response_validation","usage_validation","transport","structured_parse"}
STAGE="FINAL_AUDIT"
_SECRET_PATTERNS=re.compile(
    r"(?i)(?:sk-[A-Za-z0-9_-]{12,}|(?:bearer|api[_-]?key|authorization)\s*[:=]\s*\S+)"
)
_PATH_PATTERN=re.compile(r"^\$(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d{1,3}\]){0,8}")
_USAGE_KEYS=("api_calls","input_tokens","output_tokens","total_tokens",
             "reasoning_tokens","cost_usd","latency_seconds")


def _raw_sha(obj):
    try:
        data=json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False,
                        allow_nan=False).encode("utf-8")
    except (TypeError,ValueError,OverflowError):
        return None
    return hashlib.sha256(data).hexdigest()


def _shape(obj,depth=0):
    if depth>=3:
        return {"type":type(obj).__name__,"truncated":True}
    if isinstance(obj,dict):
        fields=("findings","summary","family","severity","repair_scope","span_ids",
                "reason","exact_text","usage")
        return {
            "type":"object","field_count":len(obj),
            "known_fields":{k:_shape(obj[k],depth+1) for k in fields if k in obj},
            "unknown_field_count":sum(k not in fields for k in obj),
        }
    if isinstance(obj,list):
        return {"type":"array","length":len(obj),
                "first_item_shape":_shape(obj[0],depth+1) if obj else None}
    if isinstance(obj,str):
        return {"type":"string","length":len(obj)}
    if type(obj) in (int,float,bool) or obj is None:
        return {"type":type(obj).__name__}
    return {"type":"unrecognized"}


def _usage(value):
    if not isinstance(value,dict):
        return {"accounting_complete":False,"values":None,"missing_fields":list(_USAGE_KEYS)}
    values={}
    missing=[]
    for k in _USAGE_KEYS:
        v=value.get(k)
        if type(v) not in (int,float) or not math.isfinite(float(v)) or v<0:
            values[k]=None
            missing.append(k)
        elif k in ("api_calls","input_tokens","output_tokens","total_tokens","reasoning_tokens") and type(v) is not int:
            values[k]=None
            missing.append(k)
        else:values[k]=v
    return {"accounting_complete":not missing,"values":values,"missing_fields":missing}


def _safe_diagnostic(message):
    if not isinstance(message,str):return {"category":"UNSPECIFIED","schema_path":None}
    if "Missing required response field" in message:
        kind="MISSING_FIELD"
    elif "Unexpected response field" in message:
        kind="UNEXPECTED_FIELD"
    elif "Invalid response type" in message:
        kind="INVALID_TYPE"
    elif "response enum" in message.lower():
        kind="INVALID_ENUM"
    elif "Response length outside contract" in message:
        kind="INVALID_LENGTH"
    elif "response items" in message.lower():
        kind="DUPLICATE_ITEMS"
    elif "response integer" in message.lower():
        kind="INVALID_INTEGER"
    elif "usage" in message.lower() or "cost" in message.lower():
        kind="INVALID_USAGE"
    else:kind="UNSPECIFIED"
    m=_PATH_PATTERN.match(message)
    path=m.group(0) if m else None
    if path and _SECRET_PATTERNS.search(path):path=None
    return {"category":kind,"schema_path":path}


def describe_failure(exc, *, stage, input_sha256, source_story_sha256, run_id):
    if stage!=STAGE:raise RuntimeError("P4.2 diagnostics only supports targeted final audit")
    evidence=getattr(exc,"provider_evidence",None)
    evidence=evidence if isinstance(evidence,dict) else {}
    phase=evidence.get("phase")
    if phase not in SAFE_PHASES:phase="transport"
    raw=evidence.get("parsed_response")
    provider=evidence.get("provider_response")
    safe_usage=_usage(getattr(exc,"usage",None))
    # Only hashed provider response and payload identifiers, never messages,
    # prompt bodies, Authorization headers or raw sensitive story text.
    out={
        "schema":SCHEMA,"stage":STAGE,"run_id":run_id,
        "source_story_sha256":source_story_sha256,
        "request_input_sha256":input_sha256,
        "failure_exception_type":type(exc).__name__ if
            type(exc).__name__ in ("AdapterResponseError","OpenRouterCallError") else "OTHER",
        "phase":phase,
        "validation_diagnostic":_safe_diagnostic(getattr(exc,"diagnostic_message","")),
        "parsed_response_sha256":evidence.get("parsed_response_sha256")
           if isinstance(evidence.get("parsed_response_sha256"),str) else _raw_sha(raw),
        "parsed_response_safe_shape":_shape(raw),
        "provider_response_sha256":evidence.get("provider_response_sha256")
            if isinstance(evidence.get("provider_response_sha256"),str) else _raw_sha(provider),
        "wire_payload_sha256":evidence.get("wire_payload_sha256")
            if isinstance(evidence.get("wire_payload_sha256"),str) else None,
        "raw_response_redacted":True,
        "raw_sensitive_text_stored":False,
        "usage":safe_usage,
        "automatic_retry_executed":False,
        "story_quality_accepted":False,
        "english_master_seal_authorized":False,
        "q25_execution_authorized":False,
        "state_commit_authorized":False,
    }
    return out


def persist_failure(exc,*,stage,input_sha256,source_story_sha256,run_id,output_dir):
    record=describe_failure(exc,stage=stage,input_sha256=input_sha256,
                            source_story_sha256=source_story_sha256,run_id=run_id)
    root=Path(output_dir)
    if root.is_symlink():raise RuntimeError("Symlink diagnostic directory forbidden")
    root.mkdir(parents=True,exist_ok=True,mode=0o700)
    dest=root/"targeted-final-audit-diagnostic.json"
    content=(json.dumps(record,sort_keys=True,indent=2,ensure_ascii=False,
                        allow_nan=False)+"\n").encode("utf-8")
    fd=os.open(dest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        try:dest.unlink()
        except OSError:pass
        raise
    # Neither original secret/error strings nor unredacted provider evidence
    # are forwarded to the original v21 runtime call ledger.
    return record


class RedactedProviderFailure(RuntimeError):
    def __init__(self,original,record):
        super().__init__("REDACTED_FINAL_AUDIT_FAILURE:"+record["validation_diagnostic"]["category"])
        self.usage=record["usage"]["values"] if record["usage"]["accounting_complete"] else None
        self.provider_evidence={
            "schema":SCHEMA,"phase":record["phase"],
            "parsed_response_sha256":record["parsed_response_sha256"],
            "provider_response_sha256":record["provider_response_sha256"],
            "request_input_sha256":record["request_input_sha256"],
            "raw_sensitive_text_stored":False,
            "usage_accounting_complete":record["usage"]["accounting_complete"],
        }
        self.diagnostic_message=str(self)

