# Final V3 F2 — G2 production authority resolution (read-only)

## Actual verified situation

The accepted F2 English/Turkish manuscripts and Luna's five earned
narrative-outcome suggestions are immutable. The previously completed
G2 state mapping and seven synthetic rollback checks are not evidence
of a real production G2 StoryContract or a live state change.

Current resolution: **AUTHENTICATED_G2_BINDING_NOT_AVAILABLE**.
No authoritative G2 StoryContract, associated AcceptedStoryArtifact,
production run, contract-intent scope, universe/world heads or
character story state snapshot can yet be verified for this F2 case
using the available repository sources.

This is **lack of verified binding**, not proof that no matching row
exists in the production database.

## Actual Production G2 code read

Repo: `necdetoskay/Project_LUMI`, main SHA
`64fe6a7201978d09ce5c3a8f38e79f05f8e7f5f0`.

- `packages/story/src/db/schema/story/g2-story-contract.ts`
- `packages/story/src/db/schema/story/g2-story-production.ts`
- `packages/story/src/db/schema/story/g2-story-outcome.ts`
- `packages/story/src/application/g2-story-outcome-commit.service.ts`
- `packages/profiles/src/db/schema/profile/g2/story-state.ts`
- `packages/world/src/db/schema/world/living-universe/world-instance-plane.ts`
- `packages/world/src/db/schema/world/living-universe/universe-plane.ts`

**AcceptedStoryArtifact** references a scoped G2 StoryContract and
an Accepted G2 ProductionRun. Its *storyText* must equal the English
master byte for byte (UTF-8 SHA256
`990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8`).
Its *storyFingerprint* uses a separate production domain fingerprint
algorithm and cannot be assumed equal to raw SHA256.

Production G2 rows contain scoping UUIDs for household/profile/
universe/world instance/primary character; snapshot revisions and
fingerprints for universe, world and character. The actual
CharacterStoryState head must match the character snapshot by
snapshot ID, revision number, fingerprint and head version.
The accepted story source can only be verified by authenticated
production read-only access, not a speculative UUID or repository file.

## Offline verifier contract

`experiments/v3_f2_g2_readonly_authority_probe.py`

Given an **untrusted** JSON snapshot, it checks G2 structural scope,
contract intent, accepted production run, accepted story bytes,
universe/world frozen head consistency and current character head
consistency. Any mismatch stops.

**Important security boundary:** A syntactically valid, consistent
input JSON is NOT an authenticated production snapshot. This verifier
cannot grant commit rights or claim the row exists in production,
even if every synthetic row passes.

The default operation uses **no external source data or credentials**.
It emits `evidence/v3-f2-g2-authority-readonly-20261015/authority-resolution.json`
with:

- verified production authority = FALSE
- missing authoritative binding fields = 16
- G2 commit request = NULL
- provider posts, cost and database writes = ZERO
- original English/Turkish stories and V3 runtime unchanged.

The test suite includes a fully synthetic G2 row set and mismatch
cases for wrong scopes, bad or stale world/character heads,
missing production acceptance, story content hash changes and
attempted commit authorization.

## Next real integration gate

An **authenticated read-only** Project_LUMI G2 source must resolve
and return the matching production Contract, accepted ProductionRun,
AcceptedStoryArtifact, frozen Universe/World heads and CharacterState
snapshot/head. That source must supply *attested provenance* instead
of arbitrary client-generated JSON. Validate that exact story
bytes and identity chain match F2 before proposing any delta.

After that, run a separate isolated PostgreSQL transaction/replay/
rollback qualification against the actual G2 commit service. No
production write, migration or publication is authorized by this
stage.

No manually changed prose or authoritative UUIDs have been invented.
