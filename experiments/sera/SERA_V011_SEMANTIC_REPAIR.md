# SERA v0.11 — Real Mara Semantic Risk Detection and Independent Repair Probes

**2026-10-16** · Isolated experimental development, original Spine untouched.  
**Source Mara S1 SHA-256:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)

## Why

SERA v0.10 obtained all **28/28** source sentence rows and **25**
source-bound candidate events from **7/7** completed groups.
Six new provider calls cost **USD 0.047925**. With the original
single batch **USD 0.005589** reused from immutable evidence, the
total provider-reported cost was **USD 0.053514**. No provider request
had an application-configured output token ceiling.

Even a complete sentence ledger can have **semantically incorrect events**
or over-triggered lexical warning signals:

- `Vane closed the case with his thumb.` has the physically supported
  model `CLOSE` event evidenced by `closed`. The independent scanner
  matched the longer `closed the case` phrase and incorrectly warned
  of missing action. This is a **false-positive coverage warning**.
- `recorded` inside the archive arrival quote that Mara copied to
  her notebook is **quoted document content**, not another real
  `RECORD` action. Previously it created a spurious repair probe.
- `She paused, then added, “Discrepancy documented; explanation
  unknown.”` was classified as `COMMUNICATE` with effect `NONE`,
  although preceding notebook-writing context strongly suggests a
  **document append**. This is a real semantic question.
- `Mara turned to the platform clock’s strike record` was classified
  as physical `MOVE` with `CHARACTER_KNOWLEDGE` effect. May be mere
  orientation/attention, not a new location.
- The earlier `pocket watch open in his palm` and later `closed
  the case` suggest a typed `case_open` state transition, but
  the initial physical property cannot be inferred blindly.

## Implemented

`semantic_risks_v011.py` consumes actual source-bound v0.10 output
and **never mutates it**. It checks exact evidence offsets, operation/effect
compatibility, writing context, quoted-document verbs, and potential
open-before-close state evidence.

The real-provider offline forensic
[run 38862521913](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38862521913)
identified **three targeted human/model review tasks**:

1. **Move vs attention:** `s014`.
2. **Document append vs speech:** `s018–s021`.
3. **Openable baseline for later closure:** `s004` and `s011`.

It also removed the **two misleading lexical gaps**, not by
suppressing model failures globally but by exact evidence overlap and
quoted-content context. All verdicts remain advisory.

The module generates source-only independent probe requests with
JSON-object responses and binds exact source quotes to source offsets.
The previous Gemini event type and diagnosis are intentionally absent
from the new model's prompt.

`mara_s1_haiku_probes_v011.py` is the new optional bounded live
second-opinion driver:

- Model: `anthropic/claude-haiku-4.5`, independent provider family.
- At most **three** source-bound tasks; no automatic retry or fallback.
- Provider-reported **USD 0.08 observed spend stop**, plus existing
  provider-key preflight. This is a dollar budget, **not** a token limit.
- Uses the vetted OpenRouter client with no configured output-token
  ceiling; stores every raw answer, request hash, cost and source-bound
  advisory result separately.
- Stops on missing cost, invalid JSON, invalid evidence or provider
  errors. Never rewrites text or commits EventGraph/WorldState updates.

The one-use workflow is:
`.github/workflows/sera-mara-v011-haiku-three-once.yml`.
It downloads the original verified risk report rather than
regenerating user/AI judgments. An isolated, branch-pinned, one-file
launch-grant commit is required before any paid calls.

## Evidence

[CI 38862839733](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38862839733)
**293/293 offline tests PASS**, real-browser E2E PASS.

The tests do **not** prove real Haiku response quality, semantic
recall or approval of Mara's first scene.

## Next acceptance

Read the actual independent second opinions.
If source-grounded `DOCUMENT_WRITE` is supported, generate a
provisional corrected candidate with `WRITE` and document aspect
changes, **without changing the underlying story prose**.
Qualify the watch-case `case_open` property and future
`writable.entries` reducer operations independently, then validate
state transitions and authority gating.

The first genuinely approved Mara S1 exit state has **not** been
created. No process silently promotes two-model agreement to truth.
