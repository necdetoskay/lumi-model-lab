"""SERA v0.22 — per-revision, restart-aware independent evidence worker.

Blind source-only sentence sweep (v0.10), source-bound independent semantic
advisories (v0.18), and separate typed facet proposals (v0.13) are
produced afresh for EVERY prose SHA + immutable entry-world SHA. The result
is a v0.21 noncanonical evidence bundle consumed by actual v0.19/v0.20
validators. This is an experimental worker: no authenticated production
commit, no human repair, no model output token ceiling.

Completed paid model replies are persisted before schema checks and reused.
Lost/unreceipted in-flight calls are NEVER sent again blindly. One fully
receipted malformed reply may route to a separate fallback model.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path

from experiments.sera.artifact_scene_checker_v021 import build_bundle, digest
from experiments.sera.coverage import CoverageError, prose_hash
from experiments.sera.mara_s1_typed_live_v05 import one_provider_call
from experiments.sera.openrouter_scene_writer_v021 import (
    _durable_provider_response, _provider_body,
)
from experiments.sera.request_policy import enforce_no_output_token_limit
from experiments.sera.semantic_recovery_v018 import execute as semantic_stage
from experiments.sera.sentence_sweep_v010 import (
    create_plan, bind_batch, aggregate,
)
from experiments.sera.world_state_v013 import EVENT_KEYS, TYPES
from experiments.sera.multifacet_physical_preview_v054 import source_backed_typed_match
from experiments.sera.sentence_ledger_v06 import sentences
from experiments.sera.world_state_v02 import canonical, validate as validate_world

SCHEMA = "sera.fresh-independent-evidence.v0.22"
SYSTEM = """Blind typed facet candidate proposal for a new story scene.
Only use the supplied source prose, REGISTERED object roles, and entry world.
Previous model reports are NOT available and must not be guessed.
Return JSON with exactly one key, typed_candidates, an array.
For a witnessed prior OPEN/CLOSED baseline return OBSERVE_OPENABLE, not
a fictional opening action. For an actual later state transition return
SET_OPENABLE only when that operation and its prior state are sourced.
For an actual verbatim document addition use APPEND_DOCUMENT_ENTRY.
Objects must be registered, co-located with their actor and have their
correct role. Every event must have EXACT v0.13 event keys:
event_id,type,actor_id,object_id,sentence_id,evidence,payload.
evidence has start,end,quote and MUST exactly slice the supplied prose.
OBSERVE_OPENABLE payload expected,observed. SET_OPENABLE payload expected,next.
APPEND_DOCUMENT_ENTRY payload expected_append_count,text.
No invented events, actions, absolute time, state, actors or object roles.
Return [] if these facet kinds do not occur. No authority or model approvals.
The v0.13 reducer validates this; raw model agreement is not world truth."""


def _require(ok, code):
    if not ok:
        raise CoverageError(code)


def _save(file, data):
    temp = file.with_suffix(".pending")
    with temp.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(
            data, ensure_ascii=False, indent=2, allow_nan=False,
        ) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(file)


def _load(file):
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CoverageError("V022_ARCHIVED_EVIDENCE_UNREADABLE") from exc


def _parse_json(raw):
    _require(isinstance(raw, str), "V022_MODEL_CONTENT_INVALID")
    content = raw.strip()
    fence = chr(96) * 3
    if content.startswith(fence):
        import re
        hit = re.fullmatch(
            r"\x60{3}(?:json)?[ \t]*\r?\n(.*?)\r?\n\x60{3}",
            content, re.I | re.S,
        )
        _require(hit is not None, "V022_MODEL_JSON_FENCE_INVALID")
        content = hit.group(1)
    try:
        answer = json.loads(content)
    except ValueError as exc:
        raise CoverageError("V022_MODEL_JSON_INVALID") from exc
    _require(isinstance(answer, dict), "V022_MODEL_JSON_OBJECT_REQUIRED")
    return answer


def _validate_typed(prose, answer):
    _require(set(answer) == {"typed_candidates"} and
             isinstance(answer["typed_candidates"], list),
             "V022_TYPED_REPLY_SCHEMA_INVALID")
    typed = answer["typed_candidates"]
    _require(len(typed) <= 256, "V022_TYPED_REPLY_TOO_MANY")
    seen = set()
    for row in typed:
        _require(isinstance(row, dict) and set(row) == EVENT_KEYS,
                 "V022_TYPED_EVENT_FIELDS_INVALID")
        eid = row["event_id"]
        _require(isinstance(eid, str) and eid and eid not in seen and
                 isinstance(row["type"], str) and row["type"] in TYPES and
                 isinstance(row["payload"], dict) and
                 set(row["payload"]) == TYPES[row["type"]],
                 "V022_TYPED_EVENT_SCHEMA_INVALID")
        seen.add(eid)
        proof = row["evidence"]
        _require(isinstance(proof, dict) and
                 set(proof) == {"start", "end", "quote"} and
                 type(proof["start"]) is int and type(proof["end"]) is int and
                 0 <= proof["start"] < proof["end"] <= len(prose) and
                 prose[proof["start"]:proof["end"]] == proof["quote"],
                 "V022_TYPED_EVENT_SOURCE_INVALID")
    return typed


SOURCE_BLOCKING_FINDING_PREFIXES=(
    "SWEEP_UNACCOUNTED_ACTION_CUE:",
    "SWEEP_MISSING_ENTITY_HINT:",
    "SWEEP_UNRESOLVED_SENTENCE:",
    "SWEEP_UNMAPPED_EVENT:",
    "SWEEP_CLAIM_PROMOTED_TO_WORLD:",
    "SWEEP_EXPECTED_EVENT_NOT_EXTRACTED:",
    "SWEEP_POSSIBLY_MISCLASSIFIED:",
    "SWEEP_COMPOUND_OPEN_WRITE_COLLAPSED:",
)


def _critical_source_findings(report):
    return [finding for finding in report["findings"]
            if isinstance(finding,str) and
            finding.startswith(SOURCE_BLOCKING_FINDING_PREFIXES)]


def _missing_critical_typed_sentence_ids(report, typed, *, prose=None):
    """Find only source-backed unaccounted critical actions (no model gold).

    This is a routing hint, NOT approval of the independent sweep or the
    typed model. Polarity matters: a typed CLOSE cannot account for OPEN.
    Nonphysical reported speech is deliberately excluded.
    """
    missing = set()
    for item in report["candidate_events"]:
        kind = item["kind"]
        if (kind not in ("OPEN", "CLOSE", "WRITE") or
                item["effect"] not in ("OBJECT", "DOCUMENT")):
            continue
        def supports(candidate):
            # SOURCE-EVIDENCED writing verb and exact quoted payload may be
            # nonoverlapping spans in the SAME original sentence.
            return source_backed_typed_match(
                prose=prose, event=item, candidate=candidate,
            )
        if not any(supports(row) for row in typed):
            missing.add(item["sentence_id"])
    return missing


def _check_critical_coverage(report, typed, *, prose=None):
    """No OPEN, CLOSE or WRITE may disappear or flip polarity."""
    _require(not _missing_critical_typed_sentence_ids(report, typed, prose=prose),
             "V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED")
    _require(not _critical_source_findings(report),
             "V022_UNRESOLVED_FULL_SENTENCE_SWEEP_FINDING")


def _source_only_repair_request(*, original, failure_code, attempt):
    """New exact request after RECEIPTED malformed answer; no prior output.

    Never insert model's rejected answer/claims into its own repair context.
    Distinct attempt and source-only deterministic validation code become
    part of the signed journal's new request fingerprint.
    """
    import re
    _require(isinstance(original,dict) and
             isinstance(original.get("messages"),list) and
             len(original["messages"])>=2 and
             original["messages"][0].get("role")=="system" and
             original["messages"][-1].get("role")=="user" and
             isinstance(original["messages"][0].get("content"),str) and
             isinstance(original["messages"][-1].get("content"),str) and
             type(attempt) is int and 1<=attempt<=2,
             "V022_REPAIR_ORIGINAL_REQUEST_INVALID")
    safe=(failure_code if isinstance(failure_code,str) and
          re.fullmatch(r"[A-Z0-9_]{1,100}",failure_code)
          else "V022_MODEL_RESPONSE_INVALID")
    amended=deepcopy(original)
    amended["messages"][0]["content"]+=(
        "\\n\\nSOURCE-ONLY AUTOMATIC RE-EXTRACTION, attempt "+
        str(attempt)+". Deterministic validator code: "+safe+
        ". Read the ORIGINAL user source from scratch and return EVERY "
        "required target row and exactly the specified JSON keys. "
        "No previous model output, Writer analysis, gold answers or "
        "manual corrections are provided. Preserve all uncertainty; "
        "never invent an event, actor, location or action time.")
    enforce_no_output_token_limit(amended)
    return amended



def _deterministic_physical_source_focus(plan):
    """Only ORIGINAL source sentences with lexical physical/document cues.

    The scanner is app-owned and source-only; this list carries NO event
    type, model verdict, suggested actor/object, gold annotation, or fix.
    It merely directs the next independent read toward likely activity.
    """
    _require(isinstance(plan,dict) and
             isinstance(plan.get("source_sentences"),list) and
             isinstance(plan.get("source_scan"),dict),
             "V022_TYPED_FOCUS_SOURCE_PLAN_INVALID")
    source={s["id"]:s for s in plan["source_sentences"]}
    focus=[]
    seen=set()
    for item in plan["source_scan"].get("sentence_cues",[]):
        if not any(c.get("family") in ("PHYSICAL_CHANGE","DOCUMENT_CHANGE")
                   for c in item.get("cues",[])):
            continue
        sid=item.get("sentence_id")
        _require(sid in source,"V022_TYPED_FOCUS_UNKNOWN_SOURCE")
        if sid in seen: continue
        seen.add(sid)
        row=source[sid]
        focus.append({"sentence_id":sid,
                      "source_quote":row["quote"]})
    return focus


def _typed_only_coverage_retry_request(*,original,attempt,source_focus=None):
    """Retry valid-schema but missed typed source action without prior replies.

    The SOURCE prose and app-owned registered roles come from the original
    typed request. Neither extractor's classification nor first typed model
    output is provided, so no rejected candidate can contaminate the retry.
    """
    _require(type(attempt) is int and 1<=attempt<=2 and
             isinstance(original,dict) and
             isinstance(original.get("messages"),list) and
             len(original["messages"])==2 and
             original["messages"][0].get("role")=="system" and
             original["messages"][1].get("role")=="user" and
             isinstance(original["messages"][0].get("content"),str) and
             isinstance(original["messages"][1].get("content"),str),
             "V022_TYPED_REEXTRACTION_ORIGINAL_INVALID")
    if source_focus is not None:
        _require(isinstance(source_focus,list) and
                 all(isinstance(x,dict) and
                     set(x)=={"sentence_id","source_quote"} and
                     isinstance(x["sentence_id"],str) and
                     isinstance(x["source_quote"],str) and
                     x["source_quote"] for x in source_focus),
                 "V022_TYPED_FOCUS_QUOTE_INVALID")
        try:
            packet=json.loads(original["messages"][1]["content"])
        except (ValueError,TypeError) as exc:
            raise CoverageError("V022_TYPED_FOCUS_ORIGINAL_PACKET_INVALID") from exc
        prose=packet.get("original_prose") if isinstance(packet,dict) else None
        _require(isinstance(prose,str) and prose.strip(),
                 "V022_TYPED_FOCUS_ORIGINAL_PACKET_INVALID")
        actual={x["id"]:x["quote"] for x in sentences(prose)}
        _require(len({r["sentence_id"] for r in source_focus})==
                 len(source_focus) and
                 all(actual.get(row["sentence_id"])==row["source_quote"]
                     for row in source_focus),
                 "V022_TYPED_FOCUS_NOT_VERBATIM_SOURCE")
    amended=deepcopy(original)
    amended["messages"][0]["content"]+=(
        "\n\nINDEPENDENT SOURCE-ONLY TYPED FACET RE-EXTRACTION, attempt "+
        str(attempt)+". Deterministic gate reported a source-backed "
        "physical/document event without a matching typed reducer action. "
        "Read the ORIGINAL prose and APP-REGISTERED facet roles from "
        "the unchanged user packet again. Return exactly one JSON object "
        "with typed_candidates, including only ACTUAL supported actions, "
        "and exact evidence spans/sentence IDs. If unable to prove an "
        "action, omit it rather than invent a transition. "
        "Previous model replies, other extractors' candidate decisions, "
        "gold answers, and manual corrections are NOT available.")
    if source_focus:
        # Quoted source cues are deterministic, not a prior model's answer.
        amended["messages"][0]["content"]+=(
            "\\n\\nLEXICAL SOURCE ATTENTION ONLY; not event labels or gold. "
            "Verify every action independently from ORIGINAL prose. "
            "These are the complete source sentence quotes selected by "
            "the deterministic cue scanner, not a list of approved events: "+
            json.dumps(source_focus,ensure_ascii=False,sort_keys=True))
    enforce_no_output_token_limit(amended)
    return amended



def _typed_source_window_request(*, original, target_sentences):
    """Independent typed reread of one exact source window, without old replies.

    The unmodified complete source and entry world remain available as
    context. Only window sentence IDs may appear in the response; neither
    sweep labels nor gold events are supplied as a proposed answer.
    """
    _require(isinstance(original, dict) and
             isinstance(original.get("messages"), list) and
             len(original["messages"]) == 2 and
             isinstance(original["messages"][0].get("content"), str) and
             isinstance(original["messages"][1].get("content"), str) and
             isinstance(target_sentences, list) and
             bool(target_sentences),
             "V022_TYPED_WINDOW_REQUEST_INVALID")
    try:
        packet = json.loads(original["messages"][1]["content"])
    except (TypeError, ValueError) as exc:
        raise CoverageError("V022_TYPED_WINDOW_SOURCE_INVALID") from exc
    prose = packet.get("original_prose") if isinstance(packet, dict) else None
    _require(isinstance(prose, str) and bool(prose.strip()),
             "V022_TYPED_WINDOW_SOURCE_INVALID")
    actual = {item["id"]: item for item in sentences(prose)}
    ids = [item.get("id") for item in target_sentences
           if isinstance(item, dict)]
    _require(len(ids) == len(target_sentences) and
             len(set(ids)) == len(ids) and
             all(isinstance(ident, str) and
                 actual.get(ident) == row for ident, row in
                 zip(ids, target_sentences)),
             "V022_TYPED_WINDOW_NOT_VERBATIM_SOURCE")
    amended = deepcopy(original)
    amended["messages"][0]["content"] += (
        "\n\nINDEPENDENT EXACT SOURCE WINDOW TYPED RE-EXTRACTION. "
        "The complete ORIGINAL prose/registered capabilities/entry world "
        "remain in the user packet as read-only context. Extract ONLY "
        "actual supported typed actions in these TARGET source sentences, "
        "with original-global evidence offsets and sentence IDs: " +
        json.dumps(target_sentences, ensure_ascii=False, sort_keys=True) +
        ". Do not output typed actions from context sentences. "
        "Do not invent missing observations, events, object states or "
        "action times. Prior model replies, proposed repairs, Writer "
        "conclusions and analyst gold are NOT supplied.")
    enforce_no_output_token_limit(amended)
    return amended


def _validate_typed_window(prose, answer, target_sentences):
    typed = _validate_typed(prose, answer)
    source = {s["id"]: s for s in target_sentences}
    _require(all(
        item["sentence_id"] in source and
        source[item["sentence_id"]]["start"] <= item["evidence"]["start"] <
        item["evidence"]["end"] <= source[item["sentence_id"]]["end"]
        for item in typed
    ), "V022_TYPED_WINDOW_OUTSIDE_TARGET")
    return typed


def create_preparer(*, evidence_root, work_root, scene_key,
                    registry, candidate_lexicon, typed_registry,
                    api_key, extraction_model, semantic_model, typed_model,
                    provider_call=one_provider_call,
                    fallback_model=None,
                    max_model_requests=24, observed_spend_guard_usd="0.30",
                    trusted_temporal_builder=None,
                    temporal_policy_id=None,
                    trusted_relation_builder=None,
                    relation_policy_id=None, reconciler=None,
                    max_source_repair_attempts=0,
                    typed_batch_recovery=False):
    """Return v0.20 prepare_evidence(prose=...,world=...) callback.

    The caller supplies only registered world identities and provider
    settings. No per-story human classification/gold/correction is needed.
    Archived evidence is keyed by source + world and never re-authorizes
    canonical publication. Distinct work_root/evidence_root per scene job.
    """
    _require(all(isinstance(x, str) and x for x in (
        scene_key, api_key, extraction_model, semantic_model, typed_model,
    )), "V022_CONFIGURATION_INVALID")
    _require(isinstance(registry, dict) and
             isinstance(candidate_lexicon, dict) and
             isinstance(typed_registry, dict) and
             set(typed_registry) == {"openables", "documents"},
             "V022_REGISTRY_CONFIGURATION_INVALID")
    _require((trusted_temporal_builder is None and
              temporal_policy_id is None) or
             (callable(trusted_temporal_builder) and
              isinstance(temporal_policy_id, str) and
              bool(temporal_policy_id.strip())),
             "V024_TEMPORAL_BUILDER_POLICY_INVALID")
    _require((trusted_relation_builder is None and
              relation_policy_id is None) or
             (callable(trusted_relation_builder) and
              isinstance(relation_policy_id, str) and
              bool(relation_policy_id.strip())),
             "V025_RELATION_BUILDER_POLICY_INVALID")
    _require(reconciler is None or callable(reconciler),
             "V030_EVIDENCE_RECONCILER_INVALID")
    _require(type(max_model_requests) is int and
             1 <= max_model_requests <= 100,
             "V022_REQUEST_GUARD_INVALID")
    _require(type(max_source_repair_attempts) is int and
             0<=max_source_repair_attempts<=2,
             "V022_SOURCE_REPAIR_POLICY_INVALID")
    _require(type(typed_batch_recovery) is bool,
             "V022_TYPED_WINDOW_POLICY_INVALID")
    _require(fallback_model is None or (
        isinstance(fallback_model, str) and bool(fallback_model.strip()) and
        fallback_model not in (extraction_model, typed_model)
    ), "V022_FALLBACK_MODEL_INVALID")
    try:
        guard = Decimal(str(observed_spend_guard_usd))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CoverageError("V022_SPEND_GUARD_INVALID") from exc
    _require(guard.is_finite() and guard > 0, "V022_SPEND_GUARD_INVALID")
    outroot = Path(evidence_root)
    workroot = Path(work_root)
    _require(outroot != workroot, "V022_OUTPUT_ROOT_COLLISION")
    known_registry = deepcopy(registry)
    lexicon = deepcopy(candidate_lexicon)
    roles = deepcopy(typed_registry)
    models = [extraction_model] + ([fallback_model] if fallback_model else [])
    typed_models = [typed_model] + ([fallback_model] if fallback_model else [])

    def prepare_evidence(*, prose, world):
        validate_world(world)
        _require(isinstance(prose, str) and prose.strip(),
                 "V022_PROSE_REQUIRED")
        source_sha = prose_hash(prose)
        world_sha = digest(world)
        contract = {
            "schema": SCHEMA, "source_sha": source_sha,
            "world_sha": world_sha, "scene_key": scene_key,
            "registry_sha": digest(known_registry),
            "candidate_lexicon_sha": digest(lexicon),
            "roles_sha": digest(roles),
            "models": [extraction_model, semantic_model,
                       typed_model, fallback_model],
            "max_model_requests": max_model_requests,
            "max_source_repair_attempts": max_source_repair_attempts,
            "observed_spend_guard_usd": str(guard),
        }
        if typed_batch_recovery:
            contract["typed_batch_recovery"] = True
        if trusted_temporal_builder is not None:
            contract["temporal_policy_id"] = temporal_policy_id
        if trusted_relation_builder is not None:
            contract["relation_policy_id"] = relation_policy_id
        job_id = sha256(canonical(contract).encode("utf-8")).hexdigest()
        root = workroot / job_id
        root.mkdir(parents=True, exist_ok=True)
        if (root / "contract.json").exists():
            _require(_load(root / "contract.json") == contract,
                     "V022_RESUME_SOURCE_OR_POLICY_DRIFT")
        else:
            _save(root / "contract.json", contract)
        final = root / "final.json"
        target = outroot / (source_sha + ".json")
        if final.is_file():
            previous = _load(final)
            if previous.get("status") != "EVIDENCE_READY_NONCANONICAL":
                # Only an authenticated, previously STARTED provider call
                # may reopen terminal safe failure: no fresh provider POST
                # is allowed for the pending signature. All other failed
                # worlds, policies or semantic gates remain terminal.
                orphaned = (
                    list((root / "receipts").glob("*/*.started")) or
                    list((root / "semantic").glob("started_*.json"))
                )
                allowed = {
                    "V021_UNCONFIRMED_IN_FLIGHT_PROVIDER_CALL",
                    "V021_UNRECEIPTED_PROVIDER_RESULT",
                    "V030_GENERATION_ID_UNAVAILABLE_NO_RESEND",
                    "V030_PROVIDER_READ_UNAVAILABLE",
                    "V022_SEMANTIC_STAGE_FAILED_SAFE",
                }
                if (reconciler is None or
                    previous.get("status") != "FAILED_SAFE_FINAL" or
                    previous.get("failure_code") not in allowed or
                    not orphaned):
                    return previous
                prior = root / "pre_reconciliation_safe_stop.json"
                if not prior.exists():
                    _save(prior, previous)
                else:
                    _require(_load(prior) == previous,
                             "V030_EVIDENCE_PRIOR_FAILURE_DRIFT")
                final.unlink()
            else:
                if target.is_file():
                    verified = _load(target)
                    _require(isinstance(verified, dict) and
                             verified.get("prose_sha256") == source_sha and
                             verified.get("world_sha256") == world_sha,
                             "V022_COMPLETED_EVIDENCE_SOURCE_OR_WORLD_CHANGED")
                    return previous
                # A completed receipt can be reconstructed from already
                # archived paid envelopes if its export vanished.
                final.unlink()

        spent = Decimal("0")
        calls = 0
        failure = None
        def finish(status, failure_code=None, *, report=None):
            result = {
                "schema": SCHEMA, "status": status,
                "failure_code": failure_code,
                "prose_sha256": source_sha,
                "world_sha256": world_sha,
                "new_source_prose_sha256": source_sha,
                "sentence_count": report.get("sentences_accounted_for", 0)
                                  if report else 0,
                "candidate_event_count": len(report["candidate_events"])
                                         if report else 0,
                "provider_calls_accounted": calls,
                "provider_spend_observed_usd": str(spent),
                "canonical_commit_authorized": False,
                "world_db_writes": 0,
                "requires_manual_intervention": False,
            }
            _save(final, result)
            return result

        def provider_json(*, tag, request, stage_models, bind, schema_retry=True):
            nonlocal spent, calls
            enforce_no_output_token_limit(request)
            last_reason="V022_ALL_RECEIPTED_MODELS_UNQUALIFIED"
            for chosen in stage_models:
                for retry_no in range((max_source_repair_attempts if schema_retry else 0)+1):
                    if calls>=max_model_requests or spent>=guard:
                        raise CoverageError("V022_CALL_OR_SPEND_GUARD")
                    exact=(request if retry_no==0 else
                           _source_only_repair_request(
                                original=request,failure_code=last_reason,
                                attempt=retry_no))
                    tag_id=(tag if retry_no==0 else
                            tag+"_source_repair_"+str(retry_no))
                    # Each repaired request is a DIFFERENT fingerprint and
                    # needs another signed grant slot. Unknown network
                    # outcomes stop before this block can reach retry.
                    try:
                        reply=_durable_provider_response(
                            root=root/"receipts"/tag_id,model=chosen,
                            request=exact,api_key=api_key,
                            provider_call=provider_call,reconciler=reconciler)
                    except (TimeoutError,ConnectionError,BrokenPipeError) as exc:
                        # Transport failed after a durable STARTED marker.
                        # This stage must halt: no billable second POST for
                        # an outcome that might already have been charged.
                        raise CoverageError(
                            "V021_UNCONFIRMED_IN_FLIGHT_PROVIDER_CALL") from exc
                    calls+=1
                    body,choice,price=_provider_body(reply,chosen)
                    spent+=price
                    try:
                        _require(choice["finish_reason"]=="stop",
                                 "V022_PROVIDER_INCOMPLETE")
                        decoded=_parse_json(choice["message"].get("content"))
                        return bind(decoded)
                    except (CoverageError,ValueError,TypeError) as exc:
                        last_reason=(exc.code if isinstance(exc,CoverageError)
                                     else "V022_MODEL_RESPONSE_INVALID")
                        # A received malformed response can be repaired
                        # autonomously; never pass old untrusted prose back.
                # An independently signed fallback model, if configured,
                # starts from the unchanged original request.
            raise CoverageError(last_reason)

        try:
            if target.is_file():
                older = _load(target)
                _require(isinstance(older, dict) and
                         older.get("world_sha256") == world_sha and
                         older.get("prose_sha256") == source_sha,
                         "V022_DIFFERENT_PROOF_FOR_SAME_SOURCE")
            plan = create_plan(
                prose=prose, scene_key=scene_key,
                entry_revision=world["revision"], registry=known_registry,
                candidate_lexicon=lexicon,
            )
            bound = []
            for batch in plan["batches"]:
                request = {
                    "messages": batch["messages"],
                    "response_format": batch["response_format"],
                }
                bound.append(provider_json(
                    tag=batch["batch_id"], request=request,
                    stage_models=models,
                    bind=lambda answer, ident=batch["batch_id"]: bind_batch(
                        plan=plan, batch_id=ident,
                        raw=answer, prose=prose,
                    ),
                ))
            report = aggregate(plan=plan, bound_batches=bound, prose=prose)
            # Fully receipted, syntactically valid extraction can still
            # omit a source-cued physical action or object. Re-run ONLY the
            # affected source batches with the original blind source packet.
            # No old model text, Writer claims or fabricated gold labels.
            if max_source_repair_attempts and _critical_source_findings(report):
                blocked_ids={finding.split(":",2)[1]
                             for finding in _critical_source_findings(report)}
                for batch_idx,batch in enumerate(plan["batches"]):
                    if not blocked_ids.intersection(batch["sentence_ids"]):
                        continue
                    original_request={
                        "messages": batch["messages"],
                        "response_format": batch["response_format"],
                    }
                    repair_request=_source_only_repair_request(
                        original=original_request,
                        failure_code="V022_SOURCE_COVERAGE_DEFICIT",
                        attempt=1)
                    bound[batch_idx]=provider_json(
                        tag=batch["batch_id"]+"_coverage_repair",
                        request=repair_request,stage_models=models,
                        schema_retry=False,
                        bind=lambda answer, ident=batch["batch_id"]: bind_batch(
                            plan=plan,batch_id=ident,raw=answer,prose=prose))
                report=aggregate(plan=plan,bound_batches=bound,prose=prose)
                _require(not _critical_source_findings(report),
                         "V022_SOURCE_COVERAGE_REPAIR_EXHAUSTED")
            _save(root / "full_sweep.json", report)
            if spent >= guard:
                raise CoverageError("V022_SPEND_GUARD_BEFORE_SEMANTIC")
            calls_before_semantic = calls
            spent_before_semantic = spent
            def semantic_call(*, model, prepared):
                nonlocal spent, calls
                if calls >= max_model_requests or spent >= guard:
                    raise CoverageError("V022_SEMANTIC_SPEND_OR_CALL_GUARD")
                answer = provider_call(key=api_key, model=model,
                                       prepared=prepared)
                calls += 1
                raw = answer.get("raw") if isinstance(answer, dict) else None
                usage = raw.get("usage") if isinstance(raw, dict) else None
                if isinstance(usage, dict) and usage.get("cost") is not None:
                    value = Decimal(str(usage["cost"]))
                    _require(value.is_finite() and value >= 0,
                             "V022_SEMANTIC_COST_INVALID")
                    spent += value
                return answer
            summary = semantic_stage(
                prose=prose, extraction_report=report,
                call_model=semantic_call, output_dir=root / "semantic",
                primary_model=semantic_model,
                fallback_model=fallback_model or semantic_model,
                max_provider_calls=min(20, max_model_requests),
                observed_spend_guard_usd=str(guard),
                reconciler=reconciler,
            )
            _require(summary["status"] in (
                "SEMANTIC_ADVISORIES_COMPLETE_NONCANONICAL",
                "NO_TARGETED_RISKS_FOUND_NONCANONICAL",
            ), "V022_SEMANTIC_STAGE_FAILED_SAFE")
            # v0.18 includes both newly paid and cached receipts; do not
            # double-count newly performed semantic calls on this iteration.
            calls = calls_before_semantic + summary["provider_calls"]
            spent = spent_before_semantic + Decimal(summary["observed_spend_usd"])
            source_input = {
                "schema": SCHEMA, "source_prose_sha256": source_sha,
                "scene_key": scene_key, "original_prose": prose,
                "registered_roles": roles,
                "entry_world": world,
                "previous_model_opinions": "NOT_PROVIDED",
            }
            # v0.54 has a separate, detached multi-capability reducer.
            # An explicit first OPEN action with unknown prior state is a
            # transition, NOT a passive observation, and must not invent
            # a CLOSED baseline. Do not advertise this policy to legacy
            # single-capability v0.13 validators.
            multifacet=bool(set(roles["openables"]) & set(roles["documents"]))
            typed_system=SYSTEM
            if multifacet:
                typed_system+=(
                    "\n\nMULTI-CAPABILITY SOURCE ACTION POLICY (v0.54): "
                    "If original prose explicitly states an opening or "
                    "closing ACTION for a registered multi-capability object "
                    "but its preceding OPEN/CLOSED state is unknown, return "
                    "SET_OPENABLE with expected UNKNOWN and next OPEN or "
                    "CLOSED as directly stated. UNKNOWN does not mean the "
                    "object was previously CLOSED or OPEN. Use "
                    "OBSERVE_OPENABLE only when the source DESCRIBES a "
                    "state, without performing an opening/closing action. "
                    "Return exact global source spans and maintain order. "
                    "Never invent a prior state or action."
                )
            typed_request = {
                "messages": [
                    {"role": "system", "content": typed_system},
                    {"role": "user", "content": canonical(source_input)},
                ],
                "response_format": {"type": "json_object"},
            }
            typed = provider_json(
                tag="typed", request=typed_request,
                stage_models=typed_models,
                bind=lambda ans: _validate_typed(prose, ans),
            )
            source_focus=_deterministic_physical_source_focus(plan)
            # A complete, paid, valid JSON facet list can nevertheless miss
            # an independently source-bound CLOSE / WRITE. A single fresh
            # typed-only reread is safer than treating syntactic JSON as a
            # completed scene, and it needs a new durable signed request.
            # Unknown in-flight POST outcomes are still NEVER blindly resent.
            for attempt in range(1,max_source_repair_attempts+1):
                try:
                    _check_critical_coverage(report,typed,prose=prose)
                    break
                except CoverageError as exc:
                    if str(exc)!="V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED":
                        raise
                typed = provider_json(
                    tag="typed_coverage_repair_"+str(attempt),
                    request=_typed_only_coverage_retry_request(
                        original=typed_request,attempt=attempt,
                        source_focus=source_focus),
                    stage_models=typed_models,schema_retry=False,
                    bind=lambda ans: _validate_typed(prose,ans),
                )
            # If full-scene rereads still omit source-cued actions, break
            # the ORIGINAL scene into existing four-sentence source windows.
            # Run each independently; never turn prior model responses into
            # ground truth or reuse full-scene candidate lists as answers.
            if typed_batch_recovery:
                missing = False
                try:
                    _check_critical_coverage(report, typed, prose=prose)
                except CoverageError as exc:
                    if str(exc) != "V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED":
                        raise
                    missing = True
                if missing:
                    gaps = _missing_critical_typed_sentence_ids(report, typed, prose=prose)
                    selected_batches = [
                        batch for batch in plan["batches"]
                        if gaps.intersection(batch["sentence_ids"])
                    ]
                    # Preserve candidates from UNTOUCHED source batches.
                    # Each targeted window is reread in full; old opinions
                    # from that window are NOT given to its extractor.
                    replaced = {
                        sid for batch in selected_batches
                        for sid in batch["sentence_ids"]
                    }
                    window_candidates = [
                        row for row in typed
                        if row["sentence_id"] not in replaced
                    ]
                    for batch in selected_batches:
                        targets = [s for s in plan["source_sentences"]
                                   if s["id"] in batch["sentence_ids"]]
                        window_request = _typed_source_window_request(
                            original=typed_request, target_sentences=targets)
                        window_candidates.extend(provider_json(
                            tag="typed_window_"+batch["batch_id"],
                            request=window_request,
                            stage_models=[typed_model], schema_retry=False,
                            bind=lambda ans, selected=targets:
                                _validate_typed_window(prose, ans, selected),
                        ))
                    window_candidates.sort(
                        key=lambda row: (row["evidence"]["start"],
                                         row["evidence"]["end"],
                                         row["event_id"]))
                    _require(len(set(x["event_id"] for x in
                                     window_candidates)) ==
                             len(window_candidates),
                             "V022_TYPED_WINDOW_DUPLICATE_EVENT_ID")
                    _require(len(window_candidates) <= 256,
                             "V022_TYPED_REPLY_TOO_MANY")
                    # Defer the final coverage check to the existing
                    # independent fallback path; a well-receipted, but
                    # incomplete window set must not skip that model.
                    typed = window_candidates
            # A syntactically valid but STILL incomplete primary facet
            # model can be checked by an explicitly configured alternate
            # model. Distinct model/request/tag = new auditable receipt.
            # No fallback is silently invented or used unless configured.
            try:
                _check_critical_coverage(report,typed,prose=prose)
            except CoverageError as exc:
                if (str(exc)!="V022_CRITICAL_TYPED_EVENT_NOT_ACCOUNTED" or
                    fallback_model is None):
                    raise
                typed=provider_json(
                    tag="typed_coverage_independent_fallback",
                    request=_typed_only_coverage_retry_request(
                        original=typed_request,attempt=1,
                        source_focus=source_focus),
                    stage_models=[fallback_model],schema_retry=False,
                    bind=lambda ans:_validate_typed(prose,ans))
                _check_critical_coverage(report,typed,prose=prose)
            temporal_case = None
            if trusted_temporal_builder is not None:
                # Application-owned route/time policy, never a model's
                # self-selected destination or invented action minute.
                temporal_case = trusted_temporal_builder(
                    prose=prose, world=deepcopy(world),
                    extraction_report=deepcopy(report),
                )
                _require(temporal_case is None or
                         (isinstance(temporal_case, dict) and
                          temporal_case.get("entry") == world and
                          temporal_case.get("scene_key") == scene_key),
                         "V024_TEMPORAL_APPLICATION_POLICY_INVALID")
            relation_case = None
            if trusted_relation_builder is not None:
                relation_case = trusted_relation_builder(
                    prose=prose, world=deepcopy(world),
                    extraction_report=deepcopy(report),
                )
                _require(relation_case is None or (
                    isinstance(relation_case, dict) and
                    relation_case.get("entry") == world and
                    relation_case.get("policy_id") == relation_policy_id
                ), "V025_RELATION_APPLICATION_POLICY_INVALID")
            bundle = build_bundle(
                prose=prose, world=world,
                extraction_report=report, semantic_summary=summary,
                typed_registry=roles, typed_candidates=typed,
                temporal_case=temporal_case,
                relation_case=relation_case,
            )
            outroot.mkdir(parents=True, exist_ok=True)
            if target.exists():
                _require(_load(target) == bundle,
                         "V022_DIFFERENT_PROOF_FOR_SAME_SOURCE")
            else:
                _save(target, bundle)
            return finish("EVIDENCE_READY_NONCANONICAL", report=report)
        except (CoverageError, OSError, ValueError, TypeError, KeyError) as exc:
            failure = str(exc)
            return finish("FAILED_SAFE_FINAL", failure)

    return prepare_evidence
