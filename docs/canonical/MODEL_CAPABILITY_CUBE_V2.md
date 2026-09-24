# Model Capability Cube & Qualification Evidence v2

Status: **Canonical**
Date: 2026-09-24
Supersedes: `MODEL_CAPABILITY_CUBE_V1.md`
Scope: LUMI Model Lab production-generator qualification

## 1. Core question

Capability Cube v2 answers:

> For this exact generator profile and production policy, under this exact
> generation/evaluation protocol, how reliable is the model for a particular
> reader age tier, reading mode, narrative family, and age-relative story length?

Performance is derived from immutable run evidence. Untested cells are
`UNKNOWN`; they are never inferred to be good or bad.

## 2. Primary dimensions

The canonical v2 capability dimensions are:

`Model × NarrativeAgeTier × ReadingMode × NarrativeFamily × RelativeLengthClass`

Every cohort is additionally bound to:

- generator runtime-profile SHA;
- generator production-policy SHA;
- generation-protocol SHA;
- evaluation-stack SHA.

Every evidence record also preserves exact values:

- `age_min` / `age_max`;
- exact `target_words`;
- actual word count;
- model/evaluator/judge identities;
- timings, repairs, usage and cost.

Exact values are never replaced by a bucket label.

## 3. Why global word-count bands were removed

Capability Cube v1 used global word-count buckets such as SHORT, STANDARD and
LONG. That model is invalid for age-sensitive qualification.

A 500-word story can be a normal complete read-aloud story for a preschool
reader while being an intentionally short story for a teenager. Likewise a
3,800-word story can be normal for a teen but inappropriate as the default
single-session target for a four-year-old.

Therefore v2 defines **relative length classes**. The meaning of STANDARD is
resolved against the reader's canonical age tier.

v2 deliberately qualifies only `STANDARD`. SHORT, LONG and any extreme
classes remain undefined until they receive their own evidence-backed policy.

## 4. Canonical narrative age tiers

The Model Lab mirrors Project_LUMI's NarrativeAgeTier policy:

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

A qualification age range must fit completely inside one tier. Exact-age
qualification is preferred for sparse benchmark waves.

## 5. Reading mode

Reading mode is a first-class qualification dimension because equal word
counts create different demands when a story is read aloud, read by an early
reader, or read independently.

Canonical v2 vocabulary:

- `READ_ALOUD`
- `EARLY_READER`
- `INDEPENDENT_READER`

Default qualification modes:

| Tier | Default qualification mode |
|---|---|
| EARLY_CHILD | READ_ALOUD |
| CHILD | EARLY_READER |
| MIDDLE_CHILD | INDEPENDENT_READER |
| TEEN | INDEPENDENT_READER |
| YOUNG_ADULT | INDEPENDENT_READER |
| ADULT | INDEPENDENT_READER |
| MATURE_ADULT | INDEPENDENT_READER |
| SENIOR | INDEPENDENT_READER |

These are benchmark defaults, not claims about an individual person's ability.
A production user may have a different reading/accessibility preference. Such
alternative modes require separate qualification cohorts rather than silently
reusing the default cohort.

## 6. STANDARD single-session length policy

The canonical v2 policy is:

| Tier | STANDARD target | Qualified normal range |
|---|---:|---:|
| EARLY_CHILD | 500 | 300–800 |
| CHILD | 1,500 | 900–2,200 |
| MIDDLE_CHILD | 2,800 | 2,200–3,500 |
| TEEN | 3,800 | 3,000–4,800 |
| YOUNG_ADULT | 4,200 | 3,200–5,000 |
| ADULT | 4,200 | 3,200–5,000 |
| MATURE_ADULT | 4,200 | 3,200–5,000 |
| SENIOR | 4,200 | 3,200–5,000 |

The exact target used by a benchmark run remains in evidence.

### 6.1 External evidence behind the policy

This table is **not** claimed to be a universal publishing standard.

For young children, the policy is anchored to children's publishing guidance:

- SCBWI critique guidance permits picture-book manuscripts up to about
  1,000 words while noting that many current picture books are under 500
  words.
  https://www.scbwi.org/events/spring-holiday-in-the-park-2025/spring-holiday-in-the-park-2025-critique-guidelines
- Writers & Artists describes picture books as averaging roughly 400–500
  words, with a top end around 750–800, and beginner-reader material around
  1,000 words for first independent reading, about 2,000 for more fluent
  readers, and 2,500–5,000 for the next transition stage.
  https://www.writersandartists.co.uk/advice/what-is-writing-for-children
- Writers & Artists separately describes younger fiction after picture books
  as varying roughly between 1,000 and 6,000 words depending on age and
  fluency.
  https://www.writersandartists.co.uk/advice/writing-and-the-childrens-book-market

For older readers, full-book publishing word counts are not copied into LUMI.
LUMI produces a **single-session story**, not a full middle-grade, YA or adult
novel. The target therefore uses session-scale engineering constraints and
reading-rate evidence instead.

A published reading-fluency review cites approximate rates of 144 words/minute
for ages 8–12, 190 for ages 13–19, 193 for ages 20–39, and 164 for adults over
40, while warning that secondary/adult reading-rate norms are limited.
https://pmc.ncbi.nlm.nih.gov/articles/PMC8699115/

The 2,800 / 3,800 / 4,200 targets are therefore **LUMI product-policy
decisions** informed by publishing categories and reading-rate evidence, not
numbers directly prescribed by those sources.

## 7. Generation-protocol boundary

Story length policy and story structure are separate authorities.

The current English story-production protocol is still a **fixed six-scene
protocol**. Its planner, writer, continuity evaluator prompts and final judge
all explicitly expect six scenes.

