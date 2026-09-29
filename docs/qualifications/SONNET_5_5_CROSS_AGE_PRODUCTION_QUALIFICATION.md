# Sonnet 5.5 Cross-Age Production Qualification

Status: C0 CANDIDATE PROFILES READY — PRODUCT BUDGET APPROVAL BLOCKS PAID RUNS

## Baseline authority

The qualification starts from the completed Sonnet 5.5 Final V3 production candidate:

- canonical run: 36581420415
- status: publication_ready=true
- English master: 1,889 words
- Turkish delivery: 1,562 words
- total cost: $0.17488370
- summed model latency: 226.663s
- final architecture:
  1. Sonnet 5.5 Episode Spine Architect
  2. GPT-5.6 Luna authority-aware Spine Gate
  3. HUMAN spine approval
  4. Aion 3.5 Mini Writer
  5. typed story-authority-packet.v1
  6. compact GPT-5.6 Luna canon/state gate
  7. confirmed-defect bounded repair only when needed
  8. Gemini 3.8 Flash EN→TR translation
  9. GPT-5.6 Luna fidelity + contextual adjudication

Do not reintroduce always-on generic multi-judge stacking. The Sonnet/Luna/Sol raw-story experiments showed that stronger judges did not solve authority-packaging blind spots. Typed compact authority raised the confirmed five-root canon/state recall from 40% to 100%.

## Goal

Qualify the Final V3 architecture across exact ages:

- 12
- 18
- 25
- 40
- 60

The purpose is not to prove only that the models can produce text. Each case must prove:

- exact-age premise maturity;
- correct narrative complexity and language register;
- writer executability from an approved spine;
- typed authority / canon-state safety;
- bounded repair behavior;
- natural Turkish delivery;
- end-to-end token, cost, and latency accounting.

## C0 blocker: reader-profile authority

The runtime already accepts --reader <profile.json>, but the repository currently contains only:

data/specifications/reader_profiles/age12_adventure_v2.json

Canonical age-tier mapping from configs/capability_cube.yaml:

| Exact age | NarrativeAgeTier | Qualification STANDARD target |
|---:|---|---:|
| 12 | MIDDLE_CHILD | 2,800 |
| 18 | YOUNG_ADULT | 4,200 |
| 25 | ADULT | 4,200 |
| 40 | MATURE_ADULT | 4,200 |
| 60 | SENIOR | 4,200 |

The capability-cube target is a qualification target, not product session authority.

The already-qualified age-12 product profile intentionally uses STANDARD 1,600–2,500 words even though its capability bridge records the MIDDLE_CHILD qualification target of 2,800 words. ReaderDevelopmentProfileV2 explicitly declares product_session_length_is_separate_authority=true.

Therefore the old cube's 4,200-word adult STANDARD target MUST NOT be copied automatically into the Final V3 product pipeline. Product-session budgets for 18/25/40/60 must be decided separately with turnaround, reading-time, and quality evidence.



## C0 candidate profiles

Schema-valid but non-authoritative candidate profiles now exist for ages 18, 25, 40 and 60 under:

data/specifications/reader_profiles/candidates/

They intentionally keep reader_profile=null in the cross-age matrix, so no paid qualification can treat them as approved authority.

Design rule:
- maturity increases through premise, conceptual, causal, agency, stakes, social, and inference complexity;
- maturity MUST NOT be simulated by simply making stories longer or vocabulary denser;
- age 40/60 MUST NOT imply frailty, nostalgia, retirement, illness, parenthood, reduced agency, or simplified cognition unless explicitly requested;
- the inherited 1,600–2,500 STANDARD range in candidate files is only a neutral schema placeholder and is NOT approved product budget.

## C0 exit criteria

No paid model call is allowed until all are green:

1. Create exact-age reader profiles for 18/25/40/60.
2. Preserve canonical capability-tier and reading-mode validation.
3. Define product STANDARD session ranges separately from capability-cube qualification targets.
4. Add deterministic tests that reject tier/profile/budget mismatch.
5. Keep age 12 Final V3 immutable as the control.
6. Record one machine-readable cross-age matrix with all paid boundaries explicit.

## Qualification sequence after C0

For each new exact age, run one case at a time:

### C1 — Spine only
Sonnet 5.5 Architect → deterministic validators → Luna authority-aware gate → HUMAN review.

Stop. No Writer without explicit human approval.

### C2 — Writer only
Approved spine → Aion 3.5 Mini → deterministic length/structure checks.

Stop before paid QA.

### C3 — Typed authority QA
Build story-authority-packet.v1 → compact Luna canon/state gate.

If clean, do not call Sol.
If confirmed defects exist, pass only those defects to bounded repair.

### C4 — English acceptance
Verify repaired English against deterministic constraints and compact authority.

### C5 — Turkish delivery
Gemini 3.8 Flash translation → Luna fidelity → contextual adjudication → repair only confirmed fidelity defects.

### C6 — Promotion decision
Compare each age against the age-12 Final V3 control for:
- publication readiness;
- age maturity;
- serious/critical defect count;
- repair count;
- total calls;
- input/output/reasoning/cache tokens;
- total USD cost;
- per-stage and total latency.

## Promotion rule

Cross-age architecture promotion requires every target age to reach publication-ready without weakening authority controls.

A pass at age 12 does not authorize assumptions about adult/senior maturity, session budget, or language register. Evidence cohorts stay separate by exact age and reader-profile SHA.
