from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.openrouter_jev import call_openrouter_jev, noul_probability, noul_question
from src.story_defect_detection import DEFECT_FAMILIES, segment_story
from src.model_registry import normalize_openrouter_request
from experiments.sera.request_policy import enforce_no_output_token_limit

from .contracts import StoryForgeRequest, StoryForgeResult


DEFAULT_PROFILE = Path("configs/storyforge/lsf_a4_w500_v1_rc1.yaml")


PLANNER_SYSTEM = r"""
You are the Spine Planner inside LUMI StoryForge.

Create PLAN ONLY. Do not write prose.

You receive:
- a StoryIntent,
- a minimal authoritative Story Context Packet,
- hard constraints,
- a generation profile.

Authority rules:
- every deterministic_core fact is authoritative;
- every StoryIntent hard constraint is authoritative;
- hard-guard facts may constrain the plan even if they never appear in the story;
- JEV enrichment is optional material, not a requirement to use every fact;
- never invent durable characters, owned inventory, relationship history, family facts, world facts, persistent object attributes, or character knowledge;
- harmless transient actions, sounds, gestures, dialogue, drawings, and sensory details are allowed;
- state changes are PROPOSALS only and are not committed here;
- no adult/helper may be invented to solve a child-led low-stakes intent;
- do not state a moral or lesson.

Return JSON only:
{
  "premise":"one concise English premise",
  "beats":[
    {
      "id":"B1",
      "density":"brief|develop|anchor",
      "beat":"one concrete ordered beat, not prose",
      "uses_fact_ids":["exact fact ids from context only"]
    }
  ],
  "assumptions":[
    {
      "text":"minimal transient assumption",
      "type":"transient_environment|action|dialogue|none",
      "why_safe":"brief"
    }
  ],
  "expected_outcome":{
    "proposed_state_changes":[
      {"kind":"knowledge|position|object_state|relationship|none","description":"proposal only"}
    ],
    "preserved_invariants":["important authoritative facts that remain true"]
  }
}

Hard shape:
- exactly 8 beats, B1..B8 in order;
- density is brief/develop/anchor;
- at least 3 anchor beats;
- B8 is a concrete ending;
- uses_fact_ids may reference only supplied context fact ids.
""".strip()


PLAN_VALIDATOR_SYSTEM = r"""
You are the independent StoryForge Spine Validator.

Judge the PLAN, not prose. Report only serious/critical defects.

Check:
- intent_alignment
- canon_state_consistency
- unavailable_object_or_character
- knowledge_or_relationship_boundary
- physical_causality
- event_order
- exact_age_fit
- closure
- outcome_safety

Rules:
- deterministic_core and hard constraints are authoritative;
- JEV enrichment is optional;
- no durable canon may be invented;
- no state change may be treated as already committed;
- harmless transient childlike behavior is allowed;
- do not demand a particular creative solution;
- do not rewrite the plan.

Return JSON only:
{
  "valid":true,
  "counts":{"critical":0,"serious":0},
  "defects":[
    {
      "severity":"critical|serious",
      "class":"intent_alignment|canon_state_consistency|unavailable_object_or_character|knowledge_or_relationship_boundary|physical_causality|event_order|exact_age_fit|closure|outcome_safety",
      "beat_ids":["B1"],
      "why":"brief"
    }
  ],
  "summary":"brief"
}
""".strip()


WRITER_SYSTEM = r"""
You are the English story writer inside LUMI StoryForge.

Write a natural read-aloud story for the exact requested age from the validated StoryIntent, Context Packet, and 8-beat spine.

Preserve:
- beat order and causal solution;
- authoritative character/object/state facts;
- knowledge and relationship boundaries;
- hard constraints;
- concrete ending.

Creative freedom is encouraged for TRANSIENT details:
- short childlike dialogue;
- playful sounds;
- gestures;
- momentary sensory detail;
- temporary drawings/play;
- harmless comparisons.

Do NOT invent unsupported DURABLE details:
- persistent object color/size/features;
- new owned inventory;
- new family canon;
- new relationship history;
- new world facts;
- knowledge the character does not possess.

Do not add an adult/helper who solves the problem.
Do not state a moral or lesson.

Return only the finished English story. First line must be the title.
""".strip()


