"""V4 pay-per-call one-use observation guard and durable provider receipts.

No prompt, raw body, API key, story text or story identity written in guard
events. Reports the full charged cost even when later validation fails.
No client output token ceilings; model/provider intrinsic limits still apply.
"""
from __future__ import annotations
import hashlib
import json
import os
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from unittest.mock import patch

from src.frozen_lane_verify import verify_frozen_lane

PROVIDER_MODELS=frozenset({
    "anthropic/claude-sonnet-5.5",
    "anthropic/claude-haiku-4.5",
    "openai/gpt-5.6-luna",
    "aion-labs/aion-3.5-mini",
    "openai/gpt-5.6-sol",
    "google/gemini-3.8-flash",
})
PROFILE=Path("data/specifications/story_lab/age18_story_lane_profile_v4_1.json")
SPEND_SOFT_STOP_USD=Decimal("2.00")
MAX_PROVIDER_CALLS=12


class V4PaidStop(RuntimeError):
    pass


def _cost(body:dict)->Decimal:
    usage=body.get("usage") if isinstance(body,dict) else None
    value=usage.get("cost") if isinstance(usage,dict) else None
    if isinstance(value,bool) or not isinstance(value,(int,float,str)):
        raise V4PaidStop("PROVIDER_COST_NOT_REPORTED")
    try:
        out=Decimal(str(value))
    except InvalidOperation as exc:
        raise V4PaidStop("PROVIDER_COST_INVALID") from exc
    if not out.is_finite() or out<0:
        raise V4PaidStop("PROVIDER_COST_INVALID")
    return out


class V4ProviderLedger:
    def __init__(self,*,evidence_dir:Path,max_reported_usd:Decimal=SPEND_SOFT_STOP_USD):
        if not max_reported_usd.is_finite() or max_reported_usd<=0:
            raise V4PaidStop("INVALID_PLANNING_SPEND_STOP")
        self.dir=evidence_dir
        self.dir.mkdir(parents=True,exist_ok=False)
        self.limit=max_reported_usd
        self.spent=Decimal("0")
        self.posts=0
        self.records=[]
        self.original_post=None

    def record(self,kind:str,**fields):
        n=len(self.records)+1
        obj={"schema":"v4-safe-paid-evidence.v1","kind":kind,**fields}
        data=(json.dumps(obj,sort_keys=True,ensure_ascii=True)+"\n").encode()
        path=self.dir/f"{n:03d}-{kind.lower()}.json"
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"wb") as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        self.records.append(obj)

    def post(self,url,**kwargs):
        from src.generate import OPENROUTER_URL
        if url!=OPENROUTER_URL:
            raise V4PaidStop("UNKNOWN_POST_DESTINATION")
        payload=kwargs.get("json")
        if not isinstance(payload,dict):
            raise V4PaidStop("NOT_JSON_POST")
        if any(key in payload for key in ("max_tokens","max_completion_tokens","max_output_tokens")):
            raise V4PaidStop("EXPLICIT_OUTPUT_TOKEN_CEILING_FORBIDDEN")
        if payload.get("model") not in PROVIDER_MODELS:
            raise V4PaidStop("UNQUALIFIED_PROVIDER_MODEL")
        if self.posts>=MAX_PROVIDER_CALLS:
            raise V4PaidStop("MORE_THAN_12_MODEL_CALLS")
        if self.spent>=self.limit:
            raise V4PaidStop("CUMULATIVE_OBSERVED_SPEND_LIMIT_REACHED")
        self.posts+=1
        model=payload["model"]
        digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        self.record("POST_INTENT",post=self.posts,model=model,request_sha256=digest)
        try:
            response=self.original_post(url,**kwargs)
        except BaseException as exc:
            self.record("NETWORK_FAILURE",post=self.posts,error_type=type(exc).__name__)
            raise
        self.record("HTTP_OBSERVED",post=self.posts,code=int(getattr(response,"status_code",0)))
        if getattr(response,"ok",False):
            try:body=response.json()
            except BaseException as exc:
                self.record("UNSETTLED_COST",post=self.posts,why="PROVIDER_JSON_UNREADABLE")
                raise V4PaidStop("PROVIDER_COST_UNSETTLED") from exc
            try:paid=_cost(body)
            except V4PaidStop as exc:
                self.record("UNSETTLED_COST",post=self.posts,why=str(exc))
                raise
            self.spent+=paid
            usage=body.get("usage") or {}
            self.record("PROVIDER_OBSERVED",post=self.posts,model=model,
                        generation_id=str(body.get("id") or "")[:150],
                        reported_cost_usd=str(paid),aggregate_cost_usd=str(self.spent),
                        input_tokens=usage.get("prompt_tokens"),
                        output_tokens=usage.get("completion_tokens"))
            if self.spent>self.limit:
                self.record("POLICY_STOP",reason="SPEND_OBSERVED_OVER_PLANNING_LIMIT",aggregate_cost_usd=str(self.spent))
                raise V4PaidStop("SPEND_OBSERVED_OVER_PLANNING_LIMIT")
        return response

    @contextmanager
    def installed(self):
        import requests
        from src import generate as g
        self.original_post=requests.post
        with patch.object(requests,"post",self.post),\
             patch.object(g,"OPENROUTER_RETRY_DELAYS_SECONDS",()),\
             patch.object(g,"_retry_delays_for_response",lambda *a,**kw:None):
            self.record("GUARD_INSTALLED",provider_posts_max=MAX_PROVIDER_CALLS,
                        observed_spend_planning_limit=str(self.limit),
                        no_explicit_max_tokens=True)
            yield self

    def summary(self):
        return {"provider_posts":self.posts,"provider_confirmed_cost_usd":str(self.spent),
                "cost_tracking":"post_observed_before_contract_parse",
                "additional_client_token_limit":False}


def verify_v4_source_pin(approved_commit:str)->None:
    import subprocess
    current=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if current!=approved_commit:
        raise V4PaidStop("SOURCE_SHA_NOT_APPROVED")
    if subprocess.check_output(["git","status","--porcelain"],text=True).strip():
        raise V4PaidStop("DIRTY_CODE_CHECKOUT")
    verification=verify_frozen_lane(PROFILE)
    if verification["runtime_revision"]!="AGE18-V4-SEMANTIC-REPLAN-REPAIR-v1" or verification["verified_files"]!=62:
        raise V4PaidStop("V4_1_62_FILE_REVISION_NOT_VALID")
