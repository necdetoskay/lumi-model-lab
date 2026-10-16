# SERA v0.22 — Fresh per-revision, unattended independent evidence worker

**Status:** Laboratory implementation only, on the isolated SERA experiment
branch. Absolutely no production/canonical WorldState/EventGraph writes or
changes to the frozen Mara Sonnet Spine. Model output-token ceilings remain
FORBIDDEN. No mandatory human review, prompt patch, approval, manual retry
or terminal review queue.

## Fixed gap

Previously a rewritten scene could reach v0.21's nonbillable source checker
without **fresh** independent evidence, and would fail safely rather than
re-extracting automatically. v0.22 supplies the missing, *separate billable
stage* before each nonbillable recheck.

### Real components connected

1. The v0.20 controller now accepts an optional
   \`prepare_evidence(prose, world)\` callback. It invokes this stage for
   **each new prose revision before** invoking \`check_scene\`. The
   preparer's required noncanonical success, exact prose SHA and world
   fingerprint, no human intervention and no DB-write indicators are
   checked. Its policy identifier is part of the resumable contract;
   switching policy on a partially processed scene is rejected. Legacy
   v0.20 use without a preparer continues to work unchanged.
2. [fresh_scene_evidence_worker_v022.py](./fresh_scene_evidence_worker_v022.py)
   uses the source-only [v0.10 sentence-sweep planner](./sentence_sweep_v010.py)
   for each revised scene (four target sentences per batch; NOT a token
   ceiling). Independent model rows, exact source quotes, sentence
   dispositions, entity mentions, event kinds/modality and lexical coverage
   are validated with \`bind_batch\` and \`aggregate\`. Required rows cannot
   be silently omitted.
3. The new independent risk audit invokes the existing
   [v0.18 semantic repair supervisor](./semantic_recovery_v018.py), which
   separately checks suspected physical/epistemic/document contradictions,
   with exact source provenance and saved paid receipts.
4. An **independent typed-facet proposal** request receives only the
   original prose, trusted registered object roles and immutable entry world
   (NOT prior models' sweep labels or response). All proposals obey exact
   v0.13 event fields and are checked for real, contiguous source spans.
   Critical CLOSE/WRITE events identified in the independent sweep cannot
   vanish from typed-event candidates. The v0.21 checker then actually
   runs the v0.19 and v0.20 semantic and typed CAS/replay validators.
5. A full versioned v0.21 evidence bundle is written atomically to the
   specific scene's evidence directory using the new prose SHA. A different
   world fingerprint cannot reuse/replace it. A missing export can be
   regenerated automatically from the saved paid provider responses
   without requesting the model again.

### Resilience & provider accounting

- All provider requests use SERA's reviewed OpenRouter transport and the
  no-output-token-cap guard. Raw provider replies are saved *before* JSON
  or source binding, keyed by model+request. If a complete, receipted answer
  is invalid, a separately configured fallback model may run automatically.
  Unconfirmed in-flight charges are never blindly retried.
- Source, immutable world, model choices, registry, lexicon and cost/request
  policy are fingerprinted in a resumable contract. Cumulative observed
  provider cost and request count are controlled; caps on request number or
  observed USD spend are NOT artificial model output-token restrictions.
- The semantic risk stage independently owns its durable replies; a restart
  includes cached spend once, never counts the same semantic receipt twice.
  Atomic checkpoints are flushed/fsynced. All failures return
  \`FAILED_SAFE_FINAL\` with \`world_db_writes=0\`, no human gate or
  invented world truth.

### Tested

The self-hosted Linux regression verifies two different versions of a
generic, non-Mara story: the first incorrectly closes a box without an
open baseline. The automatic v0.20 writer changes that scene; v0.22 then
**actually generates different independent source-bound evidence** for
the corrected prose, and v0.19/v0.20 re-audit the new version. The final
scene is only \`SCENE_CANDIDATE_READY_NONCANONICAL\`, NEVER a story commit.

Additional synthetic fault-injection covers stale evidence, changed world,
fabricated quote, unknown potentially paid call, observed-spend guard,
checkpoint replay and restoring lost exports without new provider calls.
No real model spend was incurred in these tests.

## Remaining blockers for release

- The integrated writer/extractor has been exercised with mock provider
  replies, not yet with a paid unseen-story end-to-end run. A production
  worker/model resolver and per-job durable archive location must be wired
  with real runtime credentials.
- v0.22's noncanonical evidence qualification handles source-complete
  sweep, semantic risks and typed openable/document facets; it is not
  proof that all possible event types, causality, knowledge isolation,
  movement, chronology, relationship changes and untyped events have
  production-ready authority. The full M2/M3/event/epistemic/fact
  qualification and independent quality gates remain required.
- Provider request-id idempotency/reconciliation for charges lost between
  sending the request and durable receipt is not implemented. It
  correctly fails safely rather than silently charging twice.
- Authenticated machine-only canonical authority and atomic
  WorldState/EventGraph commit/rollback remain **unimplemented**.
  Consequently the frozen first Mara S1 and production LUMI canon
  remain HOLD, regardless of the v0.22 laboratory PASS.

Tracked in [Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
