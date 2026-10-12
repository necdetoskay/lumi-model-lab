# Q25 — Terminal Object-Property Candidate and Coverage Replay

Status: **EXPERIMENTAL / READ-ONLY / NOT STORYSTATE ACCEPTED**
Date: 2026-10-12
Repository: `necdetoskay/lumi-model-lab` · PR #273
Source/test commit: `2109f05b3b4d31121a940fa9bd611d608b55319c`

## Scope

`src/q25_terminal_properties.py` accepts externally annotated proposed
changes to pre-existing scalar object properties. It verifies a precise
seed/prose hash, declared original property value, identical old/new data
types, a non-no-op change, known pre-existing object and property names,
and contiguous cited story spans. It rejects structural/identity fields
masquerading as ordinary properties. No new objects, properties, topology
or canonical authority can be injected through this gate.

`src/q25_state_coverage.py` optionally combines verified *candidate
envelope* with the existing entity/story claims. It does **not** accept a
terminal value, deem prose semantically proven, modify the original seed,
certify a model extraction, or write production state.

The saved Q24 annotation in `property-proposal.json` represents a candidate
`red_bookmark.found: false → true`, citing:
`Nisa, ayracı çıkarıp avucunda tuttu.`
at Unicode string offsets `4085..4121`.
The claim is `OBSERVED_ACTION`, but the label is **annotation**, not gold
truth or a semantic validation result. The original seed keeps `found=false`.
The unrelated `returned_to_owner` stays `UNASSESSED`.

## Deterministic replay result

Full Q24 coverage report with the explicit property proposal:

| Status | Count |
| --- | ---: |
| CANDIDATE | 12 |
| PARTIAL_CANDIDATES | 1 |
| STRUCTURAL_ONLY | 23 |
| UNASSESSED | 32 |
| UNKNOWN | 2 |
| **Total flagged fields** | **70** |

All 70 remain blocking for **automatic final-state acceptance**; this is
not a count of 70 semantic contradictions. Proposed/structural fields
still require independent review. Unknown reading-book owner/location
remain explicitly unknown. World time and incomplete knowledge are not
silently inferred.

```sh
python -m src.q25_state_coverage \
  --seed evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/seed-input.json \
  --prose-record evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24/writer-2-text.json \
  --entity-proposal evidence/q25/Q25-ENTITY-CANDIDATE-20261012/proposal.json \
  --policy evidence/q25/Q25-ADMISSION-DRAFT-20261012/policy.json \
  --story-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/story-proposal.json \
  --property-proposal evidence/q25/Q25-STORY-STATE-CANDIDATES-20261012/property-proposal.json
```

## Test results and lineage

- GitHub Actions **#38233908219 GREEN**, `108 passed in 1.29s`, at commit `2109f05`.
- Run: https://github.com/necdetoskay/lumi-model-lab/actions/runs/38233908219
- Offline tests include exact CLI replay, seed/source immutability,
  type and identity invariants, duplicate/invalid citations and
  fail-closed negative test cases.

SHA256 files at tested commit:
- `src/q25_terminal_properties.py`: `755e1c9e980966d6b48ad761e3cc7c475438dc9c7c9f623816bc97d2a4476828`
- `src/q25_state_coverage.py`: `78dec220e04aa2d87d421bef929681ca35cfd82427602bade7cc46d178e40a32`
- `tests/test_q25_terminal_properties.py`: `d509dd0249a11912f2e096488bea2154e1ddd962c735aeab758c17b506124486`
- `property-proposal.json`: `33d83d0dac58b1f2c96341c0c5f1334bf104e97cba72b9c7325ad8a4a4c07022`
- `q25-offline-diagnostic.yml`: `38c5c3b3ab643254f97938cc222c4e77f906d806ce05a32c424fca896c4e1e4f`

Provider model calls: **0**; newly incurred model API cost: **$0**.
Production writes, Q24 adjudication changes, canonical state commits,
story acceptance, merge: **none**.

## Remaining critical work

The Q24 source annotations were authored offline: this is **not
automatic extraction from arbitrary prose**. Before such extraction can
feed canonical state, implement a controlled extractor contract with
explicit evidence; preserve an independent semantic adjudication gate,
terminal state completeness and knowledge/goal/obligation validation,
and explicit canonical authority integration. Neither a quote match
nor a typed proposal is a valid semantic proof. No paid/provider
authorization has been reopened.
