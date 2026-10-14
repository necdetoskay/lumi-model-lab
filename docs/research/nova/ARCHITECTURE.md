# Verified repository state and independence

Verified on 2026-10-14 (Europe/Istanbul):

| Ref / artifact | Verified identity / disposition |
|---|---|
| `main` | `f582f3e8471882df9e012059a44cea7f92afa1c8`, read-only comparison |
| `research/stargate-narrative-mechanics-v1` | `f4f4cdc4106c6353132731de261ec8cdf793777e` |
| Predecessor Draft PR | [#292](https://github.com/necdetoskay/lumi-model-lab/pull/292), OPEN/Draft, base `research/stargate-atlantis-episode-archive` |
| Frozen source corpus commit | `9ae2874cabe582f9e626fc77f36cd208ad234600` |
| NOVA working branch | `codex/nova-independent-pilot`, separate clone and commit history above predecessor |
| NML release | `13ea240897d88ba2bc4264fd75e514639402462b43a42ff697b4da4f0546940a` |

The previous Work chat was still active when this task began. Its status and
working tree were inspected read-only; its code was not edited, messaged or
re-created. NOVA waited for the committed predecessor and fast-forwarded its own
separate branch to that commit. The prior source summaries, extraction files,
templates, code and tests remain byte-identical to that base.

## Architectural contract

The research branch's `STORY_PRODUCTION_QUALIFICATION_ARCHITECTURE_V1.md` assigns
canon/state, semantic judging and immutable evidence distinct responsibilities.
Its model/runtime configuration is historical context, not authority to dispatch
a current model. We inspected its boundaries and the predecessor's
`docs/research/narrative-mechanics/CONTRACT_REVIEW.md` / pinned provenance.
The latter records its read-only comparison with the separate Q25/SpineForge
branch. NOVA does not import or revive those experiments.

Only these new paths belong to this change:

- `experiments/nova/`: standalone Python, data, schemas, fixture evidence.
- `tests/test_nova.py`: adversarial and integration tests.
- `docs/research/nova/`: protocol, evidence and limitations.
- `.github/workflows/nova-offline.yml`: self-hosted offline CI with read-only contents permission.

No changes to `src/`, canonical documents, existing prompts, existing workflows,
source summaries, production data or the original mechanics module. No package
installation and no secrets in NOVA CI. Runtime imports only standard library
and the prior independent `experiments.narrative_mechanics` module. An AST import
allowlist checks that boundary; it is not a substitute for OS isolation or a
general malicious-code analyzer.

NOVA stores a separate LAB state fixture and possible narrative proposals.
There is no authoritative StoryState write or adapter into any production system.
SQLite here is a local research index, not LUMI's production database.

## Audit boundary

Raw corpus → pinned NML release → versioned NOVA JSONL → validated finite selection
→ abstract advice only → independent experimental requests → blind review packet.

Audit/source analysis remains private to the researcher. Generator requests are
an allowlisted projection; they do not contain the raw state metadata, source
names, corpus paths, fixture continuation examples, hash fields or mechanics IDs.
Reviewers see only the review directory and frozen evaluation context. Giving
the full repository or allocation seed to reviewers invalidates this blinding
protocol. No claim of automatic semantic anonymization or perfect blinding.

Draft PR targets the research branch; no main/prod merge, auto-merge, queue entry
or deploy is requested. A future successful pilot still cannot trigger integration.
