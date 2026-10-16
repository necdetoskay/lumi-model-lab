# SERA v0.20 — Typed Aspect Recovery and Unattended Scene Rewrite Loop

**Status:** Experimental LUMI Model Lab modules, no production integration or canonical authority.  
**Owner requirement:** ZERO manual JSON fixing, human story review or approvals, operator retries, manual resume, scene-specific repair rulebooks and application-defined model output-token ceilings.

## What was implemented

### 1. Generic typed aspect transition recovery

[typed_aspect_recovery_v020.py](./typed_aspect_recovery_v020.py) accepts *untrusted* candidate typed events, original prose, versioned registered WorldState and an explicit role registry (openable objects / documents). It reuses the previously audited, pure v0.13 reducer, enforcing:

- Known registered active object and actor; immutable base world and no invented entity/physical train arrival
- Typed facet roles; exact source-sentence evidence, actor/object co-location and source order
- Openable baseline **UNKNOWN → OPEN/CLOSED by observation**, then validated compare-and-swap transition **OPEN ↔ CLOSED**, with no unsupported closure from UNKNOWN
- Append only exact verbatim existing source text to observed document additions; original document content remains UNKNOWN
- All-or-none isolated batch simulation with verifiable hash chain, original WorldState untouched, **zero** production writes or arbitrary event timestamps

Its apparent 'approval' data is strictly an **internal v0.13 OFFLINE_APPROVAL_FIXTURE simulation** and must not be presented to a production authorizer. Neither source binding nor reducer acceptance establishes that an actor truly operated the object: independent evidence and actual authenticated machine authority are still missing.

A v0.19 upstream semantic HOLD blocks scene readiness even if the isolated typed reducer simulation succeeds. Rejections are routed to machine-readable auto re-extraction/replan, not a human queue. This is not hardcoded to Mara; custom registered IDs and role bindings are exercised in automated tests. The current v0.13 reducer requires at least one openable and one document in a registry: for worlds lacking either type, v0.20 **fails safe** pending a genuinely generic schema extension instead of inventing an object.

### 2. Durable, unattended rewrite/recheck controller

[unattended_scene_rewrite_v020.py](./unattended_scene_rewrite_v020.py) introduces a restart-aware automatic loop with injected interfaces:

- \`check_scene(prose, world)\` MUST rerun the relevant offline v0.19 and v0.20 contracts for **every** candidate; its returned projections must match the exact prose+world fingerprint, carry no write permission and report grounded blocker evidence. This callback is **nonbillable by contract**; the actual story-worker adapters are not wired.
- On typed unresolved defects, \`rewrite_scene(source, defects)\` automatically receives the original affected source and verified defect codes. Its completion must include unchanged source fingerprint, model, provider reply ID, \`finish_reason=stop\`, and observed cost. It can return a revised prose; **the entire validator is then called again from scratch**.
- Atomic per-stage receipts, original input/policy fingerprint binding, replay without a duplicate paid call when the completion was saved, explicit safe stop on an unknown in-flight call (no blind resend), bounded number of *rewrite attempts* and observed USD guard (**not** output-token ceilings).
- A rewrite that does not change text, a fabricated receipt, changed source contract, missing actionable defect evidence, a provider failure or exhausted guard reaches explicit \`FAILED_SAFE_FINAL\`. No scene is handed to a human; no unsafe DB writes.
- Successful \`SCENE_CANDIDATE_READY_NONCANONICAL\` means **only** these source-bound structural checks completed. It does **not** qualify full sentence/event completeness, semantic truth, final story delivery or production WorldState/EventGraph commit.

The controller is reusable and fully automatic **given real worker adapters**. For now, unit tests inject pure synthetic callbacks and no paid model request is run. Unknown in-flight provider response recovery still needs real provider-side idempotency/reconciliation; silently resending is forbidden.

## Non-negotiable remaining work

1. Extend the registry/reducer to support worlds without every facet role and resolve generic object/part identity without trusting a single model.
2. Connect the scene writer/model resolver and full SERA M2/M3 sentence/event/causality/epistemic verification through durable versioned worker stages, not synthetic callbacks.
3. Implement provider request idempotency and automatic recovery after an uncertain-cost crash, without human action.
4. Independently qualify all scene-critical events; authenticate machine-only canonical commit authority; use safe transactional WorldState/EventGraph writes and rollback.
5. Run real unseen end-to-end stories with adversarial failure injection, then attempt full Mara S1 and nine-scene story tests without manual intervention.

**Mara S1 canonical state: HOLD. No production DB writes. Original Sonnet Spine remains immutable.** An offline PASS proves a software contract, not a complete self-healing production narrative.
