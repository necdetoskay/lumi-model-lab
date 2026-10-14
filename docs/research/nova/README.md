# NOVA — Narrative Observation, Validation & Abstraction

**Independent LAB research. Engineering PASS is not proof of better stories.**

NOVA Analyze, NOVA Vault, NOVA Match and NOVA Evaluate are implemented under
`experiments/nova/`. Nothing imports Story Harness, SpineForge, Writer, Q25 or
production. There is no provider client, credential lookup, network transport,
state commit, merge or deployment operation. `generate` always fails closed.

## What is reused, and what is new

This branch continues the completed [Draft PR #292](https://github.com/necdetoskay/lumi-model-lab/pull/292)
at `f4f4cdc4106c6353132731de261ec8cdf793777e`, from
`research/stargate-narrative-mechanics-v1`. That work owns the frozen corpus,
18 original proposals, eight-axis extractions, allowlisted abstract templates,
and 54 tests. NOVA uses that release without editing it or duplicating its engine.

The corpus is **314 source episodes (214 SG-1, 100 Atlantis), not 314 analyzed
mechanics**. The pilot contains **18 normalized mechanics**, **17 selectable**,
one withheld, and five additional gentle adaptation profiles within those same
records. Profiles and comparative links do not increase the mechanic count.

| Layer | Implemented behavior | Important limit |
|---|---|---|
| Analyze | Source-bound editorial records; event, rule, curiosity, conflict, decision, cost, reveal, persistent state, dramatic opening, outcome, series arc, novelty | Human source review pending; actual screen openings and series-wide continuity are not certified |
| Vault | Git-versioned JSONL, schema and release pins, normalized fingerprints, exact/near duplication, two-source comparisons, SQLite source index | JSONL is authoritative; SQLite is disposable; lexical similarity is not semantic originality |
| Match | Age profiles, declared canon/state permissions, theme, reveal ceiling, SG-1/Atlantis balance, three-position usage window and recent-family exclusion | No natural-language canon oracle; abstains when no safe diverse pair exists |
| Evaluate | Same frozen context OFF/ON, balanced concealed allocation, blind review packet, two independent reviewer records, red gates, paired statistics, costs, reproducible fixtures | Fixture prose and fixture ratings establish no narrative benefit |

All 18 records are assistant-authored hypotheses, not human-certified
high-quality mechanisms. The existing broad summary spans are explicitly labeled.
Novelty is a comparative editorial hypothesis with a second episode's evidence;
it does not prove historical originality. Unknown series-arc state is preserved
as `UNKNOWN` rather than filled with invented continuity.

## Frozen LUMI test context

`data/state.v1.json` is a **LAB fixture**, derived from the repository's
`data/specifications/generator_v2/06_age7_8_canon_constraints.yaml`; source bytes
and the derived state are hashed. It preserves Lina/Bora/Mira, their distinct
contributions, a safe permitted lighthouse setting, the four-step solution order,
and no new powers/world rules. Additional finite feature/effect permissions are
explicit LAB declarations, not production canon assertions.

This 7–8 source specification is not claimed to authorize production stories for
ages 4, 10, 25 or 40. We freeze a common experimental world and vary reader age and
brief complexity to test selection and evaluation. A real age-qualified LUMI
canon/state would require a separate reviewed snapshot and release.

The balanced matrix has 16 briefs: ages **4, 10, 25, 40** × **exploration,
friendship, mystery, crisis**. All OFF/ON pairs receive identical facts, task,
word budget, temperature and generation seed. Only abstract advice differs.
Generator requests omit source passages, franchise names, evidence, raw card IDs,
fixture continuations and audit metadata. `analyze` is a researcher-only view.

## Commands already exercised by the implementation/CI

Python 3.11+ and Git; no pip installation, credentials or paid service required.
Run from the repository root. Output directories must be new; old results are
never overwritten. These are reproduction instructions, not a request for the
user to run commands.

```bash
python -m experiments.nova.lint
python -m experiments.nova verify
python -m unittest tests.test_narrative_mechanics tests.test_nova -v
python docs/research/stargate-atlantis/validate_atlantis.py
python -m experiments.nova dry-run --output runs/tmp/nova-new-run
python -m experiments.nova index --output runs/tmp/nova-new-index.sqlite
python -m experiments.nova analyze --mechanic-id NOVA-011
python -m experiments.nova match --brief-id B04-mystery --audit-dir runs/tmp/nova-usage
python -m experiments.nova match --brief-id B04-crisis --history runs/tmp/nova-usage --audit-dir runs/tmp/nova-usage
```

Usage history comprises immutable content-addressed batches. Pass its directory
to include all batches; passing one file includes only that batch. Last use is
measured by brief ordinal, not wall-clock time. History from future ordinals,
unknown IDs, or changed files fails closed. State changes do not erase recency.

Windows sandbox tests need `TMP`/`TEMP` pointing to an allowed directory **outside
the Git checkout**, e.g. a sibling `nova-temp`. A nested temp folder makes Git
discover the parent repository and invalidates the predecessor's missing-object
test. CI uses its ordinary system temporary directory.

## Future real experiments, with no dispatch in this release

```bash
python -m experiments.nova prepare-trial --output runs/tmp/nova-trial-new --repeats 3
python -m experiments.nova import-stories --trial runs/tmp/nova-trial-new --bundle path/to/stories.json
python -m experiments.nova score-trial --trial runs/tmp/nova-trial-new --ballots path/to/ballots.json
```

Preparation creates 48 pairs / 96 requests but does not generate or bill anything.
The last two commands require real external input files; none were fabricated in
the research evidence. Model use still needs explicit budget and authorization.
The optional external importer records budget/cost attestations; it cannot grant
permission or authenticate provider billing. Manual stories must declare zero
model cost. Any `generate` invocation exits 2 with `PAID_DISPATCH_BLOCKED`.

Only `review/` is given to reviewers; `private/` contains allocation, prompts,
generator provenance and ballots. The public seed and complete research repo
would defeat blinding if given to reviewers. This is a file-level protocol, not
an OS access-control system. Reviewer independence and identity are attestations
requiring an actual independent operator; two synthetic names are not two humans.

## Data evolution

`data/vault.v1.jsonl` and five closed schemas are pinned through
`data/release.v1.json`; its SHA is pinned in `vault.py`. Source archive validation
delegates to the predecessor's immutable Git-blob manifest. Changing data plus
its local hash without changing the reviewed code pin does not pass.

`build_data.py` is an explicit editorial migration recipe, not a runtime auto-fix.
Do not regenerate hashes to hide source drift. Future releases use new versioned
paths and a reviewed pin, retain prior records, and document source corrections.
The SQLite index stores the release fingerprint and every normalized record and
source link; stale or modified indexes fail verification.

See [protocol and rubric](PROTOCOL.md), [architecture verification](ARCHITECTURE.md),
[source spot-check](SOURCE_REVIEW.md), and [validation report](VALIDATION.md).
