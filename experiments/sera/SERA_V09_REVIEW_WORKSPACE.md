# SERA v0.9 — Offline Human Review Workspace & Review Intake

**Date:** 2026-10-16  
**Status:** Experimental browser review UI implemented; **human gold and Mara S1 canonical state remain blocked**  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Frozen prose SHA-256:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`

## Why this step

The prior v0.8 blind review pipeline was structurally correct but required
manually editing long JSON documents for each of the 28 Mara sentences.
That is unnecessarily difficult for independent reviewers and increases
offset/formatting errors.

v0.9 adds **standalone HTML forms** that work in a local browser without
a server, external scripts, account login, AI model calls, or network access.

These files are for real humans to mark actual observed events and
entities. **No human answers have been fabricated or pre-filled.**

## Files

- `reviewer_ui_v09.py`: generates two offline HTML review pages containing
  distinct empty v0.8 review forms, scan-only cue hints and the verbatim
  28-sentence source. Does not embed any of the nine historical analyst
  proposed events or prior reviewer answers.
- `review_adjudication_v08.py`: extended backwards-compatible support for
  **extra_entity_candidates** with exact source spans, typed presence decisions
  and explicit rationale, useful when the lexicon itself omits an object.
- `review_forms_cli_v08.py`: new `validate` command checks saved JSON against
  the original source/packet before the two reviews are compared.
- `tests/test_reviewer_ui_v09.py` and existing v0.8 review tests: security,
  blind-form generation, source binding, extra object candidate evidence,
  comparison, tampering and refusal to mark any resulting data GOLD.
- Dedicated SERA CI exports the generated offline HTML and corresponding
  blank JSON forms and validates the generated JavaScript with Node syntax
  checking (plus Python source/contract tests).

## How the browser workflow operates

[GitHub Actions offline reviewer pages](https://github.com/necdetoskay/lumi-model-lab/actions/workflows/sera-state-engine-tests.yml)
— open a completed run and download the
`sera-mara-s1-browser-review-v09-<run_id>` artifact.

In the downloaded ZIP, open
`reviewer_A_unverified.html` or
`reviewer_B_unverified.html` in a modern browser.

1. Reviewer A uses only the A page; reviewer B uses only the B page and
   does not see A's answers.
2. Each page shows the active source sentence, neighboring sentence
   context, source offsets, and lexical cues. The reviewer chooses the
   sentence's semantic disposition.
3. Every listed character/object mention needs a presence/knowledge
   classification and explanatory reason.
4. New objects missed by the scanner can be added as
   `extra_entity_candidates`; ID begins `new:`, evidence must be
   an **exact contiguous substring** within that source sentence. This
   is an independent candidate, **not a canonical entity creation**.
5. For every meaningful occurrence, add a typed event with an exact quote,
   instance/occurrence number, epistemic modality, effect family, entity refs
   and explanatory reason. Multiple events per sentence are supported.
6. The interface computes Python-compatible **Unicode code-point**
   offsets via JavaScript `Array.from`, not UTF-16 code units; this
   matters for texts containing astral Unicode symbols.
7. Download the annotated JSON file before closing the browser. Nothing
   is saved to cloud/storage and there is **no background autosave**.
   Use the browser's JSON import option to resume a source-matched draft.
8. Submit both filled forms for Python validation and then compare them.
   Example:

```bash
python -m experiments.sera.review_forms_cli_v08 validate \
  --review reviewer_A_unverified-NOT_GOLD.json \
  --require-complete

python -m experiments.sera.review_forms_cli_v08 validate \
  --review reviewer_B_unverified-NOT_GOLD.json \
  --require-complete

python -m experiments.sera.review_forms_cli_v08 compare \
  --review-a reviewer_A_unverified-NOT_GOLD.json \
  --review-b reviewer_B_unverified-NOT_GOLD.json \
  --output mara-s1-disagreements.json
```

**Reviewers are never identity-verified by this offline process.**
The comparison computes disagreements and even shared risk flags,
but cannot approve gold or authorize a world-state mutation.

### Local generation (stdlib only)

```bash
python -m experiments.sera.reviewer_ui_v09 \
  --output-dir /tmp/sera-mara-review-ui
```

### Security and data boundaries

- Each generated HTML page has a restrictive Content Security Policy,
  no external JavaScript, no `fetch` or `XMLHttpRequest`, no localStorage,
  and no remote data submission.
- Source/attribute strings are inserted through `textContent`. Embedded
  form JSON escapes literal `<` before insertion into the HTML script tag.
- JSON import checks scene, source fingerprint, reviewer role, every sentence
  quote/offset, and every known lexical entity hint; the **authoritative**
  Python validator is still required after export.
- The offline review UI cannot cryptographically authenticate a person,
  prove independence of A and B, prove completeness of events or verify
  semantic correctness.
- SERA `AGENTS.md` remains the user-specified guard against
  **application-set output-token limits**. This stage makes **zero** AI calls.
- No production LUMI database, canonical WorldState, EventGraph, or
  original Mara Spine was modified.

## Acceptance

The code is considered ready for **human input collection** when:
- all original 28 Mara sentences are bound to the exact frozen source;
- both independent pages open with no pre-filled event decisions;
- only exact source-span-backed entity/event entries can pass Python
  review validation;
- reviewer mismatch and lexicon-omitted entity records are surfaced;
- generated JS passes a syntax gate and all SERA tests pass; and
- the result explicitly remains `NOT_GOLD`, with no canonical commit.

This release does **not** meet the separate requirement for genuinely
human-adjudicated Mara gold. Human annotation, trusted final decision
authority, quantitative blind-extractor benchmarking, and an accepted
Mara S1 exit state still remain pending.
