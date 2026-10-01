# SpineForge v19 — NarrativeSpineV1 single-owner baseline

Status: **FROZEN ZERO-COST QUALIFICATION CANDIDATE**

## Canonical topology

`SpineContextPack.v1`
→ exact reader/story-family obligations
→ **Sonnet 5.5 single Narrative Spine Architect**
→ `NarrativeSpineV1`
→ deterministic authority / reveal / obligation validation
→ **GPT-5.6 Luna compact adversarial Product Gate**
→ human-readable preview
→ **STOP / human approval**

Writer, translation, and canonical-state commit are not callable inside the v19 SpineForge runtime.

## Why v19 exists

v11 proved that one Sonnet owner can produce a nearly valid complete spine in one call. v12 proved that mechanically derivable metadata should not be model-owned. v14-v17 showed that a large scoring/audit surface created repair and transport churn. v19 keeps the successful single-owner direction while replacing the legacy `EpisodeSpineV3` product contract with a smaller story-first contract.

## Product ownership

Sonnet owns story promise, story-family execution, protagonist goal/pressure, central question, stakes, world-specific use, beats, decision when required, climax, payoff, unresolved hooks, reveal limits, outcome candidates, and writer rules.

The application owns ContextPack identity/fingerprint, exact age, session, word targets, authority revisions, eligible milestone ids, commit-only-if-earned, writer authorization, approval ids, and token/cost/latency lineage.

## Deterministic gate

Code rejects objective defects only: stale/mismatched authority, unknown or locked refs, hidden-Saga system markers, exact type/shape problems, duplicate beat keys, reader/story-family obligation mismatch, and a missing required real choice.

Subjective story quality belongs to the Luna Product Gate and then human review.

## Transport

Qualification uses v19-specific **one-shot** transport. There is no automatic HTTP/model retry.

- Sonnet Architect: JSON object transport + local `NarrativeSpineV1` validation.
- NarrativeSpineV1 schema size: **4,633 bytes**. It is intentionally **not** provider-strict.
- Luna Product Gate: provider-strict JSON Schema + local typed validation.
- Luna gate schema size: **1,288 bytes**, below the **4,096-byte** strict-schema budget.
- Maximum model calls per ordinary qualification case: **2** (Architect + Gate).
- `REPAIR` and `REPLAN` stop the run; no third call executes automatically.

## Qualification matrix

The fixed matrix is:
`data/specifications/story_lab/spineforge_v19_qualification_cases_v1.json`.

All **6/6 ContextPack fixtures are frozen**:

1. age 4 — imaginative friendship/play
2. age 12 — adventure/exploration
3. age 12 — mystery/problem-solving
4. age 18 — Leyra fantasy/mystery control
5. age 40 — consequential adult adventure
6. age 60 — mature adventure/relationship/reflection

Every fixture validates as `SpineContextPackV1`, its canonical fingerprint is recomputed in tests, and reveal-safety checks prohibit hidden payload fields such as `hidden_statement` and `reveal_steps`.

## Runtime freeze

Runtime profile:
`data/specifications/story_lab/spineforge_runtime_profile_v19_narrative_spine_frozen.json`

Frozen revision:
`SPINEFORGE-NARRATIVE-SPINE-FROZEN-v19`

Runtime source commit:
`41ab5c5a43b4465207fa76c29fdcb073399c1566`

Frozen dependencies:
**23 SHA-256 locked files**

The later freeze/profile/CI documentation commits do not alter the frozen dependency set.

## Zero-cost evidence

Final GitHub Actions run:
`36887442025`

CI head:
`a072bd0ff3da67bc3dc869a136a58587ec840aa0`

Result:
**SUCCESS**

Direct ci-runner verification at the same final head:
- v19 contract / obligations / fixture / architecture / transport / freeze: **22 PASS**
- v19 runtime mock + human boundary: **5 PASS**
- ContextPack reveal-safety regression: **6 PASS**
- total: **33 PASS**
- freeze verification: **23/23 files verified**
- paid model calls: **0**
- confirmed v19 spend: **$0**

## First paid-wave acceptance bar

The six fixed cases are intended as a falsification wave, not statistical proof of the long-term 95% product goal.

Required first-wave evidence:
- 6/6 deterministic canon/reveal integrity
- 0 hidden-truth leaks
- 0 technical contract/transport failures
- at least 5/6 human `WRITER_READY`
- age-12 must not repeat the toy-play maturity failure
- age-40 and age-60 must not become child plots with harder vocabulary
- no multi-stage structural compiler

## Paid boundary

Current state: **READY_FOR_EXPLICIT_PAID_AUTHORIZATION**

No `experiments/triggers/spineforge-v19.json` exists.

Before the first paid case:
1. the user must explicitly authorize the paid call;
2. the frozen runtime/prompt/schema/model routing must remain unchanged;
3. no automatic retry is permitted;
4. Writer remains blocked even after Luna ACCEPT until the human approves the exact ContextPack fingerprint + Spine hash.

If the paid result exposes a defect that requires prompt/schema/model/routing changes, the failed attempt remains evidence and the fix becomes a new frozen revision.
