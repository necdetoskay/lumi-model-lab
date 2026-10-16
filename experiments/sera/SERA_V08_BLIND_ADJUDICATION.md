# SERA v0.8 — Blind Review & Adjudication Queue

**Date:** 2026-10-16  
**Status:** Offline review staging implemented; no authenticated human review yet  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Frozen source:** Mara S1 / 243-word HOOK / SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`

## Problem

The v0.7 28-sentence worksheet has full **structural coverage**, but nine
analyst candidate events and 28 empty review slots are **not gold labels**.
The next meaningful gate is a pair of independently prepared,
source-bound reviews, a deterministic disagreements/coverage manifest,
and **a separate real-world, authenticated human adjudication process**.
This implementation cannot impersonate the last step.

## Delivered

- `review_adjudication_v08.py` — exports blind reviewer forms, validates
  every exact source sentence and each lexical entity hint, anchors each
  event to source evidence and supports multi-sentence event identities;
  generates explicit disagreement and high-risk queues.
- `review_forms_cli_v08.py` — offline export and compare CLI.
- `tests/test_review_adjudication_v08.py` — synthetic positive/negative
  tests including fabricated quotes, forged GOLD status, missing sentence,
  unreviewed entity hints, same reviewer alias, story action labeled
  texture, cross-sentence event identity contradiction, differing
  reviewer decisions, and unscanned entity mentions.
- SERA GitHub Actions now exports a reviewer artifact after every relevant
  branch change. It contains two unreviewed JSON forms and an instruction
  file. Original analyst event candidates **are absent from both forms**.

## How to conduct review

Start by downloading the artifact from
[Actions run 38856341190](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38856341190),
or generate locally:

```bash
python -m experiments.sera.review_forms_cli_v08 export \
  --output-dir /tmp/sera-mara-review
```

Two people work independently on:

- `reviewer_A_unverified.json`
- `reviewer_B_unverified.json`

Each sentence contains its full source quote and independent lexical
entity hints (not prior analyst event annotations).

For each sentence they classify one summary disposition:
`STATE_EVENT`, `KNOWLEDGE_EVENT`, `CLAIM_ONLY`,
`NO_TRACKED_CHANGE`, `TEXTURE`, `AMBIGUOUS`.
For each lexical noun mention they explicitly choose its referential
status and explain it. They may add *multiple* source-span-backed events
to a single sentence; one event can have evidence in multiple sentences.

Event annotations record kind, epistemic class, effect category, involved
entity IDs, source character offsets, exact quote and reason.

**Critical examples to adjudicate:**
- Vane's `02:07` watch reading versus the actual time of looking at the watch.
- An archive-recorded arrival versus physical arrival of train 41.
- Watch case initially open and then explicitly closed.
- Mara writing not only to her notebook but adding another sentence.
- Physical bench/pencil sightings with or without explicit interaction.
- An event in dialogue that changes a character's knowledge but not
  objective world truth.

After both independent reviews are genuinely completed:

```bash
python -m experiments.sera.review_forms_cli_v08 compare \
  --review-a /tmp/sera-mara-review/reviewer_A_unverified.json \
  --review-b /tmp/sera-mara-review/reviewer_B_unverified.json \
  --output /tmp/sera-mara-review/adjudication-queue.json
```

The queue records disagreements by sentence:
`DISPOSITION`, `ENTITY_PRESENCE`,
`EVENT_EVIDENCE_OR_SEMANTICS`; unfinished reviews become `INCOMPLETE`.
Matching rows are identified, but agreement **does not prove correctness**.
High-risk evidence omissions (e.g. physical change mislabeled TEXTURE),
T2 downgrades or an entity reference absent from the scanner stay review
findings even if both reviewers agree.

## Non-negotiable safety and epistemic constraints

- A reviewer alias is just a string. It proves neither identity nor
  independence.
- A SHA-256 checksum proves byte consistency relative to a known source,
  **not** a genuine human attestation.
- These offline forms are `gold_status=NOT_GOLD`; editing the status to
  `GOLD` is a **validation error**.
- Neither matching reviewed labels nor a PASS on any unit test authorizes
  EventGraph or World State updates.
- The event / entity precision and recall for real Mara are still **null**
  because no independently adjudicated human gold source exists.
- No LLM calls, provider-cost events, PostgreSQL writes, or configured
  output-token ceilings are introduced.

## Next release gates

1. Independently complete A and B review for all 28 sentences.
2. Resolve conflicts and risk findings with a trusted final reviewer and
   **authenticated** provenance recording. Only that separate service
   may classify a human-adjudicated benchmark reference as eligible for
   evaluation; reviewer aliases alone are not identity verification.
3. Convert the final reference into a normalized independent gold
   dataset for per-sentence entity and event precision/recall.
4. Benchmark new blind extraction versus that reference, including
   explicit negative cases for source claims and time offsets.
5. Extend aspect/epistemic reducer operations for case open/close and
   notebook writing, then evaluate an **actual** complete Mara S1
   exit-state commit through the production-grade authority gate.

**No subsequent scene is canonically accepted at v0.8.**
