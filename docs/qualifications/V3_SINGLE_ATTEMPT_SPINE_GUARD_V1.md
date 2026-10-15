# Final V3 — external single-attempt Spine guard (OFFLINE ONLY)

Status: **not approved for paid dispatch**. Experimental protective wrapper on a new branch based on frozen original `63e1e3ce82c244bc5bb02b0463a9a1a6715c941b`. The original Final V3 source, 43 SHA-locked runtime files, prompts, and successful stories are unchanged.

## What is proved offline
- First timed-out POST => one wire attempt then STOP; no hidden retries.
- First HTTP 503/429 => one wire attempt then STOP.
- First malformed JSON => one wire attempt then STOP, no corrected prompt.
- On happy path, Spine Architect and Spine Gate are **two intentionally different provider model calls**, once each. Writer is never triggered; human Spine approval still required.
- Durable exclusive-created evidence records before each provider POST, with safe status/ID/cost after each successful provider response; denied grant fails before network.
- No automatic resume, repaired prompt, provider/model switch, production state mutation or Harness usage.

## Policy distinction
This **changes transport/retry policy at execution time** by an external wrapper. The old 43 original files remain byte-identical, but these runs **are a NEW safety-controlled qualification protocol**, not a historically identical V3 run or evidence that the old V3 runtime was free of retries.

## Paid boundary
The module `experiments.v3_single_attempt_spine_probe` requires a separate, explicitly reviewed human grant JSON. It checks exact frozen V3 base, case, models, status and a local ceiling no greater than $0.50. This is not a guaranteed provider-side hard monetary cap: provider spend is known only after the call. Keep one fresh grant and unique evidence path per trial. No paid grant exists in this change. Do not create one or dispatch until user explicitly approves stage scope and ceiling.

The intended first live stage is the previously frozen age-18 fantasy case `age18.forbidden-cartographer.fantasy.frozen-01`, **Spine only**, up to one Sonnet Architect and (if valid) one Luna Gate. STOP after the gate regardless of outcome, and review the resulting Spine with the human before any Writer.

## Remaining security review
- Confirm the original OpenRouter streaming decoder does not bypass the POST gate.
- Check provider response `usage.cost` / `id` actual shapes.
- Run offline regression in isolated CI / runner on this exact code SHA.
- Review explicit authorization and conservative budget ledger reconciliation separately.
- Never merge to main or deploy LUMI production from this draft.

## Extra live preflight hardening (2026-10-15, zero-cost)
- Require an explicitly approved **exact wrapper HEAD SHA**, not merely its parent.
- Compare all additions since frozen V3 against a four-file allowlist; reject dirty checkout.
- Require a persistent, absolute one-use **grant claim directory**, independent of the chosen evidence directory; exclusive creation before any possible provider POST. A failed attempt still consumes its grant.
- Reject an absent or invalid grant ID, wrong wrapper SHA, wrong source ancestry, a modified runtime, or an already-claimed grant.
- This is guard-only hardening. No user-approved paid request has been sent.
