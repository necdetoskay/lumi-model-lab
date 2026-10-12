# Q25 KITE-01 — Paid Sonnet attempt 02, raw rejection analysis

Date: 2026-10-12. **Status: REAL MODEL RESPONDED; OFFLINE STATE GATE REJECTED.**

This is frozen evidence from GitHub Actions [#38285710289](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38285710289), run on `5ad85ac4796dcc67a5edcc36ec91c8df36402345`. Raw original is committed as [paid-attempt-02-raw-extraction.json](./paid-attempt-02-raw-extraction.json). Account-key allowance fields are excluded from [the published ledger copy](./paid-attempt-02-public-ledger.json); the original GitHub Actions [artifact #11763048010](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38285710289/artifacts/11763048010) retains request, provider response, raw extraction and full ledger for 7 days.

## Actual execution

| Field | Recorded result |
| --- | --- |
| Model | `anthropic/claude-sonnet-5.5` |
| Model schema profile | `ANTHROPIC_STRICT_V1` |
| HTTP 400 grammar rejection | **Not observed in this attempt** |
| Provider POST attempts | **1**, no retry, no fallback |
| Provider-reported prompt tokens | 6,270 |
| Provider-reported completion tokens | 3,059 |
| Provider-reported total tokens | 9,329 |
| **Provider-reported actual cost** | **$0.04313** |
| Pilot authorization cap | $0.20 |
| Provider-response latency (ledger) | ~37.8 seconds |
| Pydantic raw JSON shape | Accepted |
| Exact source-quotation materialization | **Passed** |
| Offline state admission/coverage | **REJECTED**, `ValueError` |
| Canonical or production write | **None** |

The previous HTTP 400 incident [#38280659568](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38280659568) cannot establish that the previous error was *certainly* caused by JSON Schema constraints, because its provider error body was not retained. The new model metadata and provider-safe schema did, however, enable a complete model response.

## Exact offline rejection reasons

The first rejection is **`Subject must resolve to an existing or candidate object`**. The model supplied `subject: "blue_string"` for `IN_CONTAINER` instead of the required `"object:blue_string"`. This was not accepted or automatically rewritten.

A temporary **in-memory** diagnostic copy with only the namespace made explicit reached the second rejection: **`Epistemic classification is only for knowledge claims`**. Two non-knowledge claims—Defne's `relationship_trust` and Bora's `emotion`—carried `BELIEF` / `REPORTED` epistemic tags that are only allowed for a `knowledge` claim. These failures were revealed by read-only local replay and **do not turn the original saved raw response into an accepted state**.

A second isolated, hypothetical diagnostic copy that also removes these two invalid non-knowledge tags passes the *structural* gate, but this is a **counterfactual validity check**, not an accepted, verified, or paid extractor result. These modifications were never sent back to a model, never written into the original raw response, and never promoted into canonical state.

## Raw similarity against 16 author-curated reference labels

We separately score the *original rejected model claims* after exact hash/quotation materialization, without bypassing the actual offline state gate. The manually authored reference is **not independently adjudicated**.

| Metric (raw claim identity only) | Value |
| --- | ---: |
| Reference identities | 16 |
| Raw model identities | 18 |
| Identity matches | 13 |
| Extras relative to provisional reference | 5 |
| Misses relative to provisional reference | 3 |
| **Raw identity precision** | **72.22%** |
| **Raw identity recall** | **81.25%** |
| **Raw identity F1** | **76.47%** |
| Reference quote sets fully matched for identity hits | 3/13 |

**These are diagnostics, NOT the precision/recall of a qualified extractor.** Their denominators are an authored, not independently checked, answer key; semantic equivalence of some differing free-form character labels is not resolved. Exact quote alignment is a separate literal metric and does not prove semantics either.

Raw extras include the bare relation subject (syntactic mismatch); three free-form character assertions outside the provisional answer identities (Bora emotion, Defne self-placement knowledge, Defne's belief about Bora trust); and `wooden_box.lid_closed: true→false`. The text opens the box and later returns it to the shelf, but does not establish its terminal lid state definitively. Raw misses include the namespaced cleared containment and two explicit observation-knowledge annotations (Bora seeing Defne's note; Defne observing string inside the box).

Note that the character extra labels may include semantically plausible **reports**; equality against a short reference annotation is not a full truth test. Claims about another person's inner trust cannot be promoted from speaker uncertainty into a reliable relationship state. Every such field remains for independent semantic review.

## Engineering response, no further paid model dispatch

1. The original source-bound raw response and a sanitized cost/lineage ledger are frozen in this experiment branch.
2. `src/q25_paid_response_diagnostic.py` provides a deterministic, **zero-provider-call** replay of raw identity scoring alongside the actual gate rejection and known contract-shape violations. It always sets `state_commit_authorized=false` and `actual_accepted_extractor_precision=null`.
3. The Sonnet extractor prompt now explicitly requires `object:<id>` / `new:<key>` namespaced relation subjects and knowledge-only epistemic annotations; unclear relationship trust or closed-box state is not inferred. The unchanged application validators remain fail-closed.
4. Before another paid call, independently judge the reference claims and replay both original and deliberately defective cases through regression tests. Additional funding/dispatch is a separate decision.

### Replay (offline, read-only)

```sh
python -m src.q25_paid_response_diagnostic \
  --request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json \
  --reference-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/provisional-reference.json \
  --raw-response evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-02-raw-extraction.json \
  --ledger evidence/q25/Q25-WITHHELD-TRIAL-20261012/paid-attempt-02-public-ledger.json

python -m pytest -q tests/test_q25_paid_response_diagnostic.py
```

**Q24 frozen rejection unchanged. PR #273 Draft; no merge, canonical StoryState, production edit or additional paid model call.**
