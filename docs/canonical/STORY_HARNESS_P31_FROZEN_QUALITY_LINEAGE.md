# Story Harness P3.1 — Frozen Writer quality / repair / reaudit provenance

**Status:** experimental, PR #275 Draft. **Date:** 2026-10-13.
No paid calls, no production writes, no English Master seal and no Q25 admission.

## What was validated

P3.0 already executes the genuine version-pinned SpineForge and Writer
deterministic source/manifest verifiers. P3.1 **reruns that P3.0 prerequisite**
and verifies an additional **65 pinned historical file roles** with SHA-256,
the exact pinned Git commit `2eb3d8255...`, and an immutable exact-cohort
manifest at `configs/story_harness_p31_pinned_quality_cohort.json`.

The manifest fingerprint and all expected run/cycle identities are hard-pinned
in the adapter. The source repository is a separate clean exact Git checkout,
not a mutable branch HEAD. It accepts no model provider environment,
remote commands, production state, or automatic retries. Stored receipts
are never accepted without full fresh recomputation.

### Actual same-story lineage

1. **Writer #3:** `36965340665`, exact story hash
   `e08f686cc06c5c5a65a86f4bd8f5069aabd04e9a818b2abea5305887ec53cf0f`.
2. **Story Audit #8:** `36990160527`. This audit passed a **known-defect
   detection qualification** (`qualification_pass=true`, `status=PASS`);
   the independent **story decision** remained `LOCAL_REPAIR_REQUIRED`.
   Historical Audit #1 `36969500342` had failed qualification with
   `FAIL_KNOWN_DEFECT_MISSED`, and *also* required local repair.
3. **Stage 6 original local repair:** frozen product
   `37006087948` references the exact Writer #3 artifact, story SHA and
   Audit #8 artifact ID. Its original repaired story file SHA and text hash
   match the frozen product.
4. **Stage 7 reaudit:** frozen product `37007924152` references Stage 6
   by artifact ID, source SHA, source file path and repaired-text SHA. Its
   actual recorded story decision is `LOCAL_REPAIR_REQUIRED`.
5. **Cycle 2 repair and reaudit:** original frozen products
   `37010331757` and `37014477600`, chained to Stage 6/7 and to
   the subsequent cycle 3. Original repaired text/file SHA values are
   checked separately.
6. **Cycles 3–9:** exact repair product/result/story/handoff bytes,
   reaudit product/result/handoff bytes and previous-cycle artifact
   identities form one uninterrupted historical chain. All seven successful
   recorded reaudits: `LOCAL_REPAIR_REQUIRED`, next stage
   `STORY_LOCAL_REPAIR`. Later-model semantic verdicts are **historical
   reports only**. No original paid model audits are rerun.
7. **Cycle 10:** repair `37204419845` produced another immutable
   story and next-handoff; **no completed cycle 10 reaudit** is in the
   accepted cohort. Do not imply story ACCEPT or seal.
8. **Failed alternative reaudit runs:** `37117361651` (cycle 4) and
   `37126453862` (cycle 7) remain
   `unhandled_story_quality_loop_runtime_failure` and are never selected
   instead of the separately verified successful completed runs.

## What PASS actually means

**Audit qualification PASS** means a test of the audit's ability to detect a
specified defect passed; it does **not** mean the story itself passed its
quality gate. The source report's `qualification_pass=true` MUST NOT
promote the story's `LOCAL_REPAIR_REQUIRED` decision.

The adapter returns:

- `full_cycle3_to_cycle10_lineage_ids_and_hashes_verified=true`
- `last_completed_reaudit_cycle=9`, `last_generated_repair_cycle=10`
- `last_verified_story_audit_decision=LOCAL_REPAIR_REQUIRED`
- `original_story_quality_accepted=false`
- `unreviewed_cycle10_story_pending_reaudit=true`
- `state=STOPPED_UNACCEPTED_STORY`
- `stop_reason=STORY_QUALITY_NOT_ACCEPTED`
- Provider calls 0, new provider cost $0, no state/admission/English Master
  or Writer/repair/Q25 stage execution authority.

P3.0's separate `MISSING_SAME_STORY_Q25_ARTIFACT` stop remains valid.
For future chronological stage execution, **quality rejection blocks before
a Q25 input could be admitted**. Neither stop is a license to call a model.

## Trust boundaries

- Full cryptographic **source-byte integrity + recorded metadata lineage**
  in an explicit historical cohort, not an independent semantic/quality
  certification, human-identity authentication, or production acceptance.
- Unlike P3.0's real structural validators, later original paid
  audit/repair/reaudit model validators are **not rerun**.
- A reported `full_story_reaudited` is a statement in the original
  immutable archive, not newly authenticated model reasoning.
- P3.1 does not compare subjective writing quality, declare FINAL StoryState,
  automatically start repairs or approve paid API.
- History includes many **historical** model calls/costs; new P3.1
  experiment calls/cost are exactly 0/$0. Historical costs must never be
  presented as new spending.

## Reproduce without external providers

```sh
git worktree add --detach /tmp/lumi-p31-source 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7'
export STORY_HARNESS_PINNED_P31_ROOT=/tmp/lumi-p31-source
python -m unittest discover -s tests -p 'test_story_harness_p31.py' -v
python -m src.story_harness_p31 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P31_ROOT" \
  --verify-report evidence/story_harness_p31/pinned-quality-chain-receipt.json
```

CI regenerates the full receipt and exact-compares it, and tests reject
changed inventory roles, substituted run IDs, skipped or reordered cycles,
mutated artifact hashes, manufactured ACCEPT, false re-audit success,
forged Q25/English Master authority, and state commits.

**Next gate:** independently qualify an actual completed, accepted
English Master artifact (if one exists) with immutable story hash,
reviewable quality evidence and original stage lineage. Otherwise stop;
do not start a billable Q25 call merely because the harness itself is GREEN.

