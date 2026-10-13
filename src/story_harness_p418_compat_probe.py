"""P4.18 isolated, tiny and once-only OpenRouter compatibility diagnostic.

After three consumed HTTP 400 story requests, test the provider with a PUBLIC
tiny synthetic prompt. No user story/Canon is transmitted. Stage 1 uses a bare
chat completion; stage 2 adds strict JSON schema. Both pin the same Sonnet
and Anthropic only, max 512 output tokens and no fallback/retry. A provider
failure ends this one-time attempt. Never mark any story quality accepted.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

from src.story_harness_p410 import canonical_json
from src.story_harness_v1 import HarnessStop

SCHEMA = "lumi.story-harness-p418-small-compatibility-probe.v1"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-sonnet-5.5"
MODEL_COST_CAP = Decimal("0.03")
ATTEMPT_COST_CAP = Decimal("0.06")
PROMPT = "For a format-compatibility check, return the JSON object {\"ok\":true}. Do not include other text."
MAX_REPLY = 8192
MAX_ERROR = 4096


def must(condition, reason):
    if not condition:
        raise HarnessStop(reason)


def _write_once(folder, name, value):
    path = folder / name
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as f:
        f.write(canonical_json(value)+b"\n")
        f.flush()
        os.fsync(f.fileno())


def build_wire(step):
    must(step in ("BASE_CHAT","STRICT_JSON"), "Unknown diagnostic step")
    body = {
        "model": MODEL,
        "messages": [{"role":"user","content":PROMPT}],
        "max_tokens": 512,
        "stream": False,
        "usage": {"include": True},
        "provider": {
            "only": ["Anthropic"], "allow_fallbacks": False,
            "max_price": {"prompt":2,"completion":10},
        },
    }
    if step == "STRICT_JSON":
        body["provider"]["require_parameters"] = True
        body["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "lumi_compatibility_probe",
                "strict": True,
                "schema": {
                    "type":"object",
                    "properties":{"ok":{"type":"boolean"}},
                    "required":["ok"],
                    "additionalProperties":False,
                },
            },
        }
    must(len(canonical_json(body)) < 4096, "Probe request too large")
    return body


def safe_error_hint(payload):
    """Only error.message on a synthetic prompt; aggressively redact secrets."""
    must(type(payload) in (bytes,bytearray), "Malformed response")
    body = payload[:MAX_ERROR].decode("utf-8", "replace")
    try:
        obj=json.loads(body)
        message=obj.get("error", {}).get("message", "")
        code=obj.get("error", {}).get("code")
        if type(message) is not str:
            message=""
        if type(code) not in (str,int):
            code=None
    except (ValueError,AttributeError):
        message=body
        code=None
    # Completely suppress provider echoes of bearer/credentials or arbitrary
    # sensitive data; probe prompt itself contains no user state.
    lower=message.lower()
    if any(x in lower for x in ("bearer", "sk-or-", "authorization:",
                               "api_key", "password", "private_key")):
        return {"category":"SENSITIVE_ERROR_REDACTED","message":"REDACTED"}
    message=re.sub(r"[^A-Za-z0-9 .,:;_'/()=\[\]{}<>+-]", " ",message)
    message=re.sub(r"\s+"," ",message).strip()[:300]
    safe_code=str(code)[:40] if code is not None else None
    if safe_code and not re.fullmatch(r"[A-Za-z0-9_ -]+",safe_code):
        safe_code="OTHER"
    return {"category":"PROVIDER_REJECTED",
            "code":safe_code,"message":message or "No safe message supplied"}


def http_post_once(api_key, body):
    must(type(api_key) is str and api_key.startswith("sk-or-"),
         "Provider bearer unavailable")
    req=urllib.request.Request(
        ENDPOINT, data=canonical_json(body), method="POST",
        headers={"Authorization":"Bearer "+api_key,
                 "Content-Type":"application/json",
                 "HTTP-Referer":"https://github.com/necdetoskay/lumi-model-lab",
                 "X-Title":"LUMI Model Lab"},
    )
    try:
        with urllib.request.urlopen(req,timeout=75) as reply:
            must(reply.status==200 and reply.geturl()==ENDPOINT,
                 "Unexpected compatibility response")
            payload=reply.read(MAX_REPLY+1)
            must(len(payload)<=MAX_REPLY,"Compatibility response too large")
        return {"http_status":200, "body":json.loads(payload)}
    except urllib.error.HTTPError as exc:
        try:
            raw=exc.read(MAX_ERROR+1)[:MAX_ERROR]
        except Exception:
            raw=b""
        return {"http_status":exc.code,"error":safe_error_hint(raw)}
    except Exception:
        raise HarnessStop("Compatibility transport unknown/no retry") from None


def _money(value):
    must(type(value) in (str,int,float) and type(value) is not bool,
         "Missing provider cost")
    try:
        n=Decimal(str(value))
    except (InvalidOperation,ValueError):
        raise HarnessStop("Invalid cost") from None
    must(n.is_finite() and 0<=n<=MODEL_COST_CAP,"Cost exceeds tiny stage cap")
    return n


def run_probe(root, api_key, *, post=http_post_once):
    """Never retry, always consume the entire probe on ambiguous status."""
    folder=Path(root)
    must(folder.is_dir() and not folder.is_symlink(),
         "Missing persistent private ledger directory")
    claim=folder / "p418-sonnet55-compat-v01"
    claim.mkdir(mode=0o700,exist_ok=False)
    _write_once(claim,"00-claim.json",{
        "schema":SCHEMA,"public_synthetic_prompt_only":True,
        "maximum_http_posts":2,"maximum_exposure_usd":"0.06",
        "prior_unknown_story_exposure_reserved_usd":"1.05",
        "total_user_budget_usd":"10.00",
        "status":"CONSUMED_BEFORE_ANY_POST","automatic_retries":False,
    })
    total=Decimal("0")
    output=[]
    for num,stage in enumerate(("BASE_CHAT","STRICT_JSON"),1):
        body=build_wire(stage)
        _write_once(claim,f"{num:02d}-{stage.lower()}-intent.json",{
            "schema":SCHEMA,"stage":stage,
            "wire_sha256":hashlib.sha256(canonical_json(body)).hexdigest(),
            "output_cap_tokens":512,"retry_allowed":False,
        })
        try:
            response=post(api_key,body)
            must(type(response) is dict and type(response.get("http_status")) is int,
                 "Unknown provider response")
            if response["http_status"]!=200:
                safe=response.get("error")
                must(type(safe) is dict and
                     safe.get("category") in ("PROVIDER_REJECTED",
                                             "SENSITIVE_ERROR_REDACTED"),
                     "Invalid diagnostic envelope")
                item={"stage":stage,"http_status":response["http_status"],
                      "error":safe,"billed_cost_usd":None,
                      "provider_generation_id":None,
                      "outcome":"PROVIDER_HTTP_ERROR"}
                output.append(item)
                _write_once(claim,f"{num:02d}-{stage.lower()}-receipt.json",item)
                break
            body_response=response.get("body")
            must(type(body_response) is dict and
                 body_response.get("model")==MODEL,
                 "Wrong provider model")
            usage=body_response.get("usage")
            must(type(usage) is dict and
                 type(usage.get("prompt_tokens")) is int and
                 type(usage.get("completion_tokens")) is int,
                 "Missing provider token accounting")
            spent=_money(usage.get("cost"))
            must(total+spent<=ATTEMPT_COST_CAP, "Total microprobe limit exceeded")
            total+=spent
            gid=body_response.get("id")
            if not(type(gid) is str and
                   re.fullmatch(r"gen-[A-Za-z0-9_-]{6,120}",gid)):
                gid=None
            item={"stage":stage,"http_status":200,"error":None,
                  "billed_cost_usd":format(spent,"f"),
                  "provider_generation_id":gid,"outcome":"ACCEPTED_COMPAT_REQUEST",
                  "prompt_tokens":usage["prompt_tokens"],
                  "completion_tokens":usage["completion_tokens"]}
            output.append(item)
            _write_once(claim,f"{num:02d}-{stage.lower()}-receipt.json",item)
        except Exception:
            if not(claim/f"{num:02d}-{stage.lower()}-receipt.json").exists():
                _write_once(claim,f"{num:02d}-{stage.lower()}-receipt.json",{
                    "stage":stage,"outcome":"UNKNOWN_CONSUMED",
                    "billed_cost_usd":None,"retry_allowed":False,
                })
            raise HarnessStop("Probe failure consumes full attempt; no retry") from None
    result={
        "schema":SCHEMA, "stage_results":output,
        "two_stage_wire_compatible":len(output)==2 and
           all(x["http_status"]==200 for x in output),
        "known_provider_billed_cost_usd":format(total,"f"),
        "prior_unknown_story_exposure_reserved_usd":"1.05",
        "english_master_authorized":False,
        "quality_accepted":False,"q25_authorized":False,
        "production_state_write_authorized":False,
        "automatic_retries":False,
    }
    _write_once(claim,"result.json",result)
    return result


def status():
    return {"schema":SCHEMA,"model":MODEL,"max_posts":2,
            "microprobe_exposure_cap_usd":"0.06",
            "public_synthetic_inputs_only":True,
            "provider_calls":0,"real_story_generated":False,
            "paid_run_disabled_by_default":True}


if __name__=="__main__":
    import argparse
    cli=argparse.ArgumentParser()
    cli.add_argument("--paid-one-shot",action="store_true")
    cli.add_argument("--run-root")
    options=cli.parse_args()
    if not options.paid_one_shot:
        print(json.dumps(status(),sort_keys=True))
    else:
        must(os.getenv("LUMI_P418_ENABLE")=="APPROVED_AGGREGATE_10_USD",
             "No explicit tiny paid diagnostic grant")
        must(options.run_root,"No immutable diagnostic ledger")
        api_key=os.getenv("OPENROUTER_API_KEY","")
        print(json.dumps(run_probe(options.run_root,api_key),sort_keys=True))
