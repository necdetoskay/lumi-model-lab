# LUMI Story Pipeline V4 — Derived-route and autonomous logistics repair

**Date:** 2026-10-15  
**Lane revision:** `AGE18-V4-DERIVED-LOGISTICS-v1`  
**Scope:** New experimental lane; V3 reference files and historical records are not silently changed.

## Motivation and real evidence

Live uncapped V3 Mara detective Spine run: [GitHub Actions #38784171701](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38784171701). Sonnet 5.5 returned complete JSON in 6,952 completion tokens, reported $0.091516, but `EpisodeSpineV2` rejected it because beat-derived route had 8 transitions and independently authored `logistics_plan.location_sequence` had only 6. Two non-consecutive archive/station visits were omitted. The model's logistics prose also claimed that no decision-to-climax journey remained beyond an archive-to-station trip; this contradicted its beat sequence. This is a **real structural contradiction, not proof that the narrative beats themselves are incorrect**.

Offline regression replay of the exact archived Sonnet payload demonstrates the canonical route can be derived from the 9 authored beats, restoring `EpisodeSpineV2` validity **without changing any beat**. This does not by itself prove the travel timing feasible; Luna must judge that separately.

## General V4 policy

1. **Prompt:** `episode_spine_architect_v4_generic.md` requires a beat-first route proof, every nonconsecutive revisit, decision-to-climax and climax-to-payoff travel and branch-by-branch feasibility. It applies to every genre and world.
2. **Single source:** `src/v4_logistics.py` projects `logistics_plan.location_sequence` from `beats[].location_ref` with adjacent deduplication only. It captures before/after SHA-256 and the original authored route. It rejects unapproved locations and never changes the authored beats or story state.
3. **Narrative logistics repair:** When projection changes the route, one economical `anthropic/claude-haiku-4.5` call is allowed to propose only `logistics_plan.feasibility_rationale`, `movement_constraints`, or `time_window` replacements. The patch must be actually nonempty, change something, preserve the beats/derived route, and pass the full Pydantic spine contract. Haiku may not invent facts, destinations, times, characters, evidence or branch commitments. The original proposal, accepted field-level patch and provider spend become evidence.
4. **Independent creative review:** Luna still audits causal/logistical feasibility, all branches, deadlines, participant availability, and truth boundaries. If Luna returns `REPLAN`, Writer is blocked. V4 reports `v4_gate_replan`; it never maps this to PASS.
5. **No fake human approval:** V4 deliberately defines a distinct `episode-spine-v4-model-reviewed.v1` artifact. A Luna `ACCEPT` receipt is labeled `model_creative_review` with SHA-256 binding to the exact Spine. Human review remains `NOT_REQUESTED_FOR_V4_AUTONOMOUS_QUALIFICATION`; no invented human `APPROVE`.
6. **Full pipeline:** The separate V4 dispatcher and orchestrator run Sonnet -> derived route/Haiku if needed -> Luna -> Aion English -> deterministic/Luna/Sol English quality, bounded repair and recheck -> Gemini translation -> deterministic/Luna/Sol fidelity/adjudication, Gemini repair and recheck -> final EN/TR **unpublished** artifact. No production Canon writes, publication actions, manual story edits, model fallback or hidden additional retries.
7. **Paid boundary:** One explicit run/commit/case-bound owner claim, 12 maximum provider POSTs, $2 **observed** planning stop, no client `max_tokens`, `max_completion_tokens` or `max_output_tokens`. Model/provider intrinsic limits still apply. Model spend cannot be guaranteed to stop precisely at $2 since receipts arrive after each charged request. Charge receipts survive downstream parser/contract failures. No rerun of the same claim.

## Testing and limitations

- V4 tests include generalized nonconsecutive visits, replayable structure, forbidden Haiku patch attempts, model-review SHA tamper rejection, no-grant network refusal, mock full EN/TR routing, provider spend recording.
- The source freeze contains a separately verified SHA-256 list of **54 V4 code/prompt/workflow files**, including the paid guard, CLI runner, and exact GitHub Actions workflow.
- The prior V3 output remains archival; a V4 *fresh* Sonnet generation is required to qualify end-to-end.
- Only structural route mismatch has automated guaranteed projection; a Luna `REPLAN` outside the bounded repair capability still stops. Other future repair families need explicit scoped authorizers and evidence; do not claim a generic omnipotent repair loop.
- No real generation or Turkish delivery may be described as completed unless a provider-backed V4 run actually returns with unambiguous evidence.
