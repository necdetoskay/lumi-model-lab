# Final V3 F2 — model-only Turkish fidelity adjudication

English original: accepted and frozen at SHA
990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8.
Turkish Gemini raw story: archived, SHA
a163d9cbde430bd2023bb9e673d0e8ff4b380c7567aa84c4b476252dd2ddca19.

## Real prior run

Actions 38713969969 made two successful provider POSTs:
Gemini 3.8 Flash translation ($0.0204075); Luna fidelity
($0.002629). Total $0.0230365. The Turkish translation
contains 2,173 words and deterministic semantic guards
reported zero findings. Luna reported three potentially
serious fidelity issues; therefore the original stage stopped
and no translation was accepted, repaired or published.

## No human editing

External stage experiments/v3_f2_turkish_sol_adjudication_once.py
calls the FROZEN v3 GPT-5.6 Sol fidelity adjudicator ONCE,
requiring that model to evaluate all three original findings
and choose CONFIRM vs REJECT for each. The model may neither
invent new findings nor edit story text.

If Sol rejects all findings, the ORIGINAL Gemini translation
may be accepted as an English-to-Turkish fidelity-clean
candidate; no model repair or later review is charged.

If Sol confirms any issue, the stage preserves Sol's
machine-readable confirmed findings and stops without
accepting the Turkish story. A separate bounded Gemini model
repair and Luna recheck can then consume that evidence.
No human-generated replacement is ever permitted.

The stage uses an isolated one-use grant tied to the exact
GitHub triggering run, SHA-pinned source and guard commit,
one permitted OpenRouter model and one paid POST maximum.
It rejects run replays, model fallback, source mutation,
unexpected additional calls and network/response faults.
Existing OpenRouter GitHub Secret is used unchanged.

No automatic publication, world-state update, or English
master change. Original frozen 43 V3 files are untouched.
Budget ceiling is post-provider accounting, not a provider-
enforced hard limit. A new separately scoped grant is needed
before any real paid Sol call.

Offline tests: 9/9 pass for this new stage, and existing
broader frozen tests are required before execution.
