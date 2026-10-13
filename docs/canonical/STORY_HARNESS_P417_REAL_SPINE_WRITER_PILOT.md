# P4.17 — First REAL-CAPABLE single-attempt SpineForge → Writer pilot

**13 October 2026** · [Draft PR #275](https://github.com/necdetoskay/lumi-model-lab/pull/275) · [Issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291)

## The key correction

The repo already has `OPENROUTER_API_KEY` referenced by other production/research GitHub Actions workflows. The previous SentinelX shell being empty **does not mean the GitHub Actions secret is absent**. On actual [CI #38412094080](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38412094080) the existing secret presence probe confirmed `REPO_OPENROUTER_SECRET_AVAILABLE=YES`. No new user key requested, no secret material shown.

The user has granted **one aggregate US$10 budget** for creating a genuinely successful story pipeline with a 90% state/topic success target. That authorization does not change original frozen v21 stage-specific guardrails or permit unlimited retries. No external fee authorization is sought again for this amount.

## What is now callable

`src/story_harness_p417_live_pilot.py` is a **new versioned, default-off real model POST adapter** for the varied P4.16 input bridge, not a separate quality policy. For the first ten-case benchmark pilot it deliberately supports **one B01 story first** (age 4), with actual source pack SHA frozen before calls.

- Stage 1 `SPINEFORGE`: model `anthropic/claude-sonnet-5.5`, Anthropic-only, strict JSON schema, 4–8 causal beats tied to source, output cap 1,800 tokens.
- Stage 2 `WRITER`: a character-driven, emotion-rich narrative from the returned source-approved beat sequence; exact input pack and Spine SHA, required age-specific 300–600 words, output cap 2,500 tokens. Unknown owners/locations remain unknown without shown cause.
- Compatible with P4.12/P4.13 provider observation: `temperature` omitted (NOT equivalent to `temperature=0`), `provider.allow_fallbacks=false`, `provider.require_parameters=true`, per-million token price cap $2 input/$10 output, `usage.include=true` for actual billable usage.
- Max **two real POST calls**, exactly one each, zero automatic retry. File-system O_EXCL claim before the first POST, each stage intent before its POST, receipt only after response. Crash, malformed JSON, missing cost, output truncation, stage/model/source failure all permanently consume this attempt.
- Conservative per-pilot stage response-cost ceilings: $0.075 for Spine and $0.14 Writer, aggregate declared $0.35 per two-call attempt (and cumulative user $10 across subsequent authorized attempts). These are application-level abort rules, **not provider-guaranteed hard spending limits**. Actual provider bill cannot be retroactively stopped, so keep prompt sizes/token caps and no fallback pinned and record uncertainty as STOP.
- Story artifact is a real Writer draft **only if** genuine provider transport is actually invoked. `story-draft.json` contains prose and immutable SHA, Writer + Spine IDs, `model_generated=true`, but deliberately `quality_accepted=false`, Master/Q25/State flags false until original quality architecture actually accepts this story. Never apply P4.8's fixed 12-year-old v21 preflight to an unrelated four-year-old story.

## How to execute — safe boundaries

Default CLI only prints metadata and **never reads API credentials or POSTs**:

```sh
python -m src.story_harness_p417_live_pilot --repo-root .
python -m unittest discover -s tests -p 'test_story_harness_p417_live_pilot.py' -v
```

A separately isolated, reviewed GitHub Actions **one-shot** execution will call:

```sh
mkdir -p "$PERSISTENT_P417_LEDGER_ROOT"
LUMI_P417_ENABLE_PAID=ONE_SHOT_APPROVED_10_USD_USER_LIMIT \
OPENROUTER_API_KEY="<taken securely from GitHub Actions secret, never hardcode>" \
python -m src.story_harness_p417_live_pilot --paid-one-shot --case-id B01 \
  --run-root "$PERSISTENT_P417_LEDGER_ROOT"
```

**DO NOT commit an API key or story prompts/response to CI stdout**, do not run the paid command automatically on ordinary PR pushes or via a test fixture. Required actual authenticated key and one-shot runner are provisioned through GitHub Actions secret/controlled CI, and hardcoded P4.17 run-root should persist across later jobs. A runner environment without protected persisted storage must STOP or switch to separately validated atomic claim backend; simply using `/tmp` is insufficient.

The payload uses `usage: {include: true}` ([OpenRouter billing support](https://openrouter.ai/support/)), so a provider result lacking actual cost is a **failed consumed attempt**; never overwrite unknown spend as zero, retry the timed-out provider POST or claim literary success from a successful schema parse.

## Next full pipeline steps

1. Run first true B01 Spine→Writer generation; attach artifact/usage/hash and **assess narrative quality**. If failed, classify root cause and make three distinct same-approach fixes before switching method (free regression after each, paid rerun only under remaining total budget).
2. Integrate **new variable-source original independent v21 Quality** as separately versioned adapter (existing P4.8 static v21 fixed story not falsely generalized). Actual independent ACCEPT must be recorded before English Master.
3. Run same-story real Q25 and evidence-anchored Final StoryState read-only, then generalize age/state/genre and verify >=9/10 pilot and independently >=27/30 holdout, bounded by remaining actual user dollar budget.
4. Still **no main merge, production deployment or state commit** without separate release approval.

**Cost status at P4.17 code creation:** $0 new model inference. Any later billed result must be taken from authentic OpenRouter receipt rather than test/sample estimates.
