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
- `jev_verifier.py` — per-claim JEV choice-question builder and advisory-only verdict routing; a billable live call requires an explicit opt-in.
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

The independent model must never see the writer report in its input. The output alone does not establish complete extraction: both models can miss the same object. A structurally reconciled report is `RECONCILED_PENDING_SEMANTIC`, **not PASS**.

## Atomic JEV prototype (M3 groundwork)

`jev_verifier.build_atomic_questions(...)` takes the M2 coverage, source
reports, scene prose and registry, re-checks the coverage binding, and builds
one `choice` decision per entity/presence claim and typed event. The JEV
request sees an anonymized union of candidate claims, not source-model labels.
The supported decisions are `SUPPORTED`, `CONTRADICTED` and
`INSUFFICIENT_EVIDENCE`.

`adjudicate(...)` routes contradictions to local repair, ambiguous claims to
escalation, and remaining extractor mismatches to reconciliation. Even full
semantic agreement leaves `commit_authorized=false`. Empty claim sets are
escalated; agreement on nothing is not a success.

`call_live_jev(..., allow_billable=True)` uses the existing repository-pinned
`typesafe/jev-1.13` Decisions API adapter. M3 tests only simulate answers;
**no real JEV model qualification or runtime cost is claimed.**

Full production acceptance, gold holdout calibration, state commit and the
nine-scene live Mara demonstration are future separate milestones.

## Current evidence and status

M0/M1 completed. M2 offline harness and preliminary M3 JEV question/decision contract implemented; **no live independent-model benchmark or JEV qualification yet**. The gold cases are synthetic and must not be counted as evidence of real extraction accuracy. No Project LUMI database writes, provider calls, or production V4/V4.1/V4.2 modifications occur in offline tests.

## 2026-10-16 live Mara S1 diagnostic

The first real one-scene model experiment ran, and subsequent independent Gemini + JEV continuation completed against the **identical 243-word scene**, not a regenerated story.

- [Full measured evidence ledger](./evidence/MARA_S1_LIVE_DIAGNOSTIC_20261016.md).
- [Live source run](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38808450095) and [semantic continuation](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38809210994).
- M2 remained HOLD: 10 incompatible event signatures, 10 missing grounded event times, 1 uncertain modality.
- JEV handled 18 claims: 17 SUPPORTED, 1 INSUFFICIENT_EVIDENCE; ESCALATE, **no state commit**.
- Manual text inspection found physical object candidates 'bench' and 'pencil' missing in both extractor entity lists. Optional versioned noun-candidate scanning plus fail-closed JEV claims was added and covered by regression tests.
- Unresolved schema/time/epistemic hardening is tracked in [#304](https://github.com/necdetoskay/lumi-model-lab/issues/304); persistent object history and weather is separate [#303](https://github.com/necdetoskay/lumi-model-lab/issues/303).

**Important:** A successful GitHub workflow run here means the diagnostic executed, not that the narrative or extracted state passed acceptance. A lexicon is supplementary, not proof of exhaustive entity identification.
