# Semantic locator reference audit — 2026-09-25

Status: EXPERIMENTAL. No production promotion.

## Provenance

- Branch baseline before this audit: `e5ab3ba8b1bfeda35d7deb7867843987d035ff62`.
- Run `36170006031`: TP 6, FP 9, FN 8, P .40, R .4286. The model step passed, but its result.json was lost when the evidence push returned 403. There is no artifact and no evidence ref. Individual predictions from this run cannot be reconstructed.
- Unchanged-locator replay `36171164835` at `591fbb68`: TP 9, FP 10, FN 5, P .4737, R .6429. Full predictions are at `evidence/story-defect-locator-36171164835/experiments/results/story-defect-locator/36171164835/result.json`.
- Unchanged-locator evidence run `36171426626` at `ff4cb0e0`: TP 9, FP 6, FN 5, P .60, R .6429, F1 .6207; USD .0015055 across five calls, 20.894 s aggregate model latency. The prompt hash was `98df4368c53b9c62b9392568c694f4feb1492783461ebfef8a2ce7ecad8784dc`.
- These independent calls vary despite fixed stories/seeds. Do not attribute a score change to a prompt edit unless the prompt hash changed and repeated runs support it.

## Replay 36171164835: all ten unmatched predictions

| Case | Predicted quote (shortened) | Review | Reason |
| --- | --- | --- | --- |
| 36165831429 | “Arabalar kendi kendine mutfağa gitmez ki” | gold omission | Adult corrects imaginative play; parallel gold in case 36168417326. |
| 36165831429 | “tekerlekleri havaya dönük” | locator error | Natural comprehensible Turkish in this context. |
| 36166393877 | “sanki araba havada uçarak gitmişti” | locator error | Observable gesture rendered as a concrete simile, not mind reading. |
| 36166393877 | “bir ayı düştü, bir ayı düştü” | gold omission | Exact adjacent mechanical duplication. |
| 36166393877 | “çok emin” | ambiguous | Redundant interpretation, but dialogue conveys certainty; severity and repair value are debatable. |
| 36166723303 | “Deniz, orada araba yok ki...” | ambiguous | Adult prematurely corrects search, but one practical utterance need not be teacher/examiner behavior. |
| 36166723303 | “Annesi bunu sorgulamadı...” as caregiver_teacher | taxonomy mismatch | This is narrator interpretation; gold labels narrator_mindread. |
| 36168417326 | “O çok eski bir kraker Deniz, dokunma.” | locator error | Ordinary caregiver safety response, not teaching/examining. |
| 36169049278 | “sanki oradan çıkacakmış gibi” | ambiguous | Narrator supposition may be expendable, but does not assert a mental state. |
| 36169049278 | “Deniz elini tekrar soktu... misket... çorap” | locator error | Sequential retrieval is spatially possible; routine motions need no explicit hand reset. |

## Replay 36171164835: all five unmatched gold findings

| Case | Gold quote (shortened) | Review | Reason |
| --- | --- | --- | --- |
| 36165831429 | “koklamadı ama yüzünü buruşturdu” | locator error | Defensive negation adds no scene information. |
| 36165831429 | “yarı şaka” | locator error | Narrator assigns a tone that dialogue can carry. |
| 36166723303 | “Mutfakta dolabın altına yattı” | locator error, with geometry caveat | A standard kitchen base cabinet has no body-sized gap; the text also says he comes out from under it. The fixture does not explicitly define the furniture. |
| 36166723303 | “tozdan bir tavşan” | locator error | Calque-like image, locally unnatural. |
| 36166723303 | “Annesi bunu sorgulamadı...” | taxonomy mismatch | Same source span was predicted under caregiver_teacher. |

## Reference and metric limitations

The five fixtures all repeat one lost-car story family. Gold is a selected editorial defect list, not exhaustive annotation of every category. Its entries have no severity, so SERIOUS/BLOCKER recall is **undefined**. Two caregiver gold entries (“Öyleyse yol nerede?” and “Bulaşık makinesinde mi kaldı yoksa?”) merit independent adjudication because playful participation can be mistaken for examination. Do not silently delete them to improve a score.

The original matcher required one normalized quote to contain the other. In run 36171426626, “Yani hiç düşünmedi aslında...” overlaps the gold “Deniz düşündü. Yani hiç düşünmedi aslında” but neither contains the other: one FP and one FN are matching artifacts. The span-overlap fix is isolated in `26e4a635`; it does not change the locator prompt. On the exact stored predictions of 36171426626, this changes TP/FP/FN from 9/6/5 to **10/5/4** (P .6667, R .7143, F1 .6897). This is a measurement correction, not model improvement.

## Decision

Keep locator experimental and outside the production quality gate. Curate a versioned, independently reviewed reference with severity and multiple story families, retain this v0.1 corpus for comparison, and rerun the unchanged prompt to estimate variance. Promote only when precision, recall, severe recall and known negatives all pass on a wider held-out corpus.

## Controlled iterations and decision log

| Hypothesis | Change | Test evidence | Decision |
| --- | --- | --- | --- |
| Preserve complete provenance and make score inspectable. | `ff4cb0e0` added unmatched spans, per-kind precision, F1, cost, latency, prompt/profile hash and SHA. Missing cost or parse failures now fail closed. | Run `36171426626` succeeded and archived complete result. | Retain instrumentation. |
| Quote boundaries can shift while referring to one source defect. | `26e4a635` compared overlapping story spans. | Run `36171636192` failed because one gold quote starts with lowercase “gözleri” while source uses uppercase “Gözleri”. | Corrected in `b4a55c15`; keep fail-closed validation. |
| A case-insensitive source-span matcher prevents one FP/FN pair without changing the model. | `b4a55c15` repaired gold validation and span matching. | Run `36171814440`: 6/13/8, P .3158, R .4286, F1 .3636; USD .0015811, 17.23 s. Prompt hash unchanged. Other outputs drifted sharply, so no before/after model claim follows. | Retain matcher; report variance. |
| Clarifying category boundaries may remove speculative physical and caregiver FP. | `e97d9e12` changed only the locator prompt. | Run `36171905286`: 8/9/6, P .4706, R .5714, F1 .5161; USD .003771, 20.132 s. Physical/translationese/defensive-negation recall all remain zero; targets fail. | Rejected and reverted in `10250773`. |

The baseline prompt yielded substantially different results on the same five stories: `36171164835` 9/10/5, `36171426626` 9/6/5 under the old matcher, and `36171814440` 6/13/8 under the corrected matcher. The stored `36171426626` predictions recalculate to 10/5/4 with the corrected matcher. This variance, incomplete reference, and single story family preclude a credible production qualification. The rollback run provides another unchanged-prompt observation; its result belongs in a later evidence update.
