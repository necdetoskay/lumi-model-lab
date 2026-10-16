# SERA v0.16 — Autonomous Repair Is a Mandatory Pipeline Stage

**2026-10-16** · Branch `experiment/sera-scene-state-v0-1-20261015`  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)

## Non-negotiable product rule

**No story repair may require a human to edit model output, manually rerun a prompt, hand-patch JSON, curate a per-story rules table, or perform a manual retry.** Repair is an **internal operation of the generation workflow**, not an offline forensic task assigned to a person.

This does **not** mean every ambiguous narrative fact may be guessed into canonical truth. Each automatic workflow must finish in a machine-readable disposition:

- `VERIFIED_CANDIDATE` — a corrected, exact-source-bound candidate; **not yet WorldState truth**.
- `ABSTAIN_UNRESOLVED_AUTOMATIC` — model evidence cannot support a safe identity claim; keep the original output and diagnostic trace.
- `SCENE_HOLD` — an indispensable event or entity remains unverified after all permitted automatic recovery; automatically route the whole scene to replanning/revision or controlled failure with status and evidence.

Administrative access and monitoring may inspect audit history, but **there is no mandatory human-in-the-loop correction step** in normal story generation. A future real commit authority must be a separately authenticated **machine-verifiable** workflow policy, not either model's self-approval. Enabling production commits requires additional gate and rollback work.

## New architecture

`identity_auto_repair_v016.py` is the reusable, story-agnostic repair router. Inputs: prose, original World registry, full model mention census, **original raw provider reply**, optional inexpensive targeted model callback, and durable checkpoint callback. No Mara-specific labels or v0.14 identity rules are read.

Automatic sequence:

1. **Archive original response** and bind to its request/source digest. Strictly parse pure JSON or one complete fenced JSON object; for known malformed `support_quote` serialization, only perform narrowly verifiable lossless string escaping.
2. **Partition by entity_ref**, preserving all other records if one is malformed. Duplicate or missing references do not invalidate source-bound peers.
3. **Exact source quote verification**, with only unique, length-preserving typographic apostrophe/quotation equivalence eligible for deterministic repair. Every transformed quote retains its original source/provenance.
4. **Closed-schema validation** of identity class, candidate relation, registered parent/region kinds, abstention and cycle consistency.
5. **Narrow conservative deterministic relation repair** when it does not assert a new fact:
   - For a physical-object candidate wrongly carrying `POTENTIAL_LOCATION_WITHIN`, discard this unapproved relation and its target; **do not** infer the object's location.
   - For a registered-region alias wrongly using general `POTENTIAL_ALIAS_OF`, normalize the type to `EXISTING_REGION_NAME_CANDIDATE` without performing an alias merge.
   - Do **not** silently turn `DOCUMENT_COMPONENT` into a `DOCUMENT_ENTRY` or change any object identity just to satisfy a schema.
6. **Targeted model repair** on only the still-invalid row. Give the error, source context, legal identifiers and closed types; the model can explicitly `ABSTAIN`. Validate its entire reply again by the **same** deterministic binder. It cannot commit anything.
7. **Automatic quarantine** of rows still unresolved after the configured attempt policy. Preserve original row, error code and decision. The pipeline does not await a human edit to finish its stage.
8. **Journal and finish**: exact source-bound candidate count, automatic abstentions, repairs, attempted model calls, all audit records, and zero WorldState writes. Every expected ref receives a recorded disposition.

The allowed number of model requests is an *operational reliability/cost guard*, **not a token-generation ceiling**. Application-configured `max_tokens`, `max_output_tokens`, etc. remain forbidden.

`identity_stage_v016.py` calls the original identity model and executes the above router in **the same stage invocation**, using an automatically called targeted repair model when appropriate. The stage persists original and targeted provider outputs and their event ledger; an operator does not have to call a separate recovery command.

The old `mara_s1_identity_auto_repair_cli_v016.py` and offline forensic scripts are **reproducibility and regression evidence only**, not the runtime workflow on which the system depends.

## Real paid Mara result, zero added cost

The actual archived v0.15 paid Haiku response (run
[38872615837](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38872615837), reported cost **USD 0.015781**) was replayed through the generic automatic router, without the hand-authored Mara identity hypotheses.

[Self-hosted live-source replay run 38875977497](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38875977497):

- 16/16 identity slots accounted for.
- **15** model proposals source-bound and retained.
- **3** conservative relationship schema corrections performed by code.
- **1** remaining ambiguous identity relation (`new:strike_record`) automatically quarantined as an abstention in this **offline** replay, because the second-opinion provider callback was intentionally disabled.
- **0 new model calls**, entity creations, relationship commits or WorldState writes.
- No manual editing of the original Haiku output and no original Spine change.

