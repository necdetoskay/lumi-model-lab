# Q25 / Q24 — Offline terminal-state semantic review worklist

Date: 2026-10-12
PR: [#273](https://github.com/necdetoskay/lumi-model-lab/pull/273) (Draft)
Status: **UNTRUSTED SOURCE-BOUND ANNOTATIONS / ALL REVIEWS PENDING / NO STATE COMMIT**

## Why this exists

A contiguous, hash-bound quotation is necessary provenance, **not** proof that a claim is correct, semantically entailed, terminal, or narratively sufficient. The Q24 saved story has a structurally replayable terminal candidate, but actual final-state certification requires independent assessment. This is an **offline worklist added to the existing Q25 coverage gate**, not a new story-generation architecture or a model judge.

The historical Q24 seed/prose, initial property/story proposals, Q24 rejection and older artifacts are unchanged. The earlier `seed-terminal-comparison-report.md` remains the baseline. Two **new, separate, versioned** inputs record extra testable candidates:

- `property-proposal-return-candidate.json`: `red_bookmark.found false→true` and `returned_to_owner false→true` are **proposals**. Nisa retrieving the bookmark and placing it in her reading book are quoted at 4085–4121 and 4769–4830. Whether self-recovery qualifies as `returned_to_owner` is an explicit reviewer question. No canonical property is changed.
- `review-gap-annotations.json`: eleven reviewer questions, each bound to exact seed/prose/story/property hashes and cited full-story spans. The existing `story-proposal-knowledge-extension.json` remains the source for Nisa/Eren/Cem epistemic candidates.

## Latest candidate coverage (not a pass rate)

| Field status | Count |
| --- | ---: |
| CANDIDATE | 13 |
| PARTIAL_CANDIDATES | 3 |
| STRUCTURAL_ONLY | 23 |
| UNASSESSED | 29 |
| UNKNOWN | 2 |
| **Still blocking final-state certification** | **70** |

**11 fields have an explicit review issue**, and **59 other fields remain untriaged, not silently approved**. Candidate means syntactically and quote-bound *only*. Two UNKNOWN slots are the proposed reading book's owner and location. Initial world clock, exhaustive character knowledge and many copied properties remain unassessed.

## High-priority semantic questions

| Field/claim | What the source establishes | Still unverified |
| --- | --- | --- |
| `red_bookmark.returned_to_owner` | Nisa retrieves and uses the bookmark | Does returning to an owner include self-recovery? |
| `correct_and_apologize` | Both friends explicitly apologize | Does Cem's hurt followed by joining Nisa respect the **without instant intimacy** clause? |
| `Nisa.condition.emotion` | Nisa smiles | Does this entail relieved, or only an observed smile? |
| `Cem.relationships.Nisa.trust` | Cem says he was hurt, then sits beside Nisa | This does not fix a numeric/symbolic trust level |
| `Cem.knowledge` | Nisa tells Cem she placed the bookmark | Reported fact vs belief, and exhaustive terminal knowledge |
| `world.time` | Another mention of half an hour | Precise elapsed time at the end is not established |
| `blue_atlas.state.stored_at` | Nisa places the atlas back on a shelf | Whether copied initial storage value is independently certified |
| `correct_suspicion` | False suspicion is explicitly addressed | Closing the suspicion is not equivalent to full emotional reconciliation |

Reading book ownership and precise location remain UNKNOWN; Nisa's terminal knowledge remains PARTIAL_CANDIDATES. The worklist includes their evidence and no invented values.

The three initial OPEN narrative obligations retain **three SATISFIED candidates** and **zero independently certified closures**. All three are still pending semantic evaluation. The three story threads have RESOLVED candidates, not approved final-state facts.

## Exact free replay

Run from the repository root, with Python 3.11, `pydantic>=2.8,<3` and pytest:

```sh
python -m src.q25_review_worklist \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal-knowledge-extension.json \
  --property-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/property-proposal-return-candidate.json \
  --annotations evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/review-gap-annotations.json

python -m pytest -q tests/test_q25_review_worklist.py
```

Output `q25.review-gap-worklist.v1` includes the full `initial_to_candidate_comparison`, every explicit review issue and every untriaged field; there is no write option. Each replay recomputes Q25 entity admission, story evidence, property checks and exhaustive coverage. Wrong seed/prose/claim-set fingerprints, forged quotes, unknown fields, duplicate target/issue IDs, missing evidence, invalid issue types, forged commit or verdict fields, decisive clues, and modified seed fail closed.

All results hardcode: `review_decision=PENDING_INDEPENDENT_ADJUDICATION`, `semantic_support_certified=false`, `state_commit_authorized=false`, `provider_calls=0`. This is an engineered review packet, **not independent human adjudication**. Historic Q24 REJECT remains intact. No OpenRouter, paid story, production deployment, merge, or model extraction trial is part of this change.