AUDIT_SYSTEM = r"""
You are a strict StoryForge publication-blocker auditor.

Evaluate the finished English story against:
- StoryIntent;
- authoritative Context Packet;
- hard constraints;
- validated Spine.

Evaluate every canonical family:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Report ONLY serious/critical semantic defects.
Do not report optional polish.

Important:
- transient childlike sounds/dialogue/gestures are allowed;
- unsupported DURABLE canon/state attributes may be canon_integrity defects;
- if the exact defect can be fixed without changing the validated plan, repair_scope=local;
- if the prose needs multi-event restructuring, repair_scope=structural;
- if the validated plan itself is the source of the defect, repair_scope=replan;
- severity MUST be exactly serious or critical; if your native rubric would call a blocking defect "major", output serious instead;
- for every present=true finding, exact_quote is REQUIRED and must be one exact substring copied from one cited story sentence;
- exact_quote must be the smallest useful phrase or sentence fragment that proves the defect;
- for present=false, exact_quote must be null.

Return JSON only:
{
  "evaluations":[
    {
      "family":"physical_feasibility",
      "present":false,
      "severity":null,
      "repair_scope":null,
      "span_ids":[],
      "exact_quote":null,
      "reason":"brief"
    }
  ]
}
""".strip()


REPAIR_SYSTEM = r"""
You are the bounded local repair editor inside LUMI StoryForge.

You receive a finished English story, its validated Spine, authoritative Context Packet,
hard constraints, and confirmed serious/critical LOCAL defects.

Do NOT rewrite the story.
Return the smallest exact replacements needed to remove only the confirmed local defects.

Rules:
- old must be an exact unique substring of the story;
- preserve event order, causal solution, dialogue meaning, tone, ending, and validated spine;
- add no character/object/canon/solution/moral;
- do not repair optional style.

Return JSON only:
{
  "repairs":[
    {
      "old":"exact story substring",
      "new":"minimal replacement",
      "why":"brief"
    }
  ]
}
""".strip()


TRANSLATION_SYSTEM = r"""
You are the EN->TR literary translator inside LUMI StoryForge.

Translate the ACCEPTED English master into natural Turkish for the exact requested age.

THIS IS TRANSLATION, NOT REWRITING.

Preserve:
- characters, objects, states, event order, causal solution;
- knowledge/relationship boundaries;
- childlike dialogue and sounds;
- absence of moralizing;
- exact ending.

Do not add/remove plot events, durable canon, helpers, motivations, or explanations.
Return only the finished Turkish story.
""".strip()


FIDELITY_SYSTEM = r"""
You are the narrow EN->TR semantic fidelity gate inside LUMI StoryForge.

Report ONLY serious/critical translation defects:
- omission
- addition
- character_shift
- object_shift
- state_shift
- causal_shift
- knowledge_shift
- ending_shift

Ignore harmless Turkish phrasing differences.

Return JSON only:
{
  "findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"short EN quote",
      "translation_quote":"short TR quote",
      "why":"brief"
    }
  ],
  "fidelity_clean":true
}
""".strip()


def _load_profile(path: Path = DEFAULT_PROFILE) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if payload.get("schema_version") != "lumi-storyforge-profile.v1":
        raise RuntimeError("Unsupported StoryForge profile schema.")
    if payload.get("profile_id") != "LSF-A4-W500-v1.0-rc1":
        raise RuntimeError("StoryForge runtime is pinned to LSF-A4-W500-v1.0-rc1.")
    return payload


def _structured_call(
    *,
    api_key: str,
    model: str,
    system: str,
    payload: Any,
    seed: int,
    request_class: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed, body, request, failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=system,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=None,
        seed=seed,
        request_class=request_class,
        max_parse_attempts=2,
        forbid_output_token_limit=True,
        forbid_ambiguous_paid_retry=True,
    )
    return parsed, {
        "model": model,
        "request_class": request_class,
        "input": {
            "system_prompt": system,
            "payload": payload,
        },
        "raw_usage": body.get("usage") or {},
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
        "request": {
            "temperature": request.get("temperature"),
            "max_tokens": request.get("max_tokens"),
            "reasoning": request.get("reasoning"),
            "response_format": request.get("response_format"),
        },
        "parse_failures": failures,
        "raw_parsed_response": parsed,
    }


def _cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    cost = meta.get("cost") or {}
    value = cost.get("usd") if isinstance(cost, dict) else None
    return float(value or 0.0)


