# Final V3 F2 — standalone Turkish literary translation and fidelity

## Authoritative English source

Case: age18.forbidden-cartographer.fantasy.frozen-01
Title: The Road the Map Refused to Admit
Accepted English QA run: 38712035968
Accepted English SHA-256:
990e6a009aea84aeadd74f9734ae8663ae495bf8d9800d20e4281f248064c5a8

Previous accepted English story: 2,767 words; English story length
is an advisory only. The source was fixed by an actual GPT-5.6 Sol
model-proposed patch and a live GPT-5.6 Luna re-audit. Zero manual
story edits. The original source and all 43 frozen V3 source files
remain unmodified.

## Frozen V3 model plan

Model 1: google/gemini-3.8-flash (literary English-to-Turkish).
Model 2: openai/gpt-5.6-luna (serious / critical semantic fidelity).
Those model IDs and frozen prompts come directly from the immutable
age18 Story Lane runtime profile.

Translation must preserve plot order, names, semantic negation,
modality, unresolved mystery, report limitations, witness and mentor
boundaries, choice branch and outcome. Turkish naturalness is valued;
there is no mechanical word-count based story rejection.

## Exact bounded implementation

External runner: experiments/v3_f2_turkish_translation_and_fidelity_once.py
New grant schema: lumi.v3-f2-english-to-turkish-grant.v1
Stage: TURKISH_TRANSLATION_FIDELITY
Maximum code-admissible ceiling: USD 0.15 (NOT hard provider cap and
not authorization by itself).
One grant ID -> one GitHub run ID -> first run attempt only.
One Gemini translation POST; Luna POST ONLY after deterministic
semantic guards report no serious rule violation. If the translation
has a deterministic semantic shift, retain its original model output
and STOP; Luna and translation repair are not silently dispatched.
If Luna finds serious/critical meaning shifts, retain full evidence,
STOP without accepting or publishing.

The old frozen stage source classes and prompts remain unmodified.
All outgoing HTTP POSTs are covered by the external model-order and
cost guard. Parsing errors, malformed provider responses, HTTP or
network errors, cost overruns, retries, extra model calls and new
model IDs stop. A new English source envelope is a metadata wrapper
for the already accepted immutable English master, not a rewrite.

Acceptance only after *real* Luna clean verdict; even if a frozen
stage result says publication_ready=true, the isolated runner
explicitly sets publication_authorized=false and
world_state_commit_authorized=false. Any separate repair/secondary
adjudication requires new controlled stage authorization.

## Proof

Before any paid test, tests using mocked HTTP provider outputs have
been run: 133/133 PASS, frozen V3 SHA check 43/43 PASS. These offline
results are NOT real translation or real Luna fidelity judgments.

The user's 'devam edelim' reply after the explicitly described
translation + fidelity next phase is interpreted as permission for
that stage only. The run is to use a separate one-use provider budget
planning ceiling (not a provider pre-spend limiter); no production
deployment or world-state commit is authorized.
