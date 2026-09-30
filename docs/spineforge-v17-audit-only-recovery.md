# SpineForge v17 — Audit-Only Recovery

v17 does not repair the Spine again.

Source:
`experiments/results/spineforge-v16/36760550050/result.json`

The v16 repaired Spine already passed EpisodeSpine contract and ContextPack authority validation. Only its final complete re-audit failed because the 4,500-token output cap truncated the structured JSON.

## Architecture

validated v16 repaired Spine
→ one Sonnet compact complete audit
→ typed 18/18 audit validation
→ ACCEPT: STOP / human review
→ REPAIR: STOP / separately authorized future repair revision

No Architect. No Repair. No Writer.

## Audit transport

- Sonnet 5.5
- one call only
- compact audit prompt
- exactly one short evidence item per dimension
- all 18 protected dimensions exactly once
- FRESHNESS mandatory
- output ceiling: 8,000 tokens

The larger ceiling is headroom, not a target.

## Accounting repair

If structured output truncates or otherwise raises `StructuredJsonCallError`, v17 records provider usage/cost from the exception trace before returning failure. A paid inference can no longer disappear from the model-call ledger.

## Initial zero-cost qualification

Run `36761588959` — **SUCCESS**

- v17 audit-only/accounting tests: **4 PASS**
- v16 source regressions: **5 PASS**
- paid calls: **0**
- v17 spend: **$0**


## Final frozen qualification

- runtime revision: `SPINEFORGE-AUDIT-ONLY-RECOVERY-FROZEN-v17`
- runtime source commit: `3e9daf765b172a73fff9b345398edc04c56a82c6`
- frozen files: **25**
- source evidence: `experiments/results/spineforge-v16/36760550050/result.json`
- freeze run: `36762258634` — **SUCCESS**
- final frozen qualification: `36762453605` — **SUCCESS**
- v17 audit-only/runtime/stage/freeze/accounting tests: **10 PASS**
- inherited v16 regressions: **5 PASS**
- paid model calls before boundary: **0**
- v17 spend before boundary: **$0**

Current case/ledger: `READY_FOR_ATTEMPT_1`.

Next scope, only after separate explicit authorization:
`SPINEFORGE_V17_ATTEMPT_1_AUDIT_ONLY_COMPLETE_18_DIMENSIONS`

The paid attempt permits exactly one Sonnet call:
1. compact complete 18-dimension audit of the already validated v16 repaired Spine.

No Architect call. No Repair call. No Writer.

The Auditor receives no previous audit payload, only the authoritative ContextPack and validated Spine. The audit must return all 18 dimensions exactly once, including `FRESHNESS`. The 8,000-token ceiling is safety headroom, not a target.

If structured output fails or truncates, provider usage/cost from the structured-call exception trace is checkpointed before failure is returned, preventing another accounting gap.
