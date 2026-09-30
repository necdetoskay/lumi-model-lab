# SpineForge v5 — Contract Tolerance

Status: FROZEN QUALIFICATION CANDIDATE

Runtime revision:

SPINEFORGE-CONTEXTPACK-FROZEN-v5

Implementation source commit:

dc128b4f09c7378632c25468d28999d2e55213e3

## Why v5 exists

v4 exhausted its three paid attempts before reaching Sonnet.

The archived paid outputs show progressive correction rather than random failure:
- Attempt 1 first failed on a scalar/list shape mismatch. Offline replay also exposes a latent missing COMPLICATION phase behind that first validation error.
- Attempt 2 fixed the scalar/list shape but still omitted COMPLICATION.
- Attempt 3 added COMPLICATION but omitted new_information on a DECISION beat.

The third defect is different from the second. A DECISION beat can legitimately choose among already-established evidence without revealing a new fact. Treating the absence of new information there as a fatal story defect makes the transport contract stricter than the story semantics.

## What v5 changes

The topology does not change:

SpineContextPack.v1
-> Aion 3.5 Mini Creative Architect
-> Sonnet 5.5 Structural Hardener
-> GPT-5.6 Luna Product Gate
-> STOP / human review

Writer remains unavailable inside SpineForge.

v5 adds a narrow application-owned semantics-preserving contract-tolerance layer.

Allowed deterministic tolerance:
- when a known list[str] field contains one scalar string, wrap the same string as a one-item list;
- when a DECISION beat omits new_information entirely, represent the absence of a new fact as an empty string;
- retain every v4 normalizer-integrity rule.

Forbidden deterministic tolerance:
- never create a missing COMPLICATION or other required structural phase;
- never create a beat, causal bridge, branch, evidence claim, outcome, location or story fact;
- never repair an authority violation;
- never transform a substantive structural failure into PASS.

## Why this is generic

The new rules are independent of Leyra, Ashen Gate, age 18 and the current premise.

They distinguish representation/no-op defects from missing story structure:
- string -> [same string] preserves one semantic item;
- DECISION.new_information="" asserts no new fact;
- a missing COMPLICATION remains a creative/structural failure and must go through revision feedback.

## Real paid-output replay

Archived v4 runs are stored in:

data/specifications/story_lab/spineforge_v5_replay_fixture.json

Zero-cost v5 replay proves:
- v4 Attempt 1: scalar/list shape is safely repaired, but latent missing COMPLICATION is still rejected;
- v4 Attempt 2: missing COMPLICATION is still rejected;
- v4 Attempt 3: missing DECISION.new_information is converted to a no-op empty string and the creative contract + ContextPack authority pass.

No paid inference is used by replay.

## Zero-cost implementation regression

Run 36699836485:

32 passed in 2.33 s.

A later workflow-only label correction also preserved GREEN regression.

## Freeze

26 runtime dependencies are SHA-256 locked.

Runtime source commit:

dc128b4f09c7378632c25468d28999d2e55213e3

After freeze:
- no runtime/prompt/workflow/model-profile patch inside v5;
- a frozen hash mismatch invalidates the active v5 case;
- revision feedback is data only and context-fingerprint bound;
- case-specific recovery code counts as qualification failure.

## First v5 case

Case:

spineforge.v5.age18.forbidden-cartographer.fantasy.01

ContextPack id:

mock.character.leyra:mock.world.veiled-marches.primary:forbidden_passage_reappears:5

Context fingerprint:

05a84e09aed48fb7e5f2d177647d7bf1aa50d293e561cfc9c54726ff3e8564b2

v5 spend before paid qualification:

0 calls / 0 tokens / $0

No v5 paid trigger exists at freeze time.

Next paid boundary:

SPINEFORGE_V5_ATTEMPT_1_AION_THEN_SONNET_THEN_LUNA_IF_ELIGIBLE

It requires explicit authorization.

Writer remains blocked.
