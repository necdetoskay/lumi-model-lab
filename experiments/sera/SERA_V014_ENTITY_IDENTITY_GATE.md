# SERA v0.14 — Source-bound entity identity resolution proposals

**Date:** 2026-10-16  
**Branch:** `experiment/sera-scene-state-v0-1-20261015`  
**Epic:** [#306](https://github.com/necdetoskay/lumi-model-lab/issues/306)  
**Source:** Frozen Mara S1, SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`

## Purpose

v0.13 enumerated 60 model-suggested mentions, 22 distinct references and
16 unregistered/provisional references in the actual paid seven-batch
Mara extraction. It also enumerated 25 source-bound event candidates,
9 of which refer to unregistered/provisional identities.

Directly converting these names into `WorldState` objects would be
unsafe. A word or pronoun being `PRESENT` in the model response does
not establish identity, physical presence, object independence or
ownership. Some references are **parts**, **reported subjects**,
**negated observations**, **locations**, **document components**, or
**abstract source collections**.

## Implementation

- `identity_resolution_v014.py` — reusable, pure
  **source-bound candidate classification contract**. Requires exact
  coverage of all unregistered refs, all exact mention spans and
  model role counts. Rule hypotheses must be anchored inside the
  same numbered source sentence as a real model mention.
- `mara_s1_identity_rules_v014.py` — **Mara-specific hypotheses**,
  not generic hardcoded story ontology and not human gold.
  Every input reference has a **provisional** classification,
  optional possible parent/alias and a requested independent review action.
- `mara_s1_identity_review_v014.py` — joins the complete
  entity-mention census and 25-event blocker census.
  If an event refers to an unregistered name, that name must have
  a source-bound mention in the **same sentence**.
- `mara_s1_identity_review_cli_v014.py` — reconstructs a new report
  from the two original GitHub Actions evidence artifacts,
  with no new model calls.
- `.github/workflows/sera-mara-v014-identity-review.yml` — CI
  validates offline policy tests, retrieves **original provider-derived**
  census artifacts, and archives a full deterministic identity report.

No automatic creation, alias merge, part attachment, physical-truth
promotion, World State commit or database operation is allowed.

## Actual Mara S1 result

[Real archived-evidence run 38870235664](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38870235664)
**PASS**. **351/351 Python unit tests PASS** in the same run.

| Candidate interpretation | References | Count |
| --- | --- | ---: |
| Independent physical object candidates | `new:bench`, `new:pencil` | 2 |
| Watch components, not stand-alone inventory items | `new:watch_case`, `new:watch_hands` | 2 |
| Character anatomical part | `new:vane_thumb` → potentially part of `vane` | 1 |
| Archive/clock document components or references | `new:strike_record`, `new:entry_train_41`, `new:platform_record` | 3 |
| Negated evidence, not existing objects | `new:mark`, `new:strike_mark` | 2 |
| Unverified topics in reported testimony | `new:train`, `new:train_41` | 2 |
| Station region alias / station sublocation | `new:north_quay_station`, `new:platform` | 2 |
| Abstract source collections | `new:archive`, `new:sources` | 2 |
| **All nonregistered references reviewed as hypotheses** | | **16** |

**Important distinctions:**

- `new:watch_hands` means the two hands of the **pocket watch**,
  not human hands. It is a potential part of registered
  `vane_watch`.
- `new:vane_thumb` is a possible anatomical part of Vane;
  it must not be turned into an independent inventory item.
- `new:watch_case` is a possible component of `vane_watch`,
  not automatically a separately owned watch-case object.
- `new:mark` occurs in the explicit absence claim
  `There was no mark`. `new:strike_mark` occurs in
  `no corresponding strike`. **Neither is positive evidence that
  a mark or strike exists**.
- `new:train` and `new:train_41` are reported subjects, not
  objectively established physical train arrivals.
- `new:bench` and `new:pencil` are physical-object **candidates**
  with direct source mentions. Their identity, place/holder and world
  introduction still require a separate authorization protocol.
- `new:platform_record` may alias `new:strike_record`, but the
  rule is a *possible alias*, never an automatic merge.
- `new:north_quay_station` maps potentially to an already existing
  **region name**, not another independently created object.

Every proposed relation remains `REVIEW_REQUIRED_NOT_CANONICAL`.
Counts: 60 original mentions, 25 event candidates, 16 identity hypotheses,
**9 event candidates** with unresolved entity refs. Registered base
entities remain unchanged. **0 new entities, 0 approved relationship
links, 0 authorized event commits, 0 new model calls.**

## Next gates

1. Generalize the Mara fixture's source-context classification into
   a **blind model-assisted identity reviewer** with finite validated
   types, cross-source evidence, optional abstention and safe
   programmatic repair. The generic deterministic rule engine must
   remain the gate; model proposals cannot create objects.
2. Resolve part/region/document aliases and independent physical
   introductions with separately validated identity + ownership +
   location evidence.
3. Audit the remaining semantic event issues (especially
   `held the telegram` labeled `MOVE`, `pencil move` labeled
   `MOVE`, and reported claims), then qualify causal and
   temporal feasibility before production state commits.
4. Implement authenticated adjudication/approval, transactional
   WorldStore+EventGraph staging and rollback prior to *any*
   production migration or `HOLD` release.

**Mara S1 remains HOLD.** No generated model output-token ceiling.
