# Q25 P0/P4 offline diagnostic status

This branch now contains a small read-only diagnostic and selected frozen Q22/Q24 artifacts. It is not a story writer, state extractor or production acceptance engine. P0/P4 remain partially implemented; P1–P3 and P5–P6 are pending.

Run the saved case without provider credentials or artifact writes:

```sh
python -m src.q25_offline_diagnostic --input evidence/q25/Q25-P0-P4-OFFLINE-20261012/diagnostic-input.json
python -m pytest -q tests/test_q25_offline_diagnostic.py tests/test_q25_frozen_baseline.py
```

Q24 results are separate:

| Dimension | Result | Meaning |
|---|---|---|
| Narrative | UNVERIFIED | No independent human assessment or semantic quality PASS |
| Review | DISPUTED_REVIEW | Literal spans exist; draft adjudication disputes semantic support |
| State | STATE_MODEL_GAP | Terminal reading book lacks a canonical identity |
| Persistence | BLOCKED | No state commit, no automatic story rejection |

INVALID_REVIEW applies mechanically to wrong source hashes, mismatched/out-of-bounds quotes or factual allegations without a configured authority reference. A configured authority reference is necessary but is not semantic proof. Existing but irrelevant quotes require semantic adjudication. The original Codex draft findings are not promoted to human golden truth. The case contains mixed claims; unsupported-finding rates or model accuracy are not calculated.

The gap is an annotated source-bound observation, not automatic entity detection. This diagnostic neither adds a book nor resolves identity, inventory/possession or containment. No case-specific narrative rule is present in the diagnostic module. Empty findings, editorial preferences and draft-supported allegations cannot grant acceptance; all persistence is denied by this diagnostic.

Thirteen focused local tests passed, covering invalid citations, authority boundaries, no self-certified adjudication, gap handling and exact frozen-case replay. No claim is made about the old Relay suite on this different base. CI uses the existing self-hosted runner surface and no model credentials/provider preflight. Its completion must be verified separately.

Evidence lineage records exact source commits and byte hashes. These are selected archived artifacts, not a complete historical-engine replay. Q22/Q24 historical decisions, sources and closed paid scopes remain untouched. Paid provider calls and actual incremental model cost: zero.

Next engineering work is an agreed acceptance policy for narrative versus persistence, source-supported semantic adjudication and authorized new-entity/relationship representation. Independent human benchmark and the creative Intent/Memory/Outline hypothesis are still open; this commit does not qualify the story pipeline.

## Ordinary-object candidate representation

`src/q25_entity_candidates.py` now represents explicit source-bound ordinary-object proposals and terminal IN_CONTAINER, HELD_BY, OWNED_BY and LOCATED_IN relations. A relation graph distinguishes ownership from direct holding and containment; contents are derived from the same edges. Seed/source mismatches, bad spans, unknown or wrong-kind references, duplicate terminal relations, holding/containment conflicts, self-containment and cycles fail closed. New DECISIVE_CLUE proposals are outside this policy. A misleading ordinary-object role remains a semantic risk; typed validation is not a clue detector.

The saved Q24 case at `evidence/q25/Q25-ENTITY-CANDIDATE-20261012` represents the bookmark inside a candidate reading book, with the atlas contents empty and no direct hand-held bookmark. Original Nisa ownership is preserved. The book's owner is not inferred from her reading it. This input is an offline Codex annotation, not a successful automatic extraction or independently adjudicated label.

Candidate IDs are deterministic for seed/source/mention/key, with explicit local references; aliases are not automatically merged or carried across stories. The view supports individually identified objects and unit inventory counts; ambiguous quantities, new actors and new topology need another policy. It is not a full canonical state conversion or simulation of all physics. Entity admission, exact canonical identity, full state coverage and semantic evidence remain pending; no persistence grant is issued. Historical STATE_MODEL_GAP and Q24 rejection records remain unchanged.

Read-only replay:

```sh
python -m src.q25_entity_candidates --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json --proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json
```

CLI success means a candidate was represented, not that a story or final state was accepted. The expanded Q25 test suite now includes ordinary-object negatives and frozen-case/CLI replay. Earlier 13-test record remains historical; the current engineering check records the new count and source fingerprints. No paid call or production change.

## Structural admission policy and draft-state view

`src/q25_state_admission.py` adds an explicit `EXPERIMENTAL_DRAFT_ONLY` policy. New ordinary objects are disabled by default. When enabled, the verified proposal graph can be converted to `q25.draft-state.v1`, with stable proposed entity IDs, reciprocal contents, separate direct holding/ownership, and KNOWN/UNKNOWN/NONE values. Unknown owner/location may be retained or blocked by policy; they are never replaced with invented values. Existing external ownership facts, world and topology are preserved.

The saved Q24 result at `evidence/q25/Q25-ADMISSION-DRAFT-20261012` is ELIGIBLE_DRAFT for object relationships only. It has no revision or commit authority. Generic object properties such as found, character knowledge/goals and narrative obligations are not extracted by this step; their initial values must not be mistaken for verified terminal values. It is a partial view, deliberately incompatible with the old accepted StoryState schema. Semantic evidence, role classification, full state coverage and canonical authority integration remain required. This is not a repaired Q24 acceptance and does not change the prior gap/rejection records.

