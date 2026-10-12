# State fidelity: bound observation audit v1

Q22's S6 prose places the bookmark in the preparation notebook while the
recorded object container is null. Its historical ACCEPT and all original
captures remain unchanged. This is a material gap in prose/state fidelity,
not a failure to replay the declared transitions.

`src/spineforge_state_fidelity.py` adds an offline, non-mutating audit of
reviewer-supplied final-state observations. Each review binds the exact prose
hash and recorded state hash. Each observation supplies an existing code-owned
contiguous source range, an RFC 6901 state pointer, and the observed JSON value.
The audit copies the quotation from original source bytes and compares JSON
values without equating booleans and numbers. Missing fields differ from null.
Stale hashes, unknown ranges, duplicate paths, malformed escapes and invalid
list indices reject. Findings preserve recorded and observed values.

The Q22 regression uses its archived manual editorial observation. It does not
fabricate a provider response or claim automatic semantic extraction. A cited
range establishes provenance, not whether the interpretation is correct.
`NO_OBSERVED_DIVERGENCE` is intentionally not semantic PASS; even an empty
review never claims completeness. No state mutation or retrospective repair
is performed. No live engine, source fingerprint, prompt, admission policy,
paid authorization or historical replay is changed.

This is the first independently testable audit boundary, not a completed
runtime fix. Next integration must version the scene guard and runner, obtain
observations for all persistent prose effects, check them against the projected
exit state before freeze, and route divergences through the existing single
rewrite budget. Historical replayers must remain frozen. Adversarial semantic
controls must include unreported effects, temporary versus final containment,
negation, quoted/hypothetical actions and container/inventory consistency.
Simply comparing supplied observations cannot prove none were omitted.

Validation: 11 dedicated zero-provider-call tests pass, including the immutable
Q22 counterexample, stale bindings, bad citations, duplicate observations,
missing/null and boolean/number distinctions. Existing Q22 source CI is now
confirmed successful (37943871922); that is not CI evidence for this new commit.
No new paid run, production change or merge is authorized or performed.
