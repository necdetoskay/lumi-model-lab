# P4.38 — B04 distinct age-10 original MARKET/STUDIO pilot

**Status: generation adapter and offline tests implemented; paid story may only be reported after original provider receipts. PR #275 Draft, production/main untouched.**

B04 is the fourth registered frozen pilot from `configs/story_harness_p415_benchmark.json`. Topic **Kayıp renklerin peşinde**, main character **Emir**, reader age **10**; begins at **MARKET** with **STUDIO** an allowed but initially unknown location. Obligations: **Emir'in boyası tükenmiştir**, **Harita henüz bulunmamıştır**. Unknown owners/locations must remain unknown until the story demonstrates a cause or source. Input explicitly forbids inventing guidance absent from state.

Original deterministic input pack SHA-256: `f6edbf321afab965b1a0166ff0a4feb267935f6be556996c4168572477fa1c47`.
Target length: **800–1,400 English words**. Its Canon and locations differ materially from prior B03 `RIVERBANK/VILLAGE`.

This pilot **reuses** `src.story_harness_p417_live_pilot.BoundedOncePilot`: Anthropic Sonnet via OpenRouter, original compatible flat outer Spine/Writer schemas, original source-bound local Spine validator, ordered 4–8 beats, one immutable original Spine before Writer, exactly two one-shot POST attempts maximum, **no retries or fallback**. Run variant **r06** is per distinct B04 source; the protected claim key includes B04's SHA, preventing source reuse.

### Cost and authorization

Existing conservative total after actual B03 quality and Q25: **$1.539558**. New full B04 generation maximum **$0.350**; pre-reservation **$1.889558** of $10 cap. Generator stage caps unchanged: SpineForge **$0.075**, Writer **$0.140**. This is a software admission ceiling, not a provider prepaid guarantee. The actual receipt amount must be recorded. The independent B04 QA (**at most $0.040**) and genuine Q25 (**at most $0.050**) need separate reviewed grants after successful prior stages; no automatic promotion.

Single-use real-call workflow `.github/workflows/story-harness-p438-b04-once.yml` admits **only** an exact manifest-only PR synchronize commit with the frozen B04 source, stage budgets, model, age, one-use policy, no production writes and matching grant. Other commits return **DENIED_NO_CALL** before access to the model key. The separate offline workflow runs negative tests/mocks and performs no paid inference.

### Acceptance steps

1. Freeze genuine source-bound B04 SpineForge/Writer receipts and exact provider cost, or capture a fail-closed STOP. No `ACCEPT` at this step.
2. Run a separate real adversarial, age-sensitive, all-12-families initial quality check against the exact B04 story. Preserve `REJECT` if any unresolved blockers or reader score below 4/5.
3. Only after `ACCEPT`, seal unchanged immutable pilot English Master.
4. Run a separate one-use real Q25 quotation-checked extraction, and a deterministic read-only Final StoryState with explicit unresolved obligations, unknown ownership and world time.
5. Do not count B04 as release-certified without the frozen v21 final-quality policy and independent human narrative evaluation.

Any new case requires a distinct source, provider IDs and immutable claims. Same-method offline defect repair may occur at most three times before STOP/escalation; that does **not** permit paid provider retries. The P4.37 10×3 holdout slots remain unattempted until independently executed.
