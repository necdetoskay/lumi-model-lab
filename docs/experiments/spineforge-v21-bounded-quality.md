# SpineForge v21 — Bounded Scene Quality

## Purpose

v21 preserves the proven v20 artifact, lineage, authorization, accounting, and fail-closed foundations while replacing the non-convergent Story Quality Loop.

v20 evidence showed that sentence-span patching could keep a story inside an audit/repair loop even with strong models. v21 treats that as an architecture defect, not a reason to add more repair cycles.

## Production topology

Writer -> Initial Blocking Audit -> [0 or 1 Scene Repair] -> Final Blocking Audit -> ACCEPT | REJECT_NON_CONVERGENT

Hard limits:

- initial audit: exactly one production auditor call;
- scene repair: zero or one call;
- final audit: zero or one call, required after repair;
- no second repair;
- no automatic loop;
- final audit may return only ACCEPT or REJECT_NON_CONVERGENT;
- translation and state commit are forbidden before ACCEPT.

An optional shadow auditor belongs to Model Lab evaluation only and is not part of the production cost path.

## Blocking policy

Routing is driven by material defects, not editorial perfection.

Blocking categories are physical/causal/state/spatial/temporal/knowledge/canon/spine/narrative defects at moderate or greater severity.

Language/style findings are advisory and do not independently trigger repair. Minor findings do not independently trigger repair.

## Repair unit

The repair unit is one contiguous semantic scene cluster, not individual sentence spans.

The handoff contains:

- immutable source story artifact/hash;
- blocking findings;
- non-blocking advisories;
- exact source scene cluster;
- immutable entry/exit boundary context;
- approved Spine hash;
- canon invariants.

The repair model rewrites the whole bounded scene. Text outside the cluster must remain identical.

v21 does not require the replacement scene to preserve the old sentence count. After rewrite, the new immutable story revision receives fresh deterministic segmentation with lineage back to the source cluster.

## Model substitution

The topology does not encode a permanent model choice. Writer, blocking auditor, scene repairer, translation, and fidelity are model slots.

After the topology is stable, Model Lab may replace one slot at a time against frozen inputs and compare pass rate, blocking-defect recall, repair success, latency, tokens, and actual API cost.

The initial English-pipeline optimization target is <= $0.10 per accepted story. Cost optimization must not change topology or artifact contracts.

## v20 bridge regression

The v20 bridge/rope failure is retained as a permanent regression case.

The 13 v20 findings classify as 4 blocking findings and 9 advisory findings. The blocking defects collapse into one bounded bridge-climax scene cluster rather than multiple sentence patches.

This case must never be allowed to create an unbounded repair loop again.
