# Story Production Qualification Decision Ledger

Status: **Canonical / append-only**
Opened: 2026-09-24
Purpose: preserve when a major Model Lab story-production decision was made, what evidence caused it, and what must happen next.

Do not rewrite old decisions to make the history look cleaner. Add a new dated entry when later evidence changes a conclusion.

## 2026-09-24 — Reject global 2,000-word age sweep

Decision:

- `age-standard-v1` was declared `SUPERSEDED_INVALID`.
- A global 2,000-word target across all reader ages is not a valid age-relative qualification policy.
- Run `35961437388` remains historical/audit evidence only.

Why:

A preschool read-aloud story and an adult single-session story cannot share one global STANDARD target without distorting the capability measurement.

Replacement:

`MODEL_CAPABILITY_CUBE_V2` age-relative STANDARD policy.

## 2026-09-24 — Establish age-relative first qualification wave

Stack:

- generator: `openai/gpt-5.6-luna`;
- continuity evaluator: `typesafe/jev-1.13`;
- semantic judge: `anthropic/claude-haiku-4.5`.

Result:

- 24/24 first-wave stories accepted across 8 age tiers × 3 narrative families;
- average final semantic judge ~4.0677/5;
- lowest final criterion 4;
- average attempts/story ~7.29;
- average semantic repairs/story ~0.75;
- average pipeline time ~209 s.

Decision:

The age-relative six-scene STANDARD policy is operationally viable. One observation per cell is not enough to call the cells established.

Reference:

`docs/experiments/luna-age-relative-standard-v2-qualification-20260924.md`

## 2026-09-24 — Repeat outliers before tuning

Seven targeted repeats were run without changing prompts, model policy or thresholds.

Result:

- 7/7 accepted;
- most first-wave retry outliers did not reproduce;
- CHILD × exploration reproduced aggregate retry burden, but the internal failure signature differed.

Decision:

Do not introduce a Luna-specific prompt/policy override from a single or non-reproducing outlier.

Canonical lesson:

Repeat exact identity before tuning.

Reference:

`docs/experiments/luna-age-relative-standard-v2-targeted-repeats-20260924.md`

## 2026-09-24 — Reject story protocol v2

Experiment:

Symmetric local scene slack was relaxed on both lower and upper sides.

Observation:

TEEN × puzzle remained finally acceptable but retry/repair burden materially worsened compared with the v1 control cohort.

Decision:

Do not promote v2.

Why:

Final pass status alone is insufficient. A protocol change that creates avoidable repair burden is a regression even when the final story passes.

Reference:

`docs/canonical/ENGLISH_FIRST_STORY_PIPELINE_V2.md`

## 2026-09-24 — Promote story protocol v3

Change:

Keep the v1 under-length floor; relax only the historically dominant overshoot side.

Cross-age result:

- 5/5 accepted;
- all final judge minimum criteria = 4.

TEEN control:

- three v3 observations completed with attempts 6, 6, 7;
- semantic repairs 0, 0, 0.

Decision:

Promote `english-story-production.v3` as the shared generation protocol.

Do not add Luna-specific tuning because the defect was in a shared validation rule.

Reference:

`docs/experiments/story-word-budget-protocol-v3-qualification-20260924.md`

## 2026-09-24 — Adopt adaptive evidence-density planning

Decision:

Qualification expansion is governed by deterministic planner priority rather than arbitrary manual model testing.

Planner rules include:

- UNKNOWN > THIN > PROVISIONAL > ESTABLISHED;
- age-balanced first pass;
- bounded sentinel lane;
- fixture-diversity escalation guard;
- no invented production popularity.

Reference:

`docs/canonical/CAPABILITY_COVERAGE_PLANNER_V1.md`

## 2026-09-24 — Separate fixture anomaly from model weakness

Observed examples:

- MIDDLE_CHILD × puzzle produced a repair-heavy run, then a clean repeat;
- ADULT × puzzle reproduced repair burden on one frozen fixture;
- additional diagnostic fixture policy was introduced before any model-specific intervention.

