# Aion 3.5 Mini F2 Writer — single paid call contract

Case: age18.forbidden-cartographer.fantasy.frozen-01
F2 Spine: Sonnet 5.5 -> Luna ACCEPT, Actions run 38700326961, 53/55.
Human scope: user replied 'devam et' to explicit question approving the F2 plan and one Aion 3.5 Mini Writer call, $0.10 planning ceiling.
Approved source: age18_forbidden_cartographer_f2_approved_for_aion_20261015.json, SHA256 21f1e4e0c9f25cd1c970cccc2df8d09a0f236c9102321df7da086f85a3dac1a0.
Underlying F2 unchanged archived source SHA256 d54a747ace23f15ea3af5ef37d25e40b1e48d24ba905083e2f1c32e7b49473af.

The canonical 43 frozen Final V3 files, generation logic and v3 generic Writer prompt are NOT modified. Existing tested Aion one-attempt guard is reused. Exactly one provider POST. HTTP 429, HTTP 5xx, timeouts, malformed body, missing cost/ID, second call and over-ceiling observed cost fail closed; no Writer alternate, no retry, no automatic repair, judgement, Turkish translation, or world-state changes.

One-use local claim occurs before any model POST; live Actions must separately verify a GitHub-global claim tied to run ID, attempt 1, triggering commit, grant ID, and approved pinned guard SHA, using read-only GitHub token. Provider secret injected ONLY into paid step, never exposed to logs. Evidence uploaded even on failure.

The USD 0.10 figure is an **authorization planning ceiling**, checked against provider-reported costs AFTER the call; it is NOT a provider-side pre-spend hard billing limit. A request could cost more. No paid call is inferred successful from offline-only tests.

F2 human approval is stored in an independent approved-input file; frozen source F2 candidate remains unapproved and unchanged. Writer is only an English first draft and publication authority remains false.
