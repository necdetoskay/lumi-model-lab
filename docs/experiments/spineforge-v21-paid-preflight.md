# v21.1 paid bridge preflight — 2026-10-04

Result: **BLOCKED_COST_CONFIGURATION**. Paid model calls: **0**.

Reviewed runtime source: `57a0d5f8365750e498cf435433d1a8692dc30787`.
Frozen qualification commit: `7c1ae41e70fdd30775738a779a65e9778d3e38d8`.
The frozen runtime and paid authorization have not been changed by this review.

## Price observation

OpenRouter's model page, checked 2026-10-04:
https://openrouter.ai/anthropic/claude-sonnet-5.5

Standard listed rate: $2/million input tokens, $10/million output tokens.
The page also lists higher-priced endpoints. These figures are a price observation,
not a provider-side spending guarantee. The current normalized initial request
retains max_tokens=3000 and reasoning effort=medium, exclude=true. Excluding
reasoning from displayed output must not be treated as free reasoning.

## Offline payload measurement

Measured through the real harness/adapter with fake transport, using the historical
13-finding fixture. No inference credentials were supplied. Character counts
include serialized user payload, system prompt and response schema, but are not
provider token counts. The chars/4 conversion is only a rough planning estimate.

| Stage | Input characters | Rough input tokens | Output limit | Illustrative cost at full output limit | Stage ceiling |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial audit | 84,818 | 21,204 | 3,000 | $0.07241 | $0.040 |
| Scene repair | 24,685 | 6,171 | 3,500 | $0.04734 | $0.035 |
| Final audit | 13,309 | 3,327 | 1,800 | $0.02465 | $0.025 |

The final payload here contains a synthetic two-sentence replacement. A real
replacement will usually be longer. Later-stage inputs also depend on the live
initial findings, so this table is neither an exact quote nor an upper bound.
Actual output can be shorter than max_tokens; the table does not predict that
every call will consume the full limit. Its sum ($0.14440) demonstrates that the
configured limits are not sufficient to guarantee the $0.10 quality target.

Initial payload breakdown (serialized characters): full_story=13,704;
story_segments=59,991; canon_invariants=2,895; approved_constraints=5,567.
Frozen segment records include source_text and repaired_text plus historical
repair bookkeeping. The model therefore receives duplicate story content and
old repair metadata. Canon constraints are also repeated as both strings and
provenance-bearing records.

At the listed output price, repair's 3,500-token output allowance alone costs
$0.035, leaving no room for input at that stage's ceiling. Initial's 3,000-token
allowance leaves $0.010 for input (5,000 tokens); final's 1,800-token allowance
leaves $0.007 for input (3,500 tokens). These are arithmetic break-even values,
not measured provider token counts.

## Decision and bounded next change

Do not request paid authorization for this configuration. Offline CI established
control-flow safety, not budget suitability or semantic story quality.

Prepare a separately versioned wire-payload projection: send current story text
once, with its span IDs; omit historical source_text/disposition/finding indexes;
send approved constraints once. Preserve the complete immutable artifacts and
lineage locally. Do not truncate story, boundaries or semantic constraints.

Then measure the projected requests and choose input/output budgets together.
Any change must receive a new freeze revision with regression tests proving that
all current prose and required constraints survive projection. v21.1 remains the
reference. A request-time cost bound requires verified token accounting and
provider pricing/routing controls; the current post-call ceiling cannot provide
that guarantee. No paid authorization, paid commit marker or inference should be
enabled merely by accepting this preflight report.
