"""SERA exact-source Mara S1 resumption: no scene rewrite, at most 2 paid calls.

Source is the immutable artifact from run 38808450095. Separate independent
extractor and JEV semantic evaluation; no world DB write, no canon commit.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from experiments.sera.coverage import reconcile, prose_hash, validate_report
from experiments.sera.extractor_adapter import bind_raw_extraction, make_messages
from experiments.sera.jev_verifier import build_atomic_questions, call_live_jev
from experiments.sera.mara_s1_live import (
    REGISTRY, ROUTES, SCENE_KEY, deterministic_shadow, make_entry,
)
from experiments.sera.spine_contracts import SOURCE_BLOB_SHA

SOURCE_ARTIFACT_RUN = 38808450095
SOURCE_RESULT_SHA256 = "4e287eac417836f15c63c38a4247a56c04eecb1fed8aa0c43f034722d40e456f"
SOURCE_PROSE_SHA256 = "80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03"
EXTRACTOR_MODEL = "google/gemini-3.7-flash"
JEV_MODEL = "typesafe/jev-1.13"
SPEND_STOP_USD = 0.20
MIN_REMAINING_USD = 0.25


def load_source(path: Path) -> dict:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SOURCE_RESULT_SHA256:
        raise ValueError("SOURCE_EVIDENCE_SHA_MISMATCH")
    source = json.loads(raw)
    if (source.get("source_spine_sha") != SOURCE_BLOB_SHA or
        source.get("launch_id") != "sera-mara-s1-20261016-oneuse-38808450095" or
        source.get("stage") != "WRITER_VALIDATION" or
        source.get("status") != "DIAGNOSTIC_INCOMPLETE" or
        source.get("error", {}).get("code") != "OPENROUTER_JSON_INVALID"):
        raise ValueError("SOURCE_EVIDENCE_IDENTITY_INVALID")
    if prose_hash(source["prose"]) != SOURCE_PROSE_SHA256:
        raise ValueError("SOURCE_PROSE_SHA_MISMATCH")
    if source["entry_state"] != make_entry():
        raise ValueError("SOURCE_ENTRY_STATE_MISMATCH")
    validate_report(source["writer_report"], role="WRITER",
                    prose=source["prose"], scene_key=SCENE_KEY,
                    entry_revision=0)
    return source


EXTRACT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "mentions": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "entity_ref": {"type": "string"},
                    "role": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "occurrence": {"type": "integer"},
                },
                "required": ["entity_ref", "role", "evidence_quote", "occurrence"],
            },
        },
        "events": {
            "type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "type": {"type": "string"},
                    "arguments": {"type": "object"},
                    "at": {"type": ["integer", "null"]},
                    "modality": {"type": "string"},
                    "evidence_quote": {"type": "string"},
                    "occurrence": {"type": "integer"},
                },
                "required": [
                    "type", "arguments", "at", "modality",
                    "evidence_quote", "occurrence"
                ],
            },
        },
    },
    "required": ["mentions", "events"],
}


def call_structured_gemini(*, key: str, messages: list) -> dict:
    """One API POST; preserve metadata and raw content even if JSON invalid."""
    payload = {
        "model": EXTRACTOR_MODEL,
        "messages": messages,
        "temperature": 0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sera_extraction",
                "strict": True,
                "schema": EXTRACT_SCHEMA,
            },
        },
        "reasoning": {"enabled": True, "effort": "low", "exclude": True},
        "stream": False,
    }
    req = Request(
        "https://openrouter.ai/api/v1/chat/completions",
        method="POST",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/necdetoskay/lumi-model-lab",
            "X-Title": "SERA M3 Mara S1 Diagnostic Resume",
        },
    )
    try:
        with urlopen(req, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ValueError(f"EXTRACTOR_HTTP_{exc.code}") from None
    except URLError:
        raise ValueError("EXTRACTOR_TRANSPORT_FAILURE") from None
    if not isinstance(body, dict) or not body.get("choices"):
        raise ValueError("EXTRACTOR_RESPONSE_INVALID")
    choice = body["choices"][0]
    content = (choice.get("message") or {}).get("content")
    out = {
        "response_id": body.get("id"), "model": body.get("model"),
        "finish_reason": choice.get("finish_reason"),
        "usage": body.get("usage"), "raw_content": content,
    }
    return out


def run(source: dict, key: str, launch_id: str, output: Path) -> dict:
    from src.openrouter_preflight import fetch_key_status, enforce_key_access

    result = {
        "protocol": "sera.mara-s1-extractor-resume.v0.1",
        "launch_id": launch_id,
        "prior_run_id": SOURCE_ARTIFACT_RUN,
        "source_result_sha256": SOURCE_RESULT_SHA256,
        "prose_sha256": SOURCE_PROSE_SHA256,
        "scene_key": SCENE_KEY,
        "models": {"writer_reused": "openai/gpt-5.6-luna",
                   "independent": EXTRACTOR_MODEL, "jev": JEV_MODEL},
        "prose": source["prose"],
        "entry_state": source["entry_state"],
        "writer_report": source["writer_report"],
        "independent": None, "coverage": None, "jev": None, "shadow": None,
        "stage": "PREFLIGHT", "status": "STARTED",
        "provider_calls_attempted": 0,
        "model_call_evidence": [],
        "max_new_logical_calls": 2, "observed_spend_stop_usd": SPEND_STOP_USD,
        "canonical_commit": False, "production_db_writes": 0,
    }
    if output.exists():
        raise ValueError("EVIDENCE_PATH_ALREADY_EXISTS")
    def checkpoint():
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(".stage")
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        temp.replace(output)
    def preflight():
        enforce_key_access(fetch_key_status(key), min_remaining=MIN_REMAINING_USD)
        known = sum(
            x.get("reported_cost") or 0 for x in result["model_call_evidence"]
            if isinstance(x.get("reported_cost"), (float,int))
        )
        if known >= SPEND_STOP_USD:
            raise ValueError("SERA_SPEND_STOP_REACHED")
    try:
        preflight()
        checkpoint()
        result["stage"] = "INDEPENDENT_EXTRACTION"
        result["provider_calls_attempted"] += 1
        response = call_structured_gemini(
            key=key,
            messages=make_messages(
                prose=source["prose"], registry=REGISTRY,
                scene_key=SCENE_KEY, entry_revision=0,
            ),
        )
        result["model_call_evidence"].append({
            "stage": "INDEPENDENT", "model": EXTRACTOR_MODEL,
            "response_id": response["response_id"],
            "observed_model": response["model"],
            "finish_reason": response["finish_reason"],
            "usage": response["usage"],
            "reported_cost": (
                response["usage"].get("cost")
                if isinstance(response.get("usage"), dict) else None
            ),
            "raw_content_sha256": sha256(
                (response["raw_content"] or "").encode("utf-8")
            ).hexdigest(),
        })
        checkpoint()
        if response["finish_reason"] != "stop":
            raise ValueError("EXTRACTOR_INCOMPLETE_OUTPUT")
        try:
            raw = json.loads(response["raw_content"])
        except (TypeError, json.JSONDecodeError):
            result["raw_extractor_content"] = response["raw_content"]
            raise ValueError("EXTRACTOR_JSON_INVALID") from None
        independent = bind_raw_extraction(
            raw=raw, prose=source["prose"], scene_key=SCENE_KEY,
            entry_revision=0, role="INDEPENDENT",
        )
        result["independent"] = independent
        result["stage"] = "RECONCILIATION"
        coverage = reconcile(
            prose=source["prose"], scene_key=SCENE_KEY,
            entry_revision=0, registry=REGISTRY,
            writer=source["writer_report"], independent=independent,
        )
        result["coverage"] = coverage
        checkpoint()
        bundle = build_atomic_questions(
            prose=source["prose"], scene_key=SCENE_KEY, entry_revision=0,
            coverage=coverage, registry=REGISTRY,
            writer=source["writer_report"], independent=independent,
        )
        result["stage"] = "JEV"
        if not bundle["questions"]:
            raise ValueError("SERA_JEV_NO_QUESTIONS")
        preflight()
        result["provider_calls_attempted"] += 1
        jev = call_live_jev(bundle=bundle, api_key=key, allow_billable=True)
        result["model_call_evidence"].append({
            "stage": "JEV", "model": JEV_MODEL,
            "usage": jev.get("usage"),
            "reported_cost": jev.get("reported_cost"),
        })
        result["jev"] = jev["verdict"]
        result["stage"] = "SHADOW_REDUCER"
        result["shadow"] = deterministic_shadow(
            entry=source["entry_state"], prose=source["prose"],
            coverage=coverage, verdict=jev["verdict"],
            writer=source["writer_report"],
        )
        result["stage"] = "DONE"
        result["status"] = "DIAGNOSTIC_COMPLETE_NO_CANON_COMMIT"
        checkpoint()
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INCOMPLETE"
        result["error"] = {"type":type(exc).__name__, "code": str(exc)[:300]}
        checkpoint()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-id", required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    source = load_source(args.source_result)
    if not args.live:
        print(json.dumps({
            "mode":"SOURCE_VERIFIED_DRY_RUN", "prose_hash":SOURCE_PROSE_SHA256,
            "word_count":len(source["prose"].split()),
            "writer_events":len(source["writer_report"]["events"]),
        }))
        return
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("SERA_PROVIDER_KEY_MISSING")
    result = run(source, key, args.launch_id, args.output)
    print(json.dumps({
        "status":result["status"], "stage":result["stage"],
        "error":result.get("error"),
        "calls_attempted":result["provider_calls_attempted"],
        "cost_usd_reported":sum(
            x.get("reported_cost") or 0 for x in result["model_call_evidence"]
            if isinstance(x.get("reported_cost"),(float,int))
        ),
        "coverage":(result.get("coverage") or {}).get("status"),
        "coverage_findings":(
            [f["code"] for f in result["coverage"]["findings"]]
            if result.get("coverage") else None
        ),
        "jev":(result.get("jev") or {}).get("next_action"),
        "shadow":(result.get("shadow") or {}).get("status"),
        "production_db_writes":0,
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
