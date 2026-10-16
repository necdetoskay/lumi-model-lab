# SERA M3.5 — Typed Extraction v0.5 and Temporal Domains v0.5

**Date:** 2026-10-16  
**Status:** Experimental implementation / no live state acceptance  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Issues:** [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304), [#305](https://github.com/necdetoskay/lumi-model-lab/issues/305)  
**Frozen Mara source prose SHA-256:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`  
**Original Sonnet Spine Git blob:** `fe1dda0047000438bbfaac69022e835bf7e0a1f8`

## Purpose

Turn unstructured M2 model reports into explicitly typed candidate actions and
bounded relative-time constraints **without granting the LLM authority** over
entity history, object conditions, clothing, facts, or the SQLite world-state
ledger. This is a continuation of M3.4, not a production promotion.

## 1. Provider-facing strict schema

`typed_extractor_contract_v05.py` generates a **blind** independent
extractor prompt and a structured JSON schema in which each allowed operation
has exact required argument names (no `arguments={}`). The allowed typed
operations are:

- `INTERACT_OBJECT` → `INTERACT_ENTITY`
- `MOVE_CHARACTER` → `MOVE_CHARACTER`
- `TRANSFER_OBJECT` → `TRANSFER_HOLDER`
- `LEARN_FACT` and `TELL_FACT` → attributable `LEARN_FACT`
- `UNMAPPED_STATE_CHANGE` → explicit HOLD record, not a silent omission.

All quotations and their zero-based occurrence indices are mapped to Python
codepoint offsets; output is bound to a pinned prompt digest, the identical
prose, scene key and entry revision. The model is NOT sent other extractor
reports or prior JEV/gold labels. Unknown objects use provisional
`new:<slug>` IDs; they cannot self-authorize creation.

A typed schema does **not** prove truth or recall. Every nonempty model-provided
absolute action time remains HOLD until separately adjudicated as truly
referring to the ACTION, not a watch face or document. Empty mentions/events
also HOLD instead of becoming a spurious vacuous PASS.

**Provider compatibility caveat:** The generated JSON-schema uses `oneOf`
variants, which require explicit live provider validation. Schema validation
is repeated deterministically in Python regardless of any claimed provider
formatting guarantee. No automatic repair/retry is authorized.

## 2. Relative time without pretending to know a clock

`temporal_domains_v05.py` computes feasible bounds for application-reviewed
scene events using:

- scene-local order;
- causal predecessor and minimum-lag edges;
- per-event earliest/latest/exact constraints;
- actor-specific movement and configured minimum travel times;
- forward and backward propagation to reject incompatible event bounds.

Example: with Mara at the station at minute 135, a trip requiring 10 minutes
cannot finish at minute 139. Even when an action has a feasible range,
`narrative_exact_minute` stays `null` unless separately grounded.

An optional `simulation_schedule` exposes the earliest feasible internal
cursor, **clearly labeled NOT a narrative fact**. This is not a trusted
world-event timestamp or application approval. A full scene-level authority
and spatial/causal time resolver is still required before production commit.

## 3. Frozen live Mara v0.5 diagnostic — two distinct trials

Source: exactly the prior 243-word Mara first scene, unchanged.

**Attempt A, one independent request:**  
[GitHub Actions 38849464433](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38849464433).

- Provider: `google/gemini-3.7-flash`.
- Response: **DIAGNOSTIC_INCOMPLETE_HOLD**.
- Provider-reported cost: **USD 0.0183705** (this request only).
- Completion cap: 4096; `finish_reason=length`.
- Recorded `prompt_tokens=4084`, `completion_tokens=4082`.
- Captured raw text had 3560 characters but was not parseable as complete JSON;
  none of it was committed.
- [Read-only artifact forensics 38849793699](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38849793699)
  verified these facts using the archived evidence **without another model call**.

**Attempt B, one separately pinned request:**  
[GitHub Actions 38849926511](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38849926511).

- Same source and model; one trial with optional reasoning disabled.
- Provider returned **HTTP 400**; no valid extractor data was produced.
- The precise cause of the HTTP 400 was not established by the available
  completed log evidence; we therefore do **not** claim a proven provider
  incompatibility specific to one parameter.
- Cost for this rejected request was **not reported**; do not infer USD 0.
- The unqualified reasoning override was subsequently removed from the
  default transport. No further paid retry was run.

Neither attempt produced a completed independent typed extraction, and neither
called JEV, wrote to a story/world database, or produced a canonical exit state.
Earlier Mara M2 HOLD / JEV ESCALATE is **still in force**.

## 4. Tests and safety

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.mara_s1_typed_live_v05
```

Tests cover mandatory per-event keys, unknown object IDs, claim attribution,
JSON/quote fingerprints, empty extraction, absolute-time HOLD, partially
ordered event domains, causal cycle/forward dependencies, impossible travel,
window contradictions, and fully non-mutating dry-run transport.

All new files are isolated in `experiments/sera/` plus dedicated SERA-only
Actions workflows. No V4/V4.1/V4.2 production pipeline or Sonnet Spine mutation.

## 5. Remaining blockers and next qualified experiment

1. Reduce provider completion pressure using a tested compact schema and/or
   split **object/character mentions** from **typed event extraction** into
   separately capped calls. Preserve both independent outputs, and avoid
   losing coverage when a model does not know a type.
2. Determine provider schema compatibility and error details from stored
   diagnostics before any new billable call; do not blindly increase token
   budgets or silently fall back to weaker JSON.
3. Build a human-adjudicated first-scene gold annotation (incl. bench/pencil,
   narration-vs-claim and case-closed/notebook-writing). **No evidence that a
   dual extractor is exhaustive yet**.
4. Introduce type-safe mutations for document content and the watch-case
   open/closed attribute, and a source-grounded event-time adjudicator.
5. Create an actual provenance-bound application approval gate (authenticates
   both decision maker and evidence) before any real EventGraph SQLite write.
6. Only after **all** relevant events and objects pass independent recall,
   semantic JEV review and deterministic state checks, generate a qualified
   full S1 exit snapshot. Then move to S2.

The test-suite PASS status means the implementation behaves as expected on
offline fixtures; it does NOT imply the generated narrative state is correct.
