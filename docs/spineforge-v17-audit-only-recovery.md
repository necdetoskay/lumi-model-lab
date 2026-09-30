# SpineForge v17 — Audit-Only Recovery

v17 reused the validated v16 repaired Spine and made exactly one compact Sonnet audit call.

## Frozen runtime

- revision: `SPINEFORGE-AUDIT-ONLY-RECOVERY-FROZEN-v17`
- source commit: `3e9daf765b172a73fff9b345398edc04c56a82c6`
- frozen files: **25**
- source evidence: `experiments/results/spineforge-v16/36760550050/result.json`

## Paid Attempt 1

Run `36764631131`

Exact accounting:
- input: **22,460**
- output: **880**
- total: **23,340 tokens**
- cost: **$0.05372**
- model latency: **7.816 s**
- wall latency: **7.864 s**
- model calls: **1**

No Architect, Repair or Writer call executed.

The provider returned valid JSON but not the required audit shape. Raw semantic decision was `REPAIR`, yet only **10 of 18** protected dimensions were present:
- 8 inside `dimensions`;
- `ESCALATION` and `REVERSAL_QUALITY` were incorrectly emitted as top-level keys.

Missing:
`AGENCY`, `BRANCH_EXECUTABILITY`, `CLIMAX_PAYOFF`, `LOCAL_SATISFACTION`, `SAGA_ALIGNMENT`, `AUTHORITY_SAFETY`, `WRITER_EXECUTABILITY`, `FRESHNESS`.

`decision_reason` was also absent. Therefore the local typed audit contract correctly rejected the product.

This output is not mechanically repairable into a complete audit because eight dimensions and final audit fields were never generated. It must not authorize ACCEPT and should not drive semantic repair as if it were a complete audit.

The consumed trigger was disarmed. Guard run `36764798220` stopped before inference and persisted `RESULT_MISSING`.

## Next architecture

The validated v16 Spine remains unchanged.

The next revision should remain audit-only but replace free `json_object` transport with a provider-level **small strict JSON Schema** dedicated to the audit product. The repository already contains a proven Sonnet strict-schema transport from SpineForge v7/v9 with a preflight schema-size budget.

Goal:
validated v16 Spine
→ one strict Sonnet audit
→ complete typed 18/18 ACCEPT/REPAIR
→ STOP.

No semantic repair should be repeated until a complete audit exists.
