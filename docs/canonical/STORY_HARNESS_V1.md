# LUMI Story Harness V1 — Canonical Control-Plane Contract

**Status:** EXPERIMENTAL / MODEL-LAB-ONLY / NOT PRODUCTION READY
**Track:** Story creation control plane; distinct from Decision Engine/JEV workload harness (`#30`).
**Authority:** No change to production LUMI, G2 canonical state, SpineForge frozen evidence, Story Writer or Q25 gate semantics.
**Implementation boundary:** `src/story_harness_v1.py` (V1 is strictly a read-only, zero-provider-call archived-stage replay).

## The problem

SpineForge, scene-writing/Relay, final-state extraction (Q25) and quality gates have separately developed artifacts, budgets, provider settings and acceptance rules. A failure in one stage requires finding its run evidence and understanding what the next stage actually consumed. This control plane creates a single lineage view without rewriting these stage implementations or silently promoting any provisional output.

**A harness cannot fix poor writing, weak plans or unverified semantics.** A good harness makes them explicit and auditable. Existing source/semantic validators remain authoritative.

## Target topology

```text
Canonical Context (read-only)
       |
       v
[SpineForge/Spine Compiler]       <-- stage-specific creative model(s)
       |
  frozen spine artifact
       v
[Scene Relay / Writer]            <-- scenes + pinned story state
       |
  frozen story artifact
       v
[Q25 Terminal-State Candidates]  <-- source-bound extraction, still untrusted
       |
  frozen raw + analysis
       v
[Quality / Independent Review]    <-- existing bounded gate(s), no new autonomous loops
       |
[Finalization Gate]              <-- production integration is NOT in V1

     all stages ------> Story Harness Control Plane
                         | run manifest and lineage
                         | model-profile registry (future adapter)
                         | budget/call count (future adapter)
                         | typed stage gate evidence
                         | immutable artifact registry
                         | reproducible replay
```

## V1 boundary and truth model

- **V1 implemented:** Strictly offline archive replay. A fixed ordered plan lists existing JSON artifacts, explicit SHA-256s, dependency references and **reported** gate outcomes. The harness verifies the file bytes, order and chain and produces a deterministic run report.
- **V1 does NOT:** invoke OpenRouter or any other model; run a shell command; invoke the actual SpineForge/Q25 validators; claim semantic correctness; make or change a state commit; mutate upstream evidence; publish to LUMI; auto-retry/fallback; or automatically treat `reported_gate=PASS` as genuine model/gate acceptance.
- The exact fixture plan contains only **illustrative local archives**, not model output. A green harness CI means the orchestration code works for test cases, **not** that a new story has been generated or accepted.
- Existing experiment artifacts (including Q25 Draft PR #273) are deliberately outside this branch. Real adapters will be introduced only after their frozen version/contract is explicitly bound and separately reviewed.
- Source paths are repository-root relative JSON files with pinned hashes. Reject absolute paths, traversal, symlinks, oversized records and duplicate JSON properties. Never accept user-controlled code execution.
- `reported_gate` is unverified external metadata; preserve its provenance. `PASS` permits only the **next offline inspection**, not semantic admission.
- If a stage has `REJECT` or `REVIEW`, stop; do not process later stages. Failed hash, duplicate stage, dependency mismatch or exceeded budget must **fail closed**.
- `max_provider_calls=0` and `max_cost_usd=0` are non-negotiable V1 constants. A paid run requires a distinct future protocol with explicit authorization and maximum spending.
- Optionally archive the computed report under `runs/story_harness_v1/<run_id>/manifest.json` once; never overwrite an earlier run ID. Default replay writes nothing.
- All manifests are read-only experimental lineage evidence, with flags `semantic_support_certified=false`, `full_story_state_qualified=false`, `state_commit_authorized=false`, `production_write_performed=false`.

## Stage contract targets (next versions, not implemented by this V1 fixture)

Each real stage adapter will publish an explicitly versioned `StageInput` and `StageResult`: stage name, handler/version, input/output artifact digest(s), provider/model exact ID/revision, token/cost/latency ledger, independently authoritative gate decision, stop reason, and immutable prior-stage lineage. The harness must never overwrite the stage's actual gate verdict.

Required ordered states: `PREPARED → STARTED → COMPLETED_UNVERIFIED → GATE_ACCEPTED` or `STOPPED_<REASON>`; `GATE_ACCEPTED` is available **only if** a separately authenticated stage gate has actually returned PASS, never because a plan author wrote `PASS`.

Future integration order:

1. **V1:** Deterministic fixture replay + hash/inventory and stop-policy tests, fully offline. Verify on separate branch and Draft PR.
2. **V1.1:** Read-only adapters for **existing frozen** SpineForge and Q25 outputs, **no model calls**, preserve Q25 `SOURCE_BOUND_CANDIDATES_ONLY` as provisional and the historical GREENHOUSE paid attempt as **REJECTED**. Never auto-transform historical verdicts.
3. **V1.2:** Stage-specific actual validator invocation with typed versions and isolated, auditable gate results. Prove semantic truth/review workflow separately; do not treat a citation as semantic entailment.
4. **V2:** Explicit per-stage model profile/budget registry and bounded paid execution; pinned provider/model, immutable audit, one authorized call at a time, no implicit fallback.
5. **V3:** End-to-end scene relay with deterministic stop/resume and stage-bound artifacts. A production cutover must be a separate decision.

## Acceptance criteria for V1

- Running the same fixture plan twice returns byte-equivalent deterministic JSON (no timestamps, randomness, network, billable actions).
- Detect tampering in any supplied stage artifact or its SHA; never process the next stage after a reported reject/review.
- Detect an artifact-lineage mismatch even when a file itself exists and its digest is otherwise valid.
- No auto semantic certification, no production writes, no model calls, no new dependencies.
- SHA references remain portable across machines and do not depend on local paths or execution timing.
- All tests CI green in an isolated Draft PR. No merge into `main` or change to Q25 until explicitly reviewed.

## MVP verification

```bash
python -m unittest discover -s tests -p 'test_story_harness_v1.py' -q
python -m src.story_harness_v1 --plan configs/story_harness_v1_fixture.json --repo-root .
```

Neither command should use secrets, the network, GPU, or cost-bearing APIs.
