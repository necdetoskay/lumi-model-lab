# SpineForge v15 — Convergence Repair

v15 continues from the improved v14 product. It does not return to the original Architect output and does not call the Architect.

Source evidence:
`experiments/results/spineforge-v14/36755567557/result.json`

The v14 source already contains:
- a validated repaired Episode Spine;
- a typed aggressive re-audit;
- five remaining blocking defects grouped into four targeted repairs;
- ten audit dimensions already at score 4.

## Remaining scope

1. Remove unauthorized erased-road geometry. Reversal evidence may use only permitted map reference versus field-measurement discrepancy, plus directly observed stance/peg/needle behavior.
2. Stage Maren's arrival before her pressure at the pegs.
3. Make replicate success/partial/failure contingent on Leyra's in-scene choices rather than fixing the result.
4. Give each branch a distinct climax action, evidence state, closing image and Ilyan response basis.

## Topology

validated v14 repaired Spine + typed v14 REPAIR re-audit
→ Sonnet v15 Convergence Repair
→ deterministic route normalization
→ EpisodeSpine contract validation
→ ContextPack authority validation
→ Sonnet Aggressive Re-audit
→ ACCEPT: STOP / human review
→ REPAIR: STOP / separately authorized future revision

No Architect recall. No automatic repair loop. No Writer.

## Zero-cost qualification

Initial run:
`36756402415` — **SUCCESS**

- v15 prompt/runtime: 3 PASS
- v14 source/runtime regressions: 3 PASS
- paid model calls: 0
- v15 spend: $0


## Final frozen qualification

- runtime revision: `SPINEFORGE-CONVERGENCE-REPAIR-FROZEN-v15`
- runtime source commit: `9583bdd0d5eb4feff09b26d7a6ade118b394355e`
- frozen files: **27**
- source evidence: `experiments/results/spineforge-v14/36755567557/result.json`
- freeze run: `36757109275` — **SUCCESS**
- final frozen qualification run: `36757324305` — **SUCCESS**
- v15 convergence/runtime/stage/freeze tests: **9 PASS**
- inherited v14 repair regressions: **3 PASS**
- paid model calls before boundary: **0**
- v15 spend before boundary: **$0**

Current case/ledger status: `READY_FOR_ATTEMPT_1`.

Paid scope, if explicitly authorized:
`SPINEFORGE_V15_ATTEMPT_1_CONVERGENCE_REPAIR_THEN_REAUDIT`

The paid attempt is capped at two Sonnet calls:
1. convergence repair of the validated v14 repaired Spine using the typed v14 REPAIR re-audit;
2. aggressive re-audit only if the repaired Spine passes deterministic contract and ContextPack authority validation.

Architect recall is forbidden. Automatic repair loops are forbidden. Writer remains blocked. No paid trigger exists.
