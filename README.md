# LUMI Model Lab

Hands-on experimentation repository for learning synthetic data generation, teacher-model qualification, distillation-style dataset construction, LoRA/QLoRA, Unsloth, evaluation, and small-model fine-tuning through the LUMI story-generation use case.

## Project rule: README stays current

This README is the human entry point and current-state document for the repository. Any PR that materially changes the experiment pipeline, primary commands, dataset policy, model-selection protocol, or current milestone must update this README in the same PR.

## Story Harness V1 — offline control-plane experiment

A separate **Story Harness** experiment now explores deterministic orchestration
of the LUMI story stages (Context, SpineForge, Writer, Q25 and quality gates).
This is **different** from the existing Decision Engine/JEV harness and does
not replace any stage's authoritative validator.

V1 can **only replay demo stage-artifact lineage**: pinned SHA-256 inputs,
ordered dependencies, stop-on-reported-reject/review, no automatic model
calls and no semantic or canonical state approval. The example is **not**
a real generated story, and a green harness test **does not qualify** Q25.

```bash
python -m unittest discover -s tests -p 'test_story_harness_v1.py' -q
python -m src.story_harness_v1 --plan configs/story_harness_v1_fixture.json --repo-root .
```

- Canonical architecture: [Story Harness V1](docs/canonical/STORY_HARNESS_V1.md).
- Source: `src/story_harness_v1.py` (stdlib only).
- Branch: `experiment/story-harness-control-plane-v1`; no integration or
  modification of frozen production LUMI/SpineForge/Q25 code is authorized.
- **P1 real-evidence inspection:** six **byte-identical** frozen historical
  SpineForge/Q25 JSON artifacts from experiment Q25 PR #273 are recorded in
  `configs/story_harness_p1_frozen_import.json`. These represent **four
  independent historical cases**, not a fabricated end-to-end story.
  A historically approved spine, a failed SpineForge audit, a provisional
  KITE-01 Q25 extraction and a historically rejected GREENHOUSE-01 attempt
  preserve their original decisions; no automatic state promotion occurs.
- Run actual saved evidence replay, **free and read-only**:

  ```bash
  python -m unittest discover -s tests -p 'test_story_harness*.py' -q
  python -m src.story_harness_p1 --manifest configs/story_harness_p1_frozen_import.json --repo-root .
  ```

- Historical Q25 provider-billed subtotal on these two saved records is
  `$0.085152`; **new harness cost is $0**.
- Provenance, limitations and trust boundary: [P1 frozen real evidence](docs/canonical/STORY_HARNESS_P1_REAL_EVIDENCE.md).
- **P2 typed local-gate evidence:** `StageInput.v1`, `GateReceipt.v1`
  and `StageResult.v1` now bind four actual archived cases to a freshly
  executed **local integrity/schema check**. Submitted receipts are verified
  by deterministic full recomputation; all four original historical outcomes
  stay unchanged. This check is **not** an authenticated original human/model
  quality gate, and cannot authorize downstream production or payment.
- Run the P2 gate receipt qualification (stdlib, $0):

  ```bash
  python -m src.story_harness_p2 --repo-root .
  ```

- [P2 StageResult and integrity-receipt scope](docs/canonical/STORY_HARNESS_P2_GATE_RECEIPTS.md).
- **P2.1 real Q25 offline gate execution:** On a *second, exactly pinned
  experiment checkout* the Harness now executes the genuine Q25
  `offline_replay()` source/structural validator for the original KITE-01
  and GREENHOUSE-01 raw model outputs. KITE remains source-bound candidates,
  GREENHOUSE's **original paid rejection remains RED** despite a later
  no-cost offline structural replay with citation-order normalization.
  Neither is full StoryState or semantic acceptance.
- Reproduce the two source-bound checks (requires a local checkout at
  `2eb3d825b5baf8f0f16ccb23805f619d433c7236` and Pydantic V2):

  ```bash
  python -m src.story_harness_p21 --repo-root . \\
    --pinned-q25-root /path/to/strictly-pinned-q25-checkout \\
    --verify-report evidence/story_harness_p21/pinned-real-q25-offline-replay.json
  ```

