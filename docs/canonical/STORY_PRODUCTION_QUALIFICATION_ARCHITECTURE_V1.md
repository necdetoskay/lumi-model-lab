# Story Production Qualification Architecture v1

Status: **Canonical**
Date: 2026-09-24
AEGIS risk: **L2**
Scope: LUMI Model Lab governed story generation, qualification, evidence and model capability profiling

## 1. Purpose

This document is the top-level canonical architecture for how LUMI Model Lab:

- generates a complete story;
- validates scene and whole-story continuity;
- performs semantic judging;
- repairs bounded defects without discarding an otherwise valid story;
- records immutable qualification evidence;
- builds age × narrative-family capability profiles;
- schedules the next paid qualification work deterministically;
- separates provider/operational incidents from model capability;
- controls changes so benchmark tuning does not silently become production policy.

Lower-level canonical documents remain authoritative for their own domains. This document defines how they fit together.

## 2. Canonical component map

The current governed stack is:

- generator role: `openai/gpt-5.6-luna`;
- generation protocol: `english-story-production.v3`;
- continuity evaluator role: `continuity_evaluator`;
- current implementation: `typesafe/jev-1.13`;
- semantic judge role: `semantic_judge`;
- current implementation: `anthropic/claude-haiku-4.5`;
- evaluation protocol: `english-story-evaluation.v1`;
- capability schema: `model-capability-cube.v2`;
- adaptive scheduler: `CAPABILITY_COVERAGE_PLANNER_V1`;
- provider boundary: OpenRouter with fail-closed provider preflight;
- CI execution: self-hosted GitHub Actions only.

The current implementation models are evidence-bound implementations, not architecture names. JEV or Haiku may be replaced later, but that creates a new evaluation-stack identity and requires fresh qualification.

## 3. Authority hierarchy

### 3.1 Shared story correctness authority

The shared pipeline owns:

- StoryContract semantics;
- six-scene SceneGraph semantics;
- deterministic structure/state validation;
- scene and whole-story word-budget rules;
- repetition gate;
- continuity questions and thresholds;
- final semantic-judge rubric and acceptance gate;
- repair-count limits;
- failure classification.

These rules must not vary by generator model merely to make a weak model pass.

### 3.2 Model runtime authority

`MODEL_RUNTIME_PROFILE_REGISTRY_V2` owns model/provider-specific facts and LUMI request policy:

- provider slug and routing;
- structured output support;
- reasoning support and effort;
- max-token behavior;
- temperature/seed behavior;
- request-class policy.

If behavior changes because the model changes, it belongs in the model profile. If every model requires the rule for story correctness, it belongs in the shared pipeline.

### 3.3 Capability evidence authority

`MODEL_CAPABILITY_CUBE_V2` owns the meaning of model capability.

Capability is not a single global score. The canonical STANDARD cell is:

`Model × NarrativeAgeTier × ReadingMode × NarrativeFamily × RelativeLengthClass`

Every cohort is additionally isolated by runtime-profile, production-policy, generation-protocol and evaluation-stack fingerprints.

## 4. Canonical story-production flow

The governed English story flow is:

1. StorySpec is loaded with exact age, reading mode, narrative family and target length.
2. A StoryContract and six-scene SceneGraph are planned.
3. The plan is checked deterministically and by the continuity/evaluation stack.
4. Plan repair is bounded; a structurally bad plan is not allowed to leak into prose generation.
5. Scene 1..6 are generated sequentially.
6. Every scene is checked for schema/state correctness and v3 local word-budget bounds.
7. The continuity evaluator checks prior-state compatibility, scene purpose, unexplained dependencies, contradictions, goal preservation, future leakage and handoff validity.
8. A scene with a bounded local problem receives targeted repair rather than forcing full-story regeneration.
9. Accepted state deltas form the ContinuityLedger.
10. The six accepted scenes are assembled into the English master story.
11. Whole-story deterministic gates check total length and repetition.
12. Whole-story continuity evaluation checks causal chain, goal continuity, clue/solution progression, contradictions, repeated events and ending consistency.
13. The semantic judge evaluates instruction following, coherence, character consistency, age appropriateness, creativity, style, continuity and ending quality.
14. When the final judge identifies bounded repair targets and no critical failure exists, only the necessary scene prose is repaired while canonical state is held immutable.
15. Final acceptance requires all hard deterministic and semantic gates to pass.
16. Result, story, spec and fingerprints are packed into immutable qualification evidence.

The architecture therefore does not depend on the generator producing a perfect one-shot story. Reliability comes from bounded generation + validation + repair + final acceptance.

