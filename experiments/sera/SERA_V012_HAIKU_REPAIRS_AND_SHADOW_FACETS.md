# SERA v0.11.1–v0.12 — Independent Repairs and Shadow Facets

**Date:** 2026-10-16  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Mara S1 frozen prose SHA-256:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`

## Real independent model findings

The original blind Gemini extraction covers **28/28 sentences** with
**25 source-bound event candidates** and remained
`HOLD_MODEL_SEMANTICS_UNVERIFIED`.
We then asked independent Haiku 4.5 to review three narrow, source-only
questions about exact risk sentences. Gemini answers were not included in
those requests.

The first run [38863339302](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38863339302)
paid **USD 0.001252** for **task_001** and stopped because Haiku returned a
complete JSON document inside a Markdown code fence, with a straight
apostrophe instead of the prose's curly apostrophe. Actual
`finish_reason=stop`; **not token truncation**.

- **task_001 — s014, `MOVE` vs attention:** Haiku proposes
  `STATE_OBSERVATION / OBSERVE / CHARACTER_KNOWLEDGE`. Mara orienting
  to the strike record is not physical locomotion. The original Gemini
  proposal `MOVE` is unsuitable for a character-location transition.
- **task_002 — s018–s021, notebook continuation:** Haiku proposes
  `DOCUMENT_WRITE / WRITE / DOCUMENT`. The phrase `She paused, then
  added` follows writing to Mara's notebook; the source supports a
  candidate document append, **not speech**. Actual additional paid cost
  **USD 0.001472** in run
  [38865139580](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38865139580).
  This run stopped because provider text used straight double quotation
  marks instead of the original typographic quotes; again,
  `finish_reason=stop`, not output truncation.
- **task_003 — s004+s011, open watch then closure:** Haiku proposes a
  directly observed open watch followed by a separate closing action.
  The open state is a baseline *observation*; the closure is a state
  transition. Actual added cost **USD 0.001511** in run
  [38865604842](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38865604842).

**Total Haiku cost: USD 0.004235.** Total original Gemini
S1 sweep cost: **USD 0.053514**. Combined provider-reported diagnostic
cost: **USD 0.057749**. These are measured bills for this experiment, not
a future production price estimate.

## Strict source recovery — no repeated model charges

`haiku_evidence_recovery_v011.py` and
`haiku_historical_replay_v011.py` parse only a complete JSON object or
a single complete Markdown JSON code fence with **nothing preceding or
following it**. They can map exact-length, uniquely located typographic
apostrophe or double quotation marks back to the original source
substring. They preserve the raw model quote, exact source quote,
normalization method, response hash, provenance and original request
digest. This recovery is **not** a semantic correction and never
establishes physical truth by itself.

Paid task_001 and task_002 were reused via their original response IDs,
costs, digests and run manifests. They were **not** re-requested during
the continuation runs.

Actual artifact forensic replay was verified at
[run 38864797880](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38864797880).

## v0.12 correction proposals

`mara_s1_candidate_corrections_v012.py` consumes **actual archived**
Gemini full scene evidence and all three archived Haiku opinions.
It strictly binds both model sources and then emits only **two
noncanonical event corrections**:

1. `batch_004:s014:e1`: `MOVE` to `OBSERVE`, preserving the source,
   preventing an unsupported location mutation.
2. `batch_006:s021:e1`: `COMMUNICATE` to `WRITE` with
   `mara_notebook` as the target document. This target binding remains
   an evidence-supported **proposal**, not a proven database update.

It also emits **three typed aspect projections**:

1. Observe `vane_watch.openable.case_position: UNKNOWN → OPEN` based on
   the watch being described as open.
2. Later apply `OPEN → CLOSED` based on `closed the case`; scene/source
   order is enforced without inventing an absolute action minute.
3. Append exactly `Discrepancy documented; explanation unknown.` to
   the *observed additions* ledger for `mara_notebook`.

These were independently rebuilt from actual provider artifacts:
[run 38866189103](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38866189103).

## Shadow aspect projection

`shadow_aspect_projection_v012.py` has strict, pure deterministic
compare-and-swap semantics for two NEW PROPOSED facet families:

- `openable.case_position`: `UNKNOWN`, `OPEN`, `CLOSED`, with a
  source-observation guard and no `CLOSED` from unproven `UNKNOWN`.
- `document.written_entries`: verbatim, exact-source `APPEND`,
  preserving `preexisting_content="UNKNOWN"`. It never assumes the
  notebook was previously empty.

It validates existing v0.2 world identities and SHA, exact source spans,
monotonic narrative evidence offsets, replay detection, no arbitrary
model event times, and immutable input World State. Its isolated
projection does NOT use `world_state_v02.apply_event` or write SQL.

`mara_s1_shadow_projection_v012.py` ran the actual Mara source-backed
correction proof through this reducer successfully at
[GitHub Actions 38866515258](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38866515258).

Verified:
- **320/320 Python tests PASS** plus existing Chromium UI E2E gate.
- Shadow watch case final state: **CLOSED**.
- New observed notebook entries: **1**.
- Prior notebook document content: **UNKNOWN**.
- Original World State hash **unchanged** before/after projection.
- **Zero** canonical DB writes, **zero** claimed real action timestamps,
  **zero** additional provider calls for the shadow stage.
- Semantic qualification, gold verification and true canonical state
  commit: **NOT achieved**.

## Remaining acceptance blockers

This is NOT the full Mara S1 exit world state. In particular:

1. Extend the canonical ontology/reducer with separately reviewed
   `OPENABLE` and `DOCUMENT_APPEND` type contracts. The shadow types
   are not substitutes for canonical schema migrations.
2. Approve real physical entity introductions: bench, pencil, watch-case
   part/identity, documents; distinguish body parts from independent items.
3. Independently check all 25 event candidates, including movement
   versus holding objects, reported beliefs, speaker/listener knowledge,
   and any missed actions.
4. Confirm temporal feasibility without promoting clock readings or
   document timestamps to the actual scene clock.
5. Make an authenticated, qualified authority decision with an
   audit/rollback plan before any WorldStore+EventGraph commit.
6. Benchmark recall/precision against genuine blind human gold
   separately, for calibration; production should not require manual
   annotation for each story.

**User rule:** No application-configured LLM output token ceiling was
sent during these v0.11–v0.12 calls. Provider internal caps are outside
the application's control; our two previous errors were fenced JSON
and typographic quote differences, not evidence of a model reaching an
output-token ceiling.
