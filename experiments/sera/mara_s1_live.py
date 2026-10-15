"""SERA single-scene REAL calibration runner (3 model operations max by stage).

Mara's frozen Sonnet Spine is read-only; zero canonical or production DB writes.
Evidence is diagnostic, never a quality PASS or full-capture claim.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import traceback

from experiments.sera.coverage import reconcile, report_signatures
from experiments.sera.extractor_adapter import (
    bind_raw_extraction, extract_once_live, make_messages,
)
from experiments.sera.jev_verifier import build_atomic_questions, call_live_jev
from experiments.sera.spine_contracts import (
    SOURCE_BLOB_SHA, SOURCE_RELATIVE_PATH, compile_scene_contracts,
    load_frozen_spine,
)
from experiments.sera.state_engine import (
    StateError, apply_scene, base_snapshot,
)
from src.openrouter_preflight import enforce_key_access, fetch_key_status

PROTOCOL = "sera.mara-first-scene-live.v0.1"
WRITER_MODEL = "openai/gpt-5.6-luna"
EXTRACTOR_MODEL = "anthropic/claude-haiku-4.5"
JEV_MODEL = "typesafe/jev-1.13"
SPEND_STOP_USD = 0.35
MIN_REMAINING_USD = 0.50
SCENE_KEY = "hook_empty_platform"

REGISTRY = {
    "mara": ["Mara", "apprentice investigator"],
    "vane": ["Vane", "Teodor Vane", "porter"],
    "vane_watch": ["pocket watch", "Vane's watch", "his watch"],
    "mara_notebook": ["notebook", "Mara's notebook", "notepad"],
    "platform_clock": ["platform clock", "station clock"],
    "archive_telegram": ["archive telegram", "telegram"],
    "train_41": ["train 41", "Train 41"],
    "north_quay_station": ["North Quay Station", "station platform"],
    "sealed_dispatch_office": ["sealed dispatch office", "dispatch office"],
}
ROUTES = {
    "north_quay_station->signal_archive": 10,
    "signal_archive->rail_yard": 15,
    "rail_yard->north_quay_station": 15,
    "signal_archive->north_quay_station": 10,
}


def make_entry():
    facts = {
        "reported_arrival_0210": {
            "claim": "The archive telegram records an arrival at 02:10 (not proof of physical arrival).",
            "certainty": "OBSERVED",
        },
        "vane_watch_stopped_0207": {
            "claim": "Vane reports his watch stopped at 02:07 (not proof of a train's timing).",
            "certainty": "OBSERVED",
        },
        "platform_clock_no_mark": {
            "claim": "The platform clock record has no mark for train 41.",
            "certainty": "OBSERVED",
        },
    }
    def c(loc, knowledge):
        return {"kind": "CHARACTER", "location": loc,
                "last_action_minute": 135, "knowledge": knowledge}
    def o(loc, holder, props):
        return {"kind": "OBJECT", "location": loc, "holder": holder,
                "properties": props, "recorded_facts": []}
    return base_snapshot(
        minute=135,
        facts=facts,
        entities={
            "mara": c("north_quay_station", ["reported_arrival_0210"]),
            "vane": c("north_quay_station", ["vane_watch_stopped_0207"]),
            "vane_watch": o("north_quay_station", "vane",
                            {"functional_status": "STOPPED", "time_display": "02:07",
                             "color": "UNKNOWN"}),
            "mara_notebook": o("north_quay_station", "mara",
                               {"color": "UNKNOWN", "condition": "UNKNOWN"}),
            "platform_clock": o("north_quay_station", None,
                                 {"strike_for_41": "NO_MARK", "color": "UNKNOWN"}),
            "archive_telegram": o("north_quay_station", "mara",
                                  {"recorded_arrival": "02:10", "color": "UNKNOWN"}),
        },
    )


WRITER_SYSTEM = """You are the LUMI SERA scene writer and self-reporting extractor.
The user message contains immutable story constraints, one scene contract, an
entry snapshot and a registry. Write ONE fluent English scene corresponding
only to the specified HOOK beat, with natural dialogue. Aim for 230-320 words.
Do not resolve the central mystery or move Mara to the archive yet. Keep Vane's
watch bounded: his 02:10 assertion is NOT direct proof he witnessed that minute.
Avoid fabricating color, size, condition, new physical entities or knowledge.
Stay within the exact constraints and preserve all listed entity identities.

