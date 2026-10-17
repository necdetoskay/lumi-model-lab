"""SERA v0.52 read-only independent per-POST receipt and cost auditor.

Reports immutable billing metadata without copying prompts or model prose.
No HTTP, secrets or DB writes. Missing/ambiguous/duplicated generation IDs,
missing provider cost/tokens or request fingerprint drift cannot produce PASS.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json

from experiments.sera.provider_grant_journal_v052 import JournalBlocked, _hash
from experiments.sera.delegated_paid_budget_v052 import _raw_envelope


def _nonneg_int(value):
    return type(value) is int and value >= 0


def audit_delegated_receipts(*, journal, approval_id):
    if not isinstance(approval_id, str) or not approval_id:
        raise JournalBlocked("V052_AUDIT_APPROVAL_ID_INVALID")
    with journal._connect() as db:
        rows=db.execute("""SELECT r.request_fingerprint,r.grant_id,r.request_id,
                                  r.stage,r.revision_sha,c.model,c.status,
                                  c.envelope_json,c.envelope_sha,
                                  c.request_sha,c.binding_sha,c.started_at,
                                  c.completed_at
                           FROM delegated_requests r
                           LEFT JOIN calls c ON c.grant_id=r.grant_id
                           WHERE r.approval_id=?
                           ORDER BY r.request_id""",
                        (approval_id,)).fetchall()
    receipts=[]
    total=Decimal("0")
    ids=set()
    complete=True
    for row in rows:
        (fingerprint,grant_id,request_id,stage,source_sha,model,status,encoded,
         archive_hash,request_sha,binding_sha,started,finished)=row
        line={"request_id":request_id,
              "request_fingerprint":fingerprint,
              "source_revision_sha256":source_sha,
              "stage":stage,"model_requested":model,
              "status":status or "RESERVED_NO_POST",
              "generation_id":None,
              "input_tokens":None,"output_tokens":None,
              "reasoning_tokens":None,"cost_usd":None,
              "duration_ms":None,
              "finish_reason":None}
        try:
            if status!="RECEIPTED" or not encoded:
                raise ValueError("pending or uncertain payment")
            envelope=json.loads(encoded)
            if not isinstance(envelope,dict) or _hash(envelope)!=archive_hash:
                raise ValueError("receipt hash does not match")
            body=_raw_envelope(envelope)
            if not isinstance(body,dict) or body.get("model")!=model:
                raise ValueError("provider model drift")
            generation=body.get("id")
            if not isinstance(generation,str) or not generation or generation in ids:
                raise ValueError("missing/duplicate generation ID")
            ids.add(generation)
            usage=body.get("usage")
            if not isinstance(usage,dict):
                raise ValueError("usage missing")
            inp=usage.get("prompt_tokens")
            out=usage.get("completion_tokens")
            if not _nonneg_int(inp) or not _nonneg_int(out):
                raise ValueError("token usage missing or invalid")
            try:
                cost=Decimal(str(usage["cost"]))
            except (KeyError,InvalidOperation,TypeError,ValueError) as exc:
                raise ValueError("cost missing") from exc
            if not cost.is_finite() or cost<0:
                raise ValueError("negative or infinite cost")
            choices=body.get("choices")
            if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):
                raise ValueError("completion choice missing")
            finish_reason=choices[0].get("finish_reason")
            if finish_reason!="stop":
                raise ValueError("provider completion not finished")
            duration=envelope.get("duration_ms")
            if type(duration) not in (int,float) or duration<0:
                raise ValueError("provider latency missing")
            details=usage.get("completion_tokens_details")
            reason=(details.get("reasoning_tokens") if isinstance(details,dict)
                    else usage.get("reasoning_tokens"))
            if reason is not None and not _nonneg_int(reason):
                raise ValueError("reasoning token count invalid")
            if not isinstance(request_sha,str) or len(request_sha)!=64 or (
                not isinstance(binding_sha,str) or len(binding_sha)!=64):
                raise ValueError("journal request/source fingerprints missing")
            line.update(generation_id=generation,
                        input_tokens=inp,output_tokens=out,
                        reasoning_tokens=reason,cost_usd=str(cost),
                        duration_ms=duration,finish_reason=finish_reason)
            total+=cost
        except (ValueError,TypeError,KeyError,InvalidOperation,JournalBlocked) as exc:
            complete=False
            line["audit_failure_code"]="V052_RECEIPT_UNQUALIFIED"
        receipts.append(line)
    return {
        "schema":"sera.v052-delegated-receipt-audit",
        "approval_id":approval_id,
        "status":"COMPLETE_NONCANONICAL" if complete and receipts else "INCOMPLETE_EVIDENCE_HOLD",
        "all_provider_receipts_qualified":bool(complete and receipts),
        "total_observed_usd":str(total),
        "provider_attempts_reserved":len(rows),
        "provider_attempts_qualified":sum(1 for x in receipts if x["generation_id"]),
        "receipts":receipts,
        "canonical_commit_authorized":False,
        "production_db_writes":0,
    }
