# P4.56 — Per-run CI checkout isolation and paid workflow retirement

Scope: PR #275, experiment/story-harness-control-plane-v1. CI only; no production deploy, provider POST, or story admission.

## Root cause
Run #38605300591 B05 offline failed in actions/checkout@v4 with Git exit 128 / not a git repository before any test. Runner q25-offline-isolated used the shared default checkout workspace. This is not a model or quality verdict. Repeated PR synchronizations also queued historical paid stages.

## Controls
1. All 23 historical one-shot workflows (22 *-once.yml and one p417-paid-one-shot.yml) remain versioned, but have only workflow_dispatch and job-level if: ${{ false }}. PR synchronization and manual dispatch cannot execute these archived jobs. Reopening requires a new reviewed one-shot workflow.
2. All 16 other existing story-harness workflows use checkout path and defaults.run.working-directory matching: ${{ github.job }}-${{ github.run_id }}-${{ github.run_attempt }}. Run IDs and attempts prevent inter-run directory collisions within Story Harness CI.
3. These 16 workflows no longer trigger only because their own YAML changes. Their source/test/evidence paths remain intact. P4.56 is the single targeted offline guard for workflow-definition edits.
4. New P4.56 guard checks workflow invariants, B05 STOP, diagnostics, B06 final state and B07 source. No provider secrets or model requests. Use one batch commit and focused offline CI.
5. Durable claim roots under RUNNER_WORKSPACE remain untouched and are not cleaned up.
6. Previously queued runs are not cancelled retroactively by editing workflow files; inspect them separately.
7. Separately invoked historical non-Story-Harness self-hosted workflows may still use a shared default checkout. They are outside the scope of this PR and must not overlap with these tests until runner-wide isolation is confirmed.

## Invariants
- B05: STOP_UNKNOWN_OR_INVALID. Existing STOP evidence unchanged; not accepted.
- B06: independent-quality ACCEPT, frozen English Master, real Q25, read-only Final StoryState. Existing evidence unchanged.
- B07: not admitted. The former P4.55 one-shot is archived; any subsequent paid phase needs a new explicit idempotent grant and offline PASS.
- Aggregate user cap USD 10; existing conservative reservations unchanged. New provider spending authorized here: USD 0.
- main and production unchanged.

## Acceptance
P4.56 is confirmed only when the dedicated offline guard CI has actually executed targeted tests and completed success. Queued/skipped/cancelled is not GREEN.
