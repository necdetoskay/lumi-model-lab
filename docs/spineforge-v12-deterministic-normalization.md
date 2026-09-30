# SpineForge v12 — Deterministic Mechanical Normalization

## Goal

Preserve the v11 single-owner Sonnet story architecture while moving mechanically derivable fields out of model ownership.

## Topology

SpineContextPack.v1
-> Sonnet 5.5 Story Spine Architect
-> deterministic mechanical normalization
-> EpisodeSpineV3 validation
-> deterministic ContextPack authority validation
-> Sonnet 5.5 Aggressive Red-Team Auditor
-> ACCEPT: STOP / human review
-> REPAIR: STOP / separately authorized future repair revision

Writer remains blocked.

## Normalization boundary

v12 may normalize exactly one field:

`logistics_plan.location_sequence`

Its sole source of truth is the ordered transition sequence of `beat.location_ref`.

The normalizer:
- may collapse consecutive duplicate locations;
- may replace the model's route projection with the route already encoded by beats;
- must be idempotent;
- must not alter beats, reversal, decision, climax, payoff, saga, outcomes, writer rules, canon, enums, evidence certainty, or any other semantic field;
- must not make an invalid semantic/canon product pass.

This encodes the rule:

**The model owns story decisions. The application owns deterministic projections.**

## Evidence basis

v11 paid Attempt 1, run `36746646152`, produced a complete roleplay-first Spine in one Sonnet call but omitted the final Greyfen return from the duplicated logistics route projection.

Exact v11 Architect accounting:
- input: 16,230
- output: 6,529
- total: 22,759 tokens
- cost: $0.09775
- latency: 51.934 s

Zero-cost replay run `36747258876` proved that deriving the route from beat transitions made the same raw product pass the full EpisodeSpine contract and ContextPack authority checks with no other hidden contract/canon defect.

## v12 zero-cost qualification

Run `36749340680`:
- v12 normalizer/runtime: 8 PASS
- inherited roleplay/audit regression: 7 PASS
- Episode Spine regression: 15 PASS
- paid model calls: 0
- v12 spend: $0

The runtime test feeds the exact v11 paid Architect output into v12 and proves that normalization allows it to reach the Auditor. A separate test injects a semantic certainty defect and proves v12 still stops before the Auditor.

## Paid policy

Before any paid v12 attempt:
- runtime and prompts must be SHA-256 frozen;
- paid authorization remains false;
- no trigger may exist;
- Attempt 1 may call at most Sonnet Architect and, only after deterministic validation, Sonnet Auditor;
- no automatic retry;
- no automatic semantic repair;
- no Writer.


## Frozen qualification result

- runtime revision: `SPINEFORGE-DETERMINISTIC-NORMALIZATION-FROZEN-v12`
- runtime source commit: `55ced1fd4d4a28738e1e88fe49e1bd236174c91f`
- frozen runtime files: **23**
- freeze run: `36749951972` — **SUCCESS**
- final frozen zero-cost run: `36750136420` — **SUCCESS**
- v12 normalizer/runtime/stage/freeze: **14 PASS**
- inherited roleplay/audit regression: **7 PASS**
- Episode Spine regression: **15 PASS**
- paid model calls: **0**
- v12 spend before paid boundary: **$0**

Case status: `READY_FOR_ATTEMPT_1`.

Next paid scope:
`SPINEFORGE_V12_ATTEMPT_1_SONNET_ARCHITECT_NORMALIZE_VALIDATE_THEN_SONNET_AUDIT_IF_ELIGIBLE`

No `experiments/triggers/spineforge-v12.json` exists. A separate explicit authorization is required before paid trigger creation.
