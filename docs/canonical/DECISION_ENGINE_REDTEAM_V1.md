# Decision Engine Red-Team v1 — Metamorphic Falsification Protocol

Status: **IMPLEMENTATION BASELINE / NO REAL ENGINE VERDICT YET**  
Owner: **LUMI Model Lab**  
Linked issue: **#33**  
Parent contracts: `DECISION_ENGINE_LAB.md`, `JEV_JUDGE_LAB.md`, `JUDGE_ATOMIC_RUBRIC_V1.md`

## 1. Purpose

This protocol attempts to falsify bounded decision engines before any production discussion.

It is provider-agnostic. JEV, local/open engines, and future LUMI-specialized engines must face the same frozen red-team relations when they claim the same workload.

## 2. Red-team evidence is not human gold

The red-team suite uses controlled synthetic/metamorphic expectations such as:

- changing one causally relevant fact should move the dependent decision;
- irrelevant context should not materially move the decision;
- missing evidence should trigger abstention;
- renaming entities while preserving relations should preserve the decision;
- instruction-like text inside candidate content must not escape the declared output schema.

These relations are engineering oracles for robustness. They do **not** replace blind human story-quality labels and do not satisfy #29.

## 3. Case-pair contract

A red-team relation references:

- a baseline case,
- a mutant/paired case,
- one target dimension,
- relation type,
- tolerance/minimum delta,
- severity,
- expected evidence-gate behavior,
- reproduction metadata.

Baseline and mutant are immutable fixture IDs.

## 4. Relation types

### `decrease`

A causally harmful mutation should reduce the target score by at least the frozen minimum delta while both cases remain evidence-sufficient.

Examples:

- knowledge leak,
- relationship contradiction,
- world-state contradiction,
- unsafe age mutation,
- severe semantic repetition.

### `invariant`

A semantics-preserving or irrelevant mutation must not move the target score beyond the frozen tolerance and must preserve the evidence gate.

Examples:

- irrelevant context insertion,
- entity renaming with preserved graph,
- equivalent field ordering.

### `evidence_flip`

Removing required evidence must change the paired evidence gate:

`SUFFICIENT -> INSUFFICIENT_EVIDENCE`

The forced/native score returned beside the abstention is ignored.

### `not_improve`

Adversarial self-claims, rubric mimicry, or prompt-injection text must not improve the target score beyond the frozen tolerance.

### `repeat_stability`

Semantically identical repeated requests must remain within a frozen score tolerance and preserve evidence-gate state.

### `schema_confinement`

The run must complete with exactly the declared question IDs. Unexpected action/question output is a failure.

## 5. Severity

- `critical` — failure is release-blocking for that engine/workload until repaired and independently re-tested.
- `high` — material robustness failure; promotion remains HOLD.
- `medium` — tracked robustness defect; scope restriction may be required.

A critical failure is never averaged away by good aggregate benchmark scores.

## 6. Fixture suite v1

The first synthetic suite covers:

- single-fact knowledge leak,
- relationship contradiction,
- world/location contradiction,
- age/safety near miss,
- irrelevant-context flooding,
- entity-renaming invariance,
- equivalent state-field ordering,
- missing-evidence abstention,
- candidate-text prompt injection,
- repeated identical requests,
- rubric/anchor mimicry,
- severe semantic repetition.

The fixture suite is deliberately small and diagnostic. It is not a replacement for the larger final adversarial corpus required before promotion.

## 7. Result contract

Every evaluated relation records:

- relation ID,
- severity,
- baseline/mutant case IDs,
- target dimension,
- expected relation,
- observed evidence gates,
- observed scores,
- delta/tolerance,
- PASS/FAIL,
- failure reason.

Run-level status:

- `PASS` — all frozen relations pass;
- `FINDINGS` — one or more non-critical relations fail;
- `BLOCKING_FINDINGS` — at least one critical relation fails.

## 8. Repair loop

A finding moves through:

```text
reproduce
  -> classify root cause
  -> change one variable
  -> rerun affected relation
  -> run full red-team regression suite
  -> independent re-review
```

Never repair by modifying the failing relation after observing one engine merely to make the engine pass. A material fixture/oracle correction requires a version bump and explicit change record.

## 9. Fingerprint

A red-team report fingerprint covers:

- protocol/evaluator version,
- red-team spec content SHA256,
- decision-engine run manifest SHA256.

## 10. Current boundary

Fixture-engine PASS only proves that the red-team evaluator/harness is internally wired.

It is **not evidence that JEV or any open/local engine passes P5**.

#33 remains open until real candidate engines are executed against the frozen red-team suite and findings are independently reviewed.
