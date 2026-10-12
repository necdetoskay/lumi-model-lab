# Q25 — KITE-01: Answer-withheld real extractor trial preparation

**Date:** 2026-10-12  
**PR:** [#273](https://github.com/necdetoskay/lumi-model-lab/pull/273), Draft.  
**Status:** ONE-SHOT PILOT READY / OFFLINE CI GREEN / NO MODEL CALL / NO QUALIFIED FINAL STORYSTATE.

## Concrete fixture separation

- `request.json`: a fresh, independently named Turkish school kite-workshop story with Defne, Bora, a blue string in a wooden box, red kite and newly observed gold paper star. Holds **only** immutable seed, complete prose and experimental object-admission policy. No answer key.
- `provisional-reference.json`: a **separate** author-curated annotation set: one ordinary-object candidate, one cleared containment, two epistemic additions, two goal outcomes, three obligation candidates, three thread candidates and four object property deltas, **16 reference identities** total. Every claim has exact literal source quotations. **This is not independently adjudicated human ground truth** and must never be sent to the model.

The reference is **answer-withheld from the provider wire**, not a research-quality blind holdout or independently authenticated label set. Its existence in the same GitHub PR must not be represented as a secrecy guarantee; the structural promise is that the only paid-model input file is `request.json`, and `q25_withheld_trial.preflight` compiles the request from *only* that file.

## End-to-end protocol

```text
Label-free request.json (seed + prose + policy)
   -> q25_withheld_trial.preflight (strict hash/scheme, wire digest; NO network)
   -> [SEPARATE EXPLICIT MANUAL PAID AUTHORIZATION]
   -> q25_openrouter_pilot, one POST at most, no retry/fallback, <= $0.20
   -> archived raw response / token+cost ledger / quote validation
   -> q25_raw_reconciliation: untrusted proposed state / 0 canonical authority
   -> local/offline q25_withheld_trial.evaluate(raw response, separate reference)
   -> TP / FP / FN / precision / recall / F1 / quotation alignment
   -> independent whole-story semantic review remains REQUIRED
```

The Q25 workflow offers a manual `case` selector: `q24` or `kite-01`. The PR trigger **never** runs the paid job. A paid job requires **all**: explicit `workflow_dispatch`, `execute_paid=true`, first run attempt, valid allowlisted model, OpenRouter secret, live model capability/price verification, sufficiently funded key, signed-off max token count 3500, maximum amount $0.20, and no second dispatch. The action fails closed on unsupported models, inadequate remaining key budget, unexpected model output, price risk and invalid quotes. No automatic model fallback or retry.

The paid job receives **only** the new `request.json` for `kite-01`, not `provisional-reference.json`. It archives the immutable HTTP request/response, raw extraction, ledger, offline gate result, semantic-review packet, and an **unverified raw terminal hypothesis** if the structural gate succeeds. The archive is a private GitHub Actions artifact with seven-day retention, not a production state write. A semantic false positive with an exact quotation can still pass structural validation; it must be evaluated separately against the withheld reference and full narrative.

## Zero-cost repro (all current work)

```sh
python -m src.q25_withheld_trial \
  --request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json \
  --model anthropic/claude-sonnet-5.5

python -m src.q25_openrouter_pilot \
  --request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json \
  --model anthropic/claude-sonnet-5.5 \
  --max-cost-usd 0.20

python -m pytest -q tests/test_q25_withheld_trial.py
```

Both first commands return **DRY RUN** (no HTTP POST, no GPU/model calls, no payment, no state commit). Provider pricing and model availability are verified **live only in the explicitly authorized paid flow**, never guessed from the offline mock pricing tests.

After a separately authorized and archived paid run, use:

```sh
python -m src.q25_withheld_trial \
  --request-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/request.json \
  --reference-package evidence/q25/Q25-WITHHELD-TRIAL-20261012/provisional-reference.json \
  --raw-response /path/to/archived/raw-extraction.json
```

**No actual paid response exists yet.** Offline reference-vs-itself 16/16 is solely a metric sanity test and **must never be quoted as a model result**. The actual response should be evaluated for false ownership, mistaken emotional certainty, physical changes in `blue_string`, `wooden_box`, `red_kite`, missing goals and unresolved trust, as well as unextracted world time. Do not silently treat reference labels as independently correct.

## Acceptance boundaries

The frozen Q24 story/seed/rejection remain unmodified. LUMI production, repo base, canonical state and persisted StoryState remain unmodified. Q25 output always sets `state_commit_authorized=false`, and no semantic truth is certified by a label match or a GREEN test suite. The next valid evidence is a **real single-response, model/pricing/tokens/latency/cost archived run plus independent adjudication**, not another synthetic all-green example.

**Incremental OpenRouter API usage so far: 0 calls / $0.**