Decision:

Two anomalies on one fixture do not prove a whole capability cell is weak.

Required escalation:

- repeated anomaly on one fingerprint -> second frozen premise;
- anomaly across distinct fingerprints -> targeted intervention candidate.

## 2026-09-24 — Expand STANDARD fixtures from 24 to 80 cells

PR: #175 — Expand STANDARD qualification to all narrative families.

Canonical space:

`8 age tiers × 10 narrative families = 80 STANDARD cells`

At activation:

- observed under current v3 identity: 24;
- UNKNOWN: 56;
- fixture-missing: 0.

Decision:

Run deterministic bounded batches; do not change active prompts/model/evaluation identity during coverage expansion.

First selected family:

`world_lore_discovery × 8 age tiers`.

## 2026-09-24 — Provider incidents must not reduce model capability

PR: #174 — Separate provider access failures from capability evidence.

Incident:

Four world-lore attempts received OpenRouter 403 because the key monthly limit was exhausted.

Decision:

Classify as `PROVIDER_ACCESS_FAILURE`.

Rules:

- retain immutable operational evidence;
- exclude from capability pass-rate/coverage denominators;
- do not make Luna look worse because provider access was unavailable.

## 2026-09-24 — Add paid-wave provider preflight

PR: #177 — Gate paid qualification on OpenRouter access preflight.

Mechanism:

OpenRouter `GET /api/v1/key` is queried before paid model jobs.

First live proof:

workflow run `36000135555`, attempt 1/2 period:

- prepare succeeded;
- preflight reported exhausted monthly limit;
- qualify was skipped;
- no Luna/JEV/Haiku calls;
- no redundant 403 capability evidence.

PR #178 recorded the proof.

Decision:

Provider preflight is mandatory before paid qualification.

## 2026-09-24 — Canonical baseline after preflight work

Main SHA:

`74056d6f5092026d7d2d8fe13475767969ce7460`

At this baseline:

- repository main matched origin/main;
- worktree was clean;
- 267/267 tests passed;
- evidence integrity passed;
- active v3 observed STANDARD cells: 24/80;
- UNKNOWN: 56/80.

## 2026-09-24 — OpenRouter qualification budget restored

Operator-authorized current qualification budget:

**USD 17**

This is a session/experiment budget, not a permanent architecture constant.

Budget policy:

- use bounded adaptive batches;
- review cost and anomaly state after each batch;
- reserve budget for diagnostic repeats;
- do not spend remaining credit merely to increase sample count.

Observed current v3 cost before all-family expansion was roughly USD 0.055 per governed story on average.

## 2026-09-24 — First all-family world-lore batch executed

Workflow run:

`36000135555`, later attempt after provider access became available.

First eight-case evidence set:

| Age tier | Accepted | Target | Actual | Attempts | Repairs | Judge | Cost USD |
|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY_CHILD | no | 500 | 553 | 7 | 0 | 4.000 | 0.04470 |
| CHILD | yes | 1,500 | 1,620 | 7 | 1 | 4.000 | 0.04450 |
| MIDDLE_CHILD | yes | 2,800 | 2,766 | 7 | 1 | 4.000 | 0.05445 |
| TEEN | yes | 3,800 | 3,782 | 6 | 0 | 4.000 | 0.05365 |
| YOUNG_ADULT | yes | 4,200 | 3,848 | 6 | 0 | 4.000 | 0.05420 |
| ADULT | yes | 4,200 | 4,099 | 6 | 0 | 4.875 | 0.05421 |
| MATURE_ADULT | yes | 4,200 | 3,952 | 9 | 2 | 4.000 | 0.06620 |
| SENIOR | yes | 4,200 | 3,753 | 8 | 2 | 4.000 | 0.06491 |

First-batch total pipeline cost:

approximately **USD 0.4368**.

