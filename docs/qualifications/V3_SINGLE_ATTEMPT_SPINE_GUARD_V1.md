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

## Frozen gate decision fail-closed (2026-10-15)

The original frozen episode_spine_v2_generate.generate writes outer
status awaiting_human_review for both ACCEPT and REPLAN outcomes.
Therefore the external guard must not call it a success based on the
stage status alone. The wrapper now inspects the frozen stage envelope
and its exact local result artifact, requires exactly two model POSTs,
reads gate.decision, and stops with SPINE_GATE_REPLAN_STOP on REPLAN.
Other missing/malformed outcome or approval markers STOP. Only Gate ACCEPT
with episode_writer_authorized=false and human verdict pending is
reported as ACCEPT_AWAITING_HUMAN_APPROVAL; never schedules Writer.

This is an external qualification rule. All 43 frozen V3 runtime files
remain intact. Replay uses recorded 2026-09 Forbidden Cartographer F1
responses, not a newly charged model output. No paid retries are allowed.

## New real Sonnet F1 contract failure and F2 revision data

Actual GitHub Actions run 38697673557 (2026-10-15) made exactly ONE
OpenRouter model POST to anthropic/claude-sonnet-5.5, HTTP 200,
12,296 prompt tokens + 7,267 completion tokens, provider-reported
cost $0.097262. Original frozen EpisodeSpineV2 rejected the
Architect output; Luna Gate and Aion Mini Writer were never called.

The explicit error: deduplicated beat locations started at Ashen Gate
and then Vellum Hall; logistics_plan.location_sequence instead started
at Vellum Hall. The opening hook was placed in Ashen Gate even though
the actual chronological itinerary begins at Vellum Hall. Blindly
replacing the logistics route would conceal a narrative chronology
defect. V3 prompt ALREADY commands an exact match; more generic
prompt reminders cannot guarantee this will not reoccur.

Remediation for a NEW paid F2 attempt (not automatic retry): The
external guard now REQUIRES an explicit revision_feedback payload in
a separate v2 paid grant. It is validated before claiming any budget.
The frozen v3 stage already supports a revision_feedback file:
the wrapper serializes the approved JSON to an evidence-locked file,
passes that file path through the original trigger, and the original
Architect stage includes this exact feedback in its prompt. Do not
modify historical F1 output, frozen V3 prompts, or its 43 source files.

Case-specific spatial contract: the NEW plan must have a physical,
chronological start at Vellum Hall, proceed to Greyfen and Ashen Gate,
then return through Greyfen to Vellum Hall. A flash-forward at Ashen Gate
cannot be disguised as a real first physical beat. The deduplicated
beat-location order must equal the logistics route. The model must
provide its own causal bridges and cannot silently autocorrect an
invalid output. If the new model again violates any V3 contract,
STOP after the first charged Architect response; no Luna/Writer/retry.

This is FAIL-CLOSED nonconvergence protection and probability reduction,
not a guarantee that a generative model will produce flawless planning.
Previous F1 spend is an actual separate charge; future scope must use
a fresh grant and consider aggregate budget.

Offline verification: 50/50 relevant tests green, 43/43 frozen SHA
green; specific tests prove that missing/wrong feedback cannot create
a claim or call the provider and that the original Architect context
receives the exact feedback object using an archived-response replay.