def _build_context(
    *,
    api_key: str,
    request: StoryForgeRequest,
    profile: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = {x.id: x.model_dump() for x in request.candidate_facts}
    refs = request.story_intent.references
    direct_ids = set(refs.required_fact_ids) | set(refs.hard_guard_fact_ids)

    core = [x.model_dump() for x in request.always_required]
    core.extend(candidates[fid] for fid in sorted(direct_ids))

    soft = [x.model_dump() for x in request.candidate_facts if x.id not in direct_ids]
    questions: dict[str, dict[str, Any]] = {}
    for fact in soft:
        fid = fact["id"]
        questions[fid] = noul_question(
            (
                f"Should soft candidate fact '{fid}' be included as additional context for the "
                "StoryForge Spine Planner? Direct StoryIntent references and hard guards are already "
                "included deterministically. Select only materially useful enrichment."
            ),
            true_criteria=(
                "TRUE when this fact materially improves intent-relevant planning beyond the "
                "deterministic core."
            ),
            false_criteria=(
                "FALSE when it is redundant, decorative, unrelated, historical noise, or safely "
                "omitted from a minimal context packet."
            ),
        )

    context_cfg = profile["context_builder"]
    threshold = float(context_cfg["decision_engine"]["auto_select_threshold"])
    review_threshold = float(context_cfg["decision_engine"]["review_threshold"])

    decisions: dict[str, dict[str, Any]] = {}
    jev_response_meta: dict[str, Any] | None = None
    if questions:
        body = call_openrouter_jev(
            api_key=api_key,
            state={
                "task": "storyforge_soft_context_enrichment",
                "active_world_id": request.active_world_id,
                "story_intent": request.story_intent.model_dump(),
                "deterministic_core": core,
                "soft_candidates": {x["id"]: x for x in soft},
                "policy": {
                    "auto_select_threshold": threshold,
                    "review_threshold": review_threshold,
                    "review_sent_to_planner": False,
                },
            },
            questions=questions,
        )
        jev_response_meta = {
            "model": body.get("model"),
            "provider": body.get("provider"),
            "usage": body.get("usage") or {},
            "cost": body.get("cost") or {},
            "raw_response": body,
        }
        for fact in soft:
            fid = fact["id"]
            p = noul_probability(body["answers"][fid])
            bucket = "SELECT" if p >= threshold else "REVIEW" if p >= review_threshold else "OMIT"
            decisions[fid] = {"probability": p, "bucket": bucket}

    raw_selected = sorted(fid for fid, row in decisions.items() if row["bucket"] == "SELECT")
    review = sorted(fid for fid, row in decisions.items() if row["bucket"] == "REVIEW")

    direct_relationship_entities = {
        fid.split(".", 1)[1].split("_", 1)[0]
        for fid in direct_ids
        if fid.startswith("relationship.") and "." in fid
    }
    selected: list[str] = []
    policy_demoted: list[str] = []
    for fid in raw_selected:
        if fid.startswith("relationship."):
            entity = fid.split(".", 1)[1].split("_", 1)[0]
            if entity not in direct_relationship_entities:
                policy_demoted.append(fid)
                continue
        selected.append(fid)

    review = sorted(set(review) | set(policy_demoted))
    packet = {
        "deterministic_core": core,
        "jev_selected_enrichment": [candidates[fid] for fid in sorted(selected)],
    }
    evidence = {
        "direct_fact_ids": sorted(direct_ids),
        "soft_candidate_count": len(soft),
        "jev_decisions": decisions,
        "raw_selected_enrichment_ids": raw_selected,
        "policy_demoted_ids": sorted(policy_demoted),
        "selected_enrichment_ids": sorted(selected),
        "review_enrichment_ids": review,
        "forbidden_fact_ids": sorted(x.id for x in request.forbidden_facts),
        "forbidden_sent_to_jev": False,
        "jev_response": jev_response_meta,
    }
    return packet, evidence


def _context_fact_ids(packet: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("deterministic_core", "jev_selected_enrichment"):
        for fact in packet.get(key) or []:
            fid = str(fact.get("id") or "")
            if fid:
                ids.add(fid)
    return ids


def _validate_plan_shape(plan: dict[str, Any], allowed_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if not isinstance(plan.get("premise"), str) or not plan["premise"].strip():
        errors.append("missing_premise")
    beats = plan.get("beats")
    if not isinstance(beats, list) or len(beats) != 8:
        errors.append("beats_must_equal_8")
        beats = beats if isinstance(beats, list) else []
    if [str(x.get("id") or "") for x in beats] != [f"B{i}" for i in range(1, 9)]:
        errors.append("beat_ids_invalid")
    anchors = 0
    for beat in beats:
        density = str(beat.get("density") or "")
        if density not in {"brief", "develop", "anchor"}:
            errors.append(f"density_invalid:{beat.get('id')}")
        if density == "anchor":
            anchors += 1
        refs = beat.get("uses_fact_ids") or []
        if not isinstance(refs, list):
            errors.append(f"fact_refs_not_list:{beat.get('id')}")
        else:
            unknown = sorted(set(str(x) for x in refs) - allowed_ids)
            if unknown:
                errors.append(f"unknown_fact_refs:{beat.get('id')}:{unknown}")
    if anchors < 3:
        errors.append(f"anchors_lt_3:{anchors}")
    if not isinstance(plan.get("expected_outcome"), dict):
        errors.append("missing_expected_outcome")
    return errors


def _normalize_audit(payload: dict[str, Any], segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = payload.get("evaluations")
    if not isinstance(rows, list):
        raise RuntimeError("StoryForge audit missing evaluations.")

    segments_by_id = {str(row["id"]): row for row in segments}
    valid_span_ids = set(segments_by_id)
    seen: set[str] = set()
    findings: list[dict[str, Any]] = []

    for row in rows:
        family = str(row.get("family") or "")
        if family not in DEFECT_FAMILIES or family in seen:
            raise RuntimeError(f"Invalid/duplicate audit family: {family}")
        seen.add(family)

        present = row.get("present")
        if not isinstance(present, bool):
            raise RuntimeError(f"Invalid audit present flag: {family}")
        if not present:
            continue

        raw_severity = str(row.get("severity") or "")
        severity_aliases = {"major": "serious"}
        severity = severity_aliases.get(raw_severity, raw_severity)
        if severity not in {"serious", "critical"}:
            raise RuntimeError(
                f"Invalid blocking severity: {family}:{raw_severity}"
            )
        severity_normalization = (
            "major_to_serious_blocker_alias_v1"
            if raw_severity == "major"
            else None
        )

        scope = str(row.get("repair_scope") or "")
        if scope not in {"local", "structural", "replan"}:
            raise RuntimeError(f"Invalid repair scope: {family}:{scope}")

        spans = [str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_span_ids):
            raise RuntimeError(f"Invalid audit spans: {family}:{spans}")

        quote = str(row.get("exact_quote") or "")
        if not quote:
            raise RuntimeError(f"Missing audit exact quote: {family}")

        matches: list[dict[str, Any]] = []
        for span_id in spans:
            segment = segments_by_id[span_id]
            offset = segment["text"].find(quote)
            while offset >= 0:
                prefix_words = re.findall(r"\S+", segment["text"][:offset])
                quote_words = re.findall(r"\S+", quote)
                word_start = len(prefix_words) + 1
                word_end = word_start + max(0, len(quote_words) - 1)
                matches.append({
                    "sentence_id": span_id,
                    "paragraph_id": segment.get("paragraph_id"),
                    "paragraph_index": segment.get("paragraph_index"),
                    "sentence_word_start": word_start,
                    "sentence_word_end": word_end,
                    "exact_quote": quote,
                    "char_start": int(segment.get("char_start", 0)) + offset,
                    "char_end": int(segment.get("char_start", 0)) + offset + len(quote),
                })
                offset = segment["text"].find(quote, offset + 1)

        if len(matches) != 1:
            raise RuntimeError(
                f"Audit exact quote must resolve uniquely inside cited spans: {family}:{len(matches)}"
            )

        findings.append({
            "family": family,
            "raw_severity": raw_severity,
            "severity": severity,
            "severity_normalization": severity_normalization,
            "repair_scope": scope,
            "span_ids": spans,
            "exact_quote": quote,
            "source_locator": matches[0],
            "reason": str(row.get("reason") or "").strip(),
        })

    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError("StoryForge audit did not cover every canonical defect family.")
    return findings


class StoryForgeTraceError(RuntimeError):
    def __init__(self, message: str, trace: dict[str, Any]):
        super().__init__(message)
        self.trace = trace


class StoryForgeAuditContractError(StoryForgeTraceError):
    pass


def _run_traced_stage(
    *,
    stage: str,
    evidence: dict[str, Any],
    artifacts: dict[str, Any],
    fn: Any,
) -> Any:
    stage_started = time.perf_counter()
    event: dict[str, Any] = {
        "stage": stage,
        "status": "started",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    evidence.setdefault("trace_events", []).append(event)

    try:
        result = fn()
    except Exception as exc:
        latency = round(time.perf_counter() - stage_started, 3)
        evidence.setdefault("latency_seconds", {})[stage] = latency
        event.update({
            "status": "failed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "latency_seconds": latency,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        })
        trace = {**artifacts, "stage": stage, "evidence": evidence}
        cause_trace = getattr(exc, "trace", None)
        if isinstance(cause_trace, dict):
            trace["cause_trace"] = cause_trace
            evidence.setdefault("stage_failure_evidence", {})[stage] = cause_trace

            cause_meta = cause_trace.get("model_meta")
            if isinstance(cause_meta, dict):
                evidence.setdefault("cost_usd", {})[stage] = _cost(cause_meta)

            cause_cost = cause_trace.get("cost")
            if isinstance(cause_cost, dict):
                evidence.setdefault("cost_usd", {})[stage] = float(cause_cost.get("usd") or 0.0)

            cause_usage = cause_trace.get("raw_usage")
            if not isinstance(cause_usage, dict):
                cause_usage = cause_trace.get("usage")
            if isinstance(cause_usage, dict):
                evidence.setdefault("failure_usage", {})[stage] = cause_usage
        evidence["elapsed_seconds"] = round(
            sum(float(value or 0.0) for value in evidence.get("latency_seconds", {}).values()),
            3,
        )
        evidence.setdefault("cost_usd", {})["total"] = round(
            sum(
                float(value or 0.0)
                for key, value in evidence.get("cost_usd", {}).items()
                if key != "total"
            ),
            9,
        )
        raise StoryForgeTraceError(str(exc), trace) from exc

    latency = round(time.perf_counter() - stage_started, 3)
    evidence.setdefault("latency_seconds", {})[stage] = latency
    event.update({
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "latency_seconds": latency,
    })
    return result


def _audit_story(
    *,
    api_key: str,
    model: str,
    request: StoryForgeRequest,
    packet: dict[str, Any],
    plan: dict[str, Any],
    story: str,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    segments = segment_story(story)
    payload, meta = _structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={
            "story_intent": request.story_intent.model_dump(),
            "hard_constraints": request.story_intent.hard_constraints,
            "context_packet": packet,
            "validated_spine": plan,
            "story_segments": segments,
        },
        seed=seed,
        request_class="editorial_audit",
    )
    trace = {
        "raw_audit_payload": payload,
        "segments": segments,
        "model_meta": meta,
    }
    try:
        findings = _normalize_audit(payload, segments)
    except RuntimeError as exc:
        trace["contract_error"] = str(exc)
        raise StoryForgeAuditContractError(str(exc), trace) from exc
    trace["normalized_findings"] = findings
    # Do not attach `trace` itself to meta because trace already contains meta.
    # Store a detached audit view to keep evidence JSON-serializable.
    meta["audit_trace"] = {
        "raw_audit_payload": payload,
        "segments": segments,
        "normalized_findings": findings,
    }
    return findings, meta


def _dedupe_findings(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for group in groups:
        for row in group:
            key = (
                row.get("family"),
                row.get("severity"),
                row.get("repair_scope"),
                tuple(row.get("span_ids") or []),
                row.get("reason"),
            )
            if key not in seen:
                seen.add(key)
                out.append(row)
    return out


def _apply_local_repairs(story: str, repair_payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    current = story
    applied: list[dict[str, Any]] = []
    for row in repair_payload.get("repairs") or []:
        old = str(row.get("old") or "")
        new = str(row.get("new") or "")
        if not old or not new or old == new:
            raise RuntimeError("StoryForge local repair contained empty/no-op replacement.")
        if current.count(old) != 1:
            raise RuntimeError("StoryForge local repair target must exist exactly once.")
        current = current.replace(old, new, 1)
        applied.append({"old": old, "new": new, "why": str(row.get("why") or "")})
    if not applied:
        raise RuntimeError("StoryForge local repair returned no applicable replacements.")
    return current, applied


def _preflight_storyforge_output_policy(models: dict[str, str]) -> None:
    """Reject model-profile output ceilings BEFORE any StoryForge model call.

    A profile can force its own request max even when all callers use
    max_tokens=None. The live outbound provider boundary rechecks too.
    This is independent of usage/cost guards and provider native limits.
    """
    classes = {
        "planner": ("story_plan", True),
        "plan_validator": ("editorial_audit", True),
        "writer": ("teacher_story_medium_reasoning", False),
        "primary_auditor": ("editorial_audit", True),
        "secondary_auditor": ("editorial_audit", True),
        "repair": ("editorial_audit", True),
        "translator": ("translation", False),
        "fidelity": ("editorial_audit", True),
    }
    if set(models) != set(classes):
        raise RuntimeError("STORYFORGE_MODEL_PROFILE_ROLES_INCOMPLETE")
    for role, (request_class, structured) in classes.items():
        candidate = normalize_openrouter_request(
            models[role],
            {
                "model": models[role],
                "messages": [
                    {"role": "system", "content": "cap-free preflight"},
                    {"role": "user", "content": "cap-free preflight"},
                ],
            },
            request_class=request_class,
            structured_output=structured,
        )
        enforce_no_output_token_limit(candidate)


def run_storyforge(
    request: StoryForgeRequest | dict[str, Any],
    *,
    api_key: str | None = None,
    profile_path: Path = DEFAULT_PROFILE,
) -> StoryForgeResult:
    started = time.perf_counter()
    req = request if isinstance(request, StoryForgeRequest) else StoryForgeRequest.model_validate(request)
    profile = _load_profile(profile_path)
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("Missing OPENROUTER_API_KEY.")

    gp = req.generation_profile
    scope = profile["qualification_scope"]
    if gp.exact_age != int(scope["exact_age"]) or gp.target_words != int(scope["target_words"]):
        raise RuntimeError("RC1 runtime only supports its qualified exact-age/target-word scope.")

    models = {
        "planner": profile["spine_planner"]["model"],
        "plan_validator": profile["spine_planner"]["validator"]["model"],
        "writer": profile["writer"]["model"],
        "primary_auditor": profile["semantic_qa"]["primary"]["model"],
        "secondary_auditor": profile["semantic_qa"]["secondary"]["model"],
        "repair": profile["repair"]["default_model"],
        "translator": profile["translation"]["model"],
        "fidelity": profile["translation_fidelity"]["model"],
    }
    _preflight_storyforge_output_policy(models)

    request_snapshot = req.model_dump(mode="json")
    evidence: dict[str, Any] = {
        "profile_id": profile["profile_id"],
        "models": models,
        "request_snapshot": request_snapshot,
        "cost_usd": {},
        "latency_seconds": {},
        "trace_events": [],
    }
    artifacts: dict[str, Any] = {
        "profile_id": profile["profile_id"],
        "request_id": req.request_id,
        "request_snapshot": request_snapshot,
        "models": models,
        "context_packet": None,
        "plan": None,
        "english_story": None,
        "turkish_story": None,
    }

    packet, context_evidence = _run_traced_stage(
        stage="context_builder",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _build_context(api_key=key, request=req, profile=profile),
    )
    artifacts["context_packet"] = packet
    evidence["context_builder"] = context_evidence

    seed = 2026092801
    plan, planner_meta = _run_traced_stage(
        stage="planner",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _structured_call(
            api_key=key,
            model=models["planner"],
            system=PLANNER_SYSTEM,
            payload={
                "story_intent": req.story_intent.model_dump(),
                "context_packet": packet,
                "hard_constraints": req.story_intent.hard_constraints,
                "generation_profile": gp.model_dump(),
            },
            seed=seed,
            request_class="story_planning",
        ),
    )
    artifacts["plan"] = plan
    evidence["planner"] = planner_meta
    evidence["cost_usd"]["planner"] = _cost(planner_meta)

    plan_errors = _validate_plan_shape(plan, _context_fact_ids(packet))
    plan_validation, validator_meta = _run_traced_stage(
        stage="plan_validator",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _structured_call(
            api_key=key,
            model=models["plan_validator"],
            system=PLAN_VALIDATOR_SYSTEM,
            payload={
                "story_intent": req.story_intent.model_dump(),
                "context_packet": packet,
                "hard_constraints": req.story_intent.hard_constraints,
                "generation_profile": gp.model_dump(),
                "proposed_plan": plan,
                "deterministic_plan_errors": plan_errors,
            },
            seed=seed + 1,
            request_class="editorial_audit",
        ),
    )
    evidence["plan_validator"] = validator_meta
    evidence["cost_usd"]["plan_validator"] = _cost(validator_meta)
    counts = plan_validation.get("counts") or {}
    plan_pass = (
        not plan_errors
        and bool(plan_validation.get("valid"))
        and int(counts.get("critical", 0) or 0) == 0
        and int(counts.get("serious", 0) or 0) == 0
    )
    evidence["plan_gate"] = {
        "deterministic_errors": plan_errors,
        "semantic": plan_validation,
        "pass": plan_pass,
    }
    if not plan_pass:
        evidence["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        evidence["cost_usd"]["total"] = sum(evidence["cost_usd"].values())
        return StoryForgeResult(
            profile_id=profile["profile_id"],
            request_id=req.request_id,
            status="plan_rejected",
            publication_ready=False,
            context_packet=packet,
            plan=plan,
            proposed_story_outcome=plan.get("expected_outcome"),
            evidence=evidence,
        )

    writer_input = {
        "story_intent": req.story_intent.model_dump(),
        "context_packet": packet,
        "hard_constraints": req.story_intent.hard_constraints,
        "validated_plan": plan,
        "generation_profile": gp.model_dump(),
    }
    story, writer_body, writer_request = _run_traced_stage(
        stage="writer",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: call_openrouter(
            api_key=key,
            model=models["writer"],
            system_prompt=WRITER_SYSTEM,
            user_prompt=json.dumps(writer_input, ensure_ascii=False),
            temperature=0.72,
            max_tokens=None,
            seed=seed + 2,
            request_class="teacher_story_medium_reasoning",
            structured_output=False,
            forbid_output_token_limit=True,
            forbid_ambiguous_paid_retry=True,
        ),
    )
    artifacts["english_story"] = story
    evidence["writer"] = {
        "model": models["writer"],
        "request_class": "teacher_story_medium_reasoning",
        "input": {"system_prompt": WRITER_SYSTEM, "payload": writer_input},
        "raw_response": story,
        "raw_usage": writer_body.get("usage") or {},
        "usage": parse_usage(writer_body).model_dump(mode="json"),
        "cost": parse_cost(writer_body).model_dump(mode="json"),
        "request": {
            "temperature": writer_request.get("temperature"),
            "max_tokens": writer_request.get("max_tokens"),
            "reasoning": writer_request.get("reasoning"),
        },
    }
    evidence["cost_usd"]["writer"] = float(parse_cost(writer_body).usd or 0.0)
    hard_min, hard_max = gp.hard_range
    word_count = count_words(story)
    length_pass = hard_min <= word_count <= hard_max

    primary, primary_meta = _run_traced_stage(
        stage="primary_audit",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _audit_story(
            api_key=key,
            model=models["primary_auditor"],
            request=req,
            packet=packet,
            plan=plan,
            story=story,
            seed=seed + 3,
        ),
    )
    secondary, secondary_meta = _run_traced_stage(
        stage="secondary_audit",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _audit_story(
            api_key=key,
            model=models["secondary_auditor"],
            request=req,
            packet=packet,
            plan=plan,
            story=story,
            seed=seed + 4,
        ),
    )
    evidence["story_audit_initial"] = {
        "word_count": word_count,
        "length_pass": length_pass,
        "primary_findings": primary,
        "secondary_findings": secondary,
        "primary_meta": primary_meta,
        "secondary_meta": secondary_meta,
    }
    evidence["cost_usd"]["primary_audit"] = _cost(primary_meta)
    evidence["cost_usd"]["secondary_audit"] = _cost(secondary_meta)

    findings = _dedupe_findings(primary, secondary)
    applied_repairs: list[dict[str, Any]] = []
    repair_cycles: list[dict[str, Any]] = []
    max_local_repair_cycles = 3

    for repair_cycle in range(1, max_local_repair_cycles + 1):
        if not findings:
            break

        if any(x["repair_scope"] != "local" for x in findings):
            evidence["story_gate"] = {
                "pass": False,
                "reason": "non_local_blocker",
                "repair_cycle": repair_cycle,
                "findings": findings,
                "repair_cycles": repair_cycles,
            }
            evidence["elapsed_seconds"] = round(time.perf_counter() - started, 3)
            evidence["cost_usd"]["total"] = sum(evidence["cost_usd"].values())
            return StoryForgeResult(
                profile_id=profile["profile_id"],
                request_id=req.request_id,
                status="story_rejected",
                publication_ready=False,
                context_packet=packet,
                plan=plan,
                english_story=story,
                proposed_story_outcome=plan.get("expected_outcome"),
                evidence=evidence,
            )

        repair_stage = "repair" if repair_cycle == 1 else f"repair_{repair_cycle}"
        apply_stage = (
            "repair_apply" if repair_cycle == 1 else f"repair_apply_{repair_cycle}"
        )
        primary_stage = (
            "primary_reaudit"
            if repair_cycle == 1
            else f"primary_reaudit_{repair_cycle}"
        )
        secondary_stage = (
            "secondary_reaudit"
            if repair_cycle == 1
            else f"secondary_reaudit_{repair_cycle}"
        )

        before_story = story
        findings_before = findings

        repair_payload, repair_meta = _run_traced_stage(
            stage=repair_stage,
            evidence=evidence,
            artifacts=artifacts,
            fn=lambda repair_cycle=repair_cycle, findings_before=findings_before: _structured_call(
                api_key=key,
                model=models["repair"],
                system=REPAIR_SYSTEM,
                payload={
                    "story_intent": req.story_intent.model_dump(),
                    "context_packet": packet,
                    "hard_constraints": req.story_intent.hard_constraints,
                    "validated_spine": plan,
                    "story": story,
                    "confirmed_local_defects": findings_before,
                    "repair_cycle": repair_cycle,
                    "max_repair_cycles": max_local_repair_cycles,
                },
                seed=seed + 5 + ((repair_cycle - 1) * 3),
                request_class="editorial_audit",
            ),
        )
        if repair_cycle == 1:
            evidence["repair"] = repair_meta
        evidence.setdefault("repair_meta_by_cycle", {})[str(repair_cycle)] = repair_meta
        evidence["cost_usd"][repair_stage] = _cost(repair_meta)

        story, cycle_repairs = _run_traced_stage(
            stage=apply_stage,
            evidence=evidence,
            artifacts=artifacts,
            fn=lambda: _apply_local_repairs(story, repair_payload),
        )
        artifacts["english_story"] = story

        for row in cycle_repairs:
            applied_repairs.append({**row, "repair_cycle": repair_cycle})

        if story == before_story or not cycle_repairs:
            repair_cycles.append({
                "cycle": repair_cycle,
                "findings_before": findings_before,
                "applied_repairs": cycle_repairs,
                "findings_after": findings_before,
                "status": "stalled",
            })
            findings = findings_before
            break

        primary, primary_meta = _run_traced_stage(
            stage=primary_stage,
            evidence=evidence,
            artifacts=artifacts,
            fn=lambda repair_cycle=repair_cycle: _audit_story(
                api_key=key,
                model=models["primary_auditor"],
                request=req,
                packet=packet,
                plan=plan,
                story=story,
                seed=seed + 6 + ((repair_cycle - 1) * 3),
            ),
        )
        secondary, secondary_meta = _run_traced_stage(
            stage=secondary_stage,
            evidence=evidence,
            artifacts=artifacts,
            fn=lambda repair_cycle=repair_cycle: _audit_story(
                api_key=key,
                model=models["secondary_auditor"],
                request=req,
                packet=packet,
                plan=plan,
                story=story,
                seed=seed + 7 + ((repair_cycle - 1) * 3),
            ),
        )
        evidence["cost_usd"][primary_stage] = _cost(primary_meta)
        evidence["cost_usd"][secondary_stage] = _cost(secondary_meta)

        findings = _dedupe_findings(primary, secondary)
        repair_cycles.append({
            "cycle": repair_cycle,
            "findings_before": findings_before,
            "applied_repairs": cycle_repairs,
            "primary_findings_after": primary,
            "secondary_findings_after": secondary,
            "findings_after": findings,
            "status": "clean" if not findings else "needs_next_cycle",
        })

    evidence["repair_cycles"] = repair_cycles

    final_word_count = count_words(story)
    final_length_pass = hard_min <= final_word_count <= hard_max
    english_pass = final_length_pass and not primary and not secondary
    evidence["story_gate"] = {
        "pass": english_pass,
        "word_count": final_word_count,
        "hard_range": list(gp.hard_range),
        "applied_repairs": applied_repairs,
        "repair_cycles": repair_cycles,
        "primary_findings": primary,
        "secondary_findings": secondary,
    }
    if not english_pass:
        evidence["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        evidence["cost_usd"]["total"] = sum(evidence["cost_usd"].values())
        return StoryForgeResult(
            profile_id=profile["profile_id"],
            request_id=req.request_id,
            status="story_rejected",
            publication_ready=False,
            context_packet=packet,
            plan=plan,
            english_story=story,
            proposed_story_outcome=plan.get("expected_outcome"),
            evidence=evidence,
        )

    translation_input = {
        "exact_age": gp.exact_age,
        "hard_constraints": req.story_intent.hard_constraints,
        "accepted_english_master": story,
    }
    tr_story, tr_body, tr_request = _run_traced_stage(
        stage="translation",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: call_openrouter(
            api_key=key,
            model=models["translator"],
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=json.dumps(translation_input, ensure_ascii=False),
            temperature=0.2,
            max_tokens=None,
            seed=seed + 8,
            request_class="translation",
            structured_output=False,
            forbid_output_token_limit=True,
            forbid_ambiguous_paid_retry=True,
        ),
    )
    artifacts["turkish_story"] = tr_story
    evidence["translator"] = {
        "model": models["translator"],
        "request_class": "translation",
        "input": {"system_prompt": TRANSLATION_SYSTEM, "payload": translation_input},
        "raw_response": tr_story,
        "raw_usage": tr_body.get("usage") or {},
        "usage": parse_usage(tr_body).model_dump(mode="json"),
        "cost": parse_cost(tr_body).model_dump(mode="json"),
        "request": {
            "temperature": tr_request.get("temperature"),
            "max_tokens": tr_request.get("max_tokens"),
            "reasoning": tr_request.get("reasoning"),
        },
    }
    evidence["cost_usd"]["translation"] = float(parse_cost(tr_body).usd or 0.0)

    fidelity, fidelity_meta = _run_traced_stage(
        stage="fidelity",
        evidence=evidence,
        artifacts=artifacts,
        fn=lambda: _structured_call(
            api_key=key,
            model=models["fidelity"],
            system=FIDELITY_SYSTEM,
            payload={
                "source_language": "en",
                "target_language": "tr",
                "exact_age": gp.exact_age,
                "hard_constraints": req.story_intent.hard_constraints,
                "source_story": story,
                "translation": tr_story,
            },
            seed=seed + 9,
            request_class="editorial_audit",
        ),
    )
    evidence["fidelity"] = fidelity_meta
    evidence["cost_usd"]["fidelity"] = _cost(fidelity_meta)
    blocking = [
        x for x in (fidelity.get("findings") or [])
        if str(x.get("severity") or "") in {"serious", "critical"}
    ]
    fidelity_pass = bool(fidelity.get("fidelity_clean")) and not blocking
    evidence["fidelity_gate"] = {
        "pass": fidelity_pass,
        "result": fidelity,
    }
    evidence["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    evidence["latency_seconds"]["total"] = evidence["elapsed_seconds"]
    evidence["cost_usd"]["total"] = sum(evidence["cost_usd"].values())

    if not fidelity_pass:
        return StoryForgeResult(
            profile_id=profile["profile_id"],
            request_id=req.request_id,
            status="translation_rejected",
            publication_ready=False,
            context_packet=packet,
            plan=plan,
            english_story=story,
            turkish_story=tr_story,
            proposed_story_outcome=plan.get("expected_outcome"),
            evidence=evidence,
        )

    return StoryForgeResult(
        profile_id=profile["profile_id"],
        request_id=req.request_id,
        status="publication_ready",
        publication_ready=True,
        context_packet=packet,
        plan=plan,
        english_story=story,
        turkish_story=tr_story,
        proposed_story_outcome=plan.get("expected_outcome"),
        evidence=evidence,
    )