## 5. Active generation protocol: v3

`ENGLISH_FIRST_STORY_PIPELINE_V3` is the active shared protocol.

v1 used a symmetric ±20% local scene length gate. Historical evidence showed most length friction was overshoot.

v2 relaxed both lower and upper sides. Although its compact regression stories passed, TEEN × puzzle showed materially worse retry/repair burden. v2 was therefore not promoted.

v3 preserves the v1 80% lower bound and relaxes only the upper side:

- local minimum: `round(target × 0.80)`;
- local maximum: `target + max(round(target × 0.25), 20)`;
- whole-story hard length authority remains 75%–125% of configured target.

The lesson is canonical: a passing final story is not enough to promote a protocol change; retry/repair burden and failure signatures are part of qualification.

## 6. STANDARD capability space

The canonical STANDARD space is:

`8 NarrativeAgeTiers × 10 NarrativeFamilies = 80 cells`

Age tiers and exact benchmark ages:

- EARLY_CHILD: age 4, READ_ALOUD, 500 words;
- CHILD: age 7, EARLY_READER, 1,500 words;
- MIDDLE_CHILD: age 10, INDEPENDENT_READER, 2,800 words;
- TEEN: age 15, INDEPENDENT_READER, 3,800 words;
- YOUNG_ADULT: age 21, INDEPENDENT_READER, 4,200 words;
- ADULT: age 32, INDEPENDENT_READER, 4,200 words;
- MATURE_ADULT: age 50, INDEPENDENT_READER, 4,200 words;
- SENIOR: age 70, INDEPENDENT_READER, 4,200 words.

Narrative families:

1. exploration_mystery
2. friendship_social_problem
3. puzzle_problem_solving
4. nature_environment
5. scientific_curiosity
6. adventure_journey
7. emotional_development
8. cooperation_teamwork
9. everyday_fantastical_discovery
10. world_lore_discovery

Untested cells are UNKNOWN. They are never inferred to be good or bad.

## 7. Evidence density versus quality

Coverage states are evidence-density labels:

- 1 run: THIN;
- 2–4 runs: PROVISIONAL;
- 5+ runs: ESTABLISHED.

These are not quality grades.

A THIN cell may have a perfect pass rate but still be uncertain. A PROVISIONAL cell may contain a repaired anomaly and still require diagnostic work.

The system must keep the following separate:

- acceptance quality;
- retry/repair burden;
- latency;
- cost;
- evidence density;
- fixture diversity;
- provider reliability.

## 8. Adaptive qualification planner

Paid qualification is not a blind Cartesian sweep after the first sparse coverage pass.

The planner:

1. fills UNKNOWN before THIN, THIN before PROVISIONAL;
2. protects age balance;
3. uses deterministic tie-breaking;
4. reserves at most one sentinel-repeat lane for suspicious current-protocol cells;
5. requires a second frozen fixture after repeated anomaly on one fixture;
6. only marks a targeted intervention candidate when the anomaly generalizes across distinct fixture fingerprints;
7. never weakens thresholds or changes model policy by itself.

A clean repeat may resolve a one-off anomaly. Repeatedly sampling the same benchmark is forbidden once the fixture-diversity guard activates.

## 9. Provider and operational failure isolation

Provider incidents are not model-quality failures.

Examples:

- exhausted key/monthly quota;
- invalid authentication;
- insufficient provider credit;
- rate limiting;
- provider HTTP 5xx;
- connection/transport failure;
- timeout before governed model evaluation.

Such events remain immutable operational evidence but are excluded from capability pass-rate and coverage denominators.

Unknown terminal failures remain fail-closed capability failures until explicitly classified.

## 10. Provider preflight

Paid qualification must execute provider preflight after matrix preparation and before any paid case starts.

For OpenRouter the preflight reads safe status from `GET /api/v1/key`.

Rules:

- missing/invalid key: fail closed;
- malformed/transport failure: fail closed;
- unlimited key: proceed;
- limited key with `limit_remaining <= 0`: block the matrix;
- preflight itself creates no capability evidence;
- no generator, continuity evaluator or semantic judge call starts when access is blocked.

This rule was added after provider quota incidents produced redundant 403 operational evidence.

## 11. Immutable evidence and promotion

Canonical evidence root:

`evidence/model_qualification/`

Evidence records preserve:

- exact Git SHA and workflow identity;
- generator/runtime/policy fingerprints;
- generation/evaluation protocol fingerprints;
- exact benchmark axes;
- final judge results;
- continuity probabilities;
- scene attempts and semantic repairs;
- timings;
- provider usage and USD cost;
- artifact hashes;
- explicit limitations.

