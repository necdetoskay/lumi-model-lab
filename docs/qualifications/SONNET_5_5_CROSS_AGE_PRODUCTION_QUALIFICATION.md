# Sonnet 5.5 Cross-Age Production Qualification

Status: C0 GREEN — AGE18 C1 SPINE ONLY AUTHORIZED

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



## C0 GREEN decision

User approved a fixed product STANDARD range of 1,600–2,500 words for the first controlled 12/18/25/40/60 proof.

This intentionally holds length constant while exact-age maturity changes, preventing story length from becoming a confound.

Promoted reader-profile authorities now exist for exact ages 18, 25, 40 and 60.

The first paid scope is narrow:
- age18 only;
- Sonnet 5.5 Episode Spine Architect;
- deterministic EpisodeSpineV2 validators;
- GPT-5.6 Luna Spine Gate only if deterministic validation passes;
- stop for HUMAN review;
- no Writer, audit, repair, translation or fidelity.

Age18 uses a controlled Shattered Meridian A/B fixture so world identity is held stable while professional responsibility, institutional consequences, agency, inference and social complexity are raised.

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


## Age18 C1 result — REPLAN

Architect run: 36608347735
Luna recovery run: 36608978063

Metrics:
- Sonnet 5.5 Architect: $0.085046 / 42.817s
- Luna Gate: $0.00417195 / 17.008s
- combined: $0.08921795 / 59.825s
- combined tokens: 28,598

What passed:
- exact-age 18;
- STANDARD 1,600–2,500;
- MAIN_SAGA_ENTRY;
- first_discrepancy_logged only, commit-only-if-earned;
- AGE_MATURITY 5/5;
- AGENCY 5/5;
- SAGA_ALIGNMENT 5/5;
- REPETITION_SAFETY 5/5;
- professional/institutional stakes are materially more mature than the age12 control.

Blocking conflicts:
1. fresh_setup_repeat requires a fixed repeat-pair evidence result during the climax, while a global writer rule says no new evidence in the climax;
2. global local_payoff says the anomaly is professionally on record, while fresh_setup_repeat explicitly ends without a reviewed formal record.

Decision:
- C1 = REPLAN;
- do not call Writer;
- do not rerun Sonnet automatically;
- C1.1 revision feedback preserves the age18 maturity, professional responsibility and branch asymmetry while removing the two cross-field contradictions.


## Age18 C1.1 result — GATE ACCEPT / HUMAN REVIEW

Architect run: 36610913523
Luna recovery run: 36611398520

Metrics:
- Sonnet 5.5 Architect: $0.089900 / 42.012s
- Luna Gate: $0.00400025 / 18.284s
- combined: $0.09390025 / 60.296s
- combined tokens: 30,012

Recovery:
- deterministic safe normalizer removed one reversal self-reference only;
- valid pre-reversal support remained;
- semantic fields were unchanged;
- strict EpisodeSpineV2 validation passed.

Luna:
- ACCEPT
- blocking reasons: none
- AGE_MATURITY 5/5
- AGENCY 5/5
- WORLD_IMMERSION 5/5
- all other dimensions 4/5

Human pre-adjudication:
- previous climax evidence contradiction fixed;
- previous global-payoff branch contradiction fixed;
- fresh-setup branch => stronger independent evidence, no reviewed formal log, no milestone;
- provisional-record branch => reviewed bounded log, milestone eligibility;
- no route advisory, cause, recurrence or wider-beacon anomaly is committed;
- exact-age maturity comes from professional responsibility, evidence thresholds and institutional consequence rather than extra length.

Decision:
- C1.1 mechanically GREEN;
- Writer remains blocked pending explicit user creative approval.


## Age18 C2 result — WRITER GENERATED / C3 READY

Writer run: 36612862926

Metrics:
- Aion 3.5 Mini Writer: $0.0316043 / 317.074s
- Writer tokens: 27,141 total / 17,746 reasoning
- English words: 2,172
- deterministic length: PASS (1,600–2,500)
- spine+gate+writer: $0.12550455 / 377.37s / 57,153 tokens
- chosen branch: provisional_record

Compared with the age12 Sonnet-5.5 Writer control:
- Writer cost increased about 124.7%
- Writer latency increased about 201.6%
- Writer reasoning tokens increased about 352.0%
- full pipeline through Writer increased 18.3% in cost, 143.5% in latency and 30.7% in tokens

Interpretation:
Holding word length constant successfully isolates maturity from length, but exact-age-18 professional reasoning substantially increases Aion reasoning/latency.

Free human pre-audit confirmed three authority/state roots:
1. premature formal-record commit at Beacon Ridge before reviewer acceptance;
2. unsupported exclusion of setup/instrument explanations despite the approved inference ceiling;
3. raw field notes described as a future blank page in the unchosen branch.

Review-only observations:
- an unsupported prior rumor about Beacon Ridge;
- exact numeric evidence values not explicitly fixed by the architect.

C3 preparation:
- typed story-authority-packet.v1 pinned;
- confirmed three-root gold hidden from the model;
- next paid scope: one GPT-5.6 Luna compact authority gate only;
- no repair, Sol, translation, fidelity or writer regeneration is authorized.


## Age18 C3 result — PACKET V1 INSUFFICIENT / C3.1 READY

Run: 36614762650

Paid call:
- GPT-5.6 Luna compact authority gate only
- incremental cost: $0.00434985
- latency: 7.351s
- no repair, Sol, translation or fidelity call

Technical result:
- inference completed;
- strict post-inference normalizer rejected one model finding because the model joined multiple story spans into one exact_quote with an ellipsis;
- raw payload and full usage were preserved, so no retry was performed.