- [P2.1 real Q25 version-pinned gate and recorded boundaries](docs/canonical/STORY_HARNESS_P21_REAL_Q25_GATE.md).
- **P2.2 genuine SpineForge offline deterministic gate:** real frozen
  `validate_narrative_spine()` executed on the original approved island
  Spine, exact ContextPack and obligations. Authority/structure PASS with
  8 discovery turns and two choices, but **no human or LLM product gate
  authentication** and no Writer/Q25 execution authority.
  [P2.2 boundary](docs/canonical/STORY_HARNESS_P22_REAL_SPINE_GATE.md).
- **P3.0 same-story source lineage:** the original frozen Writer #3 manifest,
  result, envelope and story are now checked by the real pinned
  `load_verified_writer_story_artifact()` alongside P2.2 SpineForge.
  Spine hash, approval ID, context ID/fingerprint and exact story bytes
  all match one historical island story. Its original failed Story Audit
  qualification **remains RED** (`FAIL_KNOWN_DEFECT_MISSED`). The stored
  KITE/GREENHOUSE Q25 records are unrelated; the harness explicitly stops
  with `MISSING_SAME_STORY_Q25_ARTIFACT`. No Final StoryState, semantic
  certification, new paid call or automatic handoff is possible.
  [P3.0 same-story receipt](docs/canonical/STORY_HARNESS_P30_SAME_STORY_LINEAGE.md)
  and [tracking issue #281](https://github.com/necdetoskay/lumi-model-lab/issues/281).
- **P3.1 real historical Story Audit + repair/reaudit evidence:** the
  frozen Writer #3 story now has a pinned Stage 6/7/8 ancestry and
  continuous cycles 3–10 audit/repair artifact hashes. The later Story
  Audit #8 *qualification* is `PASS` but its **story quality decision**
  remains `LOCAL_REPAIR_REQUIRED`; all seven completed cycle 3–9
  reaudits likewise require local repair, and cycle 10 has no successful
  reaudit. Offline result: `STORY_QUALITY_NOT_ACCEPTED`, no English
  Master, Q25 or Final StoryState admission. Source integrity/lineage
  GREEN **does not certify a successful story**. [P3.1 frozen scope](docs/canonical/STORY_HARNESS_P31_FROZEN_QUALITY_LINEAGE.md)
  · [P3.1 tracking issue #282](https://github.com/necdetoskay/lumi-model-lab/issues/282).
- **P3.2 English Master admission (original island story):** the original
  quality pipeline's `ACCEPT → ENGLISH_MASTER_SEAL` policy is verified
  as a **conditional rule**, not a historical success. Cycle 10 is only
  `REAUDIT` pending; no exact same-story English Master seal exists in
  the 152-file pinned island source cohort. An unrelated Lighthouse
  `ACCEPT` must never be reused. Frozen result:
  `ENGLISH_MASTER_NOT_ADMISSIBLE`; no Q25, StoryState commit, new model
  call, or production write. [P3.2 source/acceptance boundary](docs/canonical/STORY_HARNESS_P32_ENGLISH_MASTER_ADMISSION.md)
  and [issue #283](https://github.com/necdetoskay/lumi-model-lab/issues/283).
- **P4.0 genuine v21 bounded-quality offline producer preflight:** the
  already-frozen v21 runtime and its original simulation adapter are now
  actually executed with offline synthetic provider responses. Six routing,
  retry, quality and budget cases pass; `ACCEPT` in these fixtures is
  **not** an accepted story. Historical paid run `37230896244`
  remains `REJECT_PROVIDER_FAILURE` (3 paid calls, historical $0.057988).
  Real English Master sealing and Q25 stay **DENIED** until a separate
  source-pinned real semantic-quality acceptance. [P4.0 preflight](docs/canonical/STORY_HARNESS_P40_V21_BOUNDED_PRODUCER.md)
  · [issue #284](https://github.com/necdetoskay/lumi-model-lab/issues/284).
- **P4.1 English Master seal evidence contract (mechanical simulation only):**
  the real frozen v21 runtime is replayed with isolated mocked model replies
  for the 1-call clean and 3-call single-repair positive paths. Strict typed
  seal candidate and read-only Q25 request *preview* contracts now validate
  same-story IDs/hashes, bounded usage/ledger, audit scope and immutable
  identities. Neither the synthetic `ACCEPT` nor an unreviewed candidate
  can produce a real seal or Q25 admission; all real trust registries remain
  empty. Result: `REAL_ENGLISH_MASTER_EVIDENCE_UNAVAILABLE`, **no provider
  spend, English Master, Q25 or state commit**.
  [P4.1 scope](docs/canonical/STORY_HARNESS_P41_ENGLISH_MASTER_SEAL_TRUST.md)
  · [issue #285](https://github.com/necdetoskay/lumi-model-lab/issues/285).
- **P4.2 redacted final-audit error diagnostics (experimental):** original
  frozen v21.4 runtime + adapter are exercised with seven deliberately bad
  **offline** targeted-final-audit responses. A separately versioned wrapper
  persists only raw-response hashes, safe schema/type/field-count summaries,
  validation path, and real-or-missing usage; injected secrets and raw prompt
  content are **not** persisted. Atomic O_EXCL/0600 receipt, no retry, no
  historical rewrite. Old v21.3 paid error details remain unrecoverable.
  Result `REAL_QUALITY_NOT_ACCEPTED_DIAGNOSTIC_READY`; no English Master,
  Q25, state writes or paid calls. [P4.2 diagnostics](docs/canonical/STORY_HARNESS_P42_REDACTED_FINAL_AUDIT_DIAGNOSTICS.md)
  · [issue #286](https://github.com/necdetoskay/lumi-model-lab/issues/286).
- **P4.3 v21.5 offline-only runner / paid kill switch:** the *original*
  frozen v21.4 audit, repair and final adapter callbacks now run behind a
  separately SHA-pinned, fake-transport-only, one-shot runner. Four callback
  cases qualify (one synthetic ACCEPT, three fail-closed final-audit errors),
  and pre-dispatch checks reject paid mode, invented grant/price/route,
  retries and unverified provider token budgets. Request sizes and output
  token allowances are recorded **only as exposure data, not cost guarantees**.
  English Master, Q25, paid model dispatch and production state remain OFF.
  [P4.3 runner](docs/canonical/STORY_HARNESS_P43_OFFLINE_V21_5_RUNNER.md)
  · [issue #287](https://github.com/necdetoskay/lumi-model-lab/issues/287).
- **P4.4 original age-12 island story review and controlled budget exception:**
  full original 2,407-word prose and the real paid v21 failed repair were
  compared, yielding five **source-quoted preliminary blocking issues**
  and two continuity/narrative advisories. Verified old paid run had
  3 calls/$0.057988 and ended `REJECT_PROVIDER_FAILURE`. Public Sonnet 5.5
  prices ($2/M in, $10/M out) imply a **conditional** $0.123178 exposure
  if original input tokens remain unchanged and frozen output caps are hit.
  User allowed exceeding the $0.10 target, **not unlimited spending**;
  a finite authorized total and real provider preflight remain mandatory.
  Zero API calls, English Master and Q25 still denied.
  [P4.4 source-bound review](docs/canonical/STORY_HARNESS_P44_STORY_FORENSIC_AND_BUDGET.md)
  · [issue #288](https://github.com/necdetoskay/lumi-model-lab/issues/288).
- **P4.5 real offline manuscript improvement (NOT an accepted model story):**
  the actual source-island bridge scene S159–S177 has been rewritten as
  **370 words**, making character banks, the belayed Nisa swing, the line
  snag, why Arda cuts it and his trust in Nisa explicit. The original
  frozen v21.4 `apply_scene_rewrite` creates a fresh **2,494-word**
  complete adventure from the immutable Writer source without changing
  anything outside the exact scene cluster; both English files and all
  SHA-256 provenance are locally prepared (GitHub publication pending). This is an **offline assistant-edited,
  unreviewed** candidate, not real model ACCEPT, English Master, Q25 or paid
  run. [P4.5 architecture](docs/canonical/STORY_HARNESS_P45_ACTUAL_SCENE_EDITORIAL_REWRITE.md)
  · [candidate scene](evidence/story_harness_p45/offline-editorial-bridge-scene.txt)
  · [full edited story](evidence/story_harness_p45/offline-editorial-full-story.txt).
- **P4.6 full-story editorial cleanup:** a separately sourced 2,482-word
  authorial Writer revision secures both gliders with independent landing
  tethers before Arda removes the expedition line and makes the return-trail
  camp/journal interruption shorter after their turnaround promise. All four
  changes are source-anchored and replayed against P4.5; the 370-word bridge
  fix stays identical. This is **UNREVIEWED** prose, not a new model run,
  signed semantic ACCEPT, English Master or Q25 source.
  [P4.6 details](docs/canonical/STORY_HARNESS_P46_FULL_STORY_EDITORIAL.md)
  · [new full draft](evidence/story_harness_p46/offline-full-story-writer-revision.txt)
  · [issue #289](https://github.com/necdetoskay/lumi-model-lab/issues/289).
- **P4.7 exact route-truth Writer correction:** a new source-anchored
  **2,491-word** English candidate now correctly distinguishes the original
  explorers' knot navigation from Arda's carried expedition rope (one exact
  full-text substitution). Preserves all P4.6 evidence; editorial review
  leaves five open questions, not independent semantic quality ACCEPT.
  The old frozen v21.4 paid profile is pinned to a **different** story
  SHA, so P4.7 **fails closed** until a separately versioned new-story
  quality profile can be qualified. New paid model calls $0/0; English Master,
  Q25 and state writes remain denied.
  [P4.7 rationale](docs/canonical/STORY_HARNESS_P47_ROUTE_TRUTH_AND_QUALITY_HANDOFF.md)
  · [full manuscript](evidence/story_harness_p47/offline-full-story-route-truth-revision.txt)
  · [issue #290](https://github.com/necdetoskay/lumi-model-lab/issues/290).
- **P4.8 actual Writer candidate through frozen original v21 model adapters,
  offline only:** a fresh immutable 2491-word English source and 228
  source-derived spans are bound to the approved Spine with a new provisional
  profile. The original frozen quality core and real model-adapter callback
  functions execute **five fake provider scenarios** against the actual NEW
  full story. The bridge now spans 45 segments, above the 40-span maximum
  repair scope; only a 37-span subset can be bounded, with out-of-scope
  issues rejected. **No actual API calls/quality ACCEPT** and no approved
  new scene scope or paid user grant. The old frozen profile is unchanged.
  [P4.8 qualification](docs/canonical/STORY_HARNESS_P48_NEW_STORY_OFFLINE_ADAPTER.md)
  · [new Writer artifact](evidence/story_harness_p48/new-story-writer-candidate.json)
  · [issue #291](https://github.com/necdetoskay/lumi-model-lab/issues/291).
- Future work: independently authenticated real gate receipts, then bounded
  model registry and executable stage adapters, each on new qualified versions.

## Current milestone

Milestone 1 validates the complete learning loop with a deliberately small but reproducible dataset before scaling data volume or training cost.

The current roadmap now separates three model-lab tracks:

1. **Teacher/data track** — GPT Luna remains the selected teacher for high-quality supervised story generation.
2. **Dense/local student track** — compact/dense candidates are baseline-tested first, then promoted to QLoRA only if both story quality and hardware feasibility justify training.
3. **Large-MoE inference track** — FreeToken is evaluated separately as an inference/benchmark runtime for supported large MoE models; it is not treated as a low-VRAM training solution.

## Visual generation architecture

LUMI Model Lab has a canonical multi-model visual-generation baseline. It separates user-selected visual style from provider/model routing, defines versioned model/style metadata, category-specific prompt contracts, character/world continuity, immutable artifacts, semantic validation, bounded retry, and per-call cost/latency lineage.

- Canonical contract: `docs/canonical/VISUAL_GENERATION_ARCHITECTURE_V1.md`
- Related runtime-profile governance: `docs/canonical/MODEL_RUNTIME_PROFILE_REGISTRY_V2.md`
- Execution epic: #218; P0–P7 implementation complete, P8 live-model qualification tracked in #227
- Fixture evidence: `runs/visual_qualification/visual-fixture-matrix-v1/summary.json`
- Production principle: users choose the look; routing may choose different qualified models per visual category while preserving that look
- Real image-model profiles remain unqualified until live evidence passes the P8 gate

No-cost contract/qualification smoke:

```bash
python -m src.visual_qualification_runner \
  --config configs/visual_qualification_fixture.yaml \
  --evidence-dir runs/visual_qualification/local-fixture
```

Guarded live screening wave (requires `OPENROUTER_API_KEY`; one run per cell, so it cannot promote a model):

```bash
python -m src.visual_qualification_runner \
  --config configs/visual_qualification_live_screen_v1.yaml \
  --evidence-dir runs/visual_qualification/live-screen-v1
```

## Long-horizon Saga architecture lab

A new **lab-only** track evaluates whether a premium narrative model can create a durable Origin + Saga Blueprint whose value survives many later stories generated by a mid-tier model. The experiment explicitly tests optional Saga usage, long dormancy, delayed re-entry, world integration, reveal ceilings, character agency, and whether Saga context creates measurable downstream narrative lift rather than merely producing an impressive creation-time document.

This track does **not** authorize Project_LUMI production integration. JEV may later be tested as a bounded seed-ranking / compatibility workload, but deterministic eligibility remains authoritative and no JEV verdict transfers automatically from the core Judge Lab.

- Experiment canon: `docs/canonical/LONG_HORIZON_SAGA_LAB.md`
- Generation contract: `docs/canonical/CHARACTER_NARRATIVE_BLUEPRINT_V1.md`
- Downstream protocol: `docs/canonical/SAGA_DOWNSTREAM_EVALUATION_PROTOCOL.md`
- Execution epic: #55 — Long-Horizon Saga Lab — Premium Narrative Blueprint Qualification

## Experimental decision-engine track

The lab is evaluating **bounded decision engines** as a fast classification/routing layer in front of expensive reasoning models. JEV remains a reference/proprietary candidate, but the architecture is provider-agnostic and must compare realistic open/local alternatives on the same frozen LUMI evidence before any production dependency is proposed.

Shared rules include deterministic authority for hard invariants, explicit `INSUFFICIENT_EVIDENCE` / `ESCALATE` paths, per-risk confidence calibration, reproducible engine/runtime fingerprints, counterfactual/invariance tests, and full cascade economics.

- Shared canonical contract: `docs/canonical/DECISION_ENGINE_LAB.md`
- Judge-specific canonical contract: `docs/canonical/JEV_JUDGE_LAB.md`
- Core research epic: #27 — JEV Judge Lab — AEGIS Qualification & Judge Cascade Decision
- Shared harness: #30 — provider-agnostic decision-engine adapter + evidence ledger
- Execution routing: #38 — bounded model/agent/repair/retry/escalation routing
- StoryOpportunity ranking: #39
- Bounded NPC reaction selection: #40
- Local target: RTX 4060 8 GB class hardware for the first open/local lane
- Production boundary: any Project_LUMI integration requires a separate L3 AEGIS review and is **not** authorized by this repository.

### Decision-engine harness

The provider-agnostic evidence harness now has a first executable baseline:

```bash
python -m src.decision_engine_runner --config configs/decision_engine_fixture_smoke.yaml
```

The initial adapter types are:

- `fixture` — deterministic dry-run/test evidence;
- `command` — JSON-over-stdin/stdout sidecar boundary for local/open or hosted engine adapters.

The command adapter never uses `shell=True`. It receives a versioned workload/case envelope and must return the normalized `DecisionEngineOutput` JSON contract.

Evidence is stored under a SHA256 experiment fingerprint and includes request fingerprints, state size, question count, exact engine identity, per-case raw output, runtime/provider metadata, usage/cost fields, cold/warm latency, malformed-output classification and runtime-error classification. Re-running the same experiment refuses silent overwrite unless `--rerun` is explicit.

#### JEV hosted sidecar

JEV is connected through the same `command` adapter rather than special-casing the Python harness.

Install the pinned optional AI SDK dependency:

```bash
npm install
```

Set either `AI_GATEWAY_API_KEY` or `VERCEL_OIDC_TOKEN`, then run:

```bash
python -m src.decision_engine_runner --config configs/decision_engine_jev_smoke.yaml
```

The sidecar is `tooling/decision-engine/jev-ai-sdk-sidecar.mjs`. It requests `typesafe-ai/jev` through AI SDK 7's experimental evaluation API with Zero Data Retention requested, does not configure a fallback model, and returns the same normalized JSON contract used by local/open engines.

The requested gateway alias and the provider-reported resolved model metadata are stored separately when exposed. Probability/confidence values are preserved rather than treated as correctness.

### Judge gold/reference corpus

The Judge track now has a frozen v2 case plan and blind-human protocol:

- protocol: `docs/canonical/JUDGE_GOLD_CORPUS_PROTOCOL.md`
- manifest: `data/specifications/judge_gold_corpus_v2.json`
- 100 case descriptors with source-family partition isolation
- 46 calibration / 27 development holdout / 27 final holdout
- explicit critical-protected and Turkish ↔ controlled-English comparison subsets
- validator: `python -m src.judge_gold_corpus`

Current status is intentionally **NOT_PROMOTABLE**: synthetic mutation artifacts still require materialization and the corpus still requires complete blind human labels. Automation must not invent human labels.

### Judge atomic rubric

The bounded Judge workload now has a frozen v1 rubric structure:

- canonical contract: `docs/canonical/JUDGE_ATOMIC_RUBRIC_V1.md`
- machine-readable rubric: `data/specifications/judge_atomic_rubric_v1.yaml`
- validator: `python -m src.judge_atomic_rubric`
- current status: `FROZEN_STRUCTURE_CALIBRATION_PENDING`

The v1.1 split keeps exact invariants in deterministic code, assigns narrow semantic dimensions to decision-engine qualification, keeps narrative progression/ending as hybrid candidates, and retains creativity/literary/deep-holistic judgment on the stronger LLM lane. Every dimension now has a paired `SUFFICIENT / INSUFFICIENT_EVIDENCE` gate; an abstained dimension's forced score is ignored. TR native, independently frozen English, and controlled-English projection are separate experiment variants. P3 does not define an aggregate story PASS/BLOCK formula.

### Decision-engine benchmark

The P4 comparison analyzer is versioned at:

- protocol: `docs/canonical/DECISION_ENGINE_BENCHMARK_V1.md`
- runner: `python -m src.decision_benchmark`

It separates historical PASS/BLOCK verdict metrics from atomic 0–4 decision-engine metrics and will not derive a story PASS/BLOCK from atomic scores. It reports exact/adjacent agreement, native-score MAE, quadratic weighted kappa, and—when native score distributions exist—multiclass Brier, log loss, ECE, selective risk/coverage and AURC.

The final holdout requires an explicit `--final-evaluation` flag. If complete final human atomic references are missing, quality metrics are suppressed and the benchmark returns `REFERENCE_INCOMPLETE`. The current real corpus is in that state.

### Decision-engine red-team

The P5 metamorphic falsification layer is versioned at:

- protocol: `docs/canonical/DECISION_ENGINE_REDTEAM_V1.md`
- frozen diagnostic suite: `data/specifications/decision_redteam_v1.json`
- evaluator: `python -m src.decision_redteam --run <decision-engine-manifest.json>`

The v1 diagnostic suite contains 24 synthetic cases and 13 frozen relations covering knowledge/relationship/world/age contradictions, irrelevant context, entity renaming, field ordering, missing-evidence abstention, prompt injection, repeat stability, rubric mimicry, semantic repetition, and schema confinement.

The committed fixture engine is only a harness self-test. A fixture PASS is **not** a JEV/open-model P5 verdict.

Current local student experiment:

- candidate: `ornith-ai/Ornith-1.5-9B`
- hardware: RTX 4060 Laptop GPU, 8 GB VRAM
- native HF/Unsloth 4-bit load: does not fit with the current pure-GPU load path; this is recorded as a hardware/load-path result, not a model rejection
- working baseline runtime: llama.cpp GGUF through an OpenAI-compatible local endpoint
- one-story smoke: PASS, 1,924 words, 101.7 s
- frozen five-story baseline: 5/5 runtime completions, 4/5 technical length passes, 1,611.8 average words, 467.2 s total runtime
- current failing case: `05_emotional_calm` produced 915 words and failed the target-length gate
- next gate: common LUMI judge rubric and failure/repetition inspection before deciding whether Ornith is a training candidate

Epic #12 (`Local Student Training & Large-MoE Inference Roadmap`) is the SSOT for this sequence. PR #11 contains the current Ornith local-baseline work.

Completed foundations:

- OpenRouter teacher-story generation with prompt/model metadata, token usage, provider metadata, and cost
- frozen five-story teacher benchmark
- LLM judge with six scored criteria and acceptance gates
- independent five-story source dataset for training-data creation
- supervised extraction into 11 examples per accepted source story (55 examples for five stories)
- deterministic curation and manual-review gate
- frozen UTF-8 JSONL training dataset with SHA256 manifest
- local CUDA / Unsloth preflight tooling
- Qwen3.5-0.8B 4-bit model-load probe on a 4 GB RTX 3050 Ti Laptop GPU
- successful QLoRA smoke training
- frozen five-story pre-finetune local baseline
- one-command teacher-model qualification pipeline and model leaderboard
- external/manual source-story ingest path with independent judge and training-example extraction
- raw, curated, processed dataset artifacts and compact experiment records tracked in Git for cross-machine reproducibility

The original 4B target remains `Qwen/Qwen3.5-4B` as the starting checkpoint for the stronger-GPU experiment. The 0.8B checkpoint is used locally to learn and validate the complete training mechanics on constrained hardware.

## Repository data policy

Small textual data and reproducibility artifacts are versioned so the same experiment can be continued on another machine.

Tracked:

```text
data/raw/
data/curated/
data/processed/
data/specifications/
runs/                 # manifests, reports, qualification outputs, benchmark text/JSON
```

Not tracked:

```text
.env
.venv/
.venv-train/
.venv-ornith/
models/
adapters/
.cache/
**/checkpoint-*/
```

Large model weights, virtual environments, Hugging Face caches, LoRA adapters, and trainer checkpoints remain local.

## API / data-generation setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
```

Set at least:

```env
OPENROUTER_API_KEY=...
TEACHER_MODEL=...
JUDGE_MODEL=...
```

`USD_TRY_RATE` is optional. When supplied, qualification summaries also show the USD total converted to TRY using that explicit rate.

### Training environment note

A separate training environment is used for the CUDA / Unsloth stack, but it still needs the repository's lightweight application dependencies (`python-dotenv`, `pyyaml`, `requests`, `rich`, `pydantic`). After creating or activating the environment, also run:

```bash
python -m pip install -r requirements.txt
```

This does not install or replace the CUDA / Unsloth training stack because those packages are intentionally not pinned in `requirements.txt`.

## Ornith local endpoint baseline

The preferred baseline path for Ornith on the RTX 4060 8 GB machine is GGUF + llama.cpp rather than the current native HF/Unsloth pure-GPU load path.

Start a local OpenAI-compatible llama.cpp server with the Ornith Q4_K_M GGUF, then run:

```bash
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 1
```

After a stable one-story smoke, expand to the frozen five-story benchmark:

```bash
python -m src.local_endpoint_baseline --config configs/local_baseline_ornith15_9b.yaml --limit 5
```

Local endpoint artifacts are written under:

```text
runs/model_baseline/pre_finetune_ornith15_9b/
```

They can be judged with the same six-criterion LUMI rubric through:

```bash
python -m src.judge_local_endpoint --input runs/model_baseline/pre_finetune_ornith15_9b/story_01.json
```

This judge adapter uses the configured `JUDGE_MODEL` and `OPENROUTER_API_KEY`, so it may incur provider cost.

## One-command model qualification

The preferred way to test a newly discovered OpenRouter model is:

```bash
python -m src.model_qualify --model "provider/model-name"
```

Default behavior is quality-gated and sequential:

```text
1. duplicate/fingerprint registry check
2. frozen 5-story technical benchmark
   └─ fail -> stop before judge cost
3. judge benchmark
   └─ fail -> stop before dataset-generation cost
4. independent 5-story training-source generation + judge
   └─ fail -> stop
5. supervised extraction (target: 55 examples)
6. deterministic curation
   └─ review/reject -> stop as NEEDS_MANUAL_REVIEW
7. frozen training JSONL + SHA256 manifest
8. registry + token/cost ledger + final report
```

Provider/request failures are not model-quality failures. If benchmark generation cannot complete because the provider rejects request parameters, the run is recorded as `generation_error` instead of `rejected_technical`. Model-specific OpenRouter compatibility options belong in `src.generate.build_model_options`; for example, `google/gemini-3.7-flash` keeps mandatory reasoning enabled at low effort while excluding reasoning text from the visible story response.

Benchmark stories are never used as training examples. Training source stories come from a separate frozen specification set.

### Fast screening only

```bash
python -m src.model_qualify --model "provider/model-name" --screen
```

This stops after benchmark + judge and avoids source-story/extraction cost.

### Duplicate protection

A qualification fingerprint includes the model id, current judge model id, prompts, protocol configs, frozen benchmark specifications, and frozen training-source specifications. The same model under the same experiment fingerprint is not run again accidentally.

```bash
python -m src.model_qualify --model "provider/model-name"
# -> ALREADY TESTED when the exact experiment already exists
```

Intentional repeat:

```bash
python -m src.model_qualify --model "provider/model-name" --rerun
```

A prompt, judge, gate, or frozen-spec change produces a different fingerprint and is treated as a new experiment.

### Import pre-registry benchmark history

```bash
python -m src.import_legacy_benchmark
```

Legacy records are marked `legacy_screened`. Historical generation manifests did not store teacher input-token counts, so their total-token value is explicitly marked as a lower bound; stored USD costs and available judge usage are preserved.

### Registry and status

```bash
python -m src.model_qualify --list
python -m src.model_qualify --model "provider/model-name" --status
```

Registry: `runs/model_registry/registry.json`.

## External/manual source story ingest

A story generated outside the normal OpenRouter teacher pipeline can be admitted as a training source only through the same independent quality controls. The canonical generation prompt is versioned at:

```text
prompts/generated_story_source.md
```

Give that prompt to any LLM, save its YAML output, and run:

```bash
python -m src.ingest_story --input path/to/story.yaml
```

The ingest pipeline is intentionally gated:

```text
external YAML story
    ↓
1. schema + technical validation
    └─ fail -> REJECTED_TECHNICAL; no judge/extraction spend
    ↓
2. independent JUDGE_MODEL evaluation
    └─ fail -> REJECTED_JUDGE; no extraction spend
    ↓
3. fixed extractor protocol
    └─ 11 supervised examples expected
    ↓
4. deterministic curation
    └─ review/reject -> NEEDS_MANUAL_REVIEW
    ↓
5. isolated training-ready JSONL + SHA256 manifest
```

The external model's own `training_eligible` or `suitability` values are stored as provenance only. They never override the local technical gate or independent judge decision.

Each successful story produces the same 11-example shape:

```text
1  full_story_from_brief
2  continuation
2  character_dialogue
2  scene_expansion
1  conflict_resolution
1  ending_generation
2  plan_to_prose
-----------------------
11 examples/story
```

The output is isolated from the frozen Milestone-1 55-example dataset:

```text
runs/manual_ingest/<story-id>__<input-sha>/
  input_snapshot.yaml
  source/
  judgment/
  extraction/
  curated/
  dataset/
  manifest.json
```
