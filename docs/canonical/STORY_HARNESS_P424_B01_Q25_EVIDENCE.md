# P4.23 / P4.24 — Genuine B01 Pilot English Master → read-only Q25 evidence

**2026-10-13** · Draft PR #275 · quality issue #291

## Actual status, not a mocked success claim

The B01-r06 generated 516-word manuscript is genuinely source-bound:
- Input synthetic Canon source SHA `91854710f46db13ee2599d567ca2fcbbcd945af50515a779ddee58211ee050dc`
- Original Spine SHA `daafc25a6701a8369be994000e71669722c1cb56364bce3559f5fb8ca944f7a9`
- Original Writer SHA `cbbf3ba8cb3a9ec5d19ed51238bc3b9a0259237cdb7896b75dcdd0584adca912`
- Separate independent initial quality `ACCEPT`, reader score 4/5, zero blocking findings, actual auditor bill $0.021066; **not a replay of original full frozen v21.4 final audit**.
- P4.23 pilot-only English Master sealed **on actual q25-offline GitHub runner**, in `$RUNNER_WORKSPACE/_lumi_p423_master_claims/b01-cbbf3ba8cb3a9ec5/`. Exact Master file bytes verified SHA equal original Writer SHA, unchanged 516 words, no text edits, **no new API charge**.
- Pilot English Master is **not** production Master, no LUMI production state update or main merge, and the synthetic B01 Canon is not production Canon.

## P4.24 actual Q25 candidate

`src/story_harness_p424_q25_evidence.py` loads original protected B01-r06 Spine, Writer, settled receipts, P4.22 independent acceptance receipt and sealed P4.23 pilot Master; it refuses to even prepare a paid request unless **all hashes and provenance agree**.

The provider uses one tightly bounded Anthropic Sonnet 5.5 request via existing GitHub Actions OpenRouter key, after an explicit one-use workflow trigger. The strict schema is a flat response envelope containing a JSON-encoded string of evidence observations; rich nested provider JSON Schema previously caused HTTP 400.

Candidate fields:
- Final protagonist location and **verbatim** quotation from last 40% of the source story.
- Newly discovered locations (only Canon-allowed locations) and verbatim quotations.
- Up to six object mentions/relations, verbatim supporting quotes. **Ownership remains UNKNOWN** even if protagonist carries the object; no invented owner.
- Exactly one status and quote per original open obligation, no dropped or duplicated obligations.
- Unknown facts preserved verbatim. Numeric world-time delta **null**, never invented.
- SHA-linked source, model generation ID, actual provider token/cost receipt, no automated retry.

Each quote must appear in the original English Master text; the final-location quote must appear in its closing section. Model output can yield an **evidence-grounded Q25 PROPOSAL only**: semantic state certification, English Master production acceptance, mutable Canon commits and LUMI production writes stay **false**. A future independent final-state confirmation is separately required. `Q25` GREEN cannot be claimed solely from mocked tests or a model schema parse.

**Budget:** User approved $10 aggregate real inference. The B01-r01–r03 and earlier P4.19 uncertain invoices reserve $1.08; verified known provider charges after P4.22 total $0.138350. Conservatively reserve $1.218350 prior to P4.24. The distinct one-shot Q25 stage cap is $0.050; remaining conservative amount after reserving it is $8.731650. Actual provider charges are still distinguished from reserved exposure, and stage application checks are not a hard provider-side account limit.

## Next
1. Run P4.24 once against actual sealed B01, inspect evidence/receipt.
2. Build independent deterministic state-transition validator P4.25, explicitly tracking unknown ownership and unproven obligation closure; retain no production writes.
3. Test multiple state/topic/age cases with real Spine/Writer/Quality/Q25 and a separate holdout. Only accept >=90% if all required stages and human-independent literary validation succeed; never extrapolate from B01.
