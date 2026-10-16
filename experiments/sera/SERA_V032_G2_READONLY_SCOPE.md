# SERA v0.32 — Project_LUMI G2 Read-only Authority Boundary

**Status:** isolated MODEL LAB preflight only; no Project_LUMI code or
production database modifications. The experiment is not production
worker integration, publisher approval, or canon persistence.

## Verified real Project_LUMI contract, not invented IDs

Read-only source inspection of \`necdetoskay/Project_LUMI\` main:
- \`packages/story/src/db/schema/story/g2-story-contract.ts\`:
  exact household/profile/universe/worldInstance/primaryCharacter scope,
  StoryIntent, immutable context snapshot, StoryContract and required
  frozen universe+world revisions/fingerprints; character snapshot refs
  live under \`story_contract_snapshot_refs\`.
- \`packages/story/src/db/schema/story/g2-story-production.ts\`:
  ACCEPTED ProductionRun and AcceptedStoryArtifact with the **same
  scoped contract**, G2 \`storyFingerprint\` (domain-specific) and
  original English story bytes.
- \`packages/profiles/src/db/schema/profile/g2/story-state.ts\`:
  character state snapshot and head IDs, revisions, fingerprints, and
  versions. The G2 story snapshot must match the current head.
- \`packages/story/src/application/g2-story-outcome-commit.service.ts\`:
  real G2 transactional, stale-head and scope-checked outcome publisher.
  SERA v0.32 **does not call this service** and never generates its
  input/authorization.

The prior
[Final V3 F2 G2 authority resolution](../../docs/qualifications/V3_F2_G2_READONLY_AUTHORITY_RESOLUTION_20261015.md)
recorded \`AUTHENTICATED_G2_BINDING_NOT_AVAILABLE\`: no authenticated
StoryContract, accepted run/artifact and universe/world/character
heads for that source were available from repository artifacts alone.
This is NOT proof that corresponding database records do not exist.

## v0.32 implementation

[Source-scoped G2 bridge](./g2_readonly_scope_bridge_v032.py) accepts
an injected \`readonly_lookup(contract_id)\` backed in production by
a genuine, application-authorized, read-only G2 reader. The reader's
complete returned row set MUST be independently authenticated by a
trusted \`verify_source(rows, provenance)\`. A document claiming to
be "signed" without this verifier is untrusted.

Only after the application verifier has authenticated the exact
row-set digest and source does the bridge check:

1. All five production UUIDs are syntactically valid, requested from
   the trusted scope and identically scoped across Contract, Intent,
   accepted ProductionRun, AcceptedStoryArtifact and Character ref.
2. Contract ID, Intent ID, production run ID and accepted artifact ID
   link exactly; the Intent is STORY_STARTED and the run ACCEPTED.
   Generated character names, story locations and profile config IDs
   are not substituted for any production UUID.
3. AcceptedArtifact \`storyText\` is **byte-for-byte** the StoryForge
   English master. G2's domain \`storyFingerprint\` is *not falsely
   treated as raw SHA-256*.
4. Frozen and live Universe/WorldInstance revision IDs and
   fingerprints match; character state snapshot, revision,
   fingerprint and current head version match.
5. Exactly one CHARACTER_STATE contract snapshot ref links the same
   original character state fingerprint and snapshot.
6. The lab WorldState SHA is kept as a separate fingerprint; it is
   **not** claimed to be the native G2 world fingerprint or
   production canonical state.

\`run_readonly_g2\` then passes a read-source fingerprint-bound
\`trusted_scope\` into the existing [v0.28 StoryForge
adapter](./storyforge_bridge_v028.py). That adapter already checks
the exact StoryForge request/result, source slice, model profiles and
durable job contract. v0.32 **forces dry-run**: no provider POST,
no billing grant, no production write, no G2 commit request, no
StoryOutcome mutation.

A changed accepted text, stale world/character heads, wrong
household/profile/world, tampered signed rows, missing authority,
alternate contract or differing signed snapshot on the same job
will fail closed. There is no human override in the worker.

## Regression and limits

[Tests](./tests/test_g2_readonly_scope_v032.py) use **synthetic UUIDs
and a laboratory HMAC signer** solely to model the external trust
boundary, including invalid signatures, cross-world/profile/character
scope, unaccepted runs, different story bytes, stale heads, missing
character refs, immutable job drift and zero provider calls.

**Still absent:**
- A *real* authenticated Project_LUMI read-only source service
  returning the rows, verifying server-side scope and cryptographic
  proof of origin/freshness. Neither GitHub source access nor an
  internally consistent JSON file authenticates live database
  existence. Never mount production credentials into Model Lab tests.
- A real production WorldState-to-SERA typed registry projection:
  G2 world fingerprint != SERA local simulated-world fingerprint.
  Trusted locations, character IDs, knowledge facts, objects and
  policies require their own read-only app-owned projection and
  evidence. Client-supplied aliases are not an authority source.
- A production SERA Job/StoryForge runtime integration and real
  billable unseen-story full qualification, with cryptographically
  scoped spend grants, durable provider receipts and provider-side
  lost-generation reconciliation.
- Authenticated transactional G2 StoryOutcome/WorldState commit with
  concurrency fencing and rollback tests in a separate isolated
  environment. An editorial PASS or SERA scene PASS is not a canon
  grant. Frozen Mara S1 remains HOLD.

No application LLM output-token limit or mandatory operator review
has been introduced. No production data or original Spine changed.

Epic: [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
