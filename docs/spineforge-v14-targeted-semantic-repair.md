# SpineForge v14 — Targeted Semantic Repair

v14 does not regenerate the Architect product.

Source:
- v12 paid run `36752663853`
- validated normalized Episode Spine
- v13-normalized typed Auditor decision: `REPAIR`
- six blocking defects
- five targeted repair groups
- explicit preserve set

Pipeline:

`Frozen validated Spine + typed REPAIR Audit`
→ Sonnet Targeted Semantic Repair Editor
→ deterministic route normalization
→ EpisodeSpine contract validation
→ ContextPack authority validation
→ Sonnet Aggressive Re-audit
→ ACCEPT: STOP / human review
→ REPAIR: STOP / future explicit repair revision

No Architect recall. No automatic loop. No Writer.

Semantic repair stays on Sonnet for this qualification because the defects concern causality, reversal, branch execution, climax, payoff and roleplay—not mechanical schema cleanup. Mechanical normalization remains deterministic.


## Frozen qualification result

- initial v14 zero-cost run: `36753556631` — **SUCCESS**
- full paid-boundary zero-cost run: `36754005451` — **SUCCESS**
- final freeze run: `36754208083` — **SUCCESS**
- runtime revision: `SPINEFORGE-TARGETED-REPAIR-FROZEN-v14`
- runtime source commit: `6fdb7313f9b006ad44a556294189e719f40cbead`
- frozen runtime/source files: **27**
- final frozen zero-cost run: `36754365949` — **SUCCESS**
- v14 repair/runtime/stage/freeze tests: **10 PASS**
- v13 audit-normalization regressions: **6 PASS**
- v14 paid model calls before boundary: **0**
- v14 spend before paid boundary: **$0**

Case status: `READY_FOR_ATTEMPT_1`.

Paid scope:
`SPINEFORGE_V14_ATTEMPT_1_TARGETED_REPAIR_THEN_REAUDIT`

The paid attempt is capped at two Sonnet calls:
1. targeted semantic repair of the already validated v12 Spine using the typed v13 REPAIR audit;
2. aggressive re-audit only if the repaired Spine passes deterministic contract and ContextPack authority validation.

Architect recall is forbidden. Automatic repair loops are forbidden. Writer remains blocked.

No `experiments/triggers/spineforge-v14.json` exists. Explicit authorization is required before paid trigger creation.
