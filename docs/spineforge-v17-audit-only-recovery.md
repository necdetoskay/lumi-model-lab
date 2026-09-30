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
