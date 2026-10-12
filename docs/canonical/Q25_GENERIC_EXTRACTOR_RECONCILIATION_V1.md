# Q25 — Generic Raw Extractor to Terminal State Candidate, V1

Date: 2026-10-12  
Branch: `experiment/q25-narrative-memory-intent`, PR #273 Draft  
**Status: zero-cost engineering capability only. Not a qualified real-model extractor or accepted StoryState.**

## Problem addressed

Q24's original experimental reconciler depended on Q24-specific authored review annotations. A future model response from a new story cannot reasonably require those files before it can become a *candidate*. This stage extends the existing Q25 pipeline with a generic, read-only input endpoint (`src/q25_raw_reconciliation.py`) that accepts only:

- an immutable story seed,
- complete prose,
- a model-shaped `q25.extractor-raw-output.v1` envelope, and
- explicit experimental admission policy.

This adds **no second story architecture** and no new model/provider transport.

## End-to-end offline flow

```text
Frozen seed + full prose + untrusted raw candidate JSON + policy
                      |
                      v
Q25 source SHA / exact quotation materializer
                      |
                      v
Existing object admission + story evidence + terminal-property validators
                      |
                      v
Existing full state-coverage/seed-vs-candidate comparison
                      |
                      v
Generic raw reconciliation (read-only)
  - proposed new ordinary objects, never admitted as canon
  - reciprocal container / contains graph
  - allowed owners, holders, inventory, location topology, no cycles
  - seed attributes stored as initial references, not terminal proof
  - proposed property/knowledge/emotion/goal changes tagged UNVERIFIED
  - open threads/obligations remain uncertified
  - incomplete world clock and epistemic coverage visible
                      |
                      v
q25.raw-terminal-hypothesis.v1
state_commit_authorized = false
```

The generic bridge recomputes all upstream gates from source. A structurally blocked, corrupt, source-mismatched or unauthorized candidate is rejected. The output always carries a closed schema, explicit source and response digests, full coverage rows, unresolved fields and no authority to modify production LUMI.

A structurally valid *but semantically false* raw candidate can still be represented. Example: if a synthetic extractor claims Aylin owns a white folder simply because she placed a card in it, a quoted OWNED_BY relation can be structurally valid but **false**. The bridge preserves that as an **unverified relationship**, and the independent reference-claim scorer flags it as an extra claim. We must never interpret structural consistency as semantic proof.

## Offline calibration, not actual model measurement

The new Turkish test story and its **publicly visible** manually prepared reference/prediction data are stored in `evidence/q25/Q25-NEW-STORY-CALIBRATION-20261012/fixture.json`; details in its `report.md`.

On deliberately flawed synthetic output, the scorer records 12 reference claims, 10 candidates, 8 identity matches, 2 extra unsupported claims, 4 missing claims; precision 0.80, recall 0.667, F1 0.727. Those numbers verify scoring mechanics, **not model performance**. No online model produced either input; manual reference labels are not independent adjudications or blind holdout labels.

The generic reconciliation path is regression-tested on both the new Turkish fixture and the historical Q24 raw output, without requiring Q24's authored semantic review files. This does not change Q24's original rejection.

## Reproduce in a local/offline environment

Create your own local JSON inputs for seed, prose wrapper, raw response and admission policy, then:

```sh
python -m src.q25_raw_reconciliation \
  --seed path/to/seed.json \
  --prose-record path/to/story-record.json \
  --raw-response path/to/extractor-response.json \
  --policy path/to/experimental-policy.json

python -m src.q25_extraction_benchmark \
  --fixture evidence/q25/Q25-NEW-STORY-CALIBRATION-20261012/fixture.json

python -m pytest -q \
  tests/test_q25_extraction_benchmark.py \
  tests/test_q25_raw_reconciliation.py
```

Both CLI programs only print results to stdout, never perform model calls or write source files. `--prediction PATH` is supported by the calibration CLI for scoring an externally obtained JSON envelope; it does **not** fetch, generate or authenticate the response.

## Remaining explicit acceptance gates

1. Prepare a genuinely held-out new story **not placed in the model's context**, with independently judged expected terminal changes and null/unknown rules. Public fixture cannot serve as a blind benchmark.
2. Separately authorize one bounded paid extractor request and archive raw request/response, exact model name, usage tokens, latency, cost, model-returned quotes and materialized candidates.
3. Evaluate semantic FP/FN and precision/recall against the independent reference including relation ownership, epistemic knowledge, terminal timing and narrative obligation subtleties.
4. Validate the projected state against an independent human review of the **whole story**, not only selected quotes, and require production-admission policy before any canonical commit.

**No paid dispatch, no automatic provider selection or retry, no merge, no production changes, no accepted StoryState.** PR #273 remains Draft.