Evidence is append-only. Historical failures are not rewritten when later runs succeed.

Workflow jobs first archive case evidence to dedicated evidence branches. Promotion into main is a governed repository action. Checked-in reports are derived views; raw immutable evidence is authority.

## 12. Qualification-budget governance

Qualification spend must be explicit and operator-authorized.

Canonical rules:

- do not spend budget merely because budget exists;
- work in bounded batches;
- recompute evidence state between batches;
- prefer UNKNOWN coverage first, then targeted uncertainty reduction;
- stop and investigate when a new systematic failure signature appears;
- do not change prompts, thresholds or model policy during the same evidence cohort;
- provider preflight must pass before a paid matrix starts;
- cost is recorded per run and reviewed alongside quality and retry burden.

The specific dollar amount is an experiment/session constraint and belongs in the decision ledger, not as a permanent architectural constant.

## 13. Current Luna baseline interpretation

Before the all-family expansion, the active v3 cohort had 45 governed STANDARD runs across 24 observed cells:

- accepted: 45/45;
- terminal failures: 0;
- average scene attempts/story: 7.0;
- average semantic repairs/story: ~0.58;
- average pipeline time: ~178 s;
- average pipeline cost: ~$0.055/run;
- evidence density: 15 PROVISIONAL, 9 THIN, 0 ESTABLISHED.

This supports the conclusion that the governed pipeline is operationally reliable on the observed scope, while still being too sparse to claim universal reliability across all 80 cells.

## 14. All-family expansion and current next work

The active manifest is:

`configs/qualification_waves/age-relative-standard-v3-all-families.yaml`

At all-family activation:

- observed: 24/80;
- UNKNOWN: 56/80.

The deterministic first batch selected `world_lore_discovery × 8 age tiers`.

After each promoted batch:

1. rebuild capability reports from immutable evidence;
2. let the planner choose the next batch;
3. do not hard-code narrative-family order;
4. repeat only planner-selected sentinels;
5. add second frozen fixtures only when fixture-diversity rules require them.

The immediate milestone is first governed observation for all 80 STANDARD cells.

## 15. After 80/80 first-pass coverage

Do not automatically run five repetitions on every cell.

Instead:

1. identify failed, repair-heavy, latency-heavy or cost-heavy cells;
2. repeat suspicious cells under identical identity;
3. introduce second fixtures only where anomaly persists;
4. keep clean cells as regression controls;
5. move only evidence-important cells toward ESTABLISHED;
6. compare alternative generators on the same governed axes;
7. build production routing only from qualified evidence, not reputation or price alone.

Candidate generators such as Aion, MiMo or Qwen must take the same governed test. A different model may be better for a specific age × family × length cell without being globally better.

## 16. Production-routing boundary

Model Lab evidence may later feed a production route resolver, but Model Lab does not directly route production traffic.

A future resolver may consider:

- capability pass rate;
- judge criteria;
- continuity/repair burden;
- latency;
- cost;
- evidence density;
- production telemetry when real telemetry exists.

No route should be selected from one sparse benchmark result.

## 17. Change control

Any change to any of the following creates a new governed evidence cohort:

- StoryContract/SceneGraph semantics;
- generation prompts;
- scene count;
- local or whole-story length rules;
- continuity questions/thresholds;
- semantic judge rubric/thresholds;
- generator runtime profile;
- generator production policy;
- evaluator or judge implementation/profile.

Historical evidence remains immutable and must not silently aggregate with the new identity.

## 18. Canonical references

This document composes, but does not replace:

- `docs/canonical/ENGLISH_FIRST_STORY_PIPELINE_V3.md`
- `docs/canonical/MODEL_CAPABILITY_CUBE_V2.md`
- `docs/canonical/CAPABILITY_COVERAGE_PLANNER_V1.md`
- `docs/canonical/MODEL_RUNTIME_PROFILE_REGISTRY_V2.md`
- `docs/canonical/JEV_JUDGE_LAB.md`
- `.github/workflows/capability-qualification-wave.yml`

Historical experiment records under `docs/experiments/` provide exact run-level evidence and must be preserved.

## 19. North-star rule

The goal is not to prove that one model is universally best.

The goal is to know, with reproducible evidence:

> which governed model/profile is reliable enough for which reader age, reading mode, narrative family and story length, at what repair burden, latency and cost.

Every future Model Lab change should preserve that question.
