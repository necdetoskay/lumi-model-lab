# Story Harness P2.2 — Real version-pinned SpineForge deterministic gate replay

**Status:** experiment / Draft PR #275, 2026-10-13. **No production permission.**

P2.1 executed the genuine frozen Q25 source/structural validator twice, but had
not executed any SpineForge gate. P2.2 now executes
`src.spineforge_v19_validator.validate_narrative_spine()` from the exact
source commit `2eb3d825b5baf8f0f16ccb23805f619d433c7236`.
This V19 deterministic contract/authority validator is the component used
by the V20 SpineForge topology. **This does not rerun the V20 LLM product
gate or independently authenticate the historical human's approval.**

## Frozen original inputs

All input bytes originate from the same verified commit and archived case:

- Historical v20.2 approved Spine: `evidence/spineforge-v20-human-review/36910614976-approved.json`
  (byte-identical to P1 frozen archive).
- Original island ContextPack V20:
  `data/specifications/story_lab/age12_island_not_on_any_map_spine_context_pack_v20.json`.
- Original age-12 obligations: single FROZEN case in
  `data/specifications/story_lab/spineforge_v20_qualification_cases_v1.json`.
- Exact checker modules: `src/spineforge_v19_validator.py` and
  `src/spineforge_v19_human_review.py`, to verify the actual Spine hash.

The source checkout is verified clean at the exact immutable commit,
and each source module, ContextPack and obligations fixture has its own
hard-coded SHA-256. Archive source path and SHA must match the pinned
source file. The P2 archived receipt/integrity gate is regenerated before
any subprocess invocation.

The only subprocess executes a fixed inline launcher which imports
the **real pinned SpineForge validator and typed Pydantic contracts**.
No shell, model provider, OpenRouter keys, dynamic commands, repair loops,
or automatic fallback. Python/PyYAML/Pydantic are installed into the
offline CI interpreter; stdout, execution time and provider environment
are bounded.

## Actual validator results

| Check | Real pinned result |
| --- | --- |
| Spine content hash vs historical approval | MATCH |
| ContextPack id and fingerprint | MATCH |
| `validate_narrative_spine()` | EXECUTED, PASS |
| Story family, age and required decision | VALID |
| Discovery turns | 8 |
| Credible real-choice options | 2 |
| Derived location sequence | 6 points |
| Authority, reveal constraints, obligations | all true |
| Additional billable model calls/cost | 0 / $0 |

This is an *offline deterministic authority and structure* result, not
independent verification of narrative quality, causal completeness, age-fit
prose, content claims or the human approver's identity.

## Provenance and explicit stop conditions

- The historical `ACCEPT` and `APPROVE` fields are **not rewritten**.
  They remain historical, unauthenticated claims; no new human approval exists.
- No proof that the separately archived failed Writer audit and two Q25
  stories belong to the same story as this approved spine.
- `spine_writer_q25_same_story_handoff_verified=false`,
  `downstream_execution_authorized=false`,
  `state_commit_authorized=false`. Model calls and cost are exactly zero.
- Archived approval mutation, ContextPack mismatch, wrong source commit,
  changed source SHA, fabricated receipt and forged downstream authority
  fail closed. A clean source/hash alone is not a semantic acceptance.
- P2.2 does not let the original `story_writer_authorized` historical
  field become current execution permission.

## Offline reproduction

```sh
git worktree add --detach /tmp/lumi-p22-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7'
export STORY_HARNESS_PINNED_SPINE_ROOT=/tmp/lumi-p22-source
python -m unittest discover -s tests -p 'test_story_harness_p22.py' -v
python -m src.story_harness_p22 --repo-root . \
  --pinned-spine-root "$STORY_HARNESS_PINNED_SPINE_ROOT" \
  --verify-report evidence/story_harness_p22/pinned-real-spine-offline-replay.json
```

The checked-in receipt is regenerated and exact-compared by CI,
including the genuine deterministic validator output and the immutable
P2 integrity receipt digest. The separate P2.1 genuine Q25 validator still
runs independently on two **different stories**.

**Next P3:** Locate or freeze actual SpineForge + Writer + Q25 artifacts
for one SAME story, pin all manifest/raw/ledger hashes and implement read-only
lineage identity checks with fail-closed mismatch rejection. This must not
automatically create a story, declare quality PASS, or admit Final StoryState.

No main merge, no production changes, no paid calls.

