# Source spot-check and unresolved quality

Checked 2026-10-14. Source archive files remain unchanged and their frozen hashes
continue to be enforced. `source_verified: true` in an old summary is not a fresh
verification or proof of the extracted mechanism.

## SG-1 S03E05 / NOVA-007: keep WITHHELD

The repository summary says that the child refuses the ceremony and starts
ending the practice for other children. The accessible
[RDA Merrin reference](https://rdanderson.com/stargate/lexicon/entries/merrin.htm)
instead describes her undergoing the ceremony; her earlier experience then
encourages teaching children afterwards. This supports retaining the existing
WITHHELD decision. The general
[episode guide](https://rdanderson.com/stargate/episodes/episodes/03-05learning.htm)
alone is not specific enough to certify the archive's final claim.

This is a documented contradiction check, not a re-verification of the whole
episode or archive. No source passages are copied into generator requests.
NOVA-012's comparison to this record is explicitly qualified, and does not use
the disputed final as corroborated evidence. A future correction must create a
new reviewed source/release rather than overwrite the frozen archive.

## Atlantis S01E05: external verification unavailable

The [GateWorld Suspicion page](https://www.gateworld.net/atlantis/s1/suspicion/)
returned HTTP 403 to the browsing tool. No successful external re-verification
is claimed. The local summary and its byte provenance are available; the
mechanic remains an assistant-proposed hypothesis with human review PENDING.

## Follow-up: narrow evidence and observed-choice distinction

The research-only `review-sources` command now audits all 18 mechanics and emits
content-addressed annotations without changing the frozen vault. Nine proposals
across NOVA-011, NOVA-015 and NOVA-018 bind exact unique UTF-8 sentence/paragraph
anchors to source and mechanic hashes. They remain `ASSISTANT_EDITORIAL`, with
human review PENDING and source quality NOT_CERTIFIED.

- NOVA-011: the summary describes a covert inspection of possessions. The safe,
  consent-based abstract experiment is a proposed adaptation, not evidence that
  the source characters used that ethical method. Attempted trust repair is not
  proof of a fully repaired persistent relationship.
- NOVA-015: the promise to stop using the resource is an explicit decision in the
  summary; return is a local outcome. Continued compliance across later episodes
  remains unverified.
- NOVA-018: the source says the team is forced to return without the resource.
  A voluntary permission negotiation is a design adaptation, not an observed
  choice. The approaching ships establish a local arc promise, not evidence that
  the promised event happened later.

The audit lists axes with spans over 800 bytes as review priorities. This is a
precision heuristic, not a semantic quality score; short spans can also fail to
support a claim. All nine proposed anchors are below that threshold. The report
is checked in under `experiments/nova/evidence/source-review-v1/`.

```bash
python -m experiments.nova review-sources --output runs/tmp/nova-source-review
```

## Remaining source work

The pilot's eight inherited axes mostly cite whole-summary spans. Opening and
comparative additions do not turn these into independently validated analyses.
Series-wide state is UNKNOWN across the current pilot until continuity evidence
is read and verified. Two independent source readers, narrow evidence spans,
counterexamples and adjudication are required by the protocol before semantic
source quality can be called PASS. No synthetic score substitutes for that work.
