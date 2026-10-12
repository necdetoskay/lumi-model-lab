# Q25 / Q24 — Initial Seed vs. Terminal Candidate Comparison

**Status:** EXPERIMENTAL / SOURCE-BOUND / NOT ACCEPTED FINAL STORYSTATE
**PR:** #273 (Draft); **date:** 2026-10-12
**Frozen Q24 seed SHA256:** `777b2d432ad292a91d9390725d4fe03c2ad91e4d358c9e3dcc785ee0b1daeb88`
**Frozen Q24 prose SHA256:** `5c68a942aae7101ecd117e24e6c8a9495ffea58d4b55f65d0fa62ba2a83be9d4`

The original `story-proposal.json` is unchanged (historical annotation). This comparison uses the separately versioned `story-proposal-knowledge-extension.json`, reuses `property-proposal.json`, and recomputes the object/admission/story/property gates from frozen Q24 evidence. Its claims are neither model-extracted semantic truth nor an approved canonical state.

## Object changes — no inferred ownership

| Field | Seed | Candidate terminal | Evidence / disposition |
| --- | --- | --- | --- |
| `red_bookmark.found` | `false` | `true` | Nisa removes and holds the bookmark, 4085–4121; **candidate only** |
| `red_bookmark.container` | `blue_atlas` | proposed `reading_book` identity | Nisa places it in the reading book, 4769–4830; **structural candidate only** |
| `blue_atlas.contains` | `[red_bookmark]` | `[]` | Derived from the cited move into the reading book; **not independently certified** |
| `red_bookmark.returned_to_owner` | `false` | **UNASSESSED** | Physical recovery is explicit, but the property is not assigned by the existing terminal-property evidence fixture |
| Reading book `owner` | not in seed | **UNKNOWN** | Do not infer the owner from Nisa reading it |
| Reading book `location` | not in seed | **UNKNOWN** | No invented exact location |
| `red_bookmark.owner` | Nisa | Nisa (structural) | Ownership and physical placement are distinct |
| `world.time` | after school; 30 minutes to activity | **UNASSESSED** | Do not infer elapsed time or reset the clock |

The candidate reading-book ID is deterministic from seed, source and candidate mention; no canonical identity has been committed. Seed object properties copied into a structural draft are **not** certified terminal values.

## Character knowledge and goals

| Actor | Initial | Source-bound candidate | Evidence |
| --- | --- | --- | --- |
| Nisa | Did not know the bookmark's exact placement | `observed_bookmark_inside_blue_atlas` / OBSERVED | The bookmark is seen between atlas pages, 3957–4035 |
| Eren | Knew Nisa could not find the bookmark | `Cem_was_wrongly_suspected` / INFERRED | Eren says they accused Cem wrongly, 3520–3561 |
| Cem | Knew he did not take Nisa's bookmark | `Nisa_placed_bookmark_in_atlas` / REPORTED | Nisa explains it to him directly, 4141–4274 |
| Nisa | `worried` | `relieved` **candidate, interpretation unverified** | Nisa smiles, 4753–4768 |

Seed goals remain unchanged as identifiers; separate proposed outcomes are **ACHIEVED** for Nisa's search (4085–4121), Eren's assistance (4037–4083), and Cem's joining the reading activity (4916–4948). These do **not** assign new goals or change health, trust, other actors' emotions or locations without evidence. Unassessed fields remain visible in the coverage report.

## Obligations and open threads — candidate closure vs. disputed certification

| Initial OPEN obligation | Proposed outcome | Cited evidence | Adjudication |
| --- | --- | --- | --- |
| `investigate_evidence` | SATISFIED | Return-log entry 2132–2198; notebook 3028–3075 | PENDING |
| `recover_bookmark` | SATISFIED | Bookmark recovered 4085–4121 | PENDING |
| `correct_and_apologize` | SATISFIED | Two apologies 4361–4422, 4447–4530 | PENDING — no independent determination that the *without instant intimacy* constraint holds |

All three open threads (`find_missing_bookmark`, `explain_actual_placement`, `correct_suspicion`) have separately cited **RESOLVED candidates**, not certified closed facts.

**Independently certified closed obligations: none.** **Proposed closed: three.** **Still requiring adjudication: three.** A terminal quote matching the text is not proof that it semantically satisfies an obligation. The disputed historic review findings are not silently accepted as gold labels, and the Q24 historic rejection is unchanged.

## Explicit coverage gaps

The deterministic coverage audit now has 70 blocking entries: **12 CANDIDATE**, **3 PARTIAL_CANDIDATES**, **23 STRUCTURAL_ONLY**, **30 UNASSESSED**, **2 UNKNOWN**. This is a completeness/authority assessment, **not** 70 narrative errors. `PARTIAL_CANDIDATES` includes the three knowledge rows: cited additions cannot prove exhaustive knowledge. `UNKNOWN` covers the book owner/location. `UNASSESSED` includes `returned_to_owner`, character state not explicitly proposed and world time.

## Zero-cost read-only replay

```sh
python -m src.q25_state_coverage \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal-knowledge-extension.json \
  --property-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/property-proposal.json
```

The output includes `initial_to_candidate_comparison`, all individual `fields`, source hashes and `state_commit_authorized=false`. Offline CI tests assert the bookmark transition, missing return flag, original/new container, atlas contents, three source-bound character knowledge additions, all proposed/uncertified obligation outcomes, unknown book owner/location, and no seed mutation.

**Boundaries:** No model calls; no OpenRouter request; no paid story attempt; no production LUMI change; no historical Q24 overwrite; no acceptance/persistence; no merge. Existing PR remains Draft. Independent semantic adjudication, fuller terminal-state coverage and explicitly authorized canonical integration remain outside this free verification scope.
