# SpineForge v10.1 — Beat-Set Invariant Parity

Status: ZERO-COST QUALIFICATION

## Why this successor exists

v10 Paid Attempt 1 completed Aion, Sonnet Frame, Sonnet Beats and Sonnet Resolution, then final EpisodeSpine assembly rejected the product because the beat set omitted the required REVERSAL phase.

Every beat was individually valid EpisodeBeatV2. The defect was set-level parity: StructuralBeatsV10 did not enforce the final EpisodeSpine required-phase invariant.

The same run exposed a retry-classification defect: all assembly failures defaulted to STRUCTURAL_FRAME although the missing phase was owned by STRUCTURAL_BEATS.

Paid v10 run: `36810208041`
- 4 calls
- 91,712 tokens
- $0.2388673
- 225.18 s summed model latency
- Luna not called
- Writer not called

## v10.1 changes

Generation topology, models, prompts, ContextPack, strict transport and Luna gate stay unchanged.

Deterministic changes only:

1. Structural Beats requires the final EpisodeSpine phase set:
   `HOOK, COMPLICATION, REVERSAL, DECISION, CLIMAX, PAYOFF`.
2. Missing required phases are rejected at the Beats boundary before Resolution is called.
3. Final assembly failures are classified to the earliest owning partition.
4. If ownership cannot be classified, the runtime stops instead of guessing a retry target.
5. STRUCTURAL_BEATS retry feedback preserves Blueprint + Frame and discards invalid Beats/Resolution.
6. Writer remains blocked before explicit human approval.

## Initial zero-cost proof

Run `36811432734`:
- exact v10 paid failure replay + owner classification: **6 PASS**
- inherited v10 runtime/transport: **20 PASS**
- historical v1→v9 regression: **94 PASS**
- 4 historical snapshots deselected by design
- paid calls: **0**

Freeze is required before any paid v10.1 attempt.
