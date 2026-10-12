# Q25 — New Turkish Story / Offline Claim-Scoring Calibration

**2026-10-12. PR #273 (Draft).** No model call, no real model prediction, no new story production run, no payment, no production promotion or Q24 rewrite.

## What actually ran

A *newly authored, openly stored* Turkish mini-story about **Aylin, Kerem, a missing yellow card, a green map and a newly mentioned white folder** has its own seed, exact full prose, model-shaped **manual reference envelope** and **deliberately flawed synthetic candidate envelope** in [fixture.json](./fixture.json).

The generic, existing `src.q25_extractor_adapter.offline_replay` independently validates both envelopes for exact seed/source hashes, literal quote occurrence, entity/property constraints, and basic structural coherence. A new read-only `src/q25_extraction_benchmark.py` then compares the materialized claim *identities*, by type, to its manually curated reference labels and separately counts exact reference-citation alignment. It never calls or impersonates a model.

**The reference is not independently gold-certified.** The story and answers are visible in the same repository, so this is **not blinded/unseen paid-model evaluation**, even though the scenario is new compared with the Q24 fixture. The scores below characterize a deliberately seeded calibration example, **not model accuracy**.

## Reproducible score on intentionally flawed input

| Statistic | Value |
| --- | ---: |
| Reference labels | 12 |
| Supplied claim candidates | 10 |
| Same claim identity as curated reference (TP) | 8 |
| Extra claims not in reference (FP) | 2 |
| Reference claims not recovered (FN) | 4 |
| Precision | 0.8000 |
| Recall | 0.6667 |
| F1 | 0.7273 |
| Exact reference quotes matched among 8 identity hits | 8 |
| Live provider calls | **0** |
| API spend | **$0** |

Two planted false positives are important:

1. **Ownership hallucination:** the synthetic extractor claims `new:white_folder OWNED_BY character:Aylin` from Aylin putting a card into the folder. Her *use* of the folder is explicit; *ownership* is not. This false claim passes structural source-quote validation and is flagged in the reference comparison.
2. **Emotion overreach:** `Aylin emotion=relieved` is supported only by `Aylin gülümsedi.` A smile is observed; the specific terminal emotion is not uniquely entailed.

Four missing references demonstrate recall accounting: Aylin's directly observed card location, the card's `found` flag, the complete apology/constraint obligation, and correcting the suspicion thread. Such omissions must not be hidden behind structurally valid output.

In a separate sanity check, the manually authored reference envelope compared to itself yields 12/12 matches and F1=1.0. **This proves only the metric's identity matching, not that any model has achieved 100%.** An empty extractor response yields zero recall. A source-exact but unrelated quote for a claim lowers the *reference quote alignment* without changing identity-level counts, which exposes why string-level provenance is necessary but not semantic certification.

## Validation commands

From repository root (Python 3.11 and Pydantic 2.x):

```sh
python -m src.q25_extraction_benchmark \
  --fixture evidence/q25/Q25-NEW-STORY-CALIBRATION-20261012/fixture.json

python -m pytest -q tests/test_q25_extraction_benchmark.py
```

Optional `--prediction PATH` loads another locally saved model-shaped `q25.extractor-raw-output.v1` JSON for **offline scoring only**. It **does not** dispatch a provider request. Invalid inputs fail closed and do not return misleading precision/recall.

The end-to-end CI [#38266985712](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38266985712) passed **263/263** tests at `3643a813`; `paid-extractor-pilot` was SKIPPED. The frozen Q24 acceptance rejection, canonical LUMI, semantic review and draft status were not changed.

## Remaining qualification barrier — no model success yet

The exposed synthetic reference labels cannot establish real extractor quality, generalization or reliable final StoryState. For a valid paid-model test, a **truly blind, independently reviewed** new story/seed and sealed labels must be kept separate from the model request, with pinned model, immutable prompt, no fallback, no retry, explicit token and dollar caps, frozen raw response and honest precision/recall/false-positive assessment. A response is still untrusted until independent semantic review. Any production/canonical state write is a different gate.

**State commit authorized: false. Real model success measured: false. Independent review performed: false.**
