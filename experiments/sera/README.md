# SERA — Scene Event Registry & Assurance

Isolated LUMI Model Lab scene-state experiment, not a production pipeline.

See [architecture](./ARCHITECTURE.md) for the authority model, invariants, acceptance gates, independent extractor and JEV strategy. The original V4.2 Mara Spine remains at its existing location and is never rewritten.

Modules:
- `spine_contracts.py`: read-only compile of Spine v2 into nine derived scene contracts.
- `state_engine.py`: typed event reducer, evidence string checks, full immutable-style snapshots, deterministic continuity checks.
- `tests/`: offline, no-cost regression suite.

Run from repository root: `python -m unittest discover -s experiments/sera/tests -v`

Phase M0/M1 only. No model calls, no JEV verification claims, no Project LUMI commits.