Interpretation:

- 7/8 passed all final acceptance gates;
- MATURE_ADULT and SENIOR passed but each required two semantic repairs, so they are repeat-worthy signals, not tuning conclusions;
- EARLY_CHILD was semantically strong: Haiku 4/4 and whole-story JEV clean;
- EARLY_CHILD failed only the hard deterministic repetition gate: `repeat_8gram_ratio=0.02381 > 0.02`.

Decision:

Do not weaken the repetition threshold from one short-story observation. Repeat under identical identity first.

Evidence branches:

`evidence/run-36000135555-<case-id>`

## 2026-09-24 — Matrix rerun behavior discovered

Action:

A GitHub rerun was requested from the failed EARLY_CHILD matrix job with the intention of obtaining one sentinel repeat.

Observed behavior:

GitHub opened workflow attempt 3 and re-executed the world-lore matrix rather than creating only one isolated new governed case.

Decision:

Do not use matrix-job rerun as the canonical sentinel mechanism.

Future sentinel work must be launched as a fresh planner/workflow dispatch with the intended bounded matrix and fresh run ids.

Attempt 3 produced a clean EARLY_CHILD story result:

- 573 words;
- `repeat_8gram_ratio = 0.0`;
- final semantic judge accepted;
- pipeline result `accepted = true`;
- pipeline cost approximately USD 0.04487.

Therefore the original `0.02381` repetition miss did not reproduce in the immediate diagnostic attempt.

However, attempt 3 reused the same `GITHUB_RUN_ID + CASE_ID`. The evidence branch already existed, so the append-only archive push was correctly rejected as non-fast-forward. The repeated story is useful diagnostic information but must **not** be counted as a second canonical Capability Cube observation.

Permanent rule: a qualification repeat that is intended to count as evidence must be a fresh workflow dispatch with a fresh run id. GitHub rerun is not a canonical qualification-repeat mechanism.

## 2026-09-24 — Secondary GitHub artifact storage is non-authoritative

During world-lore execution, `actions/upload-artifact` reported GitHub artifact storage quota exhaustion.

The primary immutable evidence branch was created and evidence-integrity verification passed.

Decision:

- canonical qualification evidence in repository evidence branches remains authority;
- secondary workflow artifact upload is convenience only;
- artifact storage failure must not rewrite a valid model result;
- storage quota should be cleaned/managed separately from model capability.

## Current operating plan

1. Finish and classify the current world-lore evidence, including the repeated attempt.
2. Promote valid immutable evidence into main and rebuild derived Capability Cube/planner reports.
3. Let the deterministic planner choose the next batch; do not manually invent the next family order.
4. Continue bounded 8-case coverage batches while provider preflight passes and budget remains healthy.
5. Reach first observation for all 80 STANDARD cells.
6. After 80/80, spend qualification budget on uncertainty reduction rather than blanket repetition.
7. Use second frozen fixtures for persistent same-fixture anomalies.
8. Move evidence-important cells toward ESTABLISHED; do not require 5 runs for every cell by default.
9. Qualify additional generators on the same governed axes.
10. Only after comparable evidence exists, design production routing by age × family × length × quality/reliability/cost.

## Permanent decision rule

Never solve an isolated benchmark problem by immediately changing the model prompt, evaluator threshold or judge threshold.

The escalation order is:

`observe -> exact repeat -> fixture-diverse diagnostic -> controlled intervention -> regression qualification -> promotion`

This sequence is part of the canonical Model Lab architecture.


## 2026-09-24 — Promote first world-lore all-age evidence

Promotion PRs:

- #180 EARLY_CHILD
- #181 CHILD
- #182 MIDDLE_CHILD
- #183 TEEN
- #184 YOUNG_ADULT
- #185 ADULT
- #186 MATURE_ADULT
- #187 SENIOR

Result after promotion:

