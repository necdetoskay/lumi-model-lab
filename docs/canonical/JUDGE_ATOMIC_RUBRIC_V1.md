# Judge Atomic Rubric v1 — Decision-Engine Qualification Contract

Status: **FROZEN STRUCTURE / CALIBRATION PENDING**  
Owner: **LUMI Model Lab**  
Linked issue: **#31**  
Parent contracts: `JEV_JUDGE_LAB.md`, `DECISION_ENGINE_LAB.md`, `JUDGE_GOLD_CORPUS_PROTOCOL.md`

## 1. Purpose

This contract decomposes broad story-quality judgment into bounded, independently testable questions.

The goal is not to teach a decision engine to answer:

> Is this a good story?

The goal is to determine whether a bounded engine can reliably answer narrow semantic questions while deterministic code retains exact invariants and a stronger LLM retains deep literary judgment.

## 2. Responsibility split

### Deterministic-only

Do not delegate these merely to increase decision-engine coverage:

- schema validity,
- missing required fields,
- exact word-count/tolerance,
- truncation / finish reason,
- exact ID and enum membership,
- exact inventory membership,
- exact graph/reachability facts when data is available,
- revision / CAS / idempotency,
- explicit safety rules that can be encoded deterministically.

### Decision-engine candidates

Atomic bounded evaluation is allowed for:

- contract alignment,
- character consistency,
- world/state semantic consistency,
- opportunity relevance,
- character agency,
- semantic repetition,
- age fit,
- relationship consistency,
- knowledge consistency.

### Hybrid candidates

Decision-engine evidence may contribute, but a stronger judge may remain authoritative for:

- narrative progression,
- ending quality.

### Strong-LLM retained

The current version retains strong-model ownership for:

- creativity,
- literary/style quality,
- deep holistic coherence requiring multi-hop interpretation,
- novel ambiguity that does not fit the frozen atomic rubric.

No benchmark result transfers ownership automatically. #34 owns cascade policy.

## 3. Atomicity rule

Every decision-engine question must:

- evaluate one semantic property;
- have an explicit bounded answer space;
- be labelable by a human without knowing machine output;
- expose uncertainty/escalation when evidence can be insufficient;
- avoid combining quality, safety, and style into one score.

A rubric item that repeatedly needs “it depends on several unrelated things” must be split before final holdout.

## 4. Score semantics

All ordinal atomic score questions use **0–4**, ordered worst → best.

This differs from the historical LLM judge’s 1–5 presentation but does not alter human truth labels. Mapping is analytical, not a rewrite of historical records.

Generic interpretation:

- 0 — clear/major violation,
- 1 — substantial problem,
- 2 — mixed/borderline,
- 3 — good/minor weakness,
- 4 — strong/clean evidence.

Dimension-specific level text in `judge_atomic_rubric_v1.yaml` is authoritative.

The engine is evaluated on its native fractional/ordinal output where applicable; thresholds are not frozen until calibration.

## 5. Critical dimensions

The following can contain critical false-PASS cases:

- contract alignment,
- world/state consistency,
- age fit / safety,
- relationship consistency,
- knowledge consistency.

A high score from an engine does not erase deterministic evidence or a known critical violation.

Critical false-PASS remains a hard qualification blocker under #27.

## 6. Synthetic anchors

Each atomic dimension contains three compact anchor definitions:

- bad,
- borderline,
- good.

These are **dedicated synthetic descriptions**, not final-holdout examples and not model-generated truth.

Anchors exist to stabilize interpretation; they must not become a large few-shot corpus.

If empirical calibration shows an anchor is misleading, change it only through a rubric version bump before final holdout.

## 7. Language variants

The same semantic rubric is represented in three experiment lanes.

### Variant A — TR_NATIVE

- Turkish source/candidate;
- Turkish instructions;
- Turkish score-level descriptions.

### Variant B — EN_REFERENCE

- independently available English representation;
- English instructions and levels;
- only cases whose English representation is independently frozen may enter this lane.

Variant B must not be created by silently translating a final-holdout Turkish case after seeing model errors.

### Variant C — CONTROLLED_EN_PROJECTION

- Turkish source remains authoritative;
- a controlled English semantic projection is produced before evaluation;
- English rubric is used.

The projection must preserve:

- IDs,
- enums,
- names/entities,
- numbers,
- chronology,
- negation,
- uncertainty,
- known/unknown distinctions,
- relationship direction,
- inventory/state facts.

Projection drift is a measured failure class.

## 8. Projection output contract

Controlled projection must produce:

```json
{
  "projection_version": "controlled-en-projection-v1",
  "source_case_id": "...",
  "structured_facts": {},
  "candidate_semantic_representation": "...",
  "preservation_checks": {
    "ids": true,
    "numbers": true,
    "chronology": true,
    "negation": true,
    "uncertainty": true
  }
}
```

A projection with failed preservation checks is not submitted to the decision engine; it is classified as projection failure.

## 9. Aggregation prohibition

P3 does not define a single “story score” or PASS/BLOCK formula for decision-engine outputs.

Per-dimension evidence is retained independently.

The later cascade-policy stage (#34) may derive routing rules only after:

- blind human calibration,
- per-dimension error analysis,
- critical false-PASS analysis,
- confidence calibration.

## 10. Fingerprint

A rubric experiment fingerprint must include:

- `rubric_id`,
- `rubric_version`,
- exact YAML content hash,
- language variant,
- projection version where applicable,
- case corpus fingerprint,
- engine identity/revision,
- threshold policy version.

## 11. Current status

Rubric structure and synthetic anchor definitions are frozen as v1.

It is **not yet empirically calibrated**.

#31 remains open until:

- calibration labels are sufficiently complete,
- anchor wording is checked against calibration examples,
- TR/EN/projection lanes are exercised,
- no material rubric repair remains before final holdout.
