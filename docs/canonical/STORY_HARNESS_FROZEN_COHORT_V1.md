# LUMI Story Harness — Frozen 10-Story Cohort V1 / $20 Aggregate Authorization

**2026-10-14 · Draft PR #275 · MODEL LAB ONLY · Canon and production unchanged.**

The user approved an increase of the **aggregate** LUMI Story Harness test ceiling from $10 to **$20**, inclusive of prior spent/unknown/reserved exposure. **Budget authorization is not automatic paid-run authorization.** Existing P4.15/P4.17/P4.37/P4.57/P4.58 historical $10 assertions, recorded receipts, grants and evidence remain immutable. A new cohort executor must be separately implemented and admitted before any paid batch. This V1 policy and CI perform zero provider model calls.

## Fixed cohort: no story-by-story fixes

1. First establish a genuinely operable, end-to-end harness (canonical input → SpineForge → Writer → independent full-story quality → immutable English Master → original Q25 → read-only Final StoryState), pinned model/profile, all prompts, quality gates, repair limits and stage-specific cost policy.
2. **Before B01 starts**, seal one baseline harness commit and SHA-256 digests of all eleven logical components plus a SHA of each of the ten frozen synthetic input cases. Status remains `PREPARED_NOT_FROZEN` until that separate freeze is proven.
3. Run B01–B10, two per age 4/10/12/25/40, with **identical baseline harness**, regardless of how many REJECT. Do not patch prompts, models, code or quality thresholds, selectively retry failures, or edit story prose. An already-frozen stage-local bounded repair remains permissible exactly as implemented.
4. Preserve **all ten attempt outcomes**, including failures, and only then run the cross-cohort root-cause analysis. Distinguish quality failures from provider/CI/unknown-charge stops; no fake ACCEPT or QC self-attestation. An operational or safety STOP can suspend the batch: never break fail-closed protection merely to finish ten. A suspended/incomplete cohort cannot be presented as a finished ten-story quality experiment.
5. Rank common defect families across the cohort by prevalence, severity, root-cause stage, and regression risk (causal, spatial, temporal, response, closure, epistemic, age, spine, narrative, Canon/state, provider). Record multiple findings per story and trace source spans; no single-story patches.
6. Implement the smallest shared corrections as **Harness V1.1**. Freeze V1.1 separately; **re-run the exact same ten input states/topics/ages** from scratch. New real model generations and independent blinded reviews must be recorded; prior story text is not a fresh run.
7. After paired comparison, test ten **unseen** preregistered cases without further tailoring. Keep the published ten-case pilot and independent holdout distinct. A 9/10 sample is not proof of 90% reliability; the original >=27/30 unseen release benchmark still stands.
8. Every actual sample SUCCESS needs genuine producer and independent auditor evidence, reader score >=4/5, same-story English Master, real Q25 and evidence-grounded read-only Final State. An offline green is not a successful story.

## Budget (planning bound, not live reconciled invoice)

- Aggregate user-approved upper ceiling: **$20.00** (not $20 additional).
- Last documented conservative prior reservation after P4.58 approval: **$3.249558**; this may be stale and is NOT a verified OpenRouter invoice or available credit.
- Indicative full new trial maximum: SpineForge + Writer **$0.350**; independent quality **$0.040**; Q25 **$0.050** = **$0.440**. Actual stricter stage limits still apply.
- Fresh baseline 10 plus paired regression 10 maximum reservation: **$8.800**.
- Ten unseen holdout trials: **$4.400**.
- Historical documented reservation plus 30 planned trials: **$16.449558**, illustrative headroom **$3.550442** ONLY if historic ledger remains reconciled and no other spending/unknown charges exist.
- Before the first baseline paid attempt: reconcile **all** provider receipts, unknown-charge holds, previously committed budget, provider credit availability, and full ten-case future reservation. If full batch cannot be reserved, **do not start**. No automatic retries or unapproved fallback.
- Earlier source code and grants still enforce $10. **They are not silently upgraded by this document**; a separate reviewed V1.x executor and grant policy must enforce the $20 aggregate ceiling safely before any billable batch.

## Evidence and contract

- `configs/story_harness_frozen_cohort_v1.json`: prepared freeze protocol and budget bound, not an inference grant.
- `src/story_harness_frozen_cohort_v1.py`: validates unchanged original ten-case matrix, budget envelope, freeze rules and future per-attempt lock; counts claims without certifying them.
- `tests/test_story_harness_frozen_cohort_v1.py`: anti-tamper, forbidden mid-cohort changes, ten-of-ten completion, no fake ACCEPT and no silent over-budget.
- `.github/workflows/story-harness-frozen-cohort-v1-offline.yml`: deterministic offline-only CI.

**Next exit gate:** independently seal a complete real production-path-equivalent Harness V1.0, pin code and input SHA, reconcile real ledger, then authorize ten distinct paid attempts through a separately reviewed runner; no new model calls in this phase.

## Previously consumed grant hygiene

The original B07 P4.58 genuine quality call already returned ACCEPT in CI #38613825422. Its old PR-synchronize workflow was archived as `workflow_dispatch` with `if: ${{ false }}`, since GitHub PR path matching can retrigger old consumed grants when later commits modify unrelated files. The follow-on run #38617164730 failed **at the exact-file grant gate**; all quality/provider POST steps were skipped and this run did not create a second model call. Future cohort workflows must never inherit one-shot grants from historical branches.
