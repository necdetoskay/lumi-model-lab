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

## P4.24 first actual Q25 attempt — fail closed, correction loop

The first paid Q25 execution on [workflow #38461314321](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38461314321) initially failed **before inference** due a broken self-hosted Git checkout (`.git` absent). The q25 runner's disposable working tree was quarantined and recreated, leaving the durable B01-r06 source, initial audit and pilot English Master claims untouched. The separate [offline CI #38461314072](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38461314072) was rerun and returned GREEN. The original Q25 job was then rerun because no model POST claim existed.

The subsequent genuine Q25 call ended in `STOP_UNKNOWN_OR_INVALID`; the original validator caught but suppressed its precise reason and actual usage. **No final-state evidence result was admitted**, no repeat model request and no production write. [Immutable failure receipt](../../evidence/story_harness_p424/b01-r06-q25-v01-failed-consumed.json) has null billed cost, not a zero-dollar verified invoice. Conservatively reserve an additional **$0.050** (application-stage declared maximum, not a provider billing guarantee). Previous total conservative exposure becomes **$1.268350**.

Same-method fixes before alternative:
1. Record **safe reason codes, provider model/generation ID, output finish reason, verified usage/cost even when evidence validation rejects**, without logging response prose, credentials or raw API errors.
2. Clarify the exact nested JSON-string observation fields and valid enums in the prompt; ownership is always `UNKNOWN` at this stage, independent of possession.
3. New provider trial must use a distinct `p424-b01-r06-q25-evidence-v02` durable claim; old `v01` remains consumed. The corrected workflow uses a separate checkout directory so damaged shared git metadata does not abort paid work. No change to Spine/Writer/English Master, or Q25 evidence verification thresholds.

The additional next Q25 stage has a capped **$0.050** application allowance, so current conservative maximum reserved exposure after it is **$1.318350** out of the user's total $10. This is not verified aggregate provider billing. All other acceptance constraints and the production/Canonical write prohibition remain unchanged.
