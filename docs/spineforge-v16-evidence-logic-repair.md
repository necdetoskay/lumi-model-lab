# SpineForge v16 — Evidence Logic Repair

v16 continues from the validated v15 repaired Spine.

Source evidence:
`experiments/results/spineforge-v15/36757835721/result.json`

The v15 re-audit returned semantic decision REPAIR but only 17 of 18 protected dimensions. `FRESHNESS` was omitted, so the audit was not accepted as a complete typed audit.

v16 therefore applies a one-way recovery rule:

**An incomplete audit may carry REPAIR blockers and targets forward, but can never authorize ACCEPT.**

## Remaining semantic scope

1. Remove under-specified/invented evidence mechanics. No invented legal-map bearing system, erased-road geometry or residue behavior.
2. Make replicate success/failure depend on a simple repeat-under-comparable-conditions observation, not arbitrary peg order.
3. Give at least one middle measurement beat a concrete external complication that changes Leyra's action.
4. Require the final re-audit to cover all 18 protected dimensions exactly once.

## Topology

validated v15 repaired Spine + partial REPAIR-only audit
→ Sonnet v16 Evidence Logic Repair
→ deterministic route normalization
→ EpisodeSpine validation
→ ContextPack authority validation
→ Sonnet Complete Aggressive Re-audit
→ complete ACCEPT: STOP / human review
→ REPAIR or incomplete audit: STOP

No Architect recall. No automatic repair loop. No Writer.

## Qualification

- initial zero-cost run `36758868808` — **SUCCESS**
- final frozen qualification `36759774816` — **SUCCESS**
- v16 tests: **13 PASS**
- inherited v15 regressions: **3 PASS**
- runtime revision: `SPINEFORGE-EVIDENCE-LOGIC-REPAIR-FROZEN-v16`
- frozen files: **28**

## Paid Attempt 1 result

Run `36760550050`

The evidence-logic repair completed successfully. The repaired Episode Spine passed the local EpisodeSpine contract and ContextPack authority checks with no deterministic route rewrite.

Recorded repair accounting:
- input: **26,936**
- output: **9,477**
- total: **36,413 tokens**
- cost: **$0.148642**
- model latency: **51.442 s**

The mandatory complete re-audit was then invoked, but Sonnet exhausted the configured `4,500` output-token ceiling before returning complete JSON:

`STRUCTURED_JSON_RESPONSE_TRUNCATED`

No re-audit decision exists and human review was not authorized.

### Accounting defect

The truncated provider response contained usage/cost in `StructuredJsonCallError.trace`, but the v16 runtime caught the exception generically and did not checkpoint that trace. Therefore:

- inference requests observed: **2**
- ledgered calls with exact usage: **1**
- known recorded spend: **$0.148642**
- exact total v16 spend: **unknown**
- exact total v16 tokens: **unknown**

No estimate is substituted for the missing provider accounting.

This is a runtime evidence defect and must be fixed before another paid attempt.

### Next architectural decision

The v16 repaired Spine should be preserved. It already passed contract/canon validation. A future revision should be **audit-only recovery**, not another semantic repair:
- reuse the v16 repaired Spine;
- use one concise complete 18-dimension Auditor call;
- allow more audit output headroom;
- checkpoint usage/cost from structured-call exceptions before returning any failure;
- STOP on ACCEPT/REPAIR; no Writer.

Attempt 1 is consumed. The trigger was disarmed. Guard run `36761032727` stopped before inference and produced `RESULT_MISSING`.
