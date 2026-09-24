# Model Capability Cube & Qualification Evidence v1

Status: **Canonical**
Date: 2026-09-24
Scope: LUMI Model Lab production-generator qualification

## 1. Purpose

The Model Capability Cube answers a narrower and more useful question than
"Which model is best?":

> For this model, production policy, audience age tier, narrative family,
> story-length band, and evaluation stack, what does the retained
> qualification evidence actually show?

The cube is derived from immutable run evidence. It is not manually scored,
and an untested cell is **UNKNOWN**, never implicitly good or bad.

## 2. Authority boundaries

The system has five separate authorities.

### Runtime profile

Describes verified provider/model facts and transport behavior.

Examples: context limits, reasoning support, structured output, temperature,
provider routing and seed support.

### Production policy

Describes how LUMI chooses to use that runtime for a request class.

Examples: reasoning effort, max-token behavior and structured-output mode.

### Generation protocol

Describes the story-production protocol applied on top of the model policy.

It includes the versioned story pipeline and the prompt/repair artifacts used
for planning, scene generation, technical repair, semantic repair and final
targeted polish.

Its fingerprint is separate from the model profile. Changing a story prompt
or generation-protocol version creates a new measurement variant even when
the model id and production policy are unchanged.

### Evaluation stack

Describes how a story is measured.

Canonical role names are model-independent:

- `continuity_evaluator`
- `semantic_judge`

Today the continuity evaluator can be JEV and the semantic judge can be
Claude Haiku. Those are implementations, not schema names.

The evaluation stack identity includes:

- continuity evaluator model/profile identity;
- semantic judge model/profile identity;
- evaluation protocol version;
- semantic-judge prompt artifact hashes.

Changing any of these produces a new evaluation cohort. Scores from different
evaluation-stack identities are not silently averaged together.

### Capability Cube

Aggregates only immutable qualification evidence that shares compatible model,
production-policy, generation-protocol and evaluation-stack identities.

It does not mutate runtime profiles or production policy.

## 3. Primary capability dimensions

The v1 cube uses:

`Model × NarrativeAgeTier × NarrativeFamily × LengthBand`

Each observed cell is additionally bound to:

- generator profile SHA;
- generator production-policy SHA;
- generation-protocol SHA;
- evaluation-stack SHA.

Exact age/range and exact target-word values remain in each evidence record
and are surfaced as sub-cohorts inside the broader age/length cell.

## 4. Canonical age tiers

The Model Lab mirrors Project_LUMI's canonical `NarrativeAgeTier` policy:

| Tier | Age |
|---|---:|
| EARLY_CHILD | 3–5 |
| CHILD | 6–8 |
| MIDDLE_CHILD | 9–12 |
| TEEN | 13–17 |
| YOUNG_ADULT | 18–24 |
| ADULT | 25–39 |
| MATURE_ADULT | 40–59 |
| SENIOR | 60–120 |

A qualification spec must fit entirely inside one tier. A range such as 8–9
fails closed because it spans two narrative policies.

Exact profile age remains valuable evidence. A future qualification can use
`age_min == age_max` when an exact-age probe is desired.

## 5. Narrative-family taxonomy

The cube reuses the Project_LUMI story-corpus narrative-family taxonomy:

1. `exploration_mystery`
2. `friendship_social_problem`
3. `puzzle_problem_solving`
4. `nature_environment`
5. `scientific_curiosity`
6. `adventure_journey`
7. `emotional_development`
8. `cooperation_teamwork`
9. `everyday_fantastical_discovery`
10. `world_lore_discovery`

Training-corpus artifacts and production-qualification evidence remain separate
datasets even though they share taxonomy.

## 6. Length bands

Model Lab groups target words into:

| Band | Target-word range |
|---|---:|
| SHORT | 300–1499 |
| STANDARD | 1500–2499 |
| LONG | 2500–3999 |
| EXTENDED | 4000–5000 |

Exact `target_words` is always retained and reported as a sub-cohort. The
band is for stable routing and coverage; it must not erase evidence that a
model behaves differently at 1800 and 2400 words.

## 7. Immutable qualification evidence

Canonical repository root:

`evidence/model_qualification/`

A native completed run stores:

- `manifest.json`
- `result.json`
- `story.txt` when story text exists
- `spec.yaml`

The complete result contains plan, scene envelopes, generation attempts,
continuity evaluations, semantic repairs, final evaluation history, costs,
usage and timing evidence produced by the pipeline.

The manifest contains the stable queryable summary:

