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
