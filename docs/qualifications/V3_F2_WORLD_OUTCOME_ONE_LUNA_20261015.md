# Final V3 F2 — One Luna model-led world outcome evidence review

## Boundaries and source

Already quality accepted bilingual story, read-only delivery bundle:
evidence/v3-f2-final-delivery-staging-20261015/
- Accepted English SHA-256: 990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8
- Accepted Turkish SHA-256: a163d9cbde430bd2023bb9e673d0e8ff4b380c7567aa84c4b476252dd2ddca19
- Frozen runtime SHA: 63e1e3ce82c244bc5bb02b0463a9a1a6715c941b
- Source delivery code commit: 3aa9af4f02154f7652d3f9844e194202efc8a936

## Model gate

The isolated external runner experiments/v3_f2_world_outcome_one_judge.py makes at most ONE GPT-5.6 Luna OpenRouter POST using the model-only evidence judge instructions at prompts/v3_f2_world_outcome_evidence_judge_v1_generic.md.

Model input includes the actual accepted English story, its SHA-256, the original approved Spine's two branch options, its constraints and saga milestone conditions, and ALL FIVE uncommitted persistent outcome candidates with their exact source commit conditions.

A real Luna must select the enacted branch and evaluate all five conditions with exact story quotations. The separate deterministic validator requires the original source hashes, branch validity, five complete results, exact quote existence and no branch/milestone contradiction. This validator checks provenance and presence of quotes; it does not independently prove all semantic interpretations.

No manual story revision, no publication, no canon/world-state commit. Even a valid judgment generates only MODEL_EVALUATED_WORLD_DELTA_UNCOMMITTED. This is not a database transaction and cannot apply changes.

## One-use spend guard

A separately scoped, one-run-bound GitHub grant is mandatory. Stage: WORLD_OUTCOME_EVIDENCE_ONLY. Model: openai/gpt-5.6-luna. Source SHA and exact guard commit are pinned; globally single-use claim and first-run-attempt requirement are checked before provider access. Existing GitHub Actions OpenRouter secret is used unchanged.

Max planning ceiling admitted by code: USD 0.03; it is measured after provider response and is NOT a provider-side hard billing cap. No transport retries, JSON parsing retries, alternate models or follow-on calls. Any failure STOPS, stores evidence if available, and never asserts state authority.

The original user continued specifically after the stated next action to have the model evaluate real-world outcome conditions. Permission is interpreted narrowly as this single read-only judgment, with the conservative ceiling; no additional billed stages, database writes or publication.

The runner archives provider generation ID, reported cost, exact model verdict and an independent uncommitted proposed delta. No model call happens during the offline tests.

## Current engineering checkpoint

The new targeted mocked-provider tests are 13/13 PASS; existing model-output validator/delivery targeted tests also PASS. A full frozen lane regression and GitHub Actions zero-provider dry run are required before a real one-use grant is activated.
