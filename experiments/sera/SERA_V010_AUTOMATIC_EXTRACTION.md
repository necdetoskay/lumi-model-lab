# SERA v0.10 — Automatic Blind Sentence Sweep + Targeted Repair

**2026-10-16** · Experimental, isolated branch only.  
**Scope:** improve automatic entity/event candidate recall; do not impose manual approval on every production story.  
**Source:** frozen Mara S1 prose SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`; original Sonnet Spine blob remains `fe1dda0047000438bbfaac69022e835bf7e0a1f8`.  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

## Why

v0.9 qualified the review **user interface**, not automatic extraction.
The original v0.5 blind extractor asks one model for an entire scene,
full entry state and nested type-union JSON. That previously generated a
truncated, unfinished response. The earlier explicit model-output ceiling
was a user-prohibited mistake, and that ceiling has been removed from all
newer vetted clients.

The new v0.10 *evidence-sweep* is an additive, provider-agnostic approach:
split narrative **by source sentences** and request one compact review row
for each target sentence. Preserve surrounding context without treating it
as new events. Each event/mention is grounded by Python to an exact substring
and occurrence within the numbered source sentence, not a model-invented
character offset.

**Four target sentences per request is a narrative partition decision,
not an LLM output-token limit.** There are seven batches for Mara's 28
source sentences. **No configured output-token limit is sent to the provider.**

## What was implemented

### Automatic structural extraction

`sentence_sweep_v010.py`:

- `create_plan`: seven deterministic blind batches, original registered
  aliases, independent lexical hints and state-change cues. It never
  includes Writer reports, the original nine analyst judgments or
  previous model decisions.
- `bind_batch`: requires exactly one result for every target sentence
  in order, exact quote+zero-based occurrence for every candidate,
  typed disposition, event epistemics, effect class, entity references
  and explicit reason. Invalid or missing rows are rejected.
- `aggregate`: requires every batch and all source sentences, binds
  evidence to the existing v0.6 Sentence Ledger, finds lexical entities
  unreported by the model and physical/document action cues that lack
  event evidence. Contradictory `CLAIM_ONLY` world events are flagged;
  model-side dispositions cannot bypass the deterministic ledger.
- `summarize_partial`: preserves completed batch identities and failed
  request digests. Missing batches remain **HOLD_INCOMPLETE_SOURCE**
  and can be targeted individually; there is no automatic unlimited retry.
- `prepare_probe_request` and `bind_probe_response`: independent
  narrow questions about under-reported entities and actions, with
  exact source evidence; no prior model opinions or unbounded
  self-confirmation. Probe verdicts are **HOLD**, never truth.

### Real, one-call pilot preflight

`mara_s1_sweep_pilot_v010.py`:

- Pinned **one batch containing `closed the case`** of frozen Mara S1.
- Reuses vetted no-token-cap OpenRouter request code and existing
  provider-key preflight; uses JSON object output without huge nested
  JSON-schema.
- Source hash, entry revision and request digest are fixed before send.
- Exactly one provider attempt; no fallback, automatic retry, Writer
  rewrite, JEV run, DB write or canonical commit.
- Records raw response, provider `finish_reason`, provider usage/cost
  (if reported), fully bound result or exact HOLD/error reason. Existing
  evidence file cannot be overwritten.
- On an otherwise successful single batch, reports **six other batches
  still pending**, never falsely declares full-scene success.

One-use workflow: `.github/workflows/sera-mara-s1-v010-case-one-shot.yml`.
The workflow only activates when a **separate isolated launch-grant
JSON commit** contains the pinned scope, exact previously reviewed code
SHA, allowed model, source hash, no output-cap flag and one request
count; the workflow refuses reruns. Historical v0.5 token-limited
launch records remain archived, not executable templates.

### Regression evidence

`tests/test_sentence_sweep_v010.py` and
`tests/test_mara_s1_sweep_pilot_v010.py` verify:

- 28/28 prose sentences partitioned into exactly seven context-bearing
  batches; no original analyst or Writer leaks;
- literal `bench`, `pencil`, `closed`, `wrote` missed by a synthetic
  model generate specific targeted probe items;
- exact text source evidence and multiple quote occurrences;
- output claiming train arrival from the archive is marked as
  epistemically unsafe and never authoritative;
- missing/duplicated source rows, forged quote, tampered source, duplicated
  batch, unknown enum, unfinished output and model HTTP error
  fail safely with no WorldStore event application;
- one-call pilot preflight, immutable evidence, actual provider cost fields,
  one-call counter and source-pinned recovery queue.

**CI preflight:** [run 38860386239](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38860386239)
— 276/276 Python tests PASS and independent Chromium E2E PASS; this is
not model-quality evidence or authenticated gold.

## Architectural boundary

An extracted **candidate** is not an approved event.

```
Frozen Spine + current accepted World State
  -> original Mara S1 prose (immutable)
  -> blind source-linked 4-sentence batches
  -> provider response
  -> Python quote binder + complete sentence ledger
  -> missing object/action cues + epistemic contradiction probes
  -> verified typed candidate / aspect and claim mapping (future)
  -> independent semantic adjudication and authority (future)
  -> validated world-state reducer and EventGraph commit (future)
```

Status remains `HOLD_MODEL_SEMANTICS_UNVERIFIED` even if every batch
returns valid JSON. A live one-batch pilot is **not** a complete Mara
independent extraction, semantic recall score, or S1 exit World State.

## Next gates

1. One source-pinned paid case-closure pilot; read actual provider error,
   usage/cost and grounded object/event proposal, **without an artificial
   output token ceiling**.
2. If model/schema compatibility is confirmed, collect all remaining
   batches with immutable evidence, strict source row count, and targeted
   probing for missed physical actions and objects.
3. Evaluate observed candidates and contextual identity (pocket watch case
   vs watch; bench/pencil physical presence; notebook writing).
4. Complete verified reducer mappings for `case_open`,
   `writable.entries`, and attributed claims; protect first scene
   state update behind a trusted authority gate.
5. Obtain independent human-adjudicated gold for *benchmark evaluation*
   (not for every production story), measure false-PASS, event/entity recall,
   and episode continuity.

The user requirement **never to impose model output token limits**
is explicitly retained in `AGENTS.md` and
`request_policy.py`.