- repository SHA;
- workflow run/job identity;
- generator model/profile/policy identity;
- generation-protocol identity;
- evaluation-stack identity;
- age tier and exact age range;
- narrative family;
- length band and exact target words;
- accepted/rejected result;
- deterministic failures;
- final semantic-judge scores;
- final repair targets;
- whole-story continuity result;
- per-scene attempts and repairs;
- scene wall time;
- per-generation-attempt time when available;
- per-continuity-evaluation time when available;
- pipeline stage and total time;
- cost and usage summaries;
- artifact hashes;
- explicit evidence limitations.

Evidence directories are immutable. Reusing a run id fails closed.

## 8. Failure evidence

Failed runs are evidence too.

If the story pipeline raises before creating a normal result, it writes
`failure.json` containing at least:

- generator/evaluator/judge identities;
- generation protocol version;
- evaluation protocol version;
- spec reference;
- terminal error type/message;
- elapsed pipeline time.

The evidence pack may legitimately omit `story.txt` when no story exists.

Failed qualification runs count in cube pass rate. They must never disappear
from the denominator merely because no final story was produced.

## 9. Timing evidence

New native runs capture:

- plan-stage wall time;
- each accepted scene's wall time;
- each generation/technical-repair/semantic-repair attempt time;
- each scene continuity-evaluator call time;
- final-stage wall time;
- total pipeline time.

Historical runs may lack some of these fields. Missing values stay missing and
must not be inferred.

## 10. Capability metrics

Each cube cell includes at least:

- run count;
- accepted count / pass rate;
- coverage status;
- average final semantic-judge score;
- minimum observed final criterion;
- per-criterion semantic-judge averages;
- total/average scene-generation attempts;
- semantic repair rate;
- final repair-target count;
- critical-failure count;
- scene continuity threshold-failure counts;
- whole-story continuity threshold-failure counts;
- average repetition ratio;
- average absolute word-target error;
- average pipeline wall time;
- average raw provider cost;
- exact-age/range sub-cohorts;
- exact target-word sub-cohorts;
- source run ids.

Raw provider cost is stored in its native currency for reproducibility.
User-facing cost reporting is converted to TRY using a stated report-time FX
rate.

## 11. Coverage states

Current v1 thresholds:

- 1 run: `THIN`
- 2–4 runs: `PROVISIONAL`
- 5+ runs: `ESTABLISHED`

These are evidence-density labels, not quality rankings.

A 100% pass-rate cell with two runs is still PROVISIONAL.

## 12. Production-policy overlays

The cube may reveal a persistent weakness such as:

`Luna × TEEN × adventure_journey × LONG`

That does **not** authorize changing Luna's global base policy.

A model-specific overlay is considered only when:

1. repeated evidence shows a stable weakness in the same cell/sub-cohort;
2. the proposed change is a model-execution policy, not a weaker quality gate;
3. the target cell improves under the same evaluation stack;
4. already-good regression cells do not materially degrade;
5. the new production-policy identity is requalified.

The cube records performance. It does not automatically mutate policy.

## 13. Routing

A future production router may consume established/provisional capability
evidence, but routing is a separate governed decision layer.

The router may consider:

- age tier / exact age;
- narrative family;
- target length;
- pass rate and evidence density;
- judge criteria;
- continuity reliability;
- repair burden;
- latency;
- cost.

It must never treat an UNKNOWN cell as evidence of superiority.

## 14. Historical migration

Older qualification runs may be migrated from retained CI logs when original
artifacts no longer exist.

Such records use a source such as
`github_actions_legacy_log_migration` and list explicit limitations.

A migration may recover observed facts such as story text, logged scene
checkpoints, final judge output and provider cost. It may not invent missing
plan payloads, scene envelopes, token usage or timing measurements.

Historical model/profile identity should be resolved from the repository SHA
that actually produced the run. For the migrated Luna batch, the source-run
registry SHA-256 was explicitly verified to be byte-identical to the current
registry (`2102f98d...`), so the recorded profile identity is equivalent.

## 15. Privacy boundary

Repository qualification evidence is for synthetic/test Model Lab material.

Real user/child production stories, personal StoryContext, private profile
data or other user-derived content must not be copied into this repository
merely because the same evidence machinery exists. Production-data retention
requires its own privacy/consent authority.

## 16. Current initial dataset

The first migrated dataset is the canonical GPT-5.6 Luna 2026-09-24
qualification matrix:

- 10 successful runs;
- 5 observed narrative-family cells;
- CHILD age tier;
- STANDARD length;
- 2 runs per observed cell;
- all five cells currently PROVISIONAL;
- all untested cells remain UNKNOWN.

Generated reports:

- `reports/model_capability_cube.json`
- `reports/model_capability_cube.md`

The JSON report is the machine-readable source for detailed diagnostics. The
Markdown report is a compact human view.
