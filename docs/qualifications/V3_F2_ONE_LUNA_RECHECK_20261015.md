# Final V3 — one new Luna-only recheck using real archived Luna + Sol

## Why this is necessary

The first paid quality attempt (run 38709109136) used exactly two
models, Luna then Sol, costing USD 0.0844978. Luna correctly detected
the one real serious local numerical continuity issue, and Sol
proposed an exact, one-local-phrase replacement. The original external
guard rejected the Sol proposal only because it included one adjacent,
unchanged context sentence within the old and new fields.

**The original story has NOT been manually edited or accepted.**
There is NO reason to re-purchase either the initial Luna audit or
the already completed Sol repair.

## Permanently corrected, generic external rule

Commit 1a6491303977b0b9897037b82df7d3869a4d28d8 introduced a
strict and general text scope validator. The original model's
replacement is accepted ONLY if exact old text is unique, Luna's
exact quote has a verified character offset, all bytes outside
the quote remain identical in old/new, growth is minimal and
sentence-final punctuation does not introduce a new sentence.
This validator has no story-specific prose edit or human-approved
replacement.

Archived REAL model responses are SHA-256-pinned:
- Luna audit JSON: 7d2a67f89372fe1c65868b8f3dd64dea946685c161536e0af2cc45af958ac189.
- Sol repair JSON: 3865c48f43929da6f10b577a72a00d2d81cc0d7a4bee3219c74b3e775946d0b3.

## Separate final-Luna stage

The independent entrypoint is
experiments/v3_f2_quality_luna_recheck_probe.py.
It is NOT a retry of the old quality/Writer run. It:

1. Verifies all 43 frozen Final V3 source hashes and the exact
   original 2,767-word Aion Writer output/source hash.
2. Rechecks both original real provider JSON payloads, provider
   generation IDs, model order, exactly two POSTs, the stage STOP
   event, exact cost and the prior report/repair linkage.
3. Reconstructs the repaired candidate using ONLY the ORIGINAL
   model-authored Sol old/new patch, with no human-written text.
4. Runs the full deterministic hard-guard screen before any new
   provider request, treating provably negated cause claims as
   false-positive only.
5. Requires an entirely NEW paid English-quality-recheck approval,
   pinned guard commit and human budget reference; consumes a
   one-use local claim and requires a separately verified GitHub
   global run-bound claim BEFORE provider access.
6. Makes exactly ONE new GPT-5.6 Luna model POST for all nine
   canonical semantic families against the actually repaired text.
7. Accepts only if the REAL new Luna verdict returns zero serious
   or critical findings. The accepted English story is emitted
   ONLY after that, along with real generation ID and spend.
8. Keeps text length 1,600-2,500 as advisory. Never silently
   truncates the English story. No translation or world-state commit.

## Status

The paid model recheck has NOT happened yet. The latest
116/116 regression tests are OFFLINE: Luna's initial and Sol's
repair payloads are ACTUAL ARCHIVED MODEL OUTPUTS, but the
final Luna recheck verdict is SYNTHETIC in the tests.

Code-level max admission for the NEW recheck grant is USD 0.03.
This is NOT an owner-approved spending budget and is NOT a
provider-side hard billing limit. The previous USD 0.10 quality
grant was consumed and may not be used again.

No production, main or any of the 43 frozen V3 sources changed.
