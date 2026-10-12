# Request-to-design admission v1

## Scope

Q12 proves the downstream six-scene frozen-input pipeline. This increment prepares the upstream boundary: explicit StoryRequestV1, request-bound StoryDesignV1, nested Relay fixture schema, deterministic compilation and immutable success/rejection records. It does not run request extraction or a paid planner. The mosaic adapter example deliberately reuses the historical Q12 plan as a test input; it is not fresh model-designed evidence or a golden label.

StoryRequest preserves the original user prompt, exact source quotations for mandatory requirements, language, reader age, tone, genre, scene count, visible assumptions and exclusions. Supported structural scope is 2–12 scenes through Relay v5. Unsupported/ambiguous planning stays unresolved; no claim of universal story support.

## Local flow

Run `python -m src.spineforge_story_design --request REQUEST.json --proposal PROPOSAL.json --output FRESH_DIRECTORY` from the repository root. The output directory must not exist. Raw intake/proposal bytes are saved before validation, including rejected proposals. Every run saves validation and a SHA-256 inventory. Successful admission also saves model-neutral planner input (request hash, prompt, output/nested fixture schemas and source fingerprints) and candidate-fixture.json.

The proposal is untrusted. Admission checks the request hash, exact requirement quotes, scene count/language/age/tone, exclusion propagation, complete unique references to existing event predicates, typed event/coverage/spatial rows, contiguous route, entry/exit state and topology/access/joint-carry compilation. Projected terminal state must resolve initial threads and preserve/satisfy initial narrative obligations. No accepted scenes, state advancement, grant registration or provider calls occur.

STRUCTURAL_PASS always retains REQUIRES_REVIEW. A request-to-predicate reference is not proof of semantic entailment. Genre, causal plausibility, mandatory content completeness, canon interpretation and literary quality need independent review. Numeric/structural checks do not certify age suitability or language in future prose. Candidate fixtures can only become live inputs through the separately approved shared paid admission.

## Next integration

Add versioned request-extraction and planner transports using the same shared reservation and complete request/response/usage recording. Freeze all upstream dependencies together with downstream contracts, record semantic design review and preserve rejection outcomes. Qualify genuinely new requests across several genres before presenting request-to-story generation as live-proven. Haiku/Sonnet comparison and golden datasets remain a separate evaluation package; no old budget is reused.

## Validation

Sixteen new zero-cost tests cover accepted adaptation, record exclusivity and raw preservation, stale hashes, uncovered/unknown/duplicate references, preference drift, unresolved questions, missing exclusions, unresolved terminal threads, stale state, invented request quotations, schema delivery and fixture substitution. Historical Q5S/Q11/Q12 evidence and frozen runtime modules remain unchanged. No production or merge.

Full Relay validation: 387 tests PASS in 166.29 seconds. Recorded accepted/rejected controls and their inventories pass. Initial focused test exposed silent unresolved-thread erasure; the correction and subsequent verification are recorded in SFR-DESIGN-V1-DEVELOPMENT-20261008/work-log.json. No provider calls / USD 0.
