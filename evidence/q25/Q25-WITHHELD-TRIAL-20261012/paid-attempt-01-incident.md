# Q25 KITE-01 first authorized single-call attempt — HTTP 400 (2026-10-12)

**Scope:** First real OpenRouter production-like extractor request, using the self-hosted Q25 offline runner and the experimental branch. **Not a success, no state output generated.**

## Exact immutable run

- Run: [GitHub Actions #38280659568](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38280659568).
- Workflow event: `workflow_dispatch`, explicitly `case=kite-01`, `execute_paid=true`, model `anthropic/claude-sonnet-5.5`, ref `experiment/q25-narrative-memory-intent`.
- Code head: `98480a114ce3ee8a73887e84f1193785cfc086a0`.
- Offline job: **PASS**. Paid job: **FAIL** with strict `STOP` on HTTP 400. **No automatic retry.**
- Provider request POSTs: **1 attempted**; provider JSON completion: **none received**.
- Archived original ledger: `attempted_calls=1`, `provider_calls=0` (old ledger bug: it counted accepted JSON responses rather than POST attempts). Its original bytes remain frozen. The meaning is clarified here, not silently rewritten.
- Computed **worst-case upper bound $0.065928**, enforced call cap **$0.20**; actual provider charge **unknown / unreported**, not assumed to be $0.
- Original request hash `ac90ebfb54c2f0ab66f15237c665b1bfcb5328c34308ff11d7f5e3ba8841d536`.
- Frozen private evidence archive: [Artifact #11760629253](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38280659568/artifacts/11760629253) (7-day retention). Contains `request.json` and `ledger.json`; no completion, proposed state or token usage evidence.
- Reference answer key was never placed in the provider wire. No model TP/FP/FN can be computed for this attempt. Q24 historical rejection, LUMI production and canon remain unchanged.

## Offline root-cause investigation (not an asserted provider verdict)

The archived strict structured-output wire JSON Schema was inspected locally. It contained **14 `minLength` and 4 `maxLength`** keywords, plus `minItems`/patterns and normal optional fields. The authoritative Anthropic structured-output documentation states that **`minLength`/`maxLength` are not supported by its constrained decoding** and may cause HTTP 400:

https://platform.claude.com/docs/en/build-with-claude/structured-outputs

OpenRouter's JSON-schema feature documents schema/endpoint compatibility errors separately:

https://openrouter.ai/docs/guides/features/structured-outputs

The 400 **error response body was not archived** under the original privacy-preserving transport implementation. Therefore the precise provider rejection reason is **unconfirmed**; incompatible schema keywords are a concrete leading hypothesis, not guaranteed to be the only issue.

## Implemented offline correction (no second paid attempt)

1. `src/q25_openrouter_pilot.py:provider_safe_json_schema` transforms only the **model-facing wire schema**. Unsupported numerical/string/collection constraints are converted into field descriptions. No invalid `additionalProperties`, unsupported schema keywords, or excess complexity is permitted.
2. The **full original Pydantic `RawExtractorOutput` validator** still enforces local constraints on every returned response; bypassing model grammar constraints cannot let invalid source claims or oversized strings through.
3. A future HTTP failure now yields **only a safe diagnostic category**, without leaking provider error text, secrets or story body into workflow logs.
4. A rejected provider HTTP POST now records `attempted_calls=1`, `provider_calls=1`, and `billing_status=UNKNOWN_UNTIL_VERIFIED_PROVIDER_USAGE`, avoiding the former misleading `provider_calls=0` / presumed $0 accounting.
5. Regression tests cover all nested JSON-schema nodes, original local length validation, schema guard fail-closed paths, redacted error classification, exactly one rejected POST and unknown actual billing.

**Latest validated code CI:** [#38281428920](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38281428920), **305/305 PASS**, paid job **SKIPPED**. All code changes are still on Draft PR #273, not merged or deployed.

## Next gate / decision

The previous one-shot run is **spent as an attempt**, regardless of whether the provider charged for the HTTP 400. **Do not automatically retry or rerun failed jobs.** A new real model request must be a **new, separately approved workflow dispatch** of the corrected branch under the original $0.20 cap. Model output is still an untrusted hypothesis until exact source validation, per-claim evaluation against separately kept provisional labels, and genuinely independent whole-story semantic adjudication. A repaired schema alone is not proof that the provider will accept the next request.
