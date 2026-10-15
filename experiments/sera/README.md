# SERA — Scene Event Registry & Assurance

Independent LUMI Model Lab scene-state experiment on `experiment/sera-scene-state-v0-1-20261015`. **Not a promoted story pipeline.**

## Frozen source

Original Sonnet 5.5 pre-Haiku Spine: `evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json`.
Pinned Git blob SHA: `fe1dda0047000438bbfaac69022e835bf7e0a1f8`.
It is read-only. The compiler creates nine derived scene contracts without rewriting source data.

## Modules

- [ARCHITECTURE.md](./ARCHITECTURE.md) — design, authority rules, semantic caveats and milestones.
- `spine_contracts.py` — immutable-source verification and derived scene-contract compilation.
- `state_engine.py` — Python event reducer and complete state snapshots. Records non-mutating object interactions as events.
- `coverage.py` — strict dual-extraction schema, lexical known-entity scanner, event/mention reconciliation; **never** authorizes commit.
- `extractor_adapter.py` — independent/blind prompt, exact-quote span binding and opt-in one-call OpenRouter client.
- `fixtures/gold_mara_m2_v0.1.json` — six **hand-authored synthetic** adversarial scenes with expected event/entity labels (not model results).
- `gold_calibration.py` — offline precision/recall metrics against manual synthetic labels.
- `tests/` — deterministic unit tests; all external responses mocked.

## Offline checks (no provider cost)

From repository root:

```bash
python -m unittest discover -s experiments/sera/tests -v
python -m experiments.sera.spine_contracts evidence/v4-2-mara-run-38794774463/sonnet-original-spine-pre-haiku.json
python -m experiments.sera.gold_calibration
```

## Independent extractor (opt-in only)

Create a local JSON input containing **exactly** these fields:

```json
{
  "scene_key": "hook_empty_platform",
  "entry_revision": 0,
  "prose": "Mara examined the quiet platform.",
  "registry": {
    "mara": ["Mara"],
    "platform_clock": ["platform clock"]
  }
}
```

Dry-run displays the blind system prompt and serialized scene payload **without calling an API**:

```bash
python -m experiments.sera.extractor_adapter path/to/input.json
```

A live call is explicitly billable and is **not** part of CI:

```bash
OPENROUTER_API_KEY=... python -m experiments.sera.extractor_adapter path/to/input.json \
  --live --model EXACT_MODEL_ID --output path/to/new-evidence.json
```

The adapter makes exactly one request, with no provider fallback. Unknown/incomplete outputs fail closed. It records requested model, observed model, usage, provider cost if returned, raw extraction, hashes and typed extraction report. A quoted phrase is resolved to codepoint offsets in Python; the model is not trusted to count indices.

The independent model must never see the writer report in its input. The output alone does not establish complete extraction: both models can miss the same object. A structurally reconciled report is `RECONCILED_PENDING_SEMANTIC`, **not PASS**. Semantic JEV/LLM verification and production authorization are outside M2.

## Current evidence and status

M0/M1 completed. M2 offline harness implemented and exercised; **no live independent-model benchmark or JEV qualification yet**. The gold cases are synthetic and must not be counted as evidence of real extraction accuracy. No Project LUMI database writes, provider calls, or production V4/V4.1/V4.2 modifications occur in offline tests.
