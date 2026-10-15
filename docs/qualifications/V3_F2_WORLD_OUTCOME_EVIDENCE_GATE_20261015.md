# Final V3 F2 — Autonomous Outcome Evidence Gate (uncommitted)

## What is implemented

The English and Turkish delivery bundle is already staged and quality accepted. The approved F2 Spine proposes five conditional persistent outcomes. These are not committed facts. Do not turn the Spine's plan into a world-state mutation without reviewing the actual English story.

This separate external gate validates a future model's JSON decisions:
- branch must be one of seal_bounded_report and extend_testing
- source English and Turkish texts and candidate-manifest hashes are pinned
- all five approved persistent candidates must be addressed exactly once
- earned outcomes must include actual unmodified quotations from the accepted English story
- invented quotes, unsupported new candidates or missing rows fail closed
- the extend_testing branch can never earn the witnessed, signed-record milestone
- no source fiction editing, no publication, no persistent state commit is permitted

Files:
- experiments/v3_f2_world_outcome_evidence_gate.py
- prompts/v3_f2_world_outcome_evidence_judge_v1_generic.md
- tests/test_v3_f2_world_outcome_evidence_gate.py

## Scope boundary

These tests use SYNTHETIC judge outputs, not an actual model judgment. The validator checks source provenance and exact quotes but CANNOT independently guarantee that quoted text truly satisfies each narrative condition semantically; the future model must assess this. The gate returns only MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED and explicitly denies commit.

For live use, add a separately approved model call with a one-use grant and fixed model identity; archive the real model response and verified output. Then independently confirm target world-state schema, inventory/NPC referents, the chosen branch, atomic transaction behavior, idempotency and rollback evidence before any persistent database write. Do not invent a provider or spending authorization.

The existing English/Turkish accepted story, frozen 43 files and staged two-language package remain untouched. No new model costs or world mutations in this stage.
