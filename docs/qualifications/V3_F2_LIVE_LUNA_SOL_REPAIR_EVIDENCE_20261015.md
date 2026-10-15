# F2 autonomous story quality — real-model first-attempt evidence

**Live run:** https://github.com/necdetoskay/lumi-model-lab/actions/runs/38709109136

## Real provider observations

- Initial audit: GPT-5.6 Luna, one HTTP 200 POST,
  generation gen-1792054531-1njIAYUaOK7SoxqISQGb,
  23,727 input tokens, 2,266 output tokens,
  cost USD 0.0086508.
- Luna examined all nine canonical semantic defect families and
  found exactly one serious local state_continuity issue: the
  narrative has first, two reset and final readings (four), while
  Ilyan's recap says 'Three timed readings.'
- Local repair: GPT-5.6 Sol, one HTTP 200 POST,
  generation gen-1792054551-g29kkJqfM6xwTzjL5ZIY,
  14,938 input tokens, 58 output tokens,
  cost USD 0.075847.
- Sol returned its OWN model-authored old/new exact replacement:
  original text 'Three timed readings. A control stone that never moved.'
  candidate text 'Four timed readings. A control stone that never moved.'
- Total two paid calls USD 0.0844978. No third model POST,
  no accepted narrative and no translation/world-state commit.
- The first guarded execution stopped safely with
  MODEL_REPAIR_NOT_IN_FLAGGED_SPAN. This was a false
  rejection of the model-authored replacement because the
  original guard expected the entire old substring to remain
  inside a single flagged sentence. Sol had included the next
  unchanged sentence as exact context.

## Permanent external guard correction

The external experimental story qualification guard now:
1. Requires exact source-location equality between Luna's
   validated finding quote and the model proposal.
2. Requires Sol's original old substring to appear exactly once.
3. Allows a proposal's old/new strings to include adjacent sentences
   ONLY if ALL bytes outside Luna's flagged quote remain unchanged.
4. Enforces minimal replacement growth and word-change boundaries,
   plus original final punctuation and sentence count.
5. Keeps the original frozen runtime and story bytes unchanged.
6. Re-runs deterministic hard guards and calls Luna to verify the
   revised story; no story is accepted without a real fresh recheck.

The exact real Luna and Sol provider JSON outputs are now archived
as read-only evidence under
evidence/v3-f2-autonomous-quality-38709109136/.
Their hash locks are:
- Luna JSON: 7d2a67f89372fe1c65868b8f3dd64dea946685c161536e0af2cc45af958ac189
- Sol JSON: 3865c48f43929da6f10b577a72a00d2d81cc0d7a4bee3219c74b3e775946d0b3

End-to-end offline regression with stored real model payloads:
106/106 PASS and all 43 original frozen V3 files PASS. The
post-repair Luna response in the offline positive test is
**synthetic**, not a real adjudication or qualification.

## Required next stage

Do NOT re-run the original Luna + Sol sequence merely to
correct this external matching bug. That would repeat previously
paid requests and violate the exhausted one-use grant.
Instead prepare a new one-stage pinned Luna re-audit that consumes
the actual archived Luna/Sol records, mechanically applies Sol's
already-authored patch and requests at most ONE new Luna verdict.
That requires a new explicit, case-specific paid permission,
globally one-use GitHub claim, verified original source SHA hashes,
and zero manual changes to the story. If the new Luna verdict
finds a serious/critical issue, STOP and record evidence.
