"""Sanitized read-only diagnostic for consumed one-shot quality-provider attempts.

Safe on CI: no raw message, prompt, story, exception string, API key or
unverified ACCEPT. It cannot discover the root cause of past attempts
where the original response was discarded. For later independent audits
capture this metadata before re-raising the terminal no-retry STOP.
"""
from decimal import Decimal, InvalidOperation
import re

from src.story_harness_p417_live_pilot import ProviderTransportFault
from src.story_harness_v1 import HarnessStop

MESSAGES={
    "Wrong independent auditor model":"AUDITOR_MODEL_MISMATCH",
    "Quality provider token accounting missing":"AUDITOR_TOKEN_ACCOUNTING_INVALID",
    "Original 0.040 initial-audit cost cap exceeded":"AUDITOR_RETURNED_COST_OVER_CAP",
    "Audit incomplete/truncated":"AUDITOR_RESPONSE_INCOMPLETE",
    "Audit response is not bounded text":"AUDITOR_RESPONSE_OVERSIZED",
    "Audit output contract mismatch":"AUDITOR_JSON_CONTRACT_INVALID",
    "Invalid strict quality JSON content":"AUDITOR_JSON_INVALID",
    "Quality auditor was not bound to same immutable story+Spine":"AUDITOR_SOURCE_LINEAGE_MISMATCH",
    "Invalid audit findings":"AUDITOR_FINDINGS_INVALID",
    "Unanchored or invented blocking finding":"AUDITOR_QUOTE_NOT_GROUNDED",
    "Invalid literary evaluation":"AUDITOR_LITERARY_EVALUATION_INVALID",
    "Model cannot accept unresolved blockers or poor reader quality":"AUDITOR_VERDICT_CONFLICT",
    "Missing authoritative auditor generation ID":"AUDITOR_GENERATION_ID_MISSING",
}
COST_LIMIT=Decimal("10.00")

def _reportable_usage(response):
    if type(response) is not dict:
        return None,None,None
    rid=response.get("id")
    gid=rid if type(rid) is str and re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",rid) else None
    usage=response.get("usage")
    if type(usage) is not dict:
        return gid,None,None
    raw=usage.get("cost")
    try:
        amt=Decimal(str(raw))
        amount=format(amt,"f") if type(raw) in (str,int,float,Decimal) and amt.is_finite() and 0 <= amt <= COST_LIMIT else None
    except (TypeError,ValueError,InvalidOperation):
        amount=None
    tokens={}
    for field in ("prompt_tokens","completion_tokens"):
        val=usage.get(field)
        if type(val) is int and 0 <= val <= 500000:
            tokens[field]=val
    return gid,amount,tokens if len(tokens)==2 else None

def sanitized_failure_receipt(exc,response,*,case_id,story_sha256):
    if isinstance(exc,ProviderTransportFault):
        code="PROVIDER_"+exc.category
        hint=exc.hint
    elif isinstance(exc,HarnessStop):
        code=MESSAGES.get(str(exc),"AUDITOR_VALIDATION_UNCLASSIFIED")
        hint=None
    else:
        code="AUDITOR_UNHANDLED_EXCEPTION_STOP"
        hint=None
    gid,amount,tokens=_reportable_usage(response)
    receipt={
        "case_id":case_id,
        "source_story_sha256":story_sha256,
        "quality_initial_verdict":"STOP_UNKNOWN_OR_INVALID",
        "sanitized_failure_code":code,
        "provider_generation_id":gid,
        "auditor_reported_cost_usd":amount,
        "auditor_usage":tokens,
        "english_master_authorized":False,
        "q25_authorized":False,
        "retry_allowed":False,
        "production_state_write_authorized":False,
        "model_attempt_consumed":True,
    }
    if hint is not None:
        receipt["safe_transport_hint"]=hint
    return receipt
