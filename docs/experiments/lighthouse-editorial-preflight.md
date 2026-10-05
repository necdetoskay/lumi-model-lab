# Fenerdeki Hırsız — approved-plan Writer/Quality experiment

Experiment: `LIGHTHOUSE-EDITORIAL-01`. Plan approved by the user's
“Evet onaylıyorum” reply to the detailed plan. Approval binds the unchanged
`546b88821ea961153840a09312e5e8d68a52ef01` source document through SHA-256.
The document retains its original historical draft status; the separate
`evidence/lighthouse-editorial/plan-approval.json` is the current approval record.

This experiment measures Writer/Quality given a human editorial plan. It does
not measure Spine Architect generation or claim a full automatic production
baseline. Production LUMI is outside scope. The bridge case is not an input.

## Exact scope for separate paid approval

One Aion 3.5 Mini Writer call, then Sonnet 5.5 initial blocking audit; only if
needed and bounded to one approved scene, one Sonnet repair and one targeted
final audit. Two calls on the clean path, at most four total. No second repair,
transport retry, new Writer generation, translation or database commit.

Writer uses the existing qualified v20 transport policy (temperature 0.76,
low mandatory reasoning, 7,000 completion token cap, seed omitted), with a new
prompt bound to Ekin/Duru and the approved 1,400–1,800 word plan. The old v20
handoff and its 1,600–2,500 word authority are not impersonated or modified.

Writer marks SC01–SC06 once each. The reader's text removes only these markers.
Actual text is segmented and mapped to its actual scene boundaries. Unknown
spans, cross-scene blocking issues, structural/replan requests, a scene exceeding
the existing 40-span repair bound, invalid markers or truncated output stop the
experiment. No automatic expansion of the repair scope follows.

Repair gets exact approved action, prior end state, required end state and
setting/outcome constraints. Original and candidate text are stored separately.
Prefix/suffix preservation is checked by the existing v21 rewrite code.

## Proposed budget (not yet authorized)

| Stage | Stop threshold | Output cap |
|---|---:|---:|
| Aion Writer | $0.030 | 7,000 |
| Sonnet initial audit | $0.080 | 3,000 |
| Sonnet scene repair | $0.070 | 3,500 |
| Sonnet targeted final audit | $0.050 | 1,800 |
| Total proposal | **$0.230** | — |

Prices checked 2026-10-05 at OpenRouter's model pages:
- https://openrouter.ai/aion-labs/aion-3.5-mini : $0.70/M input, $1.40/M output.
- https://openrouter.ai/anthropic/claude-sonnet-5.5/providers : $2/M input, $10/M output.

Writer request size is recorded in `prepared-experiment.json` including prompts and transport fields.
This is not a token count. Its maximum completion charge at the quoted rate is
$0.0098, before input cost. Sonnet completion maxima are $0.030/$0.035/$0.018;
all stage proposals therefore leave room for input. Input sizes for later stages
depend on the real Writer output and selected scene. Exact usage and reasoning
tokens come from the provider and are recorded for every call.

These are stop-after-reported-cost thresholds, not a provider-enforced $0.23
spend lock. A completed call may exceed its stage threshold; the next call is
then forbidden. Unknown usage is unknown, never zero. The $0.10 production
target remains unproven and is not an acceptance condition for this experiment.

## Authorization and records

The default entry point is `python -m src.lighthouse_experiment`. It only prepares
artifacts. The prepared artifact has `paid_execution_authorized=false`.
The dedicated GitHub workflow has no API key or paid job.

A future explicit grant must bind experiment ID, plan hash, Writer request hash,
runtime dependency manifest hash, a unique authorization ID and the proposed
$0.23 budget. `run_once` verifies these before inference and exclusively creates
the authorization directory before dispatch. Reusing the same directory stops
even after failure. A real harness must use one fixed evidence root (never a
new root to bypass consumption). The paid CLI explicitly requires `--execute
--authorization PATH`; it binds the existing v21 model adapters as callbacks and
uses a fixed `evidence/lighthouse-paid-experiment` root. No grant exists yet.

The evidence directory preserves consumed authorization, inputs, raw Writer,
original story, exact repair handoff, candidate, final results and usage.
Invalid adapter responses retain their provider evidence and diagnostic path.
No synthetic test result is evidence that the story is readable or appealing.

Human reader assessment remains separate from model ACCEPT: readable locations
and movements, lively peer dialogue, compelling discovery, an earned loss and
an ending worth reading. The first real output is still pending.
