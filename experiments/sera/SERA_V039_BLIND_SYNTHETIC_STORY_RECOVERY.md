# SERA v0.39 — autonomous blind synthetic scene extraction + repair

**STORY FIRST / OFFLINE LAB ONLY / NONCANONICAL.** This increment uses SERA's existing v0.10 sentence-sweep code with a deterministic synthetic model-double callback. It never pretends that the scripted answers are independent real LLM competence, genuine physical authority or complete semantic proof.

## Implemented pipeline

1. v0.37 SQLite ScenarioLab supplies the **current shared-world revision**. A story run belongs to one focal character, while physical state is shared with other characters in the same world. The focal writer context remains separate from validator-only world state.
2. v0.10 `create_plan` constructs a blind request from the exact source prose, sentence offsets, registered aliases and lexical cues. The double receives this source-only request and previous error codes but never receives the author's event list, independently pinned reducer fixture, character's private facts, writer extraction, SQL state or an authority grant.
3. A synthetic answer is bound by the REAL `sentence_sweep_v010.bind_batch` function. Real `aggregate` checks sentence and lexical-entity/action coverage. Initial missing watch mention triggers `SWEEP_MISSING_ENTITY_HINT`. First-try fabricated Elin sentence quote fails the real strict binder. Automatic re-extraction uses another scripted response and re-runs both checks.
4. v0.39 accepts only one complete, observed, source-bound MOVE or TRANSFER event per single-sentence test scene. More sentences, omitted candidate events, reported assertions or conflicting cues fail closed. A globally scoped deterministic event ID prevents duplicate local v0.10 IDs across scenes.
5. **Separately supplied synthetic fixture** contains the exact permitted v0.2 event and fingerprint. The model cannot change the world action, its authorized actors, location, timestamp or approval by guessing a self-issued grant.
6. v0.38's real v0.24 spatial/v0.25 relation proof, v0.5 route feasibility, v0.2 independent reducer parity and SQLite CAS run before any lab event commit. Failure yields `FAILED_SAFE_FINAL`; no bad event is written.
7. Upon success in the lab, watch OWNER Mara stays unchanged, HOLDER transfers Mara → Elin, and then the watch travels with Elin to hallway. World revisions 0 → 1 → 2 and SQLite hash-chain replay confirms determinism.

## Negative tests and guardrails

`tests/test_blind_story_recovery_v039.py` exercises missing physical entity detection and source-bound automatic re-extraction, fake quote repair by a new complete reply (never edit the underlying prose), omitted source event, reported speech rather than observed physical fact, explicitly blocked wrong recipient, hidden writer data, SQLite restart/replay, synthetic retry exhaustion and proper `FAILED_SAFE_FINAL`. No manual review is a runtime step.

`blind_ensemble_smoke_v039.py` emits a machine-readable two-scene summary. The self-hosted CI workflow runs it and archives the report separately from existing v0.38 synthetic continuity evidence.

**Boundaries:** `max_attempts` bounds *synthetic extraction attempts* only; no application-defined model output-token cap. This lab-only callback runs no external provider and assumes no paid request may have been made. Do not replace it with a billable callback before adding durable provider receipt/request-ID reconciliation and anti-double-charge recovery. SQLite events are **fixture-authorized simulated state**, never canon. The real v0.6 scene-assurance result remains **HOLD** because no independently proven semantic completeness or native trusted physical G2 source exists. An autonomous terminal `FAILED_SAFE_FINAL` is returned; a production-durable terminal journal and true provider recovery are **not yet implemented** by this increment. The original frozen Mara S1 remains HOLD; no production LUMI integration, migrations, DB writes or main merge.

## Next targeted increment

Add a durable per-scene attempt/response journal and a restart-capable synthetic provider transport. Then connect the blind requests and re-extraction to the existing StoryForge-composed runner under strict paid receipt/idempotency policy, prove independent semantic completeness across multi-sentence and multiple-event scenes before considering a live model call. Keep Origin and Saga only as reserved test identities until STORY is qualified.

[Tracking Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
