# SpineForge v10 — Partition Contract Parity

Status: PRE-FREEZE ZERO-COST GREEN

## Why v10 exists

v9 fixed the path-insensitive schema sanitizer defect and proved that the partitioned Sonnet chain can complete Frame, Beats, and Resolution under provider strict transport.

Paid v9 Attempt 1 then failed only after those three partitions had individually validated. The exact assembly error was:

- `ReversalEvidenceV2.certainty` accepts only `OBSERVED | INFERRED | HYPOTHESIS`.
- `StructuralResolutionV1` had declared the same field as unrestricted `str`.
- Sonnet therefore returned explanatory prose that was valid for the partition contract but invalid for the final EpisodeSpine contract.

This is a contract-boundary defect, not a creative prompt defect.

## v10 change

v10 preserves the v9 models, prompts, ContextPack, partition topology, strict transport, evidence durability, Luna gate, and human-review boundary.

Only the partition local contracts are tightened to match the semantic requirements of the final EpisodeSpine assembly:

- Frame `episode_role` is constrained to the final EpisodeSpine literal set.
- Resolution `certainty` is constrained to `OBSERVED | INFERRED | HYPOTHESIS`.
- Resolution persistent outcome `type` is constrained to the final EpisodeSpine literal set.
- Resolution decision branch `key` uses the same canonical key pattern as EpisodeSpine.
- Existing Structural Beats already validate directly as `EpisodeBeatV2`.

Wire JSON shapes and schema IDs remain unchanged, so existing product/human-approval compatibility is preserved. At the product boundary, v10 parity models are serialized to JSON and revalidated by the existing frozen Product v7 contract.

## v9 evidence

Paid run: `36738179384`

Result:
- status: `structural_assembly_contract_rejected`
- completed paid calls: **4**
- Aion Creative Architect: completed
- Sonnet Structural Frame: completed
- Sonnet Structural Beats: completed
- Sonnet Structural Resolution: completed
- Luna Product Gate: not called
- Writer: not called
- total tokens: **90,770**
- exact cost: **$0.2296431**
- summed model latency: **244.623 s**
- durable repo evidence: PASS
- GitHub artifact upload: failed from quota, non-blocking by design

## v10 pre-freeze proof

Run: `36742453613`

Result:
- v10 parity/runtime/transport/stage: **20 PASS**
- v9 regression: **15 PASS**
- historical v1→v9 regression: **94 PASS**
- historical trigger snapshots deselected by design: **4**
- paid v10 calls: **0**
- v10 spend: **$0**

Freeze and a separate explicit paid authorization are still required before v10 Attempt 1.

## Frozen zero-cost qualification

Runtime ID: `spineforge.contextpack.v10`  
Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v10`  
Runtime source: `dfc1e71990b640647a596524a4459db14eb280ed`  
Frozen dependencies: **30**

Final post-freeze run: `36766535995`

Result:
- v10 parity/runtime/stage/frozen: **24/24 PASS**
- v9 regression: **15/15 PASS**
- v1→v9 historical regression: **94 PASS**
- 4 historical trigger snapshots deselected by design
- frozen runtime files changed after source commit: **0/30**
- paid v10 calls: **0**
- v10 spend: **$0**

Current state: `READY_FOR_ATTEMPT_1`.

No v10 paid trigger exists.

Next paid scope:

`SPINEFORGE_V10_ATTEMPT_1_AION_THEN_PARITY_STRICT_SONNET_THEN_STRICT_LUNA_IF_ELIGIBLE`

A separate explicit authorization is required before trigger creation.

## Paid Attempt 1 — terminal v10 result

Run: `36810208041`

Runtime result: `structural_assembly_contract_rejected`.

Execution:
- Aion Creative Blueprint: completed
- Sonnet Structural Frame: completed
- Sonnet Structural Beats: completed
- Sonnet Structural Resolution: completed
- deterministic EpisodeSpine assembly: rejected
- Luna Product Gate: not called
- Writer: not called

Exact failure:

`Episode Spine missing required phases: REVERSAL`

The returned beat phases were:

`HOOK → ORIENT → COMPLICATION → INVESTIGATION → ESCALATION → DECISION → CLIMAX → PAYOFF → TAG`

Every beat individually validated as `EpisodeBeatV2`, but the partition contract did not enforce the final EpisodeSpine beat-set invariant requiring:

`HOOK, COMPLICATION, REVERSAL, DECISION, CLIMAX, PAYOFF`

Exact accounting:
- API calls: **4**
- input tokens: **74,824**
- output tokens: **16,888**
- reasoning tokens: **4,895**
- total tokens: **91,712**
- cost: **$0.2388673**
- summed model latency: **225.18 s**

By stage:
- Aion: 15,922 tokens, **$0.0167993**, 151.312 s
- Sonnet Frame: 21,605 tokens, **$0.063546**, 23.776 s
- Sonnet Beats: 24,320 tokens, **$0.075784**, 23.392 s
- Sonnet Resolution: 29,865 tokens, **$0.082738**, 26.700 s

A second generic defect was exposed: the assembly failure generated retry ownership `STRUCTURAL_FRAME`, but this failure is owned by `STRUCTURAL_BEATS`. Because Beats should have rejected the missing phase before Resolution, the Resolution call was avoidable.

v10 Attempt 2 is forbidden.

A successor must:
1. enforce final beat-set required-phase invariants at the Structural Beats boundary;
2. classify cross-partition/final-assembly failures to the earliest owning partition;
3. preserve already-valid upstream sections and retry only the owning partition when future paid revision feedback is authorized;
4. prove these behaviors zero-cost before paid inference.

Terminal status:

`QUALIFICATION_FAILED_BEAT_SET_FINAL_INVARIANT_PARITY_GAP`