- active v3 STANDARD observed cells: **32/80**;
- UNKNOWN cells: **48/80**;
- active v3 governed runs: **53**;
- accepted: **52/53**;
- evidence density: 17 THIN, 15 PROVISIONAL, 0 ESTABLISHED.

The canonical EARLY_CHILD world-lore run remains a failed observation because the hard repetition gate was exceeded, even though the semantic judge and continuity evaluator rated the story clean.

The immediate same-run diagnostic produced a clean story with zero 8-gram repetition, but it cannot be counted as second evidence because the rerun reused the existing immutable evidence id.

Decision:

- preserve the failed first observation;
- do not weaken the repetition threshold;
- require a fresh workflow dispatch for any counted repeat;
- continue UNKNOWN coverage from 32/80 using the deterministic planner.


## 2026-09-24 — Freeze fixed-six coverage expansion at 32/80

Reason:

The product requirement does not require a fixed six-scene story. Review of the v3 implementation showed that six scenes were encoded in planner validation, scene budgets, scene/whole-story evaluator prompts, payoff/resolution positions, and qualification fixtures.

Decision:

- stop the v3 32/80 -> 80/80 spend before expanding the wrong structural assumption;
- retain all existing v3 evidence as historical evidence under its frozen protocol identity;
- do not mix dynamic-scene evidence into the v3 Capability Cube;
- evaluate a variable-scene v4 candidate before resuming broad coverage.

Reference:

`docs/canonical/DYNAMIC_SCENE_NARRATIVE_ARCHITECT_V4_EXPERIMENT.md`

## 2026-09-24 — Dynamic Scene v4 Run 1 exposed fixture and repair-ownership defects

Run:

`36008607397`

Result:

- Sonnet selected six scenes only because the inherited fixture explicitly required continuity across all six scenes;
- therefore the run did not test free scene-count selection;
- final story was produced but failed the semantic gate at 3.875 average;
- total cost: USD 0.16752763;
- an ambiguity originating in the immutable SceneGraph survived repeated prose repairs.

Decision:

- classify Run 1 as diagnostic, not valid dynamic-scene evidence;
- make qualification fixtures scene-count-neutral unless count is an explicit product requirement;
- route repair according to defect ownership;
- a plan defect must not be chased indefinitely with prose-only repair.

## 2026-09-24 — First valid dynamic-scene observation passed with five scenes

Run:

`36009516596`

Changes from Run 1:

Only the experimental fixture's fixed-six continuity constraint was replaced by continuity across the complete story and the planner-selected SceneGraph.

Sonnet selected:

`SETUP -> RISING_ACTION -> RISING_ACTION -> PAYOFF -> RESOLUTION`

with five scenes.

Result:

- accepted: yes;
- 2,607 / 2,800 words;
- repeated 8-gram ratio: 0.0;
- final Haiku: 4.0 average, minimum 4;
- whole-story JEV: all dimensions above threshold;
- total scene attempts: 8;
- semantic repairs: 3;
- final targeted repairs: 0;
- total cost: USD 0.131251818;
- total time: 277.160 s.

Important unresolved governance signals:

- plan JEV had below-threshold `constraint_coverage=0.65` and `no_unexplained_dependencies=0.79`, while Haiku accepted the plan;
- Scene 4 still ended with `no_contradiction=0.77<0.80` and `continuity_escalation_required=true`;
- the whole-story evaluators later accepted the assembled story.

Decision:

Do not promote v4 from one successful story. Before broad qualification, define repair ownership, stale-evidence isolation, plan-JEV authority, and cross-level continuity-gate semantics.

## Superseding operating plan after dynamic-scene discovery

1. Keep v3 coverage frozen at 32/80.
2. Preserve all v3 evidence under its existing protocol identity.
3. Harden v4 repair ownership and evaluator authority boundaries.
4. Use scene-count-neutral fixtures.
5. Run a small, diverse dynamic-v4 validation set before spending on 80-cell coverage.
6. Compare Luna vs Sonnet as Narrative Architect under the same v4 protocol.
7. Promote only with evidence that the higher-cost planner materially improves reliability/quality or reduces repair burden.
8. Restart broad Capability Cube qualification only under the promoted protocol identity.


