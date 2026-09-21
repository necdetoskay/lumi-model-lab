# Decision Engine Benchmark v1 — Human-Gold Comparison Protocol

Status: **IMPLEMENTATION BASELINE / REFERENCE DATA INCOMPLETE**  
Owner: **LUMI Model Lab**  
Linked issue: **#32**  
Parent contracts: `DECISION_ENGINE_LAB.md`, `JEV_JUDGE_LAB.md`, `JUDGE_GOLD_CORPUS_PROTOCOL.md`, `JUDGE_ATOMIC_RUBRIC_V1.md`

## 1. Purpose

This protocol defines how JEV, open/local bounded decision engines, and the current stronger-LLM judge are compared against frozen human/reference truth.

The benchmark must not collapse distinct evaluation surfaces into one misleading score.

## 2. Two evidence lanes

### 2.1 Legacy verdict lane

The existing broad human story decision and current LLM-judge behavior may be compared as PASS/BLOCK evidence.

Allowed metrics include:

- confusion matrix,
- agreement,
- false-PASS,
- false-BLOCK,
- critical false-PASS,
- probability calibration when a comparable PASS probability exists.

This lane preserves compatibility with historical judge evidence. It does not grant a bounded decision engine an aggregate story verdict.

### 2.2 Atomic decision-engine lane

Bounded engines are evaluated per atomic rubric dimension.

Required metrics:

- exact agreement,
- adjacent agreement,
- mean absolute error on the native score,
- quadratic weighted kappa where defined,
- per-dimension case count,
- per-dimension high-confidence error inventory.

When native score-level probabilities are available:

- multiclass Brier score,
- reference-label log loss,
- expected calibration error,
- selective risk / coverage curve,
- area under the risk-coverage curve.

No aggregate PASS/BLOCK is derived from atomic scores in P4.

#34 owns later cascade/routing policy.

## 3. Reference readiness

Quality metrics are emitted only for cases with a complete final human/reference label required by the lane.

For the atomic lane, a reference case requires:

- `human_reference.status = final`,
- `atomic_scores` for every dimension being evaluated,
- each atomic score in 0–4.

If reference evidence is incomplete, the benchmark must return:

`REFERENCE_INCOMPLETE`

It may still report operational evidence such as runtime failures and latency, but it must not manufacture quality metrics.

## 4. Partition policy

Default benchmark work uses calibration or development holdout.

The immutable final holdout is protected from accidental use.

A final-holdout benchmark requires an explicit final-evaluation flag. Before the actual qualification run, thresholds/policies must already be frozen under #34.

## 5. Same-corpus rule

Engines compared in one quality table must evaluate the same frozen case IDs and semantic question set.

Missing engine cases are reported as missing coverage, not silently removed from the reference set.

Malformed outputs and runtime/provider failures are quality-system failures and remain visible in coverage/error summaries.

## 6. Score-point semantics

Atomic reference scores are integers 0–4.

An engine may return a fractional score.

For exact/adjacent classification metrics, the engine score is rounded to the nearest integer and clipped to the rubric range.

For mean absolute error, the native fractional score is retained.

This prevents a native probabilistic score from being prematurely discarded.

## 7. Probability semantics

Provider-native values are preserved.

For score distributions:

- probability keys correspond to score-level indices;
- the benchmark does not renormalize provider output;
- incomplete/invalid distributions are omitted from probability metrics and reported.

For separate provider confidence statistics:

- they are stored as native confidence evidence;
- they are not assumed to be calibrated probabilities;
- they are not silently substituted for a missing probability distribution.

## 8. Calibration metrics

### Multiclass Brier

For K score levels:

`sum_k (p_k - y_k)^2`

averaged across cases with complete native distributions.

### Log loss

`-log(p_reference_level)`

with numerical clipping only for calculation safety; stored provider probabilities are never rewritten.

### ECE

ECE uses the maximum native score-level probability as confidence and exact rounded-score correctness as the binary correctness target.

The report records the bin count.

### Selective risk

Cases are ordered from highest to lowest usable confidence.

At each coverage prefix:

`risk = 1 - exact_accuracy`

The area under the risk-coverage curve is reported as the mean prefix risk for v1.

This v1 definition is frozen for reproducibility.

## 9. Critical false-PASS

Critical false-PASS remains a hard Judge safety concept.

P4 must not infer “critical pass” merely from a high atomic average.

A critical false-PASS metric is valid only when the evaluated workload has an explicit bounded PASS/BLOCK decision against a human critical label.

Atomic dimension results feed later cascade design but do not redefine this hard gate.

## 10. Operational evidence

Every engine report also records, when exposed:

- requested/resolved engine identity,
- case coverage,
- malformed-output count,
- runtime/provider-error count,
- latency p50/p95,
- usage,
- cost,
- request/state size.

Full cascade economics remain #34’s responsibility.

## 11. Benchmark fingerprint

A benchmark fingerprint covers:

- benchmark implementation version,
- gold manifest content SHA256,
- rubric content SHA256,
- selected partition,
- final-evaluation flag,
- every engine run manifest SHA256.

Intentional reruns create separate report artifacts; source inputs remain immutable.

## 12. Current status

The benchmark implementation may be exercised with synthetic unit fixtures.

The current real Judge Gold Corpus remains:

- structurally valid,
- only 30/100 cases materialized,
- 0 final human labels.

Therefore no real JEV-vs-human quality result is currently authorized.

The correct real-corpus status remains:

`REFERENCE_INCOMPLETE`
