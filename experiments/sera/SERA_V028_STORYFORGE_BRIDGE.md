# SERA v0.28 — StoryForge source bridge and authenticated model preflight

**Status: ISOLATED EXPERIMENT, NONCANONICAL.** v0.28 does not deploy the
real LUMI story worker, does not authenticate a production WorldStore
commit, and does not authorize EventGraph/WorldState writes. Frozen
Mara S1 canonical remains HOLD. No charged provider call was made
during this development/test run.

## The real contract boundary

The code reads the existing first-party StoryForge contracts:
- **Input:** \`StoryForgeRequest\` v1 — \`request_id\`, \`active_world_id\`,
  profile ID, trusted direct/soft facts, story intent and generation
  profile.
- **Output:** \`StoryForgeResult\` v1 — identical request/profile IDs,
  \`publication_ready\` status, accepted English story, validated plan,
  context packet, independent editorial story/fidelity gate evidence,
  and proposed outcome.

[storyforge_bridge_v028.py](./storyforge_bridge_v028.py) accepts either
JSON-like Python dictionaries or already validated Pydantic models via
\`model_dump(mode="json")\`. It binds an EXACT scene substring of the
accepted English master to the source SHA. The StoryForge
\`publication_ready\` status is *editorial only*. A proposed state
change has NO authority to create/update canonical facts. Every scene
still enters the existing v0.22 fresh independent source extraction
and v0.19/20/23/24/25/27 causal/typed validators before it may earn
**SCENE_EVIDENCE_QUALIFIED_NONCANONICAL**. This is not full-story
publication qualification or proof of model semantic truth.

## Trust and billing protections

1. A caller-supplied \`trusted_scope\` binds request ID, active world ID,
   entry WorldState SHA and external policy version. An independent
   injected \`verify_scope\` must authenticate that complete application
   snapshot before accepting any source. Merely naming a world is not
   proof of authority. The laboratory verifier is deliberately synthetic;
   **no production signed world verifier has been connected yet**.
2. Every writer, independent sentence-sweep, semantic risk and typed
   facet model requires a resolved **exact**, qualification-ready
   profile. The bridge can consult the real repository runtime profile
   registry via \`real_profile_attestor\`; generic/fallback/unready
   model profiles fail before any billable request. It fingerprints
   profile, transport and production policy. The composed SERA
   provider client still performs its no-output-token-ceiling check.
3. A frozen work contract includes hashes for StoryForge request,
   StoryForge result, original English master, exact scene source,
   world snapshot, identity scope, model policies, trusted source
   registries, and the selected work controls. Resume with a
   different source/context/profile/world/policy in the same job slot
   fails closed.
4. **Default is nonbillable dry-run.** It can perform input, identity,
   profile and policy preflight and save the immutable fingerprint,
   but NEVER invoke a model. When billable execution is needed, the
   caller must explicitly set \`paid_authorized=True\`, provide a real
   authenticated \`paid_grant\` tied to this exact job, original result,
   world SHA and qualified model profiles, and an independent
   \`verify_paid_grant\`. It writes the grant digest before calling the
   existing durable SERA runner. A source's own model opinion, UI
   publication flag or a bare boolean cannot approve charges.
   The application may issue the scoped grant AUTOMATICALLY without
   any per-scene human button/review.
5. The paid worker archives complete provider envelopes prior to
   parsing, does not blindly resend a potentially charged missing
   response, can replay fully receipted responses after restart and
   re-runs scene-specific extraction for rewritten prose. All
   failure/success outputs explicitly deny production canon writes
   and operator intervention requirements.

These controls do not claim aggregate all-scene budget enforcement or
provider-side missing-response reconciliation; per-stage observed-spend
guards exist, but full authenticated LUMI budgeting and idempotent
provider recovery remain separate acceptance gates.

## Verified offline tests

[tests/test_storyforge_bridge_v028.py](./tests/test_storyforge_bridge_v028.py)
covers zero-call dry-run (even if a provider callable and key are
provided), exact StoryForge source/profile/ID matching, independently
passed StoryForge story+translation editorial gates, active world
scope binding, exact qualified model profiles, immutable job drift,
a complete v0.27 simulated model transport through StoryForge bridge,
receipt reuse without second provider call, denial of forged billing
grant, unavailable provider, and unchanged original WorldState.
All mocked model costs are synthetic; no billed provider calls.

## Remaining mandatory work

- Production-authenticated LUMI world/identity/verified-fact/route
  providers and signer/verifier for world and paid-job grants.
- Real LUMI Story worker/model resolver invocation into this bridge
  with durable job volume, proper scene slicing/scene planning,
  actual funded and authorized unseen-story proof, and cross-scene
  canonical boundaries.
- Existing historical StoryForge runtime has some hardcoded model
  output ceilings in \`src/storyforge/runtime.py\`. v0.28 does NOT call
  that generator and does NOT introduce new ceilings. Before routing
  an actual StoryForge generation through the future production bridge,
  remove those legacy configured output caps and requalify the
  StoryForge runtime under the user's no-output-token-limit policy.
- Provider-side idempotency/reconciliation of potentially billed
  responses lost before journaling, and machine-authenticated
  transactional WorldState/EventGraph commit/rollback with independent
  world-state qualification; none is authorized by \`publication_ready\`.
- Frozen Mara S1 and unseen full-story real-model end-to-end acceptance.
  Dry-run or mocked-provider PASS is not proof of live qualification.

No manual repair queue, manual JSON fixing, approval gate or restart
button will be added to the story runtime. No production DB write,
no LUMI main merge and no canonical Mara state changes.

[Tracked in SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