## 2026-09-24 — Whole-draft v5 prototype justified for further validation

Motivation:

Sequential scene generation increased call count, latency, repeated-context overhead, evaluator disagreement surface and repair-loop complexity. A simpler candidate was tested:

`Dynamic Architect -> Whole Draft -> Deterministic Gate -> Whole-Story JEV -> Haiku -> StoryOutcome`

Run `36016223639` showed that the semantic path could produce a strong story (Haiku 4.875, JEV clean) but a single whole-draft call still needed application-owned word-budget governance; 2,119 words exceeded the 1,500 target's hard range.

After adding normalized per-scene targets derived from planner weights, Run `36016585318` produced:

- accepted story;
- 1,567 / 1,500 words;
- six dynamically chosen scenes;
- zero prose repair;
- repeated 8-gram ratio 0;
- whole-story JEV clean;
- Haiku 4.875, minimum 4;
- validated StoryOutcome proposal;
- `commit_ready=true`;
- no database write by design;
- 82.77 seconds;
- approximately USD 0.019667 total observed cost.

Decision:

- preserve v5 as an experimental production candidate;
- do not promote from one accepted sample;
- prefer a small cross-length/cross-family validation cohort before any broad 80-cell spend;
- keep StoryOutcome extraction after final story acceptance;
- keep database authority in the LUMI application, with atomic/idempotent commit required before user-visible delivery;
- do not mix v5 evidence with v3/v4 Capability Cube evidence.

Reference:

`docs/canonical/STORY_PRODUCTION_V5_WHOLE_DRAFT_PROTOTYPE.md`


## 2026-09-24 — Close v5 state proposal surface with application-owned authority

Evidence:

`36023172608`

Decision:

The untyped StoryOutcome shape is not acceptable for production persistence.

The v5 candidate now requires a closed State Mutation Authority containing:

- authority revision;
- canonical entity reference;
- expected entity revision;
- expected entity fingerprint;
- allowed mutation type;
- allowed field key;
- persistence classification.

A model proposal must copy the matching `base_revision` and `base_fingerprint` and may not invent a tuple outside the authority.

The first typed calibration produced five authorized, evidence-backed mutations and no transient emotional/activity/inventory/relationship persistence.

Permanent rule:

> Story evidence is necessary but never sufficient to create a database mutation. Persistence authority belongs to the application contract.

Real LUMI commit still requires deterministic revision/fingerprint/conflict validation and atomic/idempotent commit.

## 2026-09-24 — Strong pairwise judge is evidence, not single-verdict authority

Calibration pair:

Two accepted versions of the same 1,500-word fixture.

Judge:

`anthropic/claude-sonnet-5`

Initial request failure in run `36023172608`:

- high reasoning;
- max completion 2,200;
- reasoning consumed 2,199 tokens;
- no visible JSON;
- classify as request-policy failure, not judge-quality evidence.

Fresh corrected run:

`36023582660`

Policy:

- medium reasoning;
- max completion 5,000;
- blind A/B comparison;
- second blind comparison with candidate order reversed;
- normalize the reversed decision back to original labels.

Observed:

- forward overall: B / SMALL;
- reverse normalized overall: TIE / SMALL;
- stable criteria: 3/7;
- calibration: `POSITION_SENSITIVE`;
- calibrated winner: `INCONCLUSIVE`.

Decision:

- never choose a model from one pairwise judgment;
- never count a pair unless presentation-order sensitivity is tested;
- order-sensitive pairs are inconclusive;
- model-level preference requires multiple stable comparisons across distinct fixtures;
- Haiku scalar score and Sonnet pairwise preference remain measurement signals, not promotion authority.

The purpose of the pairwise layer is to improve discrimination, not to replace one unquestioned judge with another.