Return ONLY valid JSON with keys prose, mentions and events.
'prose' is the full scene prose. 'mentions' and 'events' must conform to this
extraction schema:
mentions: [{entity_ref, role, evidence_quote, occurrence}]
events: [{type, arguments, at, modality, evidence_quote, occurrence}]
Where role is MENTIONED / PRESENT / INTERACTED / REPORTED_ONLY,
and modality is ASSERTED / REPORTED / HYPOTHETICAL / NEGATED / UNCERTAIN.
Use canonical registry IDs for entities; unknowns as new:<slug>.
Event type can be CREATE_ENTITY, MOVE_CHARACTER, TRANSFER_OBJECT,
UPDATE_OBJECT, INTERACT_OBJECT, LEARN_FACT, TELL_FACT, RECORD_FACT,
OPEN_THREAD, RESOLVE_THREAD, MOVE_OBJECT, UNMAPPED_STATE_CHANGE.
Quote must be EXACT contiguous text in your prose and occurrence index
is 0-based. Do not invent grounded event times: use 'at':null unless event
completion time is explicitly known from prose. Include all state changes,
non-mutating object interactions, knowledge exchanges and openings of inquiry
threads; if in doubt record an UNMAPPED_STATE_CHANGE with evidence.
Dialogue and observations may express uncertain reports, not confirmed facts.
Never mark an event as fact simply because a character claims it.
If events are implicit or cannot be typed, do not silently omit them.
No markdown, no additional keys."""


def writer_messages(spine, contract, entry):
    payload = {
        "original_spine_blob": SOURCE_BLOB_SHA,
        "story_title": spine["title"],
        "story_promise": spine["story_promise"],
        "constraints": spine["constraints"],
        "writer_rules": spine["writer_rules"],
        "scene_contract": contract,
        "next_beat_guard": spine["beats"][1],
        "entry_state": entry,
        "known_entity_aliases": REGISTRY,
        "word_target": "230-320",
        "instructions": "First HOOK scene only; no rest-of-story generation.",
    }
    return [
        {"role": "system", "content": WRITER_SYSTEM},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def safe_cost(response):
    value = response.get("reported_cost")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return max(0.0, float(value))
    return None


def deterministic_shadow(*, entry, prose, coverage, verdict, writer):
    """Never commit. Replay only unanimously described events on a dry copy.

    Uncertainty blocks. No model can propose new authority/fact creation
    in a calibration pilot. Any event without exact time blocks reducer replay.
    """
    if coverage["status"] != "RECONCILED_PENDING_SEMANTIC":
        return {"status": "HOLD_COVERAGE", "exit_state": None}
    if verdict["next_action"] != "PENDING_DETERMINISTIC_AND_COMPLETENESS_REVIEW":
        return {"status": "HOLD_SEMANTIC", "exit_state": None}
    if not writer["events"]:
        return {"status": "NO_EVENTS_TO_REPLAY", "exit_state": None}

    events = []
    for i, item in enumerate(writer["events"]):
        if item["type"] in ("CREATE_ENTITY", "MOVE_OBJECT", "UNMAPPED_STATE_CHANGE"):
            return {"status": "HOLD_UNSUPPORTED_EVENT", "exit_state": None}
        if item["at"] is None or item["modality"] != "ASSERTED":
            return {"status": "HOLD_UNGROUNDED_TIME_OR_MODALITY",
                    "exit_state": None}
        events.append({
            "event_id": f"sera-s1-{i}",
            "type": item["type"],
            "at": item["at"],
            "evidence_text": prose[item["start"]:item["end"]],
            **item["arguments"],
        })
    try:
        candidate = apply_scene(
            entry, events, scene_key=SCENE_KEY, prose=prose,
            travel_minutes=ROUTES,
            forbidden_locations=("sealed_dispatch_office",),
            allowed_new_entity_ids=(),
            allowed_observations=(),
        )
    except StateError as exc:
        return {"status": "HOLD_DETERMINISTIC", "error_code": exc.code,
                "exit_state": None}
    return {"status": "SHADOW_REDUCED_NOT_COMMIT_AUTHORIZED",
            "exit_state": candidate}


def run(*, key: str, outpath: Path, launch_id: str) -> dict:
    spine_path = Path(SOURCE_RELATIVE_PATH)
    spine = load_frozen_spine(spine_path)
    contracts = compile_scene_contracts(spine)
    entry = make_entry()
    result = {
        "protocol": PROTOCOL, "launch_id": launch_id,
        "source_spine_sha": SOURCE_BLOB_SHA, "source_spine_path": str(spine_path),
        "models": {"writer": WRITER_MODEL, "independent": EXTRACTOR_MODEL,
                   "semantic": JEV_MODEL},
        "max_calls": 3, "observed_spend_stop_usd": SPEND_STOP_USD,
        "stage": "INIT", "status": "STARTED", "calls": [],
        "entry_state": entry, "prose": None,
        "writer_report": None, "independent_report": None,
        "coverage": None, "jev_verdict": None, "shadow": None,
        "commit_authorized": False, "production_db_writes": 0,
    }

    def persist():
        outpath.parent.mkdir(parents=True, exist_ok=True)
        if outpath.exists():
            raise ValueError("SERA_EVIDENCE_IMMUTABLE_PATH_EXISTS")
        # Atomic-safe relative to interruptions: write stage evidence then
        # replace a single owned file; never overwrite a prior run artifact.
        stage_path = outpath.with_suffix(".stage")
        stage_path.write_text(json.dumps(result, ensure_ascii=False,
                                         indent=2, default=str) + "\n")
        stage_path.replace(outpath)

    def call(stage, model, messages):
        if len(result["calls"]) >= 3:
            raise RuntimeError("SERA_OPERATION_LIMIT_REACHED")
        observed = sum(x["reported_cost"] or 0.0 for x in result["calls"])
        if observed >= SPEND_STOP_USD:
            raise RuntimeError("SERA_OBSERVED_SPEND_STOP")
        # Check provider key between calls; unknown spend remains explicit
        # rather than being portrayed as zero cost.
        enforce_key_access(fetch_key_status(key), min_remaining=MIN_REMAINING_USD)
        payload = extract_once_live(model=model, messages=messages, api_key=key)
        result["calls"].append({
            "stage": stage, "model": model,
            "observed_model": payload.get("observed_model"),
            "provider_response_id": payload.get("provider_response_id"),
            "usage": payload.get("usage"), "reported_cost": safe_cost(payload),
        })
        persist()
        return payload

    try:
        result["stage"] = "PREFLIGHT"
        enforce_key_access(fetch_key_status(key), min_remaining=MIN_REMAINING_USD)
        persist()
        writer_body = call("WRITER", WRITER_MODEL,
                           writer_messages(spine, contracts[0], entry))
        raw = writer_body["raw"]
        if not isinstance(raw, dict) or set(raw) != {"prose", "mentions", "events"}:
            raise ValueError("SERA_WRITER_FORMAT_INVALID")
        prose = raw["prose"]
        if not isinstance(prose, str) or not prose.strip():
            raise ValueError("SERA_EMPTY_PROSE")
        result["prose"] = prose
        result["scene_word_count"] = len(prose.split())
        result["stage"] = "WRITER_VALIDATION"
        writer = bind_raw_extraction(
            raw={"mentions": raw["mentions"], "events": raw["events"]},
            prose=prose, scene_key=SCENE_KEY,
            entry_revision=entry["revision"], role="WRITER",
        )
        result["writer_report"] = writer
        persist()

        independent_body = call(
            "INDEPENDENT", EXTRACTOR_MODEL,
            make_messages(prose=prose, registry=REGISTRY,
                          scene_key=SCENE_KEY,
                          entry_revision=entry["revision"]),
        )
        independent = bind_raw_extraction(
            raw=independent_body["raw"], prose=prose,
            scene_key=SCENE_KEY, entry_revision=entry["revision"],
        )
        result["independent_report"] = independent
        result["stage"] = "COVERAGE"
        coverage = reconcile(
            prose=prose, scene_key=SCENE_KEY,
            entry_revision=entry["revision"], registry=REGISTRY,
            writer=writer, independent=independent,
        )
        result["coverage"] = coverage
        persist()

        bundle = build_atomic_questions(
            prose=prose, scene_key=SCENE_KEY,
            entry_revision=entry["revision"], coverage=coverage,
            registry=REGISTRY, writer=writer, independent=independent,
        )
        result["stage"] = "JEV"
        # Unlike writer/extractor transport, JEV has its own bounded transient
        # HTTP retry policy. Count logical operations, not HTTP attempts.
        if bundle["questions"]:
            if len(result["calls"]) >= 3:
                raise RuntimeError("SERA_OPERATION_LIMIT_REACHED")
            jev_response = call_live_jev(bundle=bundle, api_key=key,
                                         allow_billable=True)
            result["calls"].append({
                "stage": "JEV", "model": JEV_MODEL,
                "usage": jev_response.get("usage"),
                "reported_cost": jev_response.get("reported_cost"),
            })
            result["jev_verdict"] = jev_response["verdict"]
        else:
            result["jev_verdict"] = {
                "next_action": "ESCALATE_NO_CLAIMS", "commit_authorized": False
            }
        result["stage"] = "SHADOW_REDUCER"
        result["shadow"] = deterministic_shadow(
            entry=entry, prose=prose, coverage=coverage,
            verdict=result["jev_verdict"], writer=writer,
        )
        result["status"] = "DIAGNOSTIC_COMPLETE_NO_CANON_COMMIT"
        result["stage"] = "DONE"
        persist()
    except Exception as exc:
        result["status"] = "DIAGNOSTIC_INCOMPLETE"
        result["error"] = {"type": type(exc).__name__,
                           "code": str(exc)[:320]}
        persist()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--launch-id", required=True)
    args = parser.parse_args()
    if not args.live:
        print(json.dumps({
            "mode": "DRY_RUN", "source": SOURCE_RELATIVE_PATH,
            "writer": WRITER_MODEL, "independent": EXTRACTOR_MODEL,
            "semantic": JEV_MODEL,
            "max_logical_operations": 3,
            "observed_spend_stop_usd": SPEND_STOP_USD,
        }, indent=2))
        return
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        raise RuntimeError("SERA_OPENROUTER_KEY_MISSING")
    result = run(key=key, outpath=args.output, launch_id=args.launch_id)
    print(json.dumps({
        "status": result["status"], "stage": result["stage"],
        "error": result.get("error"),
        "word_count": result.get("scene_word_count"),
        "m2": (result["coverage"] or {}).get("status"),
        "m3": (result["jev_verdict"] or {}).get("next_action"),
        "shadow": (result["shadow"] or {}).get("status"),
        "model_operations": len(result["calls"]),
        "reported_usd": sum(
            x["reported_cost"] or 0 for x in result["calls"]
            if isinstance(x.get("reported_cost"), (int, float))
        ),
        "canonical_commits": 0,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
