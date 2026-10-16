# SERA v0.43 — Two real providers, source-trace reconciliation, zero new calls

**16 October 2026 — experimental / shadow only**. User goal: make each meaningful sentence/object/action traceable in source-order without confusing static state, observation, spoken claims or model hypotheses with accepted world transitions.

## Provenance, not fabricated benchmarks

The run reopens and SHA-256-validates two already-paid OpenRouter experiments against the SAME immutable Mara S1 prose SHA `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`:

- [Bench batch: Gemini 3.7 Flash + Claude Haiku 4.5](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38936451931) ($0.01637775 provider-reported historical charge).
- [Pencil batch: same two independent models](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38938438488) ($0.01397425 historical charge).
- [v0.43 comparison CI](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38944797185) successful; **688 Python tests PASS**; evidence artifact `sera-v043-real-mara-dual-evidence-38944797185` (ID `12064686771`).

The v0.43 run made **0** provider calls and incurred **$0 incremental cost**. The previous two pilot charges ($0.030352 total) are historical; not newly spent here.

## Implementation

`scene_trace_dual_real_v043.py` uses SERA's existing real v0.10 `bind_batch`, real v0.11 full JSON fence decoder, v0.41.1 approved nonsemantic metadata repair, and the v0.41.2 per-sentence quarantine. It performs **separate** source binding for each model. It NEVER permits one model's report to validate the other's physical claims, never registers new entities, never assigns a speaker or movement agent, never invents an event second, never calculates a model-claimed state delta.

For every one of the **28** original source sentences, it exposes two per-model statuses: `SOURCE_BOUND`, `QUARANTINED` or `NOT_EXTRACTED`. Candidate event type/epistemic/effect/entity-reference tuples are compared **only when both rows are source-bound**. Quarantined rows are NOT treated as missing events or zero-event valid rows.

## Actual observed results

| Indicator | Gemini 3.7 Flash | Claude Haiku 4.5 |
| --- | ---: | ---: |
| Real sampled sentence rows across bench+pencil | 8 | 8 |
| Source-bound model rows | 8 | 6 |
| Quarantined invalid-source rows | 0 | 2 |
| Exact story timestamps trusted | 0 | 0 |
| Authoritative world transitions | 0 | 0 |

**Six** source-bound sentence-level event-signature disagreements were found. These are candidate differences, **not six proven model errors**.

Two specific **advisory** risk flags were recorded against model events after confirming exact source bindings:
1. Haiku `s004`: `STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK` — the prose already describes the watch as open, but the model proposes `CHANGE_STATE` based on that adjective. The candidate needs independent state-transition authority; none is granted.
2. Gemini `s022`: `PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN` — the source says Vane *watched* the pencil move. The model proposes a physical `MOVE` without source support to identify who caused it. Observation and physical mutation are separated.

These two fault **categories were already suspected by earlier v0.40.1/v0.41.1 checks**. The new contribution is a single source-bound, per-sentence and per-model comparison with isolated quarantined responses and explicit disagreements. Do not falsely count the two known warning types as two newly discovered actual defects.

## Decision

**SceneTrace remains SHADOW ONLY.** Cross-model agreement/disagreement does not constitute semantic proof; a deterministic heuristic does not show that independent recall, precision, hallucination rate, cost or latency improved. Only **8 of 28** source sentences were in the two sampled model batches; the other 20 remain *unassessed by this real pilot*. Source-line visibility is complete, independent extractor assessment is not.

Next experiment should focus on **independent semantic acceptance**, preferably a predeclared corpus with known event/static/claim/unknown role distinctions and source-anchored reversible checks; compare the same model on normal text vs structured relative-time/beat metadata with a separate, explicitly authorized one-use paid experiment only when needed. Avoid putting a model-produced sidecar inside an independent extractor's input. No mandatory manual fixing in production.

References: [Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306), [SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307), [Object State #303](https://github.com/necdetoskay/lumi-model-lab/issues/303), [EventGraph #305](https://github.com/necdetoskay/lumi-model-lab/issues/305), [Temporal #304](https://github.com/necdetoskay/lumi-model-lab/issues/304).

**Safety:** No Project_LUMI DB, no SERA SQLite writes, no main merge, no output-token ceilings. Original real Mara S1 HOLD persists.
