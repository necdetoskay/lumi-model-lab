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
