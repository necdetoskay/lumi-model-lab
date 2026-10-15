# Final V3 F2 — Real Luna world-outcome evidence, deterministic replay

## Original single billable Luna call

Original Actions run: https://github.com/necdetoskay/lumi-model-lab/actions/runs/38726200623
Artifact: https://github.com/necdetoskay/lumi-model-lab/actions/runs/38726200623/artifacts/11967383579

- Real model: openai/gpt-5.6-luna
- Generation ID: gen-1792063036-NcKV7agmrCPmqqOQEiWk
- Provider calls: ONE HTTP 200 POST
- Original run spend: USD 0.0030664
- Original run status: STOP — WORLD_JUDGE_INVENTED_EVIDENCE_QUOTE
- Initial world-state changes: zero; no output accepted in original run
- Original unmodified provider response SHA256: dd000b88809065e112ccf369a2b659eddffc48fd34698d7e68b3575feec5d95a

The validator failed because an exact quotation ended its italic markdown with a terminal * before the underlying original italic paragraph actually ended. All literary prose characters of the cited excerpt were byte-for-byte present in the accepted story. The judge's quotation prematurely marked the markdown closing boundary; no story event or wording was invented.

The ORIGINAL provider JSON and STOP evidence are preserved read-only under evidence/v3-f2-world-outcome-luna-38726200623/. The one-use grant is CONSUMED and must not be retried.

## Narrow generic deterministic improvement

The external quote gate accepts EXACT source prose, with one extremely narrow exception: a quote may end with an early italic closing asterisk ONLY when:

1. The quote begins and ends with a single italic asterisk and contains no other such delimiters.
2. All quote bytes except the final closing marker occur exactly once and contiguously in the source.
3. The accepted prose continues after the quoted prefix with a space in the SAME paragraph.
4. The full original paragraph contains exactly one later closing italic asterisk.
5. No content word, punctuation or story event may be inserted, deleted, shortened or rewritten.

Every quotation receives its own EXACT or ITALIC_CLOSER_BOUNDARY_ONLY provenance marker in the derived, nonauthoritative proposal. The original model JSON is never altered.

This is a parser fix, not manual authoring or approval of a persistent state mutation.

## Free replay of genuine model judgment

Replay command: python -m experiments.v3_f2_world_outcome_offline_replay --out-dir <empty-output-path>

The replay independently verifies all 43 frozen V3 files; SHA-locks the accepted source manuscripts and original model response; verifies generation ID, original single POST, prior STOP event and provider-reported cost. It then passes the byte-for-byte unchanged model JSON through the generic evidence gate and writes two read-only files.

Result from ACTUAL archived Luna decision:

- selected branch: seal_bounded_report
- 5/5 conditional persistent outcomes: MODEL_VERDICT=EARNED
- witnessed bounded field record, possible future exterior survey, Greyfen response, Leyra/Ilyan professional relationship, recorded Ilyan private field mark
- saga milestone forbidden_passage_observed suggested as earned BY MODEL, but never committed
- one italic-marker boundary exception; all other cited quotes are exact
- additional provider calls: 0
- additional spend: USD 0
- persistent operations applied: 0
- publication: false
- world-state commit authorization: false

The model's EARNED decisions do NOT prove that particular database rows must be changed. Review remains a proposal and requires a separate state-target mapping, deterministic guard, idempotent atomic transaction and rollback plan, plus explicit authorization before a commit. The report does not claim the road is reopened or safe; an authorized future survey is only POSSIBLE, not granted.

The full historical F1/F2/Writer/English QA/Turkish stages cost was USD 0.4364515, and this ONE new Luna judgment adds USD 0.0030664. Total recorded here USD 0.4395179 (other unrelated experimental activity excluded).

Frozen Final V3 sources and accepted English/Turkish manuscripts remain unchanged. No manually authored story text or model finding entered the pipeline.