The current 41-test focused suite includes default-deny admission, unknown-field policies, ownership retention, seed immutability, frozen full-case replay and read-only CLI execution. Historical 13/31-test checks are not overwritten. No provider calls, paid permission changes or production writes.

## Source-bound story-state proposals (new, still non-authoritative)

`src/q25_story_evidence.py` consumes an already eligible `q25.draft-state.v1` plus
a separately annotated `q25.story-evidence-proposal.v1`. It validates the
seed/prose/draft binding, exact contiguous text spans, known actors, permitted
existing locations, known initial goal IDs, known **OPEN** narrative obligation
IDs, and known open-thread IDs. Duplicate terminal claims, invalid citations,
out-of-order multi-span evidence and silent relabeling of seed knowledge fail
closed. Newly acquired knowledge requires an explicit OBSERVED/REPORTED/BELIEF/
INFERRED epistemic label. Neither an exact quote nor an annotation gives a
semantic correctness certificate.

Accepted input here means *structurally representable candidate*, not semantic
approval. Character knowledge, emotion, health, location and established
relationship-trust changes are recorded under `proposed_character_changes`;
goal outcomes, obligations and thread outcomes have their own proposal lists.
The input seed's `characters`, world, object properties and original narrative
obligations remain unchanged, as does the original admission result.
Unannotated fields remain unknown/unverified; initial `found=false` is not
automatically promoted to a verified terminal fact. Full story-state coverage
and persistence/merge/revision authority are always false.

The Q24 example at
`evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json`
is a human/Codex *offline annotation*, **not** model-generated extraction,
independent adjudication or golden ground truth. It cites direct text for
Nisa's newly observed bookmark location and proposed emotional change,
three character goal outcomes, three possible narrative-obligation
satisfactions and three proposed thread resolutions. Narrative quality and
semantic sufficiency remain UNVERIFIED; no automatic extractor, independent
judge or canon state writer is supplied.

Read-only Q24 replay (no provider credentials or API calls):

```sh
python -m src.q25_story_evidence --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json
python -m pytest -q tests/test_q25_story_evidence.py
```

The historical 41-test local pass predates this additional module. The new
tests and updated self-hosted workflow require independent CI verification.
Q25 P0/P4 remain partial; P1–P3, P5–P6, human review and actual
automatic story-to-state semantic extraction are still pending. No paid
authorization reopening, production release, seed mutation or Q24 decision
replacement is permitted.

## Q25 source-bound story-state annotation verification (2026-10-12)

See `evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/report.md`
for SHA256 bindings, test command and measured results. The separate
`src/q25_story_evidence.py` stage now records two character change claims,
three goal outcomes, three narrative obligation outcomes and three thread
outcomes as **cited proposal records**, not accepted terminal values. The
historical 41-test record above is retained, while the most recent
cross-platform **isolated CI-host execution** passed **71/71 tests**
(commit `8c813c1`).

Safety improvement: given a claimed admitted object draft, the stage
replays `build_draft` from immutable Q24 seed/prose/entity proposal/policy
and compares the complete result; forged character, object, world, identity
map and topology values fail closed. Frozen artifacts and original seed
are unchanged. CLI and all tests are read-only in terms of canonical state.
Model provider calls/cost: zero.

This is **not a fully extracted final state**, not a semantic verdict, and
not a production persistence proposal. Q24's rejection is unchanged.
**Historical infrastructure record:** Q25 jobs were initially QUEUED
because the repository had 0 registered runners. On 2026-10-12, a
separate `q25-offline` runner was registered with a dedicated, non-root
system account. Existing IT-Manager and Marathon runner services remain
separate. The queue observation is no longer the current CI status;
see the later GitHub GREEN records below.

## Terminal object-property claims and granular coverage (2026-10-12)

`src/q25_terminal_properties.py` provides a separately versioned
`q25.terminal-property-proposal.v1` input, requiring the frozen
seed/prose digests, exact precondition, unchanged scalar type, and
literal evidence for non-no-op terminal property proposals. Structural
fields, invented objects/properties and unsupported changes fail closed.
It **does not semantically certify** even a correctly cited claim.

The saved Q24 offline annotation proposes `red_bookmark.found:
false → true` based on the observed-action excerpt where Nisa
takes the bookmark out. The seed's `false` value **remains untouched**;
other fields such as `returned_to_owner` remain `UNASSESSED`.
The optional `--property-proposal` for
`python -m src.q25_state_coverage` classifies this as a CANDIDATE.
It does not change existing read-only replay output when the optional
proposal is absent.

Actual replay at `2109f05`: 12 CANDIDATE, 1 PARTIAL_CANDIDATES,
23 STRUCTURAL_ONLY, 32 UNASSESSED, 2 UNKNOWN = 70 fields blocked
for final acceptance. A non-assessed field does not imply a
contradiction or that a value must change. Complete extraction,
semantic/role adjudication, obligation/goal and memory completeness,
real StoryState contract adaptation and production authorization
remain pending.

