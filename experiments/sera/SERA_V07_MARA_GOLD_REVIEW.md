# SERA v0.7 — Mara S1 Reference Review and Independent Extractor Binding

**Date:** 2026-10-16  
**Status:** IMPLEMENTED OFFLINE — GOLD PENDING HUMAN ADJUDICATION  
**Related architecture:** [SERA v0.6](./SERA_V06_SCENE_ASSURANCE_ARCHITECTURE.md)  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)

## Problem

SERA v0.6 makes **28/28 source sentences structurally accountable**, but
a full set of sentence review slots is not proof of semantic completeness.
Both writer and independent extractor can miss the same physical object
(bench/pencil), and a reviewer can mark an event-bearing sentence as TEXTURE.

We need a **reviewable source-grounded reference**, a way to bind a blind
extractor's report to the same source units, and an evaluator that **refuses
to invent precision/recall numbers when adjudicated truth is absent**.

## Frozen sources

- Original Sonnet Mara Spine blob:
  `fe1dda0047000438bbfaac69022e835bf7e0a1f8`.
- Real 243-word HOOK prose SHA-256:
  `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`.
- Nine earlier event annotations originate from
  `fixtures/mara_s1_real_eventgraph_candidates_v03.json`,
  marked `ANALYST_CURATED_LIVE_SCENE_INSPECTION`.
  **These are not adjudicated ground truth.**

## Delivered modules

### 1. `sentence_review_packet_v07.py`

Generate an explicitly **UNREVIEWED** worksheet for the exact Mara prose,
or any source prose and lexicon. The packet records:

- prose SHA-256 and character length;
- 28 source-bound sentence IDs, exact codepoint offsets and verbatim quotes;
- known entity aliases, T2 physical object candidate sightings (including
  `candidate:bench` and `candidate:pencil`);
- action, document-change, epistemic, time and pronoun cues;
- any overlapping existing analyst candidate events, with exact span
  evidence and `ANALYST_CANDIDATE_NOT_ADJUDICATED` status;
- review slots initially `UNREVIEWED`, labels and evidence acceptance empty;
- explicit `adjudicated_gold=false`, `canonical_commit_authorized=false`.

```bash
python -m experiments.sera.sentence_review_packet_v07 \
  --output /tmp/mara-s1-28-sentence-unreviewed.json
```

The validator fails on different source text, quote tampering, missing
sentence rows, wrong packet fingerprint or a forged claim that this source
worksheet is already human-approved. The packet SHA is an integrity
checksum, **not a cryptographic human identity signature**.

A finished human reference must be reviewed and accepted through a future
authenticated workflow. Do not edit this packet into an arbitrary
`adjudicated_gold=true` JSON and treat it as qualification.

**CI-generated review artifact:**
[Run 38855425609](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38855425609),
artifact `sera-mara-s1-unreviewed-worksheet-38855425609`
(ID `12027206389`). Use the GitHub Actions artifact interface to
download for external human annotation.

### 2. `independent_ledger_bridge_v07.py`

`bind_independent_to_ledger` takes an **already generated** M2 report from
a blind `INDEPENDENT` extractor, verifies it against its exact frozen
source, and projects every event's reported evidence span across all
overlapping sentence rows.

- A single narrative witness testimony spanning two sentences creates two
  exact quote bindings but remains **one event ID**.
- Unreported known objects and candidate nouns become additional findings;
  the source candidate scanner is independent from the extractor.
- Unknown `new:...` mentions receive review flags, never automatic
  creation.
- Every ledger row stays `AMBIGUOUS` until independent semantic
  review—**having an exact substring does not establish its semantic
  meaning**.
- `scene_assurance_v06.audit_scene(independent_only=...)` explicitly
  distinguishes one blind extractor from a completed Writer/Extractor
  cross-check. Single-source status remains HOLD.
- The function makes **zero paid model calls and zero WorldStore/DB writes**.

Only source-validated pre-existing reports may be bound. It does not repair
empty Gemini arguments or treat previously failed provider responses as
independent successful extractions.

### 3. `offline_benchmark_v07.py`

`compare_reviewed_labels` computes deterministic precision, recall and
F1 on **sentence-level disposition labels and per-sentence entity
references**. The tests demonstrate true positives, false positives and
false negatives on **synthetic** source-pinned examples.

The function reports neither full semantic event recall nor physical
state-transition accuracy. Any human-reviewed reference must be separately
authenticated; the current code explicitly sets
`reference_authenticity_verified=false` and
`eligible_for_canonical_state_commit=false`.

`summarize_unreviewed_packet` returns **null** for real Mara entity and
event precision/recall: `NO_ADJUDICATED_GOLD_REFERENCE`. The actual Mara
reference is **not yet eligible for a measured accuracy claim**.

## Exact experimental outcomes

- 28/28 frozen Mara sentences have review slots and exact source quotes.
- 9 earlier event candidates are linked **as suggestions**, not accepted.
- T2 bench/pencil evidence and state-change cue scan are preserved.
- A single independent extractor report can connect one event across
  multiple sentences and cannot silently claim full Writer consensus.
- Invalid role, forged offsets, missing sentence rows, changed source,
  unauthorized gold labels and incomplete references fail closed.
- All previous M1–M3.5 offline contracts, SERA v0.6 and
  **no configured output-token ceiling** CI rules remain active.

## Still needed before a genuinely accepted Mara S1 exit state

1. **Human adjudication:** For each sentence, determine what actually
   happens, include multiple actions per sentence, list all relevant
   entities and epistemic provenance, resolve disagreements.
2. **Independent extractor benchmark:** Obtain a completed blind result
   (provider compatibility needs qualification), bind its event evidence
   with the v0.7 bridge and score against the adjudicated reference.
3. **Qualified review authority:** Authenticate reviewer provenance,
   resolve disagreements and define non-fabricated approvals; simple
   metadata and checksums cannot impersonate this.
4. **Reducer extensions:** Implement verified note-write,
   `case_open` and epistemic transitions (v0.6 aspect proposals are not
   canonical reducer events yet).
5. **Commit gate:** Only after all relevant events/objects have grounded
   independent semantic evaluation and deterministic replay qualification
   may S1 produce an authorized exit snapshot. Then and only then S2.

The system must not generate false PASS or fabricate gold labels to
accelerate the narrative pipeline. There are **no paid calls** and
**no changes to the original Spine or production DB** in v0.7.
