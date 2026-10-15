# Story Harness P4.2 — Redacted, immutable final-audit failure diagnostics

**Status:** Experimental v21.5 **failure-only wrapper** over original frozen
v21.4; Draft PR #275, issue #286. Date: 2026-10-13.
No new paid provider calls, English Master, Q25 or canonical state mutation.

## Exact gap — preserve the old result, do not reinterpret it

The old authorized paid run `37230896244` was v21.3:
`REJECT_PROVIDER_FAILURE`, at targeted `FINAL_AUDIT`, 3 paid calls,
21,870 tokens and historical **$0.057988**. The archived reviewer notes
say the adapter discarded the returned raw payload and detailed
schema-validation message. The exact invalid field cannot be recovered
from its stored result; no one should infer `ACCEPT` from
`final_blocking_count=0` when schema parsing failed.

The pinned v21.4 adapter, unlike old v21.3, already has a
`response_evidence()` path. It can attach raw parsed responses, provider
message `choices`, and full wire request content into an exception.
**Blindly persisting this as-is risks storing story/prompt text, malicious
provider content or credentials.** We do not modify its frozen code.

## New experimental boundary

`src/story_harness_p42_diagnostics.py` is an independently versioned
**v21.5 experimental diagnostic quarantine** wrapping the final-audit
callback of the authentic frozen v21.4 runtime. The wrapper operates on
actual returned adapter errors but never dispatches to a real provider.

For each failed targeted final audit it captures, **before propagating
failure**, a uniquely named `0600` immutable JSON record created with
atomic `O_EXCL`, flushed and fsynced. The record includes:

| Retained safely | Intentionally absent |
| --- | --- |
| Original parsed-response SHA-256 (when available), known field types/lengths, count of unexpected fields | Raw model prose, untrusted field contents and freeform error text |
| Original provider response SHA and wire/request SHA, if available | Raw `choices[].message.content`, HTTP headers, access tokens and full prompts |
| Known validation category and safe JSON path such as `$.findings[0].family` | Unsanitized exception strings and traces |
| Provider usage: reported tokens, cost and latency when valid | Fabricated cost `$0` when accounting is missing or nonfinite |
| Frozen same-story repaired text hash and final audit request hash | Story text, credentials, production canonical state |

The reduced exception is forwarded back to the actual v21 runtime
with the same usage when valid; otherwise its usage is marked incomplete,
with partial values in the immutable diagnostic record. The runtime
remains `REJECT_PROVIDER_FAILURE`, never `ACCEPT`, with no retry,
second scene repair, translation, Q25 or StoryState commit.

**Cryptographic SHA ≠ recoverable raw data.** This is a redacted structural
record, not a reconstruction of the lost paid v21.3 response. The full
unredacted provider answer is deliberately **not** stored. If later
authorized forensic work needs raw content, its storage would require a
separate explicitly reviewed encrypted and access-controlled channel.

## Actually executed frozen runtime — seven offline scenarios

Source `2eb3d825b5baf8f0f16ccb23805f619d433c7236` (original pinned
v21.4 runtime) is checked via the P4.1→P4.0→P3.2 chain first. P4.2
uses that genuine `execute_paid_quality_once(simulation=True)` engine,
the real model adapter, and a fake final-audit transport. The production
adapter and frozen source hashes stay unchanged.

| Scenario | Quarantined failure | Usage |
| --- | --- | --- |
| Additional untrusted JSON field | `UNEXPECTED_FIELD` | Recorded |
| Missing required `summary` | `MISSING_FIELD` | Recorded |
| Wrong type for `findings` | `INVALID_TYPE` | Recorded |
| Transport cannot parse JSON | `structured_parse` | Recorded if reported |
| Provider exception after returning usage | `transport` | Recorded |
| Missing provider cost | `INVALID_USAGE` | Incomplete; never zeroed |
| Nonfinite provider cost | `INVALID_USAGE` | Incomplete; never zeroed |

Each scenario attempts exactly 3 simulated calls (initial audit, one
scene repair, targeted final audit). The final callback fails. Actual
v21 runtime quality status is `REJECT_PROVIDER_FAILURE`; no second
repair, automatic retry or full-story final audit. Seven atomic
diagnostic artifacts are created in isolated temporary directories,
checked for forbidden injected secrets and tested against overwrite.
Only a stable **redacted summary receipt** is committed to evidence,
not raw provider content or any temporary mock artifact.

## Scope and next requirement

- P4.2 proves that the **experimental wrapper** persists safe failure
  diagnostics with original runtime adapters. It is **not wired to
  production or the frozen paid workflow**.
- It does **not** retrospectively restore the old v21.3 malformed
  response, fix semantic defects in the root-bridge scene, or establish
  a genuine accepted English Master. Current story admission remains
  closed: `REAL_QUALITY_NOT_ACCEPTED_DIAGNOSTIC_READY`.
- If a real future experiment is authorized, use a separately frozen
  and tested v21.5+ runner/wire profile that invokes this quarantine
  on actual provider callbacks, with a private evidence artifact sink,
  verified redaction and reviewed retention/access controls.
- No automatic paid attempt. Any new bounded 1× real experiment needs
  explicit user authorization, verified current provider pricing,
  request-time spending exposure, stage budgets and a new paid marker.
  A post-usage ceiling is **not** a guaranteed provider hard cap.

## Offline reproduction

```sh
git worktree add --detach /tmp/lumi-p42-pinned 2eb3d825b5baf8f0f16ccb23805f619d433c7236
python -m pip install 'pydantic>=2.8,<3' 'PyYAML>=6,<7' \
  'requests>=2.31,<3' 'python-dotenv>=1.0,<2' \
  'rich>=13,<15' 'httpx>=0.27,<1'
export STORY_HARNESS_PINNED_P42_ROOT=/tmp/lumi-p42-pinned
python -m unittest discover -s tests -p 'test_story_harness_p42.py' -v
python -m src.story_harness_p42 --repo-root . \
  --pinned-source-root "$STORY_HARNESS_PINNED_P42_ROOT" \
  --verify-report evidence/story_harness_p42/pinned-targeted-audit-diagnostics.json
```

The offline suite also rejects a forged accepted story, a fourth call,
stage substitution, mismatched same-story text hash, a fabricated zero
cost, changed or deleted diagnostic cases, symlink output, duplicate
receipt write, and untrusted prompt-injection/secret strings. Full
Story Harness tests and CI must remain GREEN.

