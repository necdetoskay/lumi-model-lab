# Needle 3 U1 — Story State Delta Extraction Contract v1

Status: **FROZEN STRUCTURE / DATASET PENDING**  
Parent canon: `NEEDLE3_UTILITY_SLM_QUALIFICATION.md`  
Epic: #77  
Corpus issue: #80  
Benchmark issue: #81

## 1. Task statement

Given:
1. a finished story;
2. bounded pre-story state/context;
3. a supplied set of known canonical IDs/aliases;

produce **candidate state deltas supported by evidence in the story**.

The extractor does not decide whether a candidate is canonically committed.

## 2. Input contract

A v1 case contains at least:

```json
{
  "case_id": "u1-...",
  "schema_version": "needle3-u1-input.v1",
  "language_variant": "tr_native",
  "pre_state_fingerprint": "sha256:...",
  "story_text": "...",
  "known_entities": [
    {
      "canonical_id": "char_or_npc_id",
      "type": "character|npc|item|location|thread",
      "aliases": ["..."]
    }
  ],
  "bounded_pre_state": {
    "inventory": [],
    "relationships": [],
    "known_locations": [],
    "open_threads": []
  }
}
```

The bounded context must include only evidence needed for the fixture. Full production state is neither required nor desirable.

## 3. Output contract

A normalized v1 result:

```json
{
  "schema_version": "needle3-u1-output.v1",
  "evidence_status": "SUFFICIENT|INSUFFICIENT",
  "candidates": [
    {
      "kind": "ITEM_ACQUIRED",
      "subject_ref": "known-id-or-null",
      "object_ref": "known-id-or-null",
      "unresolved_mention": null,
      "proposed_change": {},
      "evidence": {
        "text": "...",
        "start": 0,
        "end": 0
      },
      "confidence": 0.0
    }
  ]
}
```

Notes:
- `confidence` is optional when the runtime does not expose a comparable value.
- unknown entities must remain unresolved mentions; the model must not invent canonical IDs.
- empty `candidates` is valid for a no-change case.
- `INSUFFICIENT` is valid when evidence is materially inadequate.

## 4. Candidate kinds v1

Initial bounded set:
- `ITEM_ACQUIRED`
- `ITEM_LOST`
- `ITEM_CHANGED`
- `NPC_INTRODUCED`
- `RELATIONSHIP_CHANGED`
- `LOCATION_DISCOVERED`
- `THREAD_OPENED`
- `THREAD_ADVANCED`
- `THREAD_CLOSED`
- `SAGA_BREADCRUMB_CANDIDATE`

New kinds require a schema/version change.

## 5. Evidence rule

Every non-empty candidate must be traceable to supplied story evidence.

The extractor must distinguish:
- event happened;
- event did not happen;
- event might happen;
- event was imagined;
- event was quoted/reported by someone;
- event was planned;
- event is ambiguous.

A mention is not automatically a state change.

## 6. Canonical-ID rule

The model may reuse a canonical ID only if that ID was supplied in the input.

If a story introduces a new entity that has no supplied ID:
- `*_ref` remains null;
- the raw mention is retained in `unresolved_mention`;
- later deterministic/entity-resolution logic decides identity.

Invented IDs are a hard extraction error.

## 7. No-change semantics

A valid no-change output is:

```json
{
  "schema_version": "needle3-u1-output.v1",
  "evidence_status": "SUFFICIENT",
  "candidates": []
}
```

The model must not manufacture deltas merely to avoid an empty result.

## 8. Deterministic post-validation

Before any candidate is considered usable evidence, deterministic validation checks:
- schema;
- candidate kind allowlist;
- supplied-ID membership;
- required evidence fields;
- evidence span bounds;
- duplicate candidates;
- impossible field combinations;
- numeric/enum validity.

Failure means reject/repair/escalate, never canonical commit.

## 9. Corpus families

#80 must freeze examples for:
- no change;
- clear acquisition/loss;
- NPC introduction;
- relationship change;
- location discovery;
- thread state change;
- Saga breadcrumb;
- multi-delta;
- negation;
- double negation;
- hypothetical/conditional;
- quotation/reporting;
- plan/intention;
- ambiguous implication;
- conflicting evidence;
- false mention;
- unsupported-ID lure;
- long story with one relevant delta;
- irrelevant-context flood.

## 10. Reference labels

Reference truth must identify:
- expected candidates;
- explicitly forbidden/unsupported candidates;
- ambiguity status;
- evidence span/text when practical;
- criticality class.

Synthetic teacher output is never automatic ground truth.

## 11. Evaluation

Per candidate kind and overall:
- precision;
- recall;
- F1;
- exact structured match where meaningful;
- unsupported candidate rate;
- omission rate;
- no-change accuracy;
- canonical-ID fabrication rate;
- evidence correctness;
- ambiguity/abstention accuracy.

Language variants are reported separately.

## 12. Critical failures

Critical examples include:
- invented canonical ID;
- converting explicit negation into a positive state change;
- converting a hypothetical/planned event into a completed event;
- extracting a high-confidence unsupported critical delta;
- schema-valid but semantically unsupported output that would corrupt state if trusted.

Critical failure thresholds are frozen before final-holdout evaluation.

## 13. Dataset isolation

Use separate partitions for:
- calibration;
- development holdout;
- protected final holdout.

Training data for P6 must not contain final-holdout cases or source-family derivatives.

## 14. Production non-authority

This contract defines a **candidate extraction** experiment only.

No output from this workload can mutate Project_LUMI state without a separate production architecture and deterministic commit path approved under AEGIS L3.