**GitHub Actions #38233908219 GREEN: 108/108 offline tests PASS.**
See frozen test proof and SHA256 list at
`evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/terminal-properties-report.md`.
The dedicated low-privilege `q25-offline` runner is now functional.
Provider calls and model API spend: zero. Original Q24 and frozen
seed are unchanged; no production merge/write.

## Provider-neutral extractor response boundary (2026-10-12)

`src/q25_extractor_adapter.py` now supports a deterministic
`q25.extractor-request.v1` with original seed and story, source/seed
hashes and a versioned Pydantic response JSON Schema. A model-shaped,
untrusted `q25.extractor-raw-output.v1` can be ingested offline; the
application deterministically finds exact source citations and rejects
missing/ambiguous quotes (unless uniquely disambiguated by explicit
exact surrounding context). Its output is forwarded into the prior
entity/admission, narrative evidence, object-property and coverage
gates. A separate synthetic story verifies generic names and contract
processing. **No actual model/provider is connected**; the Q24 raw
fixture is derived from existing offline annotations, not a newly
generated, human-judged extraction.

GitHub Actions **#38235452237 GREEN: 134/134 tests PASS**. Full
test/hash and scope report:
`evidence/q25/Q25-EXTRACTOR-ADAPTER-20261012/report.md`.
Canonical boundary design:
`docs/canonical/Q25_EXTRACTOR_BOUNDARY_V1.md`.

No provider call, no incremental model API spend, no semantic
certification, no final state, no production deployment and no merge.
PR remains Draft pending independent semantic extraction and
authorized backend integration. P0/P4 are partial; P1–P3/P5–P6 remain
outstanding.

## Q25 semantic-review packet and current CI evidence (2026-10-12)

`src/q25_semantic_review.py` generates a deterministic reviewer packet
from structurally validated extractor candidates, with every exact source
quotation and claim fingerprint. Saved Q24 replay produces 15 candidate
claims across 7 categories. All 70 terminal-field assessments remain blocked
for final-state admission; 15 proposals do not represent complete recall.

A typed reply binds to the exact packet hash; missing, extra, duplicate,
misbound and invalid labels fail closed. Even all `SUPPORTED` labels remain
self-reported and unverified: a JSON label does not authenticate an independent
human reviewer or prove the semantic truth of a citation. State commit stays
disabled, Q24 rejection unchanged, production untouched, no provider calls.

**GitHub Actions [#38238636392](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38238636392) GREEN: 177/177 tests PASS** (code commit `b75c767`).
Paid extractor job `skipped`; no charged dispatch was made. The documentation
commit that follows does not change code. Scope, limitations and the replay
command: `docs/canonical/Q25_SEMANTIC_REVIEW_BOUNDARY_V1.md`.


## Q25 single-call pilot artifact and default-branch launcher (2026-10-12)

The paid pilot transport now writes `semantic-review-packet.json` after a
source-bound offline-gate PASS **within the same immutable evidence archive**,
and binds its SHA256, candidate count and `AWAITING_EXTERNAL_REVIEW` status
in the ledger. This does not certify claims or permit canonical writes. A
model response failing provenance, schema or policy checks produces no review
packet. The replay fixture's 15 candidates are not human-certified gold.

**Real GitHub Actions [#38239282412](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38239282412):
178/178 offline tests PASS** at code commit `999937c5`; the paid job was
**SKIPPED**, provider calls and new API cost zero. The follow-up documentation
changes do not alter that tested code.

**Manual dispatch blocker identified:** the original Q25 experimental workflow
is only on the experiment branch, absent from repository default branch
`main`. For GitHub's standard Run workflow UI, default-branch workflow
registration is required. A small inert default-branch launcher was prepared
as **[PR #274](https://github.com/necdetoskay/lumi-model-lab/pull/274)**,
separate from Q25 Draft PR #273. PR #274 includes only
`.github/workflows/q25-manual-extractor-pilot.yml`; it has no push/PR
trigger, defaults to DENY, and has been statically checked (YAML structure,
bash syntax, owner/main/run-attempt gate, immutable Q25 SHA, q25-offline
label, cost ceiling and private evidence archive). It is ready for human
review but **NOT MERGED**. No change has been made to `main`.

After independent human review/merge of **only PR #274**, an authorized
operator can explicitly launch one Q24 extraction from GitHub Actions using
the default branch `main`, the named model and `execute_paid=true`.
The launcher runs the immutable Q25 experiment at commit `d6ad984cf30952c345de98349222beb57143f43d`,
not whatever code may later be pushed to the experiment branch.
The default-branch launcher reserves a persistent one-shot lock on the
dedicated CI runner **before** handing the secret to the paid step.
Any subsequent manual dispatch stops before provider contact. This lock
also persists after a preflight failure and must not be reset automatically.

The prior tool-environment refusal to dispatch paid work is respected; no
alternate API/agent invocation was used to circumvent it. No live paid
extractor run has occurred as part of this change. Q24 remains REJECTED,
all canonical state mutations/promotion remain forbidden, and production
LUMI is untouched.
