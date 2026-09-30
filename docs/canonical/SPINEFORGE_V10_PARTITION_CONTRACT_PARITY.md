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
