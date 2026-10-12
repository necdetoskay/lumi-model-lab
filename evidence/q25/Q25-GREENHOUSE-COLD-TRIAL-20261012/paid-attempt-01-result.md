# Q25 GREENHOUSE-01 — Distinct-story real Sonnet trial and source-order replay

**Date:** 2026-10-12  
**Status:** Original real paid attempt **REJECTED_BY_OFFLINE_GATE**. Newly enhanced offline replay **SOURCE_BOUND_CANDIDATES_ONLY** after deterministic citation ordering. **These outcomes must not be conflated.**

## Independent scenario, but not independently verified labels

GREENHOUSE-01 is a new rain-and-greenhouse storyline: Mina and Eren begin in separate rooms, move between rooms, acquire knowledge from reporting/observation, close a roof vent, protect wet seedlings, and face a countdown from 25 to 10 minutes. It is **not a KITE-01 or lost-object retelling**.

- [Label-free immutable request](./request.json) — only this package was included in the real paid model request.
- [Separate frozen provisional reference](./provisional-reference.json) — 16 author-curated claim labels, not included in the provider request; **not independently human-adjudicated**.
- [Exact unedited raw model extraction](./paid-attempt-01-raw-extraction.json).
- [Sanitized cost and rejection ledger](./paid-attempt-01-public-ledger.json).
- [GitHub Actions original paid run #38291167588](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38291167588), [private archived provider evidence #11765791978](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38291167588/artifacts/11765791978) (7-day retention).

## Verified real model execution

| Attribute | Result |
| --- | ---: |
| Model | `anthropic/claude-sonnet-5.5` |
| Bounded provider POST attempts | 1 |
| Repeated calls/fallbacks | 0 |
| Input tokens | 6,903 |
| Output tokens | 2,894 |
| Total tokens | 9,797 |
| **Provider-reported cost** | **$0.042746** |
| Approved cap | $0.20 |
| Provider latency | 18,919 ms |
| Original saved outcome | **REJECTED_BY_OFFLINE_GATE** |
| Original failure class | ValueError |
| Canonical state acceptance | **NO** |
| Production LUMI writes | **NONE** |

## Exact rejection reason and generalized engineering fix

The model found two **literally present and individually valid** citations for `protect_seedlings_without_harm`, but returned them in reverse narrative order:

- Source offset **1373**: Mina observes that no seedling was crushed.
- Source offset **1190**: the protective tarp did not touch the leaves.

The legacy `q25_story_evidence.extend_draft` requires evidence arrays ordered by increasing source start position, and therefore raised `Duplicate or out-of-order supporting evidence`. Nothing was hallucinated in these two citations; their **list ordering** was wrong.

A general, strictly read-only **raw adapter boundary** now:

1. Checks every model-provided quote, context and exact source position using the existing unmodified quote resolver.
2. Rejects duplicated quotations or failed source bindings **before** sorting.
3. Sorts only the **already validated evidence spans**, for goal/obligation/thread/property lists, by deterministic story character offset. A complete original raw response remains unchanged.
4. Emits explicit audit entries, e.g. `obligation_claims[2]: [1373,1190] → [1190,1373]`, with reason `SOURCE_POSITION_SORT_ONLY_NOT_SEMANTIC_REPAIR`.
5. Retains strict direct annotated evidence checks and independent semantic/canonical gates. Does **not** guess state, change a claim, adjust epistemic types, add owner/location, or certify story truth.
6. Adds a corresponding model-facing chronology hint so better formatted outputs are encouraged, while still allowing transport-level correction of harmless list order.

The saved original paid ledger remains **REJECTED**. Replaying its **unaltered raw bytes** under this newer adapter is **structurally eligible only**: `SOURCE_BOUND_CANDIDATES_ONLY`, **54** coverage fields with `14 CANDIDATE / 1 PARTIAL / 23 STRUCTURAL_ONLY / 14 UNASSESSED / 2 UNKNOWN`. No new paid model call was made for replay, and the source adapter's chronology transformation is not semantic acceptance.

## Provisional identity-only scoring on the archived real raw response

Using the unreviewed 16-claim reference:

| Metric | Value |
| --- | ---: |
| Reference claims | 16 |
| Real model raw claims | 17 |
| Exact identity overlaps | 13 |
| Different or extra identities | 4 |
| Reference identities not matched | 3 |
| Precision, identity level | **76.47%** |
| Recall, identity level | **81.25%** |
| F1, identity level | **78.79%** |

These are **not independently verified semantic precision/recall** and are NOT a product readiness signal. Important differences include:

- Model names the new ordinary bell `copper_rattle` vs author label `copper_bell`. **Same plausible object**; pure key-string mismatch must not be presumed a hallucination.
- Eren's observed vent knowledge is phrased differently from the reference, and the model also proposes his earlier reported knowledge received from Mina. This is an **epistemic sequence requiring adjudication**, not automatic duplication or acceptance.
- Mina's `location=greenhouse` candidate repeats the initial location, without proving every other unchanged terminal fact. The source does ground her staying there.
- The model did not include the reference's Mina knowledge claim for her direct observation that none of the plants were crushed.

Some correct candidates include Eren moving and the blue tarp's `LOCATED_IN greenhouse` change, roof vent closed, tray covered, tarp unfolded, both character goals, and three narrative obligations (all still unapproved proposals).

**Architecture/expression gaps remain** even if structure passes:

- The story explicitly changes `minutes_until_shift_end: 25 → 10`; Q25 raw schema **cannot yet propose world-clock changes**, so the terminal world time stays `UNASSESSED`.
- The tarp is fastened to support bars, physically covering seedlings, but the generic relation vocabulary **has no attached-to/covering graph edge**.
- The wet soil remains wet at story end. No typed terminal confirmation of *unchanged* scalar properties is accepted just because the seed said they were true.
- Independent final-story semantic adjudication, character-knowledge completeness, reciprocal physical graph checks, and canonical write authorization remain separate gates.

## Tests and qualification boundary

The real failed-run raw fixture is part of `tests/test_q25_greenhouse_order_normalization.py`. Tests prove the original paid failure ledger, unchanged raw evidence, precise citation offsets, sorted-only replay, duplicate/forged quotation rejection, arbitrary entity/authority rejection and non-committable terminal hypothesis.

The generic semantic dispute queue, `src/q25_semantic_gap_queue.py`, also pairs KITE-01's differently phrased actor-knowledge claims **without** auto-judging equivalence.

Latest source-order and cold-story offline CI [#38291912444](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38291912444): **377/377 tests PASS**, paid job SKIPPED. No further API request was dispatched after the recorded greenhouse attempt.

**PR #273 remains Draft. Historical Q24 reject unchanged; production LUMI and canonical StoryState untouched.** A further paid test should use a new or meaningfully different holdout, not another paid retry on GREENHOUSE-01 merely to increase a green count.
