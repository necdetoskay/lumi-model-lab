# SERA v0.15 — Blind model-assisted entity identity review

**Date:** 2026-10-16  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Source Mara S1 SHA-256:** `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`

## Change from v0.14

The previous v0.14 work used 16 source-anchored *Mara-specific*
interpretation rules. These proved deterministic guard behavior but
cannot be the required per-story production solution: a new story
might contain entirely different objects, body parts, documents and
regions. Treating `MARA_RULES` as authoritative or making every
new object depend on hand-authored interpretation would not scale.

v0.15 adds a **reusable blind identity model contract**:
`blind_identity_v015.py`, independent of the v0.14 rule table.

The model receives source-only narrative evidence associated with all
unregistered reference IDs; up to two neighboring sentences for
pronoun/part-of context; existing World v0.2 entity IDs/kinds/locations
and registered region IDs. The model **does not receive** v0.14
classifications, proposed parent mappings, v0.10 Gemini event judgments,
Haiku semantic event corrections or any claimed gold answers.

For example, identifying `new:watch_hands` requires distinguishing
the pocket watch's hands from Vane's own anatomical hands. The
neighboring original source sentence provides context, but the model's
returned `support_quote` must be copied **verbatim from a sentence
which actually mentioned this reference**.

## Closed model output and abstention

One response object must provide a row for **every** requested
unregistered ref, no duplicates or additional refs.

Each row is strictly:

`entity_ref, decision, classification, relation, relation_target,
support_sentence_id, support_quote, reason`

- `decision = PROPOSE | ABSTAIN`.
- `ABSTAIN` requires `classification=UNRESOLVED`, no relation,
  no target and no fabricated evidence; it cannot create a world fact.
- `PROPOSE` accepts only finite review categories such as
  independent physical object, object component, anatomical component,
  region alias/sublocation, document component/entry/alias,
  negated marker, reported topic or abstract source collection.
- Typed relation targets must exist among the World registry, regions
  or supplied provisional refs. Anatomical parents must be registered
  CHARACTERS, and object-component parents must be registered OBJECTS.
- The deterministic binder checks exact source sentence and
  quote offsets; attempts to invent parents, use wrong sentences, add
  unknown enum labels, omit/duplicate refs or create relation cycles
  are rejected.
- Provider JSON may be a pure JSON object or **only** one complete
  fenced JSON block, with no surrounding conversational prose.
  The raw content and any errors are retained; no broad fuzzy matching.

Even a completely valid model response is
`BLIND_IDENTITY_MODEL_OPINIONS_SOURCE_BOUND_HOLD`.
It grants **zero physical presence confirmations, object creations,
part links, alias merges, ownership changes, canonical WorldState
or EventGraph commits**. Matching the v0.14 diagnostic hypotheses
is not human gold or semantic ground truth.

## One-call runtime and cost evidence

`mara_s1_blind_identity_pilot_v015.py` is a **Mara-only integration
adapter** for the generic model contract, not a second per-story
decision table. It downloads the *original* run 38868633198
source-mention evidence, then sends only one
`anthropic/claude-haiku-4.5` request through the existing vetted
OpenRouter client.

The runner requires explicit `--live` and a provider key; no
retry, fallback, second provider call, writer regeneration or JEV.
The output JSON file is created before the request and updated
atomically **before binding** so an invalid response cannot be
silently discarded or repeatedly charged. The caller receives
an advisory report or a diagnostic HOLD, and no WorldStore
writes are available.

The one-use GitHub workflow lives in
`.github/workflows/sera-mara-v015-blind-identity-once.yml`
and requests a **Linux self-hosted runner**. Its launch requires a
single-file grant commit pinned to the exact preceding branch
commit SHA; it cannot be rerun and cannot be triggered for arbitrary
branch changes. GitHub Actions runner availability and provider
credentials are independent operational gates.

**User requirement:** no application-configured output token ceiling
(`max_tokens`, `max_output_tokens` etc.) is supplied.
Request/response counts and dollar costs may be measured, but
measuring usage is not an output limit.

## Acceptance and next stage

- [x] Reusable prompt/closed schema, source verification, registered
  entity/region and parent-cycle checks.
- [x] Explicit model abstain, no implicit entity creation.
- [x] Adversarial offline tests (fabricated quote, duplicate/missing
  ref, forged parent, anatomical/wearable ambiguity, alias cycle,
  prompt injection envelope, and archived provider error).
- [x] Raw-before-bind one-call OpenRouter adapter and single-use,
  self-hosted CI workflow.
- [ ] Read **actual** blind Haiku result, measure source-bound
  proposal/abstention count and compare categories with v0.14
  **only after** the blind model response is archived.
- [ ] Follow with independent semantic identity adjudication,
  guarded entity/part introduction, temporal/action
  consistency, and production commit authorization.
- [ ] Generalize the old v0.13 Mara-specific mention-source adapter
  schema name; the v0.15 review engine itself does not hardcode
  Mara's classifications, but the current input census has a
  legacy `sera.mara-s1-entity-mention-census.v0.13` schema ID.

**S1 remains HOLD.** A passing binder does not prove identity
accuracy, that all mentions were detected by the upstream model,
or that all 25 events can safely commit.

## Self-hosted checkout diagnostic and one-use recovery

The initial **single-use** launch
[38872127365](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38872127365)
found the configured self-hosted runner `q25-offline-isolated`, but
`actions/checkout@v4` stopped before any Python or provider step.
The logs show `fatal: --local can only be used inside a git
repository`, followed by a missing artifact warning.
**Zero LLM API attempts** took place.

Do not rerun that grant or reuse a paid-response ID: none exists.
The v0.15b workflow repair clears only a *non-git*
`GITHUB_WORKSPACE` after the failed checkout and requests
`clean: false` plus `set-safe-directory: false`.
It requires a **different**, specifically named
`mara-s1-blind-identity-once-v015b.json` single-file
approval pinned to the repaired branch SHA and the ID of the
pre-provider failure. No alteration to the model prompt, output token
policy or state-writing authority was made by this operational change.

## v0.15c — Non-destructive self-hosted checkout isolation

[Second isolated launch 38872399171](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38872399171)
also stopped **before Python, preflight or any provider call**.
The first recovery attempted to clear a repository-local workspace
without `.git`; the runner lacked permission to remove historical
root-owned `src/__pycache__/*.pyc` files. We did **not** change
filesystem permissions or attempt privilege escalation, and no LLM
was billed.

The v0.15c workflow now uses an independent
`actions/checkout@v4` target `sera-v015c-source` inside the
runner's repository workspace, and runs all Python commands from
that isolated checkout using the job's `defaults.run.working-directory`.
There is no cleanup/deletion command, no production filesystem change,
and no attempt to modify the old root-owned cache. A different,
single-file `v015c` launch grant is required, pinned to the exact
updated workflow SHA and both previous pre-provider failed run IDs.
