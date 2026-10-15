# Story Harness P4.57 — B07 original Generation Paid Gate

Scope: PR #275, draft branch only. No production or main changes.
Purpose: B07 (25 years, Fenerdeki eski mektup, 1,800–2,800 EN words). Generation alone is not quality ACCEPT.

## Why a new gate
- P4.56 archived 23 historical paid one-shots. P4.55 v02 run #38605301285 SKIPPED its provider step.
- The previous P4.55 grant JSON is absent. A newly reviewed grant gate is required.

## Additional trigger-scope correction
Historical 16 offline Story Harness workflows are now source-branch push filters, not pull_request paths. GitHub pull_request paths match the entire accumulated PR diff, which had enqueued 16 old checks on every synchronization. Push paths apply to newly pushed changes only. P4.56 remains the central targeted PR guard; one B07 explicit grant gate remains PR-synchronize only and checks exact HEAD diff.

## Two explicit commits
1. Commit only gate, checker, tests and docs; no grant. Only offline CI runs.
2. Only after offline CI GREEN, create sole configs/story_harness_p457_b07_trigger.json in a separate commit.
3. Gate requires PR #275, expected branch, synchronization event, attempt 1, and HEAD diff containing exactly the new grant file. No ordinary PR updates or reruns may POST.

## Offline preflight
- Exact frozen B07 source SHA, age, model, source constraints and output caps.
- B05 original quality STOP receipt hash and denial of Master authority.
- Prior conservative reservation $2.859558, maximum new spend $0.35, aggregate user-approved limit $10.
- Reject existing B07 r06 claim in both historical v01 and v02 runner roots; refuse symlink roots.
- Targeted B07, B05 STOP, B06 final-state tests. OpenRouter credit check is read-only. Unknown credit or inappropriate key stops.

## Single bounded real execution
- Reuse protected v02 B07 claim root with atomic exclusive child creation; no fresh alternate retry root.
- At most two provider POSTs (original SpineForge then Writer), no retries; uncertainty consumes the claim.
- Upload immutable story artifact if any. Output remains NOT_YET_AUDITED; no English Master, Q25 or production Canon writes.
- No further paid stage until independent quality and explicit budget revalidation.

Acceptance: P4.56 offline CI must finish SUCCESS; queued/skipped is not sufficient. The B07 grant must be the only HEAD file modification.
## Post-generation archival
P4.57 run #38611801159 completed with immutable B07 model receipts and $0.093066 reported provider charges. The consumed P4.57 workflow is retired with job-level false guard; no PR update may launch the original B07 generation again. New work is independent quality P4.58 only.
