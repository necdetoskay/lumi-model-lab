# Luna v3 World-Lore Adaptive Wave — Provider Limit Block — 2026-09-24

Status: **QUALIFICATION NOT EXECUTED — PROVIDER ACCESS BLOCK**

Workflow run: `35997537807`  
Generator: `openai/gpt-5.6-luna`  
Generation protocol: `english-story-production.v3`  
Wave: `age-relative-standard-v3-all-families`

## Purpose

This was the first paid adaptive batch after expanding the STANDARD
qualification fixture set from three narrative families to all ten canonical
families.

The deterministic planner selected `world_lore_discovery` across all eight age
tiers.

## What happened

The prepare job completed successfully and produced the expected eight-case
matrix.

Four cases started before the workflow was cancelled:

- EARLY_CHILD
- CHILD
- MIDDLE_CHILD
- TEEN

All four terminated before story generation with the same provider response:

- OpenRouter HTTP 403
- key monthly limit exceeded

The remaining four cases were cancelled before qualification:

- YOUNG_ADULT
- ADULT
- MATURE_ADULT
- SENIOR

## Capability interpretation

This run provides **no model-quality conclusion** for
`world_lore_discovery`.

The four started cases have:

- accepted: false;
- word count: 0;
- no final semantic-judge result;
- no continuity result;
- no story-generation evidence.

They are classified as `PROVIDER_ACCESS_FAILURE`, not
`CAPABILITY_FAILURE`.

Per the canonical Capability Cube rule, these records remain immutable
operational evidence but are excluded from pass-rate and coverage denominators.

## Isolation verification

After promoting the four evidence packs and rebuilding reports:

- total Cube evidence runs: 103;
- capability-eligible runs: 99;
- excluded non-capability runs: 4;
- excluded outcome: `PROVIDER_ACCESS_FAILURE × 4`;
- active v3 STANDARD observed cells: 24;
- active v3 STANDARD UNKNOWN cells: 56.

Therefore the provider incident does not make any world-lore cell appear tested
or failed.

## Rerun rule

Do not change prompts, thresholds, model profile, production policy, or fixture
content in response to this incident.

The same adaptive batch should be rerun only after OpenRouter access is restored
or the key's monthly limit is raised/reset.

A successful rerun must produce fresh run ids and normal immutable evidence
packs. The 403 evidence remains as historical operational evidence.

## Permanent workflow mitigation

The incident motivated a provider-access preflight in the paid capability-wave
workflow. After matrix preparation and before any story case starts, the
workflow calls OpenRouter's current-key endpoint and fails closed when the key
cannot be inspected or its configured `limit_remaining` is exhausted.

The preflight makes no model request and creates no capability evidence. It
exists only to prevent repeated provider-access failures from spawning
redundant case jobs while keeping provider incidents separate from model
quality.