The fully automatic **model-targeted** path is covered by synthetic provider-injection tests: when a valid targeted answer returns it passes the binder and the previous 15 proposals survive; when it returns hallucinated identifiers/quotes, invalid JSON or fails, only the affected record abstains. Do not claim the real `strike_record` has already been successfully repaired by another live model.

## Acceptance and deployment status

[Offline state engine 38876361061](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38876361061): **387/387 Python tests PASS**, including the new single-invocation primary+targeted repair stage and runtime ledger tests.

**Important boundary:** This implementation and tests are in SERA's isolated experiment. It has **not** yet been wired into the production LUMI service, nor has a real multi-model WorldState+EventGraph canonical commit been approved.

Required before calling the whole LUMI production workflow autonomous:

- Integrate `identity_stage_v016.execute` into the durable story worker between extraction and state qualification; configure cheap targeted repair automatically through the central model resolver.
- Extend identical repair-disposition contracts across Spine planning, sentence coverage, event typing, causality, epistemic state and draft/Judge.
- Implement durable idempotent provider-call receipt/recovery (on crash, do not charge twice for an unknown in-flight response).
- Implement scene-critical versus incidental HOLD propagation, automatic replanning when needed, retry/circuit-breaker behavior and a machine-verifiable production commit gate.
- Verify on unseen stories with source-grounded automatic/adversarial benchmarks, differential independent-model probes and explicit semantic-risk metrics; **source binding is not semantic accuracy**. Human-authored gold may be used in separate optional research, but it is neither a production story-stage dependency nor an operator action to unblock a story.

**Status:** v0.16 identity self-healing stage and real archived-response offline qualification **PASS**. First fully approved Mara S1 canonical exit state **HOLD**. No human correction is required by the v0.16 identity-stage control flow.


## 2026-10-16 binding clarification — zero manual intervention at EVERY runtime gate

**Owner requirement (mandatory; supersedes every older human-review / 'human adjudicator' / manual-gold wording if construed as part of the production pipeline):** From the first Spine request to final scene state and story delivery, **zero required manual work**. Never require a user, developer or operator to edit output, supply scene-specific expected answers, rerun a failed prompt, approve extracted entities/events, adjudicate model disagreements, press a resume button, or manually release a HOLD. This requirement applies to *all* scenes, not only the v0.16 identity module.

The durable runtime must be an automatic state machine, not a reviewer queue:

1. Capture immutable source, prompt, model/version, response, provider cost, schema and checkpoint receipts. No application-defined model output-token ceilings.
2. Detect structural, semantic, missing-event/entity, object-state, causality, chronology, epistemic, scene-contract and continuity problems deterministically wherever provable, plus independent model-based challenge checks.
3. Apply narrowly safe deterministic repair; automatically use a separately routed low-cost model for uncertain/localized repairs; verify corrected results against the **same** source-bound schema, WorldState/EventGraph invariants, and independent verifier. Disagreement is not evidence of correctness.
4. If targeted repair fails, automatically re-extract, replan the affected portion, regenerate the scene/draft as necessary, re-run the **full** affected checks, and resume from a durable checkpoint without an operator.
5. On provider timeout, invalid JSON, unavailable model, or crash: persist recoverable receipts, schedule automatic idempotent retry/fallback/circuit-breaker transition with bounded *attempts and cost*, avoid repeated charge of an unknown in-flight request. Attempt limits are **not token limits**.
6. A noncritical unresolved observation can be quarantined with explicit provenance **only if** it cannot alter a scene-critical event, persistent entity, causal dependency or authorized state effect. An unresolved scene-critical fact may **never** be silently dropped, invented, or committed.
7. The scene enters the next step only after automatic qualification and machine-verifiable policy authorization. No model self-approval and no human approval prompt. On exhausted automatic recovery, transition to `FAILED_SAFE_FINAL` with a visible machine-readable reason, and no unauthorized world mutations; never remain in an indefinite `HOLD_WAITING_FOR_HUMAN` state.

**Meaning of HOLD:** An internal transient safeguard while automatic recovery/replanning proceeds, not an instruction to ask a person to fix the story. If no safe solution exists, report an explicit terminal failure; it would be dishonest to promise that every possible narrative ambiguity can always be resolved successfully.

**Nonnegotiable release acceptance:** End-to-end unattended execution on unseen stories, injected schema/provider/semantic failures, scene-critical vs incidental omissions, checkpoint/crash/restart replay, no duplicated paid calls, fully automated retry/replan/abstain/final-state transitions, and proof of no manual gate. Automatically constructed synthetic/adversarial reference fixtures and independent blinded model challenges can support tests, but their agreement is not objective semantic gold. Optional external human evaluation cannot be a hidden prerequisite for producing a story.

**Current implementation boundary:** v0.16 has this behavior within its experimental **identity-stage** scope (the live second-model success path is still unqualified). The **whole** production story pipeline does not yet meet this contract; Mara S1 remains noncanonical. Do not mark the whole-system checkbox complete until verified end-to-end.
