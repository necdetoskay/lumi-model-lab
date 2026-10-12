# Q25 — Terminal State Reconciliation V1 (Offline Experimental)

**Status:** implemented, read-only, structurally checked, **NOT approved Final StoryState**  
**Date:** 2026-10-12  
**Branch/PR:** `experiment/q25-narrative-memory-intent`, [#273](https://github.com/necdetoskay/lumi-model-lab/pull/273) (Draft)  
**Production LUMI:** untouched.

## Purpose and boundary

The Q25 experiment already discovers source-bound object, property, character, goal, narrative obligation and thread **candidates** from a frozen story and compares them against its frozen seed. It does not yet demonstrate a reliable automatic extractor or independent semantic proof.

`src/q25_terminal_reconciler.py` is a deterministic, zero-provider-call **candidate-only** reconciliation step on top of the existing admission, story evidence, property, coverage and provisional-review gates. It never claims that the story has been accepted or that candidate fields are ready for canonical state persistence.

The reconciler returns **`q25.terminal-reconciliation-candidate.v1`**, not the production StoryState contract. It is a *possible terminal interpretation with explicit unresolved authority*, not a signed/mutable state.

## Preservation rules — no silent promotion

Every one of the 70 Q24 fields has a source-bound or seed-bound explanation and `reconciliation_policy`:

| Rule | Meaning |
| --- | --- |
| `UNVERIFIED_TERMINAL_CANDIDATE` | A source-quoted, structurally admitted proposed change/outcome; not semantic approval |
| `STRUCTURAL_SEED_OR_PROPOSED_RELATION_ONLY` | Existing/derived relation is consistent with the graph; not independently terminal-certified |
| `HISTORICAL_SEED_FACT_UNVERIFIED_AT_TERMINAL` | A descriptive or historical seed fact (e.g. color, notebook author) may remain a reference, never proof of unchanged terminal state |
| `UNASSESSED_DO_NOT_INFER_UNCHANGED` | No evidence-backed candidate was supplied; do **not** copy the seed as an accepted final fact |
| `PARTIAL_KNOWLEDGE_CANDIDATE` | A knowledge addition has a source/epistemic class; exhaustive knowledge is unverified |
| `UNKNOWN_REQUIRES_EVIDENCE` | New entity owner/location is explicitly unknown, not null and not inferred from use |
| `UNADMITTED_OBJECT_IDENTITY` | Ordinary-object candidate is distinct from a canonical entity identity |

Only a descriptive/historical whitelist (`color`, `author`, `entry_day`, `entry_text`, `placed_by`, `returned_by`) gets a tagged historical seed reference. Neither this classification nor an exact quotation grants final-state truth. The remaining unassessed fields stay unassessed, including terminal emotion, health, directed relationship trust, world clock and copied relationship state.

A character's initial goal remains the seed goal identifier. An achievement candidate appears **separately** as an outcome, not an invented replacement goal. Character knowledge holds original facts and proposed epistemic additions separately. Existing character inventory is checked against graph-held objects, not freely updated from an untrusted character claim.

## Reconciliation and coherence

The offline flow is:

```text
Frozen seed + complete story prose + hash-bound proposals
    |
    v
Q25 object admission -> evidence extensions -> terminal properties
    |
    v
70-field coverage -> 11 provisional reviews + 59 untriaged fields
    |
    v
Terminal Reconciler (read-only)
    |- candidate objects and reciprocal containment
    |- object property initial_value vs proposed_terminal_value
    |- character facts vs unverified knowledge/scalar/goal claims
    |- open obligation/thread proposals (never certified closure)
    |- time and unknown owner/location left unresolved
    |- field policy and full provenance, no missing-field acceptance
    |
    v
COHERENT_UNVERIFIED_TERMINAL_HYPOTHESIS
State commit = FALSE; semantic certified = FALSE
```

The reconciler recomputes the upstream admission, checks seed/prose/review lineage and explicitly validates:

1. Every `KNOWN` object relation has a typed target; every `NONE/UNKNOWN` relation has no forged target.
2. No object is inside a container while directly held by an actor.
3. Every object's `container` agrees reciprocally with its container's `contains`.
4. No duplicate content membership, self containment or containment cycle.
5. Known object locations are within the existing approved topology.
6. Directly held objects match character inventory exactly.
7. Exactly **70** source coverage fields have field decisions; every decision remains noncommittable.

This proves *structural consistency under candidate assumptions*. It does **not** prove a quoted inference is true, that all narrative events were extracted, or that all inherited facts survived.

## Frozen Q24 replay result

- Red bookmark: `found false → true` is a **change candidate**; `returned_to_owner false → true` remains **context-dependent candidate**, not asserted truth.
- It is **proposed** inside the newly identified reading book. The blue atlas **proposed** contains list is empty; neither Nisa nor anyone else directly holds the bookmark at the terminal moment.
- Reading book remains `PROPOSED`, with `UNKNOWN` owner and location; Nisa's use does **not** imply ownership.
- Known blue-atlas owner `library` stays a **seed-derived structural reference**, not a newly certified final owner.
- No world-time estimate, inferred trust score, emotional certainty or new goal is written.
- Three obligations have proposed `SATISFIED` outcomes; **0 are independently certified closed**. `correct_and_apologize` remains under review concerning the no-instant-intimacy condition.
- All 70 field decisions are pending validation. Earlier 11 author-draft interpretations and 59 untriaged fields remain identifiable.

## Reproduce — zero cost, no output file written

From the repository root:

```sh
python -m src.q25_terminal_reconciler \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal-knowledge-extension.json \
  --property-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/property-proposal-return-candidate.json \
  --annotations evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/review-gap-annotations.json \
  --assessments evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/provisional-meaning-assessment.json

python -m pytest -q tests/test_q25_terminal_reconciler.py
```

The command only prints JSON to stdout. The canonical story seed/prose and all source proposals remain byte-for-byte unchanged. The full existing Q25 offline GitHub workflow runs the reconciler test suite without an API key. CI after initial implementation: [#38264156148](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38264156148), **243/243 PASS**; `paid-extractor-pilot` SKIPPED. API calls and incremental spend: **0 / $0**.

## What this does not solve

- Semantic correctness of each candidate, including `returned_to_owner` semantics and relationship/obligation closure.
- **Extractor completeness/recall** on unseen prose, since Q24 has manual annotation fixtures.
- Independently authenticated semantic adjudication or canonical state admission.
- A production-ready StoryState with explicit certified values for every required field.

**Next gate:** preserve this reconciler as an experimental candidate boundary, run a separately authorized bounded extractor on an unseen story, evaluate false positives and omissions against independent human judgment, then—only if reliable—design canonical commit authority. No production cutover, paid job dispatch or merge occurs here.
