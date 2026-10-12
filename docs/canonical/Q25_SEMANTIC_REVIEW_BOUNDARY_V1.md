# Q25 — Semantic Evidence Review Boundary V1

Status: **OFFLINE REVIEW PACKET ONLY; NOT SEMANTICALLY APPROVED**
Date: 2026-10-12
Experiment: PR #273, branch `experiment/q25-narrative-memory-intent`
Authority: **none**. A reviewer-written JSON file does not establish who wrote it.

## Purpose

Q25 can compile a strict extractor request, parse model-style candidate JSON,
locate exact source spans, and block schema, entity and structure violations.
That is **not** proof that a cited sentence justifies the proposed event or
describes the state at the **end** of the story.

`src/q25_semantic_review.py` adds the next strictly offline boundary:
a reproducible, source-bound packet with every proposed ordinary object,
terminal relation, character/knowledge change, goal, narrative obligation,
thread resolution and terminal object property. Each entry has a stable
claim ID, its **claim SHA256**, and exact citations with source offsets.

On the saved *manually derived* Q24 replay, the expected packet has **15
candidates**, while the source-bound state coverage still has **70 blocked
terminal-field assessments**. These numbers are a fixture illustration only,
not a quality score or an extractor recall/precision measurement.

The four review questions are: is the citation semantically sufficient;
does it establish the **terminal** state rather than an earlier event; is the
evidence fact/report/belief; and does another passage contradict it?

A complete set of judgments is required for recording. Valid labels:
- Semantic support: `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT`, `UNCERTAIN`.
- Time scope: `TERMINAL`, `EARLIER_ONLY`, `UNDETERMINED`.
- Epistemic status: `OBSERVED`, `REPORTED`, `BELIEF_ONLY`, `UNDETERMINED`.
- Each judgment must have a note of at least 12 characters.

## Reproduction, no model calls

Run from repository root (does not create or modify files):

```sh
python -m src.q25_semantic_review \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --raw-response evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/raw-extractor-replay.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json

python -m pytest -q tests/test_q25_semantic_review.py
```

An operator can save the printed JSON packet, compute its digest from the
canonical `review_packet_digest(packet)`, and prepare a separate response
with schema name `q25.semantic-review-response.v1`, that packet's digest,
a nonempty `reviewer_label`, and one uniquely ID-bound `ItemVerdict` for
every candidate. `--review-response PATH` replays this input against the
same source packet.

For now, even a fully populated packet and **15/15 SUPPORTED** labels returns
`SELF_REPORTED_REVIEW_LABELS_UNVERIFIED`, not acceptance. Unknown reviewer
identity, fabricated self-attestation, missed claims, contradictions elsewhere,
incomplete knowledge, temporal and world-state coverage remain unresolved.

## Fail-closed invariants

- Both immutable seed and complete source SHA256 must match source material.
- The entire raw extractor replay is revalidated through the previous
  materialization/admission/coverage gates before any review packet is made.
- Unquoted claims, invented actors, decisive clues, unresolved entity
  policy, forged source offsets or unapproved topology cannot bypass the gate.
- Review packet content is digest-bound. Duplicate, missing, unknown, or
  invalid verdicts and extra authority fields are rejected.
- Neither a reviewer label nor a vote is accepted as authenticated independent
  adjudication. **No grant, promotion, StoryState write, or Q24 verdict change.**
- No OpenRouter call or credit use. A genuine provider pilot and independent
  blinded human evaluation remain separate, explicitly controlled stages.

## Next step

Obtain exactly one authorized, archived, real extractor response from a
new/unseen story and collect independently verified semantic reviews against
the *entire prose*, with both false-positive and missing-event scoring.
This cannot be substituted with the Q24 hand-annotated replay or self-reported
labels. Production LUMI remains frozen until a separate qualification gate.
