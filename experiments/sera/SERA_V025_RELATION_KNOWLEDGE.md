# SERA v0.25 — Source-bound possession and verified character knowledge

**Release status: LAB / NONCANONICAL.** Isolated experiment branch; no
production WorldState/EventGraph writes, no original Mara/Sonnet Spine
mutation, no human stage approval, correction or manual restart, no
application-defined model output-token ceiling, and no paid model calls
in the integration tests.

## What v0.25 adds

[relation_knowledge_preview_v025.py](./relation_knowledge_preview_v025.py)
models two formerly unsupported kinds of persistent character-world
change, using a *pure detached* WorldState v0.2 snapshot and
application-owned trusted information.

**TRANSFER_HOLDER** (possession, not legal ownership):
- Requires one independently source-bound \`TRANSFER / OBJECT|WORLD\`
  event with an exact original quote and \`OBSERVED_ACTION\` epistemic
  status; reported allegations do not transfer physical belongings.
- The registered item and both parties must appear in the exact quote
  through application-owned identity aliases, and must be present in
  the independent source event's entity references.
- Sender is the old holder (compare-and-swap); receiver and sender are
  registered active characters at the item's same location. Worn items,
  imaginary recipients, unregistered objects and identity drift block.
- Only \`holder\` changes; \`owner\` does not. A contained/nested graph
  that lacks its own qualified reducer remains a safe blocker, not a
  silently broken relationship.

**LEARN_FACT** (character knowledge, not objective claim authority):
- Independently extracted \`KNOWLEDGE_UPDATE / CHARACTER_KNOWLEDGE\`
  event (or equivalent compatible source-bound operation) must show
  registered learning actor and exact source phrase.
- Fact ID must ALREADY exist in application-owned verified fact registry
  with \`truth_status=VERIFIED\`; the registered fact phrase must be
  quoted in the original prose. Neither a model assertion, a rumor,
  a negation, a hypothesis, nor a bare mentioned claim becomes
  canonical knowledge.
- The known-fact set is compare-and-swap checked (no duplicate
  learning) and updated only in the isolated preview. Existing world
  and all other character profiles remain unchanged.

The v0.25 preview is NOT proof that the source text is true, nor does it
grant production publishing permission. The application must govern the
identity alias and verified-fact registries; this laboratory worker
does not import them from an untrusted model's opinion.

## Full scene worker binding

The [v0.21 archived evidence contract](./artifact_scene_checker_v021.py)
has an optional \`relation_case\` scoped to each source+world SHA.
The v0.22 independent evidence worker can call a deterministic,
application-owned \`trusted_relation_builder\` after the new source
blind sweep. The trusted builder and \`relation_policy_id\` are included
in the durable resume contract and carried through the
[v0.23 composed runner](./composed_scene_runner_v023.py).
The [v0.23 full scene qualifier](./full_scene_qualification_v023.py)
only exempts relation/knowledge events from its unsupported-state
blocker when the complete source-bound v0.25 preview succeeds.
Without the trusted policy, unverified fact, exact quote, complete
source events or CAS correctness, the event remains a machine-only
re-extraction/replan blocker.

**Critical mixed-family guard:** v0.13 object facets, v0.24 movement
and v0.25 relation/knowledge currently simulate independently from the
same entry snapshot. A scene requiring more than one of these state
families could be causally inconsistent despite each individual PASS.
The all-event gate now returns
\`CROSS_FAMILY_STATE_ORDER_UNQUALIFIED\` in that case; a future single
ordered reducer must qualify the sequence before such a scene can
advance. The safety block requires no human adjudication.

## Regression proof

- [v0.25 isolated reducer tests](./tests/test_relation_knowledge_v025.py):
  same-location holder transfer, unchanged owner, verified character
  learning, duplicate fact, missing source recipient, false previous
  holder, other-region recipient, nested object, source quote forgery,
  missing fact registration, rumor status, uncertain/reported physical
  claims, source ordering and original-world immutability.
- [Full scene gate tests](./tests/test_relation_full_scene_v025.py):
  registered handoff and registered learning, missing trusted
  policy, reported handoff, rumored fact, cryptographic report
  binding, and mixed independent facet + possession ordering HOLD.
- [Composed mocked provider tests](./tests/test_relation_worker_v025.py):
  real v0.10 independent sweep, v0.18 semantic workflow, v0.19,
  v0.20, v0.23 and v0.25 lab composition using synthetic OpenRouter
  envelopes; original model receipts replayed without second charge;
  unknown or rumored facts fail safely.

## Explicitly not solved

- Objective fact verification and cryptographically authenticated
  knowledge/claim origins in the actual LUMI Universe (rumors/beliefs
  need a separate epistemic projection rather than fabricated truth).
- Legally transferring ownership as distinct from exchanging physical
  custody, consent/causality/receiver intent, co-moving nested containers
  and mixed temporal/physical/epistemic ordered transactions.
- Production LUMI story worker/model resolver binding; provider-side
  idempotent reconciliation when a charged reply is lost; transactional
  authenticated machine-only WorldState/EventGraph writes and rollback;
  real unseen paid stories and frozen Mara S1 canonical qualification.

v0.25 does NOT remove the canonical HOLD; it narrows the supported
state preview to two more conservative categories while keeping
unknown effects visible and safe.

[Tracked by Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