Human adjudication of the raw findings:
- confirmed human roots: 3
- matched: 1
- root recall: 33.3%
- matched: setup/instrument exclusion overclaim
- missed: raw-notes blank-page contradiction
- missed: formal-record committed before reviewer acceptance

The v1 packet also produced systematic false positives because it carried strong negative-space rules but omitted positive authority for:
- exact age and professional role;
- certification stakes and institutional context;
- explicitly authorized stakeholder-pressure beat;
- explicitly authorized historical-mark beat;
- explicitly authorized reviewer/filer payoff mechanics;
- explicitly authorized forward-tag cross-check activity.

Conclusion:
The age12 story-authority-packet.v1 remains frozen and valid for its qualified cohort, but it is not sufficient as a general cross-age packet.

C3.1 preparation:
- story-authority-packet.v2 adds positive character, premise and spine-event authority;
- transient scene instantiation is distinguished from durable canon;
- exact non-decisive numeric values are not serious merely because the spine used qualitative values;
- unresolved cause/recurrence/scope and branch record-state rules remain strict;
- gate prompt v3 requires exact_quote from one span;
- scorer can safely split a model-supplied combined multi-span quote without another inference;
- regression 42/42 PASS.

Next paid scope:
one GPT-5.6 Luna C3.1 typed-authority-v2 gate only.
No repair, Sol, translation or fidelity is authorized.


## Age18 C3.1 / C3.2 result — DETERMINISTIC HARD GUARDS GREEN

C3.1 run: 36616784331

C3.1 Luna v2:
- incremental cost: $0.0042653
- latency: 5.197s
- confirmed-root recall: 2/3 = 66.7%
- matched: premature formal-record commit; setup/instrument overclaim
- missed: raw-notes blank-page contradiction

Conclusion:
Luna improved materially with authority packet v2 but remains insufficient as the sole hard authority gate.

C3.2 deterministic guards:
- formal record ordering
- raw observation erasure
- unresolved setup/instrument hard overclaim
- expandable hard patterns for cause, recurrence and other-beacon scope

Evidence:
- age18 confirmed roots: 3/3 = 100% recall
- unmapped/extra findings on age18 target story: 0
- publication-ready age12 Final V3 clean-control findings: 0
- synthetic positive/negative guard tests PASS

Architecture decision:
Hard record-state and high-confidence epistemic invariants move to deterministic guards.
Luna remains only for semantic gray-area adjudication where deterministic rules cannot decide safely.

C4 prepared:
- one GPT-5.6 Sol bounded repair only
- input defects are exactly the three deterministic confirmed local findings
- unaffected prose may not be rewritten
- branch choice, five-reading series and no-advisory outcome are frozen
- post-repair deterministic guards rerun locally
- translation remains blocked unless post-repair guard count is zero

No C4 paid trigger has been created.


## Age18 C4 / C4.1 result — ENGLISH AUTHORITY CLEAN / C5 READY

C4 run: 36618878723

C4 bounded Sol repair:
- model: GPT-5.6 Sol
- exactly three confirmed local defects supplied
- model replacements: 3
- incremental cost: $0.030771
- latency: 5.710s
- repair tokens: 11,130
- initial post-repair guard result under the then-current guard set: clean
- English words after model repair: 2,174

Free human regression found two same-root residual variants that the initial deterministic patterns did not cover:
1. no documented series for the next certifier, despite raw five-reading notes already existing;
2. Offset is unlikely to be simple instrument or setup error, stronger than the approved unresolved setup/instrument ceiling.

The guard was generalized, not patched only to the exact story:
- raw-observation erasure now covers no documented series / measurements / readings variants;
- unresolved setup guard covers unlikely-to-be setup/instrument-error claims;
- uncertain wording that explicitly preserves setup/instrument as possible remains allowed.

C4.1 deterministic recovery:
- model calls: 0
- cost: $0
- exact local replacements: 2
- accepted English words: 2,176
- age18 post-recovery authority findings: 0
- publication-ready age12 clean-control findings after guard expansion: 0
- regression: GREEN

Accepted English product-path cost through C4:
- $0.15627555
- C4.1 adds zero token/model cost.

C5 prepared:
- Gemini 3.8 Flash translation only
- no fidelity call in the same workflow
- C6 Luna fidelity remains a separate paid boundary
- no C5 trigger has been created.


## Age18 C5 result — TRANSLATED / C6 READY

C5 run: 36620129124

A first workflow attempt (36619770385) failed before importing the translation runtime because of an incorrect parse_cost module path. It reached no model call and incurred zero model cost. The import was fixed and regression-tested before rerun.

Successful translation:
- model: Gemini 3.8 Flash
- English master: 2,176 words
- Turkish delivery: 1,814 words
- translation tokens: 7,391
- incremental cost: $0.01754025
- latency: 28.517s
- product-path pipeline through translation: $0.17381580 / 75,674 tokens / 411.597s

Free human translation pre-audit:
- serious candidate: title modality shift
  - EN: The Route That Might Need Closing
  - TR: Kapatılması Gereken Rota
  - concern: Turkish removes the source uncertainty and implies closure is required.
- review: recurrence unknown -> tekrarlanabilirlik bilinmiyor may collapse recurrence with independent repeatability.
- several literal/technical Turkish phrasings are stylistically awkward but not automatically serious fidelity defects.

C6 prepared:
- one GPT-5.6 Luna narrow EN->TR semantic fidelity gate only
- no repair or adjudication in the same workflow
- publication_ready only if the direct fidelity gate is clean
- trigger not created.
