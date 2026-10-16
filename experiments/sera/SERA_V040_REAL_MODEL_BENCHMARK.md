# SERA v0.40 — Real-model blind benchmark on original frozen Mara scene

## Real live pilot, not synthetic inference

This experiment uses the genuine frozen 243-word Mara S1 scene (SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`). Its earlier real diagnostic documented two missed objects, bench and pencil; here the first paid pilot chooses **the four-sentence batch containing bench**. It is NOT a full 28-sentence benchmark, an accepted story or a new physical source.

Two independent one-shot v0.10 source-only prompts go to `google/gemini-3.7-flash` and `anthropic/claude-haiku-4.5`. Neither receives the other's answer, a writer event list, desired labels, G2 private state, fixture event fingerprints or existing semantic judgements. Existing `one_provider_call` supplies the only network transport and enforces `enforce_no_output_token_limit`; the application imposes **no model output-token generation ceiling**.

The application preflights the provider key and uses a two-request maximum, no automatic retry, and an **observed $0.05 USD spend stop** between calls. This stop is NOT a provider-enforced per-call charge ceiling; actual provider cost may exceed it on a single response. If cost cannot be reconciled, a request fails or an in-flight response is lost, **stop and preserve evidence without a repeated paid call**. The pilot does not ask a human to fix model output, and does not run a normal generation pipeline.

## Preflight and trigger safety

The one-shot workflow `.github/workflows/sera-v040-real-blind-one-shot.yml` runs **only on self-hosted Linux**, only when a new file `experiments/sera/launch/sera-v040-real-blind-one-shot.json` is committed with the exact `[SERA-V040-PAID-ONCE]` commit marker, only on the experiment branch, and only on the first GitHub run attempt. Grant schema, authorized models, frozen source SHA, max two requests, budget, no output cap, and **pinned previous code commit SHA** are all verified before loading the `OPENROUTER_API_KEY` GitHub secret. The trigger commit must change only the single grant file. GitHub-hosted Actions is not used.

Secrets are not printed. Stored response artifacts contain model output/provenance and must be handled as potentially private. Persist intent before each API call, then raw provider envelope immediately after return; if that window fails, the current run records charge unknown and stops. Do not retry by rerunning the workflow. This one-use structure is a diagnostic safeguard and **not a durable provider-side idempotency guarantee**.

## Measured outputs

For each provider: response ID/model, usage/cost if reported, finish reason, structural source-binding status under real v0.10 `bind_batch`, number of candidate mentions/events, bench lexical candidate detection, and reasons for HOLD. Other batches in the story remain unassessed. Do not compute full event recall/precision on partial batches; the original hand-inspected omissions are calibration hints, not complete gold data.

The status must remain diagnostic **HOLD** even when a model passes the strict schema and identifies bench. Agreement alone does not certify that each objective event was captured. No character, object, fact or event may be committed to Project_LUMI or even the v0.37 simulated world by this pilot. Mara S1 remains frozen and unchanged. The v0.39 synthetic SQLite continuity tests remain independent.

## Next

Evaluate actual provider outcomes and independently review missed action/entity spans without model self-grading. Only after that design broader multi-scene source coverage, targeted automatically repaired responses with durable receipt reconciliation and independent temporal/semantic qualification. Roll out stronger live tests with separate approval and bounded cost, not silently through this one-use grant.

[Tracking Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
