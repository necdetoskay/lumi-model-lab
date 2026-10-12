# Q25 / Q24 — Exhaustive 70-Field Initial State vs. Terminal Candidate Matrix

Date: 2026-10-12
PR: [#273](https://github.com/necdetoskay/lumi-model-lab/pull/273) (Draft)
Status: **OFFLINE, UNTRUSTED CANDIDATES / INCOMPLETE STORYSTATE / ZERO CANONICAL AUTHORITY**

## Concrete improvement

Previously 11 of 70 terminal-state coverage fields had source-quoted, provisional *meaning* assessments while the remaining 59 appeared as an index of unresolved paths. Existing `src/q25_provisional_review.py` now emits `full_field_matrix` with **exactly one row for every one of the 70 coverage fields**. This is deterministic *mechanical accounting*, **not an additional 59 semantic reviews**.

Each row includes:

- `path`, category, source coverage status, and the original coverage note.
- `seed_snapshot` with an explicit `PRESENT` value or `NOT_IN_INITIAL_SEED`. Absence is never represented as `false`, `null` or an inferred new owner.
- `terminal_hypothesis`: a source-bound proposed change, partial knowledge addition, separate goal/obligation/thread outcome, explicit new-entity UNKNOWN, or `NO_TERMINAL_VALUE_PROPOSED`. In particular, a copied initial value **is not represented as a proven final value**.
- Previously collected exact supporting/competing citations for one of the 11 pre-assessed issues. Other fields are explicitly `NOT_INDIVIDUALLY_SEMANTICALLY_TRIAGED`.
- Mechanical `required_next_action`, `independently_certified=false` and `terminal_value_committable=false`.

## Coverage accounting

| Category | Coverage fields | Provisional individual assessments | Not individually reviewed |
| --- | ---: | ---: | ---: |
| CANDIDATE | 13 | 4 | 9 |
| PARTIAL_CANDIDATES | 3 | 2 | 1 |
| STRUCTURAL_ONLY | 23 | 0 | 23 |
| UNASSESSED | 29 | 3 | 26 |
| UNKNOWN | 2 | 2 | 0 |
| **Total** | **70** | **11** | **59** |

**Both groups still block final-state certification.** This is not a 70-item list of story contradictions; it is a strict, deliberately conservative *verification-completeness* inventory.

## Material distinctions enforced by the matrix

| Path | Seed snapshot | Terminal hypothesis | Required interpretation |
| --- | --- | --- | --- |
| `/objects/red_bookmark/properties/found` | `false` | `true` **candidate** | Semantic check of the witnessed recovery |
| `/objects/red_bookmark/properties/returned_to_owner` | `false` | `true` **candidate** | Define whether self-recovery counts as return |
| `/objects/red_bookmark/container` | `blue_atlas` | Proposed reading-book identity | Independent check before admitting the new object |
| `/objects/blue_atlas/contains` | `[red_bookmark]` | `[]` **candidate** | Verify the terminal reciprocal contents |
| `/objects/blue_atlas/owner` | `library` | **NO_TERMINAL_VALUE_PROPOSED** | Seed owner is not a certified terminal-owner observation |
| New reading book `owner` | **NOT_IN_INITIAL_SEED** | **EXPLICIT_UNKNOWN_NEW_ENTITY_FIELD** | Do not invent ownership |
| `/characters/Cem/relationships/Nisa/trust` | `good` | **NO_TERMINAL_VALUE_PROPOSED** | Cem's lingering hurt does not yield a unique final trust value |
| `/characters/Nisa/knowledge` | Initial fact list | **PARTIAL_EPISTEMIC_ADDITIONS** | Known acquisitions do not prove exhaustive knowledge |
| `/characters/Cem/condition/goal` | `join_reading_activity` | **ACHIEVED outcome only** | Do not pretend a new character goal was established |
| `/narrative_obligations/correct_and_apologize/status` | `OPEN` | **SATISFIED candidate only** | The full no-instant-intimacy condition remains under review |
| `/world/time` | after school, 30 minutes remaining | **NO_TERMINAL_VALUE_PROPOSED** | Do not invent duration or reset the clock |

The old source, seed, manually annotated candidates, policy and historical rejection are unchanged. All results remain draft-only and cannot be written to canonical StoryState.

## Free replay

```sh
python -m src.q25_provisional_review \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal-knowledge-extension.json \
  --property-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/property-proposal-return-candidate.json \
  --annotations evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/review-gap-annotations.json \
  --assessments evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/provisional-meaning-assessment.json
```

Read `full_field_matrix` (70 entries), `full_field_matrix_summary` (11 author-draft vs. 59 untriaged, zero certified/committable) and `initial_to_candidate_comparison` from stdout. It creates no files or API requests. The Q25 no-credential offline GitHub Actions suite covers deterministic replay, immutable seed, distinction between initial values vs candidates, explicit UNKNOWN, and fail-closed forged/invalid source cases.

Code/test CI: [#38261487149](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38261487149) **221/221 PASS** at `da01cc1`; the paid extractor job is **SKIPPED**. Provider calls: **0**; incremental API spend: **$0**.

## Real remaining blocker

The matrix makes field coverage auditable, but it cannot decide whether every quote entails a correct **terminal** state, whether unmentioned properties persist, or whether `correct_and_apologize` has satisfied its full narrative contract. It also cannot authenticate an independent reviewer or grant a state commit. An actual semantic adjudication plus an explicit field-completeness policy is still needed. **There is no accepted Q24 final StoryState yet.** No auto-extraction, new story run, merge, canonical persistence or production change was attempted.
