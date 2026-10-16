# SERA v0.9 — Real Chromium UI Qualification

**Date:** 2026-10-16  
**Experiment branch:** `experiment/sera-scene-state-v0-1-20261015`  
**GitHub Actions evidence:** [run 38858676688](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38858676688)  
**Workflow:** `.github/workflows/sera-state-engine-tests.yml`  
**E2E code:** `experiments/sera/browser_e2e_v09.py`

## User-visible objective

Verify that the offline HTML blind-review workspace works in a **real
browser**, beyond Python unit tests or a JavaScript syntax check.

The test is synthetic software quality assurance. It is **not real human
adjudication** and does not produce human gold, grant model authority,
qualify semantic coverage, or apply a world-state transition.

## Actual test sequence

1. Generate Mara's **28 frozen sentences** into reviewer A/B standalone
   HTML workspaces, each with an independent empty review form.
2. Start real **headless Chromium**, load reviewer A from a local `file:`
   URL and check 28 navigation buttons, 0/28 initial progress and title.
3. Navigate to the actual watch-case-closure sentence. Classify the
   sentence as `STATE_EVENT`, fill existing entity decisions and notes.
4. Attempt to create an event citing the **fabricated** quote
   `the train definitely arrived physically`. The browser **blocks**
   the event because this phrase is not an exact source quotation.
5. Add a lexicon-missed candidate entity `new:watch_case` with exact
   source evidence `case` and typed presence decision.
6. Add the real `CLOSE` event, citing `closed the case` with
   `OBSERVED_ACTION`, `OBJECT` effect and linked entity references.
7. Navigate to the actual `Arrival recorded: 02:10` statement and
   preserve it as `CLAIM_MENTION` / `REPORTED_CLAIM` / `NONE`
   rather than physical train arrival or an action timestamp.
8. Switch back to the first edited sentence. Confirm that the event,
   new entity sighting and reviewer notes remain in the UI.
9. Trigger a real **browser JSON download**. Re-open it with the existing
   Python validator `review_forms_cli_v08.validate_file`.
   Confirm two reviewed / 26 unreviewed sentences, no gold approval.
10. Load a fresh reviewer A tab. Use actual browser file-import to restore
    the downloaded JSON. Verify source evidence and notes, then download
    again and compare the full JSON round-trip exactly.
11. Try to import reviewer A's JSON into the independent reviewer B
    workspace. Reject cross-reviewer source/role mismatch without
    changing B's 0/28 review progress.
12. Open reviewer B at mobile viewport (390 × 844), navigate to the
    watch-case sentence, ensure its source text remains accessible.
13. Capture and assert **zero uncaught browser JavaScript exceptions**.

Each step runs automatically on the branch CI using Playwright Chromium.
The Playwright package and Chromium are **test dependencies only** and
make no model/API requests. The command can be repeated locally:

```bash
python -m pip install playwright==1.56.0
python -m playwright install chromium
python -m experiments.sera.browser_e2e_v09
```

## Verified outcome

- Offline Python test job: **257/257 PASS**.
- Browser E2E job: **PASS**; `SERA_BROWSER_E2E_VERIFIED_GREEN`.
- `source_bound_object_added=true`.
- `fabricated_event_blocked=true`.
- `source_claim_kept_reported=true`.
- `download_python_validated=true`.
- `json_roundtrip_exact=true`.
- `cross_reviewer_import_blocked=true`.
- `mobile_navigation_passed=true`.
- `browser_javascript_errors=0`.
- Real human reviews created: **0**.
- Valid Mara gold / real canonical commits: **0**.
- Paid LLM calls: **0**.
- Explicit model output token ceilings: **none**.

Run artifacts:
- `sera-browser-e2e-38858676688`: the machine-readable pass/hold proof.
- `sera-mara-s1-browser-review-v09-38858676688`: offline HTML reviewer
  A/B pages, blank JSON forms and instructions.
- `sera-mara-s1-unreviewed-worksheet-38858676688`: source-bound
  analyst-suggestion worksheet **not suitable for blind reviewers**.

All output is evidentiary/noncanonical; production database unchanged.

## Next decision gate

We have now qualified the offline review UI as *software* on real desktop
and mobile Chromium. The next missing input is **genuinely independent
reviewer A/B decisions** on the 28 Mara sentences.

Once actual reviews are supplied, use:

```bash
python -m experiments.sera.review_forms_cli_v08 validate \
  --review reviewer_A_unverified-NOT_GOLD.json --require-complete

python -m experiments.sera.review_forms_cli_v08 validate \
  --review reviewer_B_unverified-NOT_GOLD.json --require-complete

python -m experiments.sera.review_forms_cli_v08 compare \
  --review-a reviewer_A_unverified-NOT_GOLD.json \
  --review-b reviewer_B_unverified-NOT_GOLD.json \
  --output mara-s1-adjudication-queue.json
```

The comparison is not an authenticated adjudication. A genuine third-party
decision and trusted provenance are required before registering gold labels.
Until then, do not calculate real Mara recall/precision or claim its first
canonical exit state was accepted.

Original Sonnet Spine and story prose are unchanged.
