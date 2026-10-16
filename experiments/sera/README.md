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


## Object State v0.2 — Active Experimental Prototype (Issue #303)

Per the object-history backlog, SERA now includes a second, isolated, strictly typed
state/event system. **Existing v0.1 scene/extractor/JEV code and the immutable
Sonnet source remain untouched.** This is NOT a production database migration.

- [Full v0.2 architecture](./WORLD_STATE_V02_ARCHITECTURE.md).
- `world_state_v02.py`: entity identity, object color/material/dimensions,
  condition/age, ownership vs holding/wearing, character traits/knowledge,
  and environmental weather/temperature/wind/wet ground. Verified changes
  require application-owned event-fingerprint grants and explicit causes.
- `world_store_v02.py`: standard-library SQLite atomic/idempotent events,
  append-only histories, revisional/historical entity lookups, snapshot replay
  and hash-chain consistency checks.
- `tests/test_world_state_v02.py`: demonstrates **10 scenes without silent
  object/color/clothing/weather changes**, authorized repairs, ownership and
  dimension constraints, temperature jumps, SQLite historical retrieval,
  rollback, idempotency and closed-form append-only records.

Run from the repository root:

```bash
python -m unittest discover -s experiments/sera/tests -v
```

M3's actual Mara first-scene extraction is still held by typed-event/time
problems ([#304](https://github.com/necdetoskay/lumi-model-lab/issues/304)).
**No provider model or JEV response is allowed to commit the new v0.2 state
without a separately qualified evidence-to-authority adapter.**

## EventGraph v0.3 — Structural history and causal dependency graph

[Experimental architecture](./EVENTGRAPH_V03_ARCHITECTURE.md) ·
[Issue #305](https://github.com/necdetoskay/lumi-model-lab/issues/305) ·
[Real Mara S1 candidate evidence](./fixtures/mara_s1_real_eventgraph_candidates_v03.json)

- `event_graph_v03.py` now implements independent narrative event IDs,
  participant/object role relations, causal prior-event links, typed
  preconditions, prose-SHA+exact-span binding and advisory epistemic classes.
- **Only the Python world reducer** calculates the before/after entity and
  region diffs. Language-model-proposed before/after snapshots are rejected.
- `EventGraphStore` writes event relationships/effects and the v0.2 world
  transition in **the same SQLite transaction**. If an affected coat/notebook
  is missing from a movement event's related objects, both ledgers roll back.
- Append-only graph lifecycle supports accepted
  PROPOSED→VERIFIED→COMMITTED and independent REJECTED proposal records.
  A graph query can retrieve object/character history, scene timeline,
  event descendants and reducer-derived effects. Replay requires a one-to-one
  mapping of all world events to narrative events.
- The original **243-word live Mara S1 scene** is frozen as an isolated,
  read-only candidate set of nine event proposals. **All remain HOLD** and
  no world/production canon is modified: JEV had previously returned ESCALATE
  and the event-time/extractor schema is still incomplete.
- Test suite is fully offline; no model requests and no LUMI production DB
  writes. The status string `APPLICATION` and SHA equality bindings are
  NOT authentication; a trusted server-side review/capability adapter remains
  necessary before deployment.

## M3.4 typed model event / JEV / EventGraph bridge

- [Architecture and validation boundaries](./M3_EVENTGRAPH_BRIDGE_V04.md)
- `typed_event_bridge_v04.py`: strict per-event required-key/ID validation, canonical v0.2 reducer mapping, source SHA/offsets and unknown-time preservation. Empty Gemini-style arguments are HOLD, never auto-completed.
- `m3_event_graph_bridge_v04.py`: compares independently normalized proposals, revalidates JEV claim identity, produces **non-committable** EventGraph drafts and optionally shadow-replays physical invariants with zero DB writes.
- `mara_s1_v04_audit.py`: read-only recheck of the exact archived 243-word first Mara scene; **9/9 event candidates remain HOLD**, bench and pencil remain unregistered, prior live JEV ESCALATE not overturned.
- Tests are offline. No real JEV provider authentication, independent gold qualification, accepted real-world state, or production DB integration is claimed. Fingerprint equality and `authority=APPLICATION` text fields are not a security boundary.

To inspect the real scene's unresolved findings without model calls:

```bash
python -m experiments.sera.mara_s1_v04_audit
```
