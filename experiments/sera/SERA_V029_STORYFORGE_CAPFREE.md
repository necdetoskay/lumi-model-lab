# SERA v0.29 — StoryForge Cap-free Runtime and Unknown-Charge Safety

**Release status:** Experimental branch only. The complete real LUMI story
worker, trusted production registries and transactional canon publisher
remain disconnected. No paid provider calls or production WorldState /
EventGraph writes were performed by this change.

## Why v0.28 wasn't enough

The v0.28 StoryForge→SERA bridge can validate the old StoryForge
\`request.v1\` / \`result.v1\` records without billing, but it deliberately
did not call the old StoryForge generator: the generator still imposed
four **application-configured model output token ceilings** in its
plan-validator, English-story auditor, local repair and EN→TR fidelity
stages. Additionally, its shared OpenRouter transport could silently
retry a request if a timeout hid an already billed response.

Neither behavior satisfies the user's explicit SERA constraints.

## v0.29 fixes

### Remove old application-configured output ceilings

In [src/storyforge/runtime.py](../../src/storyforge/runtime.py), remove
all four numeric output-token arguments from the editorial call sites.
The structured model helper now always sends \`max_tokens=None\` to the
existing generic JSON client; StoryForge's writer and translator already
used None and continue doing so.

In addition, SERA's pre-existing
[request-policy](./request_policy.py) is enforced at TWO levels:

1. **Before any StoryForge model stage:** \`_preflight_storyforge_output_policy\`
   resolves the FINAL request behavior from the actual
   [model runtime profile registry](../../src/model_registry.py) for
   all eight StoryForge model roles and their real request classes:
   planner, plan validator, writer, primary and secondary auditors,
   repair, translator and translation fidelity. If a profile forcibly
   injects an output cap, execution fails BEFORE even the context
   builder's JEV operation. Cost and model-native limits remain separate.
2. **Immediately before each HTTP request:** new optional
   \`forbid_output_token_limit=True\` runs the SERA guard AFTER
   \`normalize_openrouter_request\` on the actual OpenRouter JSON
   payload in [src/generate.py](../../src/generate.py). StoryForge
   structured JSON calls propagate this setting through
   [src/english_story_pipeline.py](../../src/english_story_pipeline.py).
   Caller \`max_tokens=None\` alone is not accepted as proof, because
   a registry policy might add one later.

This is restricted to StoryForge's opted-in paths: the generic
transport's old callers retain their prior behavior until separately
qualified. **Do not claim every historical Model Lab pipeline has been
made cap-free.**

### Safe network uncertainty

StoryForge now opts into \`forbid_ambiguous_paid_retry=True\` on
every structured/prose/translation OpenRouter request. If the
transport times out or disconnects before a provider response,
a request may have been charged. Instead of blindly sending it again,
the transport raises \`OPENROUTER_UNKNOWN_CHARGE_NO_RESEND\`, with a
machine-readable trace and \`needs_provider_idempotent_reconciliation\`.
This is safe refusal, NOT successful provider reconciliation, and
does NOT introduce a human-required retry/approval stage.

Do not mistake provider HTTP errors with a known response for a
definitive billing outcome. Full provider-side idempotent
reconciliation of unknown charged calls remains a separate worker
acceptance requirement. v0.28's SERA scene provider already uses
its own durable receipt-based response handling.

### Self-hosted regression proof

[tests/test_storyforge_capfree_v029.py](../../tests/test_storyforge_capfree_v029.py)
proves:
- No numeric configured token-output caps in StoryForge runtime calls.
- A model profile injecting a cap is rejected before any network call.
- A cap-free normalized payload can still be sent successfully.
- StoryForge structured stage, JSON retry and OpenRouter transport
  propagate the cap-free guard.
- The preflight resolves and checks all eight model stages.
- An uncertain billed timeout triggers ONE transport attempt,
  no blind resend, a durable-safe diagnostic.

[Dedicated self-hosted workflow](../../.github/workflows/sera-v029-storyforge-capfree.yml)
also reruns the existing StoryForge RC1 contract, generic streaming,
and structured JSON pipeline regression suites. No production deploy,
model billing or runtime tokens were consumed by the mocked tests.

## Still not qualified for production

- StoryForge's historical result may be editor-approved but that is
  **not** WorldState permission. Continue to use the v0.28 bridge's
  request/result/world/model fingerprinting, authenticated job-paid
  grant and v0.27 source-state independent recheck.
- LUMI real story-worker invocation; production signed world identity,
  registered character/fact/route authority and durable scene archive.
- Provider-supported request ID reconciliation and true crash/outage
  recovery when billable provider replies are missing before journaling.
- Unified full-story cross-scene causal, epistemic and world-state
  qualification, plus machine-only authenticated atomic
  WorldState/EventGraph commit with rollback.
- Genuine funded and approved unseen-story and frozen Mara S1
  end-to-end qualification. Mara S1 is still **HOLD**.
- Separate historical scripts elsewhere in Model Lab may still contain
  application-configured token limits; v0.29 does not assert a
  repository-wide purge of those legacy code paths.

At no point is a normal story required to wait for a person to fix JSON,
approve a scene, edit a fact, press retry or intervene in recovery.
Fail-safe outcomes may be terminal without canon write. The original
Sonnet Spine, main branch and production data are unchanged.

Follow [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
