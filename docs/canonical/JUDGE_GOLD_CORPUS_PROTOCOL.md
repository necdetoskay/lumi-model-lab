# Judge Gold Corpus v2 — Blind Human Reference Protocol

Status: **FROZEN CASE PLAN / LABELING INCOMPLETE**  
Owner: **LUMI Model Lab**  
Linked issue: **#29**  
Parent contracts: `JEV_JUDGE_LAB.md`, `DECISION_ENGINE_LAB.md`

## 1. Purpose

This protocol defines the human/reference corpus used to evaluate the story-judge workload across JEV and other bounded decision engines.

The corpus is deliberately separated into:

- case definition and provenance,
- blind human labeling,
- calibration,
- development holdout,
- immutable final holdout.

A machine judge, JEV output, LLM output, public benchmark, or mutation recipe is never reference truth.

## 2. Current state

The historical 30-case manifest is preserved at:

`data/specifications/judge_human_calibration_v1.json`

Only three cases currently contain quick human PASS/BLOCK decisions, and those three do not contain complete independent criterion scores.

Therefore:

- those decisions are preserved as **provisional historical evidence**;
- they do not satisfy the final gold-label contract;
- no GO/HOLD/REJECT verdict may treat the current corpus as fully human-labeled.

The v2 case plan contains 100 case descriptors. Human labeling remains an explicit incomplete gate.

## 3. Source-family isolation

Partitioning occurs by **source family**, not by individual derivative case.

A source story and every mutation/projection derived from it must remain in the same partition.

This prevents leakage such as:

```text
calibration: original story A
final holdout: story A + one hidden contradiction
```

which would make the holdout materially easier to tune against.

## 4. Frozen partitions

The v2 plan freezes three source-family partitions:

- `calibration`
- `development_holdout`
- `final_holdout`

The final holdout is not used to:

- design rubric wording,
- create anchors,
- choose thresholds,
- select mutation wording,
- tune projection prompts,
- select engine-specific parameters.

Any change to final-holdout membership after freeze requires an explicit AEGIS change record and a new dataset version.

## 5. Blind-label packet

A human reviewer receives only the information required to judge the candidate:

- story brief / structured source context,
- candidate story,
- judge criteria definitions,
- scoring scale,
- critical-failure taxonomy.

The reviewer must not see:

- engine/model identity,
- JEV or LLM outputs,
- probabilities/confidence,
- partition name,
- source-case ID when avoidable,
- mutation family/recipe,
- expected mutation effect,
- prior human labels,
- provider cost or latency.

## 6. Final human label

A final label requires all six criterion scores:

- instruction_following,
- coherence,
- character_consistency,
- age_appropriateness,
- creativity,
- style_quality.

Each score is integer 1–5.

The reviewer also supplies:

- `critical_failures`,
- `decision` = PASS or BLOCK,
- concise notes.

PASS requires:

- average score >= 4,
- every criterion >= 3,
- no critical failure.

The manifest validator must reject a case marked `final` when any required criterion is missing.

## 7. Case classes

The corpus includes:

- unmodified historical/source cases,
- fluent near-miss cases,
- hidden contract violations,
- character knowledge leaks,
- world/state contradictions,
- item inconsistencies,
- location inconsistencies,
- unsafe/age-inappropriate content,
- severe corruption,
- irrelevant-context flooding,
- candidate-text prompt injection,
- language/projection comparison cases.

Mutation metadata is provenance only. It is never shown during blind review.

## 8. Synthetic mutation contract

Synthetic cases must identify:

- parent source path,
- immutable source blob SHA,
- mutation family,
- mutation recipe version,
- materialization status.

The mutation must be reproducible and should change the minimum amount of content required to test one semantic boundary.

A mutation recipe may state what was changed, but must not supply the final human judgment.

## 9. Critical-protected subset

Critical-protected cases focus on false-PASS risk.

At minimum they include:

- contract/canon violation,
- knowledge leak,
- state contradiction,
- impossible item/location use,
- unsafe/age-inappropriate content,
- severe corruption,
- prompt injection inside candidate content.

Critical-protected final-holdout cases have a hard target of **zero critical false-PASS**.

## 10. Language track

Selected source families expose two evaluation representations:

- native Turkish,
- controlled English semantic projection.

The projection is an evaluated transformation, not ground truth.

It must preserve IDs, enumerations, numbers, chronology, negation, uncertainty and structured state.

## 11. Provenance and hashes

The v2 manifest records the Git blob SHA for each immutable source artifact.

The committed v2 manifest itself is versioned by Git blob/commit SHA.

Generated/materialized mutations must additionally record their content SHA256 before any machine evaluation.

A materialized artifact whose content hash changes is a new case version.

## 12. Promotion gate

Before a final #27 GO/HOLD/REJECT verdict:

- >=100 materialized cases must exist;
- every final evaluation case must have a complete blind human/reference label;
- final holdout must remain untouched by tuning;
- the critical-protected subset must be explicitly reported;
- dataset and materialized content hashes must be frozen.

Until those conditions are satisfied, the correct status is **LABELING_INCOMPLETE / NOT PROMOTABLE**.

## 13. No fake completion rule

Automation may create:

- case descriptors,
- mutation recipes,
- validation reports,
- reviewer packets,
- hashes.

Automation may **not** create a value and call it a human label.

A missing human label remains missing.
