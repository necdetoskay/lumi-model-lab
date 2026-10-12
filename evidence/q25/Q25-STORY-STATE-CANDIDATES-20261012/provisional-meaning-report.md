# Q24 — Provisional meaning review of 11 source-bound terminal-state gaps

**Date:** 2026-10-12 · **Branch:** `experiment/q25-narrative-memory-intent` · **PR:** #273
**Scope:** Q24 frozen prose/seed only. No new story, model call, paid extractor, architecture redesign or production write.

## What this DOES and does NOT establish

The existing coverage audit distinguished 70 fields that could not be certified at the story end. The previous 11-item worklist attached exact source evidence. This change adds an **explicit provisional interpretation** to each issue, without pretending that Codex-authored interpretations are authenticated independent adjudication.

Each `provisional-meaning-assessment.json` row contains: an issue ID, one of six **non-authoritative** meaning categories, indices into the already hash-verified supporting/competing prose spans, the directly observable subevent, and an explanation of why final state certification is still blocked. `src/q25_provisional_review.py` replays the complete unchanged Q25 Q24 source-bound coverage and rejects mismatches, unknown/duplicate/missing issues, out-of-range/duplicate reference indices, injected authority fields or unadmitted entities. The original Q24 text, rejection, seed and archived proposal files are unchanged.

## Provisional assessments (not semantic-certified findings)

| Issue | Provisional reading | What is still open |
| --- | --- | --- |
| `bookmark_return_semantics` | **CONTEXT_DEPENDENT** — Nisa recovers and then reuses the bookmark | Whether self-recovery constitutes `returned_to_owner`; `false → true` is a cited *candidate*, not final truth |
| `apology_without_instant_intimacy` | **CONTEXT_DEPENDENT** — both apologies stated, Cem still hurt, later rejoins | Whether the complete no-instant-intimacy obligation is satisfied |
| `nisa_relief_from_smile` | **NOT_ENTAILED** — Nisa smiles | `relieved` is a possible interpretation, not a unique terminal-emotion fact |
| `cem_trust_not_equivalent_hurt` | **UNDETERMINED** — Cem is hurt, later participates | No justified unique final trust value |
| `elapsed_world_minutes` | **UNDETERMINED** — half-hour reference | No precise terminal world time or earned minutes elapsed |
| `cem_reported_knowledge` | **PARTIAL_REPORT** — Nisa directly informs Cem | Distinguish hearing a report from independently verifying its contents; whole knowledge set incomplete |
| `reading_book_owner` | **UNDETERMINED** — Nisa uses a reading book | No ownership evidence; stays UNKNOWN |
| `reading_book_location` | **UNDETERMINED** — book is used in the scene | No independent admitted canonical terminal location; stays UNKNOWN |
| `nisa_knowledge_completeness` | **PARTIAL_OBSERVATION** — written note then physical bookmark discovered | Additional knowledge candidates do not establish exhaustive terminal knowledge |
| `atlas_shelf_terminal` | **DIRECT_EVENT_CANDIDATE** — the atlas is put back on a shelf | Exact retained `stored_at` value not independently certified by a seed copy |
| `suspicion_thread_scope` | **CONTEXT_DEPENDENT** — accusation corrected; hurt persists | Closing wrongful suspicion need not imply restored emotional trust |

The labels are **author-authored triage descriptions**, not independently established truth. A directly reported subevent can be source-quoted without warranting a particular end-state property value.

## Measured accounting, with all gaps visible

- **11/11** existing targeted issues have a provisional interpretation; **59** other fields remain untriaged.
- Entire coverage remains **70 unresolved field assessments**: 13 `CANDIDATE`, 3 `PARTIAL_CANDIDATES`, 23 `STRUCTURAL_ONLY`, 29 `UNASSESSED`, 2 `UNKNOWN`.
- **3** narrative obligations have `SATISFIED` proposals; **0** have an independent semantic closure certificate. All three remain under review.
- The `initial_to_candidate_comparison` survives intact and includes both `red_bookmark.found: false → true` and `red_bookmark.returned_to_owner: false → true` as *candidates*. No overwrite of seed booleans.
- No new goals, emotion certainty, relationship trust, location or world time are invented. No automatic story-extraction accuracy claim.

## Zero-cost deterministic replay

From repository root, using Python 3.11, pytest, Pydantic 2.x:

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

python -m pytest -q tests/test_q25_provisional_review.py
```

The CLI writes JSON to stdout only and includes selected verbatim cited spans, every untriaged field, complete initial/terminal candidate diff and explicit `independent_review=NOT_PERFORMED` for all 11 rows. Negative tests cover misbound or stale fingerprints and forged/incomplete inputs. The overall Q25 offline workflow also runs these tests without OpenRouter credentials.

**All authoritative output fields remain false:** `semantic_support_certified=false`, `full_story_state_qualified=false`, `state_commit_authorized=false`, `provider_calls=0`; Q24's original rejection is unchanged. PR remains Draft and is not eligible for production promotion on the basis of these annotations.

## Next necessary qualification (not part of this change)

An independently verified reviewer must adjudicate both supporting and contradictory context, including the meaning of `returned_to_owner`, the full apology obligation, and unobserved terminal fields. Neither the provisional notes nor an all-green unit test substitutes for those decisions. Any later new/unseen-story automatic extractor benchmark and production state integration are separate, explicitly gated work.
