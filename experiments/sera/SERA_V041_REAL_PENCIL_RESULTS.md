# SERA v0.41 Real Model Audit — Pencil Motion, Source Integrity and Quarantine

**2026-10-16 — Real provider results, no production commitments**

## Fixed source

Same historical frozen Mara S1 prose SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`, but a DIFFERENT four-sentence batch (`s021`–`s024`) than v0.40's bench segment.

Source sentence: "Vane watched the pencil move."

Important: this describes an **observation of a moving object**. It does *not* prove Vane moved the pencil, Mara moved it, the exact physical cause, previous ownership or time. A generated observer cannot substitute for the mover in the canonical world.

## Exactly two real independent OpenRouter calls

[Real workflow 38938438488](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38938438488) completed SUCCESS with 672/672 offline tests and one independent source-blind request per model. Actual provider artifact `sera-v041-real-pencil-once-38938438488`, artifact ID `12061129188`.

| Provider | Raw cost | Initial source binding | Real raw observation |
| --- | --- | --- | --- |
| Gemini 3.7 Flash | USD $0.00837525 | PASS, diagnostic HOLD | pencil identified, 5 event candidates in 4-sentence batch, OBSERVE and MOVE both proposed for pencil sentence. Mover/cause unspecified. |
| Claude Haiku 4.5 | USD $0.00559900 | FAIL, diagnostic HOLD | raw pencil reference and observation exist, but model used Markdown JSON code fence plus extra `reason` fields on two mention records. |
| Combined | USD $0.01397425 | — | No scene, simulation or production world commits |

Total original two independent REAL model pilots v0.40 bench + v0.41 pencil: **USD $0.03035200 provider reported**. This is not a projection of full-story costs.

## Distinguish source/format errors from physics/epistemic errors

[Offline real replay 38938995313](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38938995313), artifact ID `12061034942`, used **zero new provider calls** and actual saved response hashes:

1. Reused existing strict JSON fence parser v0.11 and verified unmodified archived provider reply.
2. On Haiku, removed **exactly two unsupported optional `mention.reason` annotations in a copy**, recording each original value's SHA. These are not physical event fields or source quotes.
3. Full binding still correctly failed: `SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE`. The original quote of an earlier `added` sentence used ordinary rather than typographic quotation marks. Another reported quote reversed the original clause/attribution sequence. **Do not** silently reorder prose or hallucinate source evidence to force a PASS.
4. Haiku also suggested `new:unidentified_female` for a pronoun that refers to the existing Mara in the contextual scene. This is a **potential identity hallucination**, not permission to create a fourth character.
5. Both models' counts are **proposals**, not truth labels. Gemini's pencil `MOVE` does NOT establish who moved the pencil or any valid custody transition.

The partial per-row replay `real_pencil_partial_rows_v0412.py` performs strict v0.10 binding independently for each real model sentence. It keeps source-bound candidate rows but quarantines invalid quoted rows rather than discarding all well-grounded observations or inventing a whole-scene PASS. For this stream, source completeness remains **unproved** even if pencil candidate is preserved. No automatic re-billing or output token ceilings.

## Engineering implications

**Needed next:**
- Keep `no-more-than-known` epistemic validation separate from schema parsing. A quote being sourced does not prove physical identity, ownership, mover or transition.
- Strengthen prompt and source-quote grounding; strict binder must still be final arbiter. JSON structural repair should be source-preserving and use minimal deterministic repairs only.
- Quarantine individual invalid sentences and plan a separately authorized, durable-receipt-aware targeted re-extraction, without discarding valid other rows.
- Expand to multiple event types and full scene before claiming true precision/recall; independent source ground truth cannot be inferred simply because models agree.
- Do not relax original Mara S1 HOLD, physically trusted Project_LUMI G2 source requirement, or forbid-human-manual-step / forbid-app-output-token-cap policies.

[Tracking Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306)
