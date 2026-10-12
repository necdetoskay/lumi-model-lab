# Q25 KITE-01 — First real source-gate PASS (Attempt 03)

**Date:** 2026-10-12  
**Run:** [GitHub Actions #38287248179](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38287248179)  
**Branch/PR:** `experiment/q25-narrative-memory-intent`, [#273](https://github.com/necdetoskay/lumi-model-lab/pull/273) Draft.  
**Model:** `anthropic/claude-sonnet-5.5`.  
**Critical qualification:** This was **source- and structural-gate eligible**, NOT accepted/certified Final StoryState.

## Actual paid production-boundary result

| Signal | Recorded value |
| --- | ---: |
| Provider POSTs / retries | **1 / 0** |
| Prompt / completion tokens | 6,788 / 2,883 |
| Total tokens | 9,671 |
| **Provider-reported actual cost** | **$0.042406** |
| Upper token-cost bound before request | $0.069872 |
| Authorization maximum | $0.20 |
| Provider latency | 20,185 ms |
| Paid extractor result | **`SOURCE_BOUND_CANDIDATES_ONLY`** |
| Real model raw claims | 16 |
| Source-verified coverage fields | **57** |
| Candidate | 13 |
| Partial candidates | 2 |
| Structural only | 23 |
| Unassessed | 17 |
| Unknown | 2 |
| Validated Final StoryState | **NO** |
| Canonical commit and LUMI production write | **NONE** |

This is the **first real Sonnet KITE-01 run** to pass the full unchanged Q25 source/structural gate; previous paid run [#38285710289](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38285710289) failed for malformed IDs/epistemic field usage. The third run used stricter system and JSON Schema field descriptions; no post-hoc correction or silent normalization occurred. The initial HTTP 400 incident [#38280659568](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38280659568) remains separately frozen; its billed amount is unverified.

## Frozen immutable result artifacts

- [Original raw extractor output](./paid-attempt-03-raw-extraction.json)
- [Sanitized provider usage and lineage ledger](./paid-attempt-03-public-ledger.json)
- [Read-only projected terminal state hypothesis](./paid-attempt-03-terminal-hypothesis.json)
- [Full semantic review packet](./paid-attempt-03-review-packet.json)
- [Private GitHub Actions archive — artifact 11763209593](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38287248179/artifacts/11763209593), includes original provider request/response and the full ledger; 7-day retention

The model's original response, derived state and review pack are **frozen evidence**, not accepted story canon. The regression suite recomputes these from source for bytewise-equivalent JSON values and asserts every semantic/canonical authorization flag remains false.

## Raw scoring against the authored provisional answer key

The reference consists of **16 author-authored, not independently adjudicated** claim identities, kept out of the provider wire.

| Diagnostic claim-identity metric | Result |
| --- | ---: |
| Original reference claims | 16 |
| Model claim candidates | 16 |
| Exact semantic-slot/string identities shared | **14** |
| Extra identities versus reference | 2 |
| Missing identities versus reference | 2 |
| **Identity precision / recall / F1** | **87.5% / 87.5% / 87.5%** |
| Exact *reference-quote* sets matched on 14 identity hits | **3/14** |

All 16 model evidence excerpts were found in the source, but quote equivalence to the author's chosen excerpts is a **different metric**. These scores cannot be interpreted as independently verified semantic precision or completeness; they are only comparisons to an open provisional key. No accepted extractor success rate is established.

**By type:** the ordinary new object (1), cleared container relation (1), goals (2), proposed narrative obligations (3), thread outcomes (3) and proposed terminal property changes (4) match by identity. **Character knowledge identities (2) do not match the authored reference** because the model used different natural-language values.

## Provisional semantic inspection — NOT independently adjudicated

**Supported candidate changes:**
- `blue_string` was physically removed from `wooden_box`, visibly found and tied to `red_kite`; `wooden_box.contains` is therefore empty in the candidate graph.
- The red kite has its string attached and is described as ready.
- `gold_paper_star` is an additional ordinary object. Ownership is **unidentified**, not inferred from Defne using it.
- Both characters' initial goals have proposed ACHIEVED outcomes. Three narrative obligations have source-cited SATISFIED proposals, but **zero independently accepted closures**.

**Remaining evidence/semantics issues:**
- Defne's model knowledge text centers on her having written the placement note; the author reference separately requires her **direct observation of the string inside the box**. Those are not interchangeable observations. The model's knowledge completeness is not established.
- Bora's model knowledge statement says he saw the note and that they should look inside the box. This is close to the author's knowledge observation, but **not identical text/identity**; an independent reviewer must adjudicate semantic equivalence.
- The note reports that Defne put the string in the box. Authorship and reading the note are observed; the past placement is a **reported** fact, not independently witnessed in-scene.
- The box was opened; it was later placed back on a shelf. The text does **not** establish whether its **terminal lid is closed**. The model correctly refrained from repeating the prior run's unsupported `lid_closed=false` terminal claim, but the slot remains unverified.
- Defne's uncertainty about Bora's restored trust is not a measured change to Bora's trust. The model did **not** propose a trust reset or invented a definite emotion.
- Elapsed minutes and a numerically updated final world clock are **unknown**; no time advancement was fabricated.
- The golden star was glued to the kite's tail; the current raw relation vocabulary does **not** express `ATTACHED_TO`. This is an **expressiveness/completeness gap** even though graph consistency passes. The new object's terminal location also remains unknown without asserted relation evidence; no location is invented.

**Interpretation:** PASS means **safe to represent an untrusted candidate with exact story citations and coherent object-container state**, not universal state extraction, complete world simulation or sound narrative closure.

## Generalization gate — next work, no immediate repeat purchase

1. **Independent semantic adjudication:** a reviewer other than the extraction model must compare *all* source/seed facts and disputed claims, including quote-equivalent but paraphrased knowledge.
2. **Expression coverage:** decide how attached objects, physical state persistence, location provenance and epistemic report-vs-observation should be represented without inventing new story facts.
3. **Blind unfamiliar scenario:** use a new, *genuinely distinct* story and an independently adjudicated reference to test reliability; repeated KITE-01 runs after prompt tailoring are not proof of model generalization.
4. Only after semantic checks may a canonical StoryState admission design be considered; LUMI production must remain untouched.

## Deterministic offline replay

```sh
python -m pytest -q tests/test_q25_successful_extractor_03.py

python -m src.q25_withheld_trial \
 --request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json \
 --reference-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/provisional-reference.json \
 --raw-response evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-03-raw-extraction.json
```

These do not call a provider, spend money, repair the response, write a canonical state or mark any semantic claims as independently accepted.