Capability Cube v2 therefore does **not** invent age-specific scene counts.

If LUMI later decides that, for example, preschool stories should use fewer
scenes, that is a new generation protocol. It requires:

1. new versioned prompts/contracts;
2. a new generation-protocol fingerprint;
3. fresh qualification evidence;
4. no silent aggregation with six-scene results.

## 8. Narrative-family taxonomy

The canonical narrative-family vocabulary remains:

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

Sharing taxonomy with a training corpus does not make training data
qualification evidence. The datasets remain separate.

## 9. Evidence identity and immutability

Canonical evidence root:

`evidence/model_qualification/`

Native evidence records retain:

- repository SHA and workflow identity;
- generator runtime/profile/policy identity;
- generation-protocol identity;
- continuity-evaluator and semantic-judge identities;
- evaluation-protocol identity;
- exact age and age tier;
- reading mode;
- narrative family;
- relative length class;
- exact target words and actual words;
- final judge scores and repair targets;
- continuity probabilities and threshold failures;
- scene attempt/repair histories;
- stage and per-call timings when available;
- raw provider usage/cost;
- artifact SHA-256 hashes;
- explicit evidence limitations.

Evidence directories are append-only. A duplicate run id fails closed.

Failed runs remain evidence, but pass-rate denominators distinguish **capability failures** from **qualification-not-executed operational failures**.

A run remains capability-eligible when the model/evaluation stack was actually exercised and the run either passed or failed a story-quality, schema, validation, continuity, judge, or other governed qualification condition. Unknown terminal failures are fail-closed and remain capability failures.

Provider-access and provider-transport failures are preserved immutably but excluded from capability denominators because the governed qualification did not complete. Examples include authentication/authorization failure, exhausted key or monthly quota, rate limiting, insufficient provider credit, HTTP 5xx transport failure, connection failure, and timeout. These events remain visible as operational reliability evidence and must not be rewritten as model-quality failures.

This distinction must not be used to hide a genuine model failure. Only explicitly classified non-capability failure domains may be excluded; unrecognized failures stay in the denominator.

## 10. Legacy evidence

Pre-v2 evidence may contain global `length_band` values but no explicit
reading mode or relative length class.

Such evidence is preserved as historical evidence with
`LEGACY_UNSPECIFIED` dimensions. It is **not silently reclassified** into
v2 STANDARD cells, even when its word count happens to fall inside a v2
range.

This prevents a new taxonomy from rewriting the meaning of historical runs.

A deliberate migration may be implemented later, but only with an explicit
migration version and retained provenance.

## 11. Capability-cell identity

Two runs aggregate into the same v2 cell only when all governed identity
dimensions match, including:

- generator;
- runtime profile;
- production policy;
- generation protocol;
- evaluation stack;
- NarrativeAgeTier;
- ReadingMode;
- NarrativeFamily;
- RelativeLengthClass.

Exact target-word and exact-age values remain visible as sub-cohorts inside
that governed cell.

## 12. Coverage states

Evidence-density labels remain:

- 1 run: `THIN`
- 2–4 runs: `PROVISIONAL`
- 5+ runs: `ESTABLISHED`

These describe evidence density, not quality.

## 13. Controlled qualification wave v2

The active sparse age wave is:

`configs/qualification_waves/age-relative-standard-v2.yaml`

Representative exact ages:

| Tier | Age | Mode | STANDARD words |
|---|---:|---|---:|
| EARLY_CHILD | 4 | READ_ALOUD | 500 |
| CHILD | 7 | EARLY_READER | 1,500 |
| MIDDLE_CHILD | 10 | INDEPENDENT_READER | 2,800 |
| TEEN | 15 | INDEPENDENT_READER | 3,800 |
| YOUNG_ADULT | 21 | INDEPENDENT_READER | 4,200 |
| ADULT | 32 | INDEPENDENT_READER | 4,200 |
| MATURE_ADULT | 50 | INDEPENDENT_READER | 4,200 |
| SENIOR | 70 | INDEPENDENT_READER | 4,200 |

Each age is crossed with three deliberately different families:

- `exploration_mystery`
- `emotional_development`
- `puzzle_problem_solving`

Total: **24 cases**.

The manifest is the authority for maximum parallelism. The workflow reads
`max_parallel` from the manifest rather than maintaining a second hard-coded
value.

## 14. Invalidated v1 age wave

`configs/qualification_waves/age-standard-v1.yaml` is
`SUPERSEDED_INVALID`.

Reason: it applied a global 2,000-word target to every age tier, including
preschool readers.

Run `35961437388` was cancelled after the design defect was identified.
Any case evidence produced by that wave is experimental historical evidence
only and must not be promoted into the canonical capability dataset.

The invalid wave and generated specs remain in the repository as an audit
record of why the policy changed.

## 15. Expansion policy

Adaptive scheduling is governed by `docs/canonical/CAPABILITY_COVERAGE_PLANNER_V1.md`. The planner may prioritize executable cells, but it cannot redefine capability dimensions, acceptance gates, evidence identity, or fixture authority.

After the age-relative STANDARD sweep:

1. identify weak or surprising cells;
2. repeat those cells before tuning a model;
3. compare judge criteria, continuity probabilities, repairs and latency;
4. preserve good cells as regression controls;
5. only then define SHORT/LONG/extreme relative-length policies;
6. qualify any new relative class independently for each relevant age tier.

No model-specific production-policy override should be introduced from one
isolated failure.

## 16. Privacy boundary

Repository qualification evidence is synthetic Model Lab evidence.

Real child/user profile data, private StoryContext, or production stories must
not be copied into the repository merely because the qualification machinery
can retain stories.

Production-data retention requires separate privacy and consent authority.
