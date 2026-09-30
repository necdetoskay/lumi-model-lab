# SpineForge v5 — Creative Blueprint Boundary

Status: FROZEN QUALIFICATION CANDIDATE

Parent epic: #253
Implementation issue: #255

## Why v5 exists

SpineForge v4 ended as QUALIFICATION_FAILED_MAX_ATTEMPTS before Sonnet was ever reached.

Paid v4 sequence:
1. Attempt 1 repaired/normalized generic runtime details but Aion emitted movement_constraints as scalar instead of list.
2. Attempt 2 fixed that exact problem, then omitted required COMPLICATION.
3. Attempt 3 fixed COMPLICATION and materially integrated it, then omitted beat.new_information.

The creative plan remained coherent and revision feedback repaired the immediately preceding defect each time. The failure pattern is therefore boundary-level: Aion was required to perform creative invention and compile the entire rigid EpisodeSpine contract before Sonnet could participate.

## v5 architecture

SpineContextPack.v1
→ Aion Creative Architect
→ SpineCreativeBlueprintV2
→ deterministic blueprint authority validation
→ Sonnet Structural Compiler / Hardener
→ SpineStructuralAssemblyV1 containing strict EpisodeSpineV3
→ deterministic EpisodeSpine + ContextPack validation
→ Luna Product Gate
→ STOP / human review

Writer is never callable inside SpineForge.

## Creative Blueprint boundary

Aion owns the creative product:
- dramatic engine
- protagonist desire and pressure
- wonder / intrigue
- roleplay opportunities
- scene promises
- emotional turns
- world-specific mechanics
- freshness
- episode intent
- causal creative beat intentions
- decision pressure
- climax idea
- local payoff
- forward question

Aion does not own:
- strict phase completeness
- logistics projection
- full per-beat structural metadata
- typed persistence contract
- final saga progression structure
- final writer-rule structure

## Structural Compiler boundary

Sonnet receives the same ContextPack and the validated creative blueprint.

Sonnet owns:
- converting creative beats into 8–12 strict EpisodeSpine beats
- assigning required phases
- completing every required beat field
- causal/logistics/evidence integrity
- executable branches
- strict EpisodeSpineV3 conformance

Sonnet must preserve Aion's creative signature. Material deviations must be explicit.

## Non-negotiable rules

- same context_pack_id / context_fingerprint across Aion, Sonnet and Luna
- hidden Saga truth remains absent
- application owns model identity
- stale context invalidates downstream artifacts
- no case-specific recovery
- no paid qualification before zero-cost tests + freeze
- human approval required before Writer


## Frozen qualification candidate

Runtime ID: `spineforge.contextpack.v5`  
Runtime revision: `SPINEFORGE-CONTEXTPACK-FROZEN-v5`  
Freeze profile commit: `fec5e3b90088634b327ee0dd5a7fa35ca1ed89ad`

Frozen runtime dependencies: **24 SHA-256 locked files**.

Pre-freeze zero-cost proof:
- v5 contract/runtime tests: 9/9 PASS
- v1–v4 active regression: 51 PASS, 1 historical snapshot deselected

Paid qualification has not started.

Next paid boundary:

`SPINEFORGE_V5_ATTEMPT_1_AION_BLUEPRINT_THEN_SONNET_STRUCTURAL_THEN_LUNA_IF_ELIGIBLE`

Writer remains blocked until explicit human approval.
