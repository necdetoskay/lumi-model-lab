# Story Harness P2.1 — Genuine pinned Q25 offline source gate replay

**Status:** experimental / Draft PR #275. **Not a Final StoryState acceptance.**
**Date:** 2026-10-13. **Original paid runs are historical and immutable.**

## What P2.1 actually runs

P0 used mock archives. P1 imported four genuinely recorded historical cases
without executing their validators. P2 added *executed local archive integrity*
gate receipts, but no original stage validators.

**P2.1 now executes the original Q25 validator implementation**
`src.q25_extractor_adapter.offline_replay()` in a **distinct pinned Git
checkout** of source commit
`2eb3d825b5baf8f0f16ccb23805f619d433c7236`, using the **unaltered
original paid Sonnet raw extractions** for KITE-01 and GREENHOUSE-01. The
checkout must be at exactly that commit with a clean tracked tree, and the
validator entrypoint bytes must have the pinned SHA-256
`a562d4c96f3c99ee7014f1de5df24765edbb4d223b029ff6a57cdddaf8bce992`.

Q25 seed, prose and policy are extracted from the original `request.json`
files at that pinned commit; request byte SHA hashes are pinned separately.
Each raw result is required to match both the P1 archived frozen SHA and its
original path at the pinned source commit. This is an executable source-bound
validation call, not an assertion copied from a public ledger.

- Fixed `python -m src.q25_extractor_adapter` command, no shell expansion
- Only explicitly version-pinned `pydantic>=2.8,<3` dependency
- No model/provider secrets passed to the subprocess
- No `OPENROUTER_API_KEY`, network request, fallback or billable API
- No automatic retry on failure; subprocess is bounded and fails closed
- JSON stdout is parsed and strict rejection/authority flags remain enforced
- Verifier source/run snapshots are a **hash/clean-checkout integrity check**,
  not a code-signature or a human-identity authentication

## Actual verified outcomes

| Case | Original paid gate (historical) | New pinned offline replay | Coverage |
| --- | --- | --- | --- |
| KITE-01 | `SOURCE_BOUND_CANDIDATES_ONLY` | `SOURCE_BOUND_CANDIDATES_ONLY` | 57 fields, 13 CANDIDATE, 2 PARTIAL |
| GREENHOUSE-01 | **`REJECTED_BY_OFFLINE_GATE`** | `SOURCE_BOUND_CANDIDATES_ONLY` | 54 fields, 14 CANDIDATE, 1 PARTIAL |

**These two statements must not be merged.** GREENHOUSE paid attempt originally
failed for two **valid but reverse-ordered** supporting citations. The pinned
versioned code used in this later offline replay sorts only validated source
spans and records the exact audit **[1373,1190] → [1190,1373]**,
`SOURCE_POSITION_SORT_ONLY_NOT_SEMANTIC_REPAIR`. That does **not** revise
the original paid ledger, or prove the claim's semantic accuracy.

All model outputs remain `UNTRUSTED_SOURCE_QUOTED_CANDIDATES_ONLY`, pending
independent semantic review. No history is interpreted as an accepted terminal
state, and neither case is permitted to proceed to a production stage.

**SpineForge human/semantic verifier has NOT been invoked** in P2.1:
`spineforge_gate_invocations=0`. A future separate version-pinned adapter
must be defined for it; hash-inspecting a historical `ACCEPT` is insufficient.

## Reproducible commands

```bash
# Clone/check out the exact Q25 commit (no branch head accepted)
git worktree add --detach /tmp/lumi-q25-p21 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3'

export STORY_HARNESS_PINNED_Q25_ROOT=/tmp/lumi-q25-p21
python -m unittest discover -s tests -p 'test_story_harness*.py' -q
python -m src.story_harness_p21 \
  --repo-root . --pinned-q25-root "$STORY_HARNESS_PINNED_Q25_ROOT" \
  --verify-report evidence/story_harness_p21/pinned-real-q25-offline-replay.json
```

In CI the pinned Q25 source is independently checked out into
`_pinned_q25_source/` and the tests require this explicit source path.
The generated replay receipt is stored at
`evidence/story_harness_p21/pinned-real-q25-offline-replay.json` and is
fully recomputed on every run; stored decisions/authority flags cannot be
promoted or falsified without failure.

## Honest remaining limitations

1. No independent semantic/human verification, no quality verdict, no age
   appropriateness verdict, no world-time canon write.
2. Only Q25 **source/structural** offline gate was actually invoked; the
   original historical paid provider-side gate run was not recreated.
3. The source commit is an experiment branch's explicitly pinned SHA, not a
   production-approved deployment or an externally authenticated model.
4. The Q25 extractor is not yet orchestrated after a real SpineForge/Writer
   handoff of **the same story**. The two tested stories are separate from
   the stored SpineForge island story; no cross-story lineage is invented.
5. Any billable model registry/executor is outside this gate, requires
   a separate explicit budget and approval, and must remain fail-closed.

No production LUMI changes, no merge, no automatic retry and no new API spend.
