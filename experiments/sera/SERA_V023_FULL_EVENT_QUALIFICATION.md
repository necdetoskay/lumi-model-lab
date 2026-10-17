# SERA v0.23 — All-event qualification and composed unattended lab worker

**Release state: EXPERIMENTAL / NONCANONICAL.** No production LUMI
story-worker integration, WorldState/EventGraph commits, authenticated
machine-granted canon authority, paid unseen-story proof or Mara S1 canon
exit is claimed. The frozen Mara Sonnet Spine remains immutable.

## What changes from v0.22

v0.22 already regenerated complete blind model evidence for every rewritten
scene source SHA and ran v0.19 semantic/temporal candidates plus v0.20
openable/document state CAS simulation. This did **not** mean every
reported event had a qualified reducer. A move, transfer, knowledge update,
untyped event or reported claim wrongly carrying a physical effect could
coexist with a successful watch/document simulation and the scene could
be mislabeled structurally ready.

[full_scene_qualification_v023.py](./full_scene_qualification_v023.py)
adds an explicit **full-sentence / all-candidate-event gate** after
the source-complete v0.10 sweep, v0.18 independent probes, v0.19 source
review and v0.20 typed reducer.

It checks:
- Exact original report and independent typed candidates are cryptographically
  bound by their SHA-256 digests to the v0.19 and v0.20 assessments. Neither
  another source nor a previous source revision can replace them.
- Every independently extracted event has a source-bound unique ID,
  sentence evidence, valid entity references and a coherent epistemic/effect
  distinction. A reported, negated, uncertain or hypothetical claim cannot
  carry physical/document changes.
- Unknown/unmapped or as-yet unsupported MOVE, TRANSFER, CHANGE_STATE,
  DISCOVER, KNOWLEDGE_UPDATE and similar durable effects cannot pass as
  if the *openable/document* reducer had simulated them.
- Physical state-changing event candidates have registered active references,
  and their typed proposals are supported by the independent sentence sweep
  (matching operation family, source sentence and overlapping evidence).
  The separately prompted typed model is not permitted to invent a state
  operation missing from blind extraction.
- Serious v0.10 lexical/identity/disposition gaps remain machine-visible,
  even when the narrow v0.19 risk-task set happens to be empty.

The result is either
\`FULL_SCENE_COVERAGE_CANDIDATE_NONCANONICAL\` or
\`REEXTRACTION_OR_REPLAN_REQUIRED_NONCANONICAL\`, with typed defects.
Neither means machine-verified truth or authorizes world writes. The
unsupported families must eventually gain their own actual reducers;
rewriting prose alone is not a substitute for these implementations.

## Integration

[artifact_scene_checker_v021.py](./artifact_scene_checker_v021.py)
has a \`full_qualification=True\` option that actually invokes the v0.23
gate on the exact archived v0.22 evidence, in addition to v0.19/v0.20.
The v0.20 controller accepts the third result, requires a consistent
source/world/no-authority contract, and automatically routes typed defects
to its bounded rewrite/re-extraction loop.

[composed_scene_runner_v023.py](./composed_scene_runner_v023.py)
provides a reusable **lab** entrypoint that connects:
- Original, frozen input prose and entry world
- Existing SERA cap-free OpenRouter-shaped writer with durable paid receipts
- Per-revision v0.22 independent sweep, risk review and typed extraction
- Actual v0.19/v0.20/v0.23 source/world-bound validators
- Crash/restart-safe bounded v0.20 automated scene controller

All models, trusted registered identity data and story context are
caller-selected application inputs, not model-created authority.
Their fingerprints are included in the resumed stage policy. The
composed runner uses injection in tests; no real billed model calls
or production DB writes were made here.

## Proof scope / remaining blockers

Self-hosted offline regression covers genuine integrated **mock transport**
for an unrelated box-scene rewrite and independent new-prose evidence,
a simulated MOVE misread invisible to partial object validators,
a reported claim falsely carrying WORLD effect, spoofed/swapped report
digests, independent typed operations missing in the blind sweep, stable
paid-response replay, changed immutable policy and browser E2E.

**Still required before production deployment:**
- Full typed reducers and validation for spatial movement, transfers,
  world-object relations, character knowledge/claim isolation, scene-to-
  scene causality, cross-scene temporal windows and every other real state
  mutation. Current blockers are fail-safe by design, not solved semantics.
- Authentic model resolution/runtime profile selection and production
  LUMI story-worker orchestration with per-story credentials/archive scope.
- Provider-side request idempotency/reconciliation of a potentially charged
  but not delivered response. No blind retry and no manual rescue queue.
- Authenticated machine-only canon authority, transactional
  WorldState/EventGraph commits/rollback and unseen, paid, end-to-end
  qualitative evaluation, including frozen Mara S1.
- No model output token ceiling, no mandatory human review/approval/
  patching/retry, no untracked canon writes.

Tracked at [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

## 2026-10-17 — Preserve source OPEN actions (v0.54 handoff)

The frozen Mara source says **"Mara opened her notebook"**. It is an
*actual action*, not just a passive statement that the notebook is open.
Earlier tests accepted `OBSERVE_OPENABLE` against a source `OPEN`,
which could silently erase the physical opening from the staged event trace.

The existing v0.22→v0.54→v0.23 path now enforces:
- An independent, source-bound `OPEN` requires a typed
  `SET_OPENABLE` action. `OBSERVE_OPENABLE` only supports independently
  extracted `OBSERVE` (a described OPEN/CLOSED state).
- In v0.54's detached multi-capability simulator, a source-explicit
  first opening/closing may use `SET_OPENABLE(expected=UNKNOWN,
  next=OPEN|CLOSED)` when the prior state truly is unknown. This **does
  not invent an opposite prior state** or authorize a canon transition.
  Later operations must match the last source-established state.
- The v0.22 typed request explains this rule only for the v0.54
  multi-capability path. The legacy single-facet v0.13 CAS contract is
  not silently changed.
- v0.22 early coverage, v0.54 independent source backing and v0.23
  whole-scene gate reject the passive-observation-for-opening substitution.
  New regressions exercise the exact frozen Mara quote and an independent
  two-sentence adversarial check.

[Offline self-hosted CI #39054833912](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39054833912)
verified 759 baseline + 138 v0.52 + 28 v0.53 = **925 Python PASS** and browser
E2E PASS at commit `bd8a47a2429e`. This is a **real correctness
invariant fix**, not proof of positive 28-sentence independently generated
Mara semantics or a Writer-repaired end-to-end result. Original Mara still
stops safely in the scripted empty-typed diagnostic; Issue #309 remains OPEN.
