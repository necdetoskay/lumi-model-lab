# Q25 Terminal Supplement V1 — Explicit Countdown and Physical Attachment/Covering

**Date:** 2026-10-12  
**Status:** read-only experimental sidecar; 100% **non-canonical**.  
**Implementation:** `src/q25_terminal_supplement.py`, `tests/test_q25_terminal_supplement.py`.  
**Scope:** previously frozen Sonnet responses and their **separately authored** evidence annotations. No model/API calls, acceptance, retry, production write or modification to the existing `q25.extractor-raw-output.v1` provider contract.

## Problem this addresses

Real KITE-01 and GREENHOUSE-01 model calls showed gaps that cannot be
represented by the existing Q25 raw schema: (a) a numerical world countdown
explicitly going from 25 to 10 minutes and (b) a **physical relation** such as
a gold star glued to a kite's tail or a tarp covering a seedling tray.

A source-bound raw state could be structurally eligible yet remain
**semantically incomplete** because there was no field for these facts.

## Design: Separate explicit evidence, not inferred final state

`q25.terminal-supplement-annotation.v1` stores:

- `source_kind=AUTHOR_CURATED_NOT_INDEPENDENTLY_REVIEWED`: the annotations were
  manually authored after the corresponding real model outputs were already
  visible. They are **not** additional claims the model extracted and are **not**
  an unseen/independent holdout.
- Immutable `seed_sha256`, `source_sha256` and materialized
  `raw_output_sha256`: the supplement must belong to the original source.
- `world_time_claims`: a previously seeded integer `minutes_until_*` field,
  initial integer, proposed lower nonnegative integer, and an exact story quote
  containing a **matching explicit minute quantity**.
- `physical_relation_claims`: `ATTACHED_TO` or `COVERING` between two
  existing or source-proposed objects, with one exact story quote.

The validator checks the full frozen Q25 source/structural replay and rebuilt
terminal hypothesis; it does not amend either. Supplemented objects must
resolve to `object:<seed_id>` or `new:<raw_proposal_key>`. No implied
ownership, location, containment, holder or inventory is created.

It rejects unknown IDs, self-relations, duplicate/conflicting edges, invented
quotes, source mismatches, unseeded time fields, non-integer/bool values, values
outside an explicit decreasing countdown, unsupported relation types or added
authority flags. World-minute anchors currently accept **decimal digits and
conservative Turkish number words up to 99** next to `dakika`. An English
phrase or more complex temporal expression not qualified by this parser is
**not accepted** in V1; do not guess a conversion or weaken the check.

**Crucial limitation:** a quote containing `on dakika` can establish that
the numeric phrase appears in the story, but **not** that it refers to the
authoritative *terminal* world time. Independent full-story semantic review
must still verify chronology, context, contradictions and proposed terminal
value. A quote saying that elapsed minutes are not specified must never be
used to fabricate a number.

## Frozen replayable examples

| Story | Model run | Supplemented facts | Still unresolved |
| --- | --- | --- | --- |
| KITE-01 | [paid run #38287248179](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38287248179), source-gate **PASS** | `new:gold_paper_star ATTACHED_TO object:red_kite` | No numeric terminal world clock; star ownership unknown; interpretation still unreviewed |
| GREENHOUSE-01 | [paid run #38291167588](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38291167588), original paid run **REJECTED** | `minutes_until_shift_end:25→10`, `object:blue_tarp COVERING object:seedling_tray` | Semantic terminal time not certified; original paid run stays rejected |

GREENHOUSE-01's historic real paid result stays `REJECTED_BY_OFFLINE_GATE`.
A later **zero-cost deterministic source-order adapter** can replay the
unaltered raw claims as structurally eligible; the supplement relies on
this newer *offline* replay. This does **not** retroactively convert the
historical paid attempt to PASS.

Stored source-bound annotations and **separate** deterministic projections:

- [GREENHOUSE-01 author annotation](../../evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/terminal-supplement-author-annotation.json) and [read-only projection](../../evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/terminal-supplement-projection.json).
- [KITE-01 author annotation](../../evidence/q25/Q25-WITHHELD-TRIAL-20261012/terminal-supplement-author-annotation.json) and [read-only projection](../../evidence/q25/Q25-WITHHELD-TRIAL-20261012/terminal-supplement-projection.json).

## Offline commands

```sh
python -m pytest -q tests/test_q25_terminal_supplement.py

python -m src.q25_terminal_supplement \
 --request-package evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/request.json \
 --raw-response evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/paid-attempt-01-raw-extraction.json \
 --supplement evidence/q25/Q25-GREENHOUSE-COLD-TRIAL-20261012/terminal-supplement-author-annotation.json
```

Outputs contain source quote **character offsets**, hashes, the stated
numeric and relation candidates and these explicit flags:
`semantic_support_certified=false`,
`full_story_state_qualified=false`,
`state_commit_authorized=false`,
`production_write_performed=false`,
`provider_calls=0`.

## What must happen next

1. Independent semantic review of existing Q25 model claims **and** these
   new supplemental annotations. An author-provided test oracle is not a
   blind independently adjudicated gold standard.
2. Design a future **versioned** raw extractor output schema to express
   `world_time` and non-containment physical relations directly, then
   qualify its JSON Schema profile on a new unseen test. Do not retroactively
   pretend the current Sonnet extracted these author annotations.
3. Extend the story state/coverage completeness ledger and independent
   semantics gate to include these attributes without silently rewriting
   old `q25.extractor-raw-output.v1` artifacts.
4. Until all of this passes, PR #273 remains Draft, production LUMI and
   canonical StoryState are untouched, and no paid model call is automatic.
