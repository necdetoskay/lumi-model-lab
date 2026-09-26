# LUMI StoryForge Agent Contract v1

Status: **RELEASE-CANDIDATE CALLABLE PACKAGE PASS / MODEL LAB ONLY**  
Profile: `LSF-A4-W500-v1.0-rc1`  
Date: 2026-09-26

## 1. Purpose

StoryForge is the governed story-production agent boundary for LUMI.

It is not a single model.

It is a validated protocol that converts an immutable LUMI story context into:
- a validated story plan;
- an accepted English master story;
- a Turkish delivery story;
- provenance / cost / latency evidence;
- a **proposed** StoryOutcome.

StoryForge has no authority to mutate LUMI Canon, World, CharacterStoryState, inventory, relationship state, knowledge state, or saga state directly.

## 2. Agent boundary

Conceptual LUMI input:

```
CanonSnapshot
+ CharacterStoryStateSnapshot
+ StoryIntent
+ GenerationProfile
```

Current callable Model Lab RC1 input:

```
NormalizedFactProjection
  - always_required
  - candidate_facts
  - forbidden_facts
+ StoryIntent
+ GenerationProfile
```

The callable RC1 does **not** yet own raw Project_LUMI Canon/State projection. That adapter remains a separate integration boundary so the agent does not silently gain unqualified database-selection authority.

Output:

```
StoryArtifact
+ ProposedStoryOutcome
+ Evidence
```

No direct commit occurs inside the agent.

## 3. Qualified flow

```
Canon + State + StoryIntent
        ↓
Deterministic Candidate Extraction
        ↓
Deterministic Always-Required / Direct-Ref / Guard Policy
        ↓
JEV Soft Context Enrichment
        ↓
Minimal Story Context Packet
        ↓
Aion 3.5 Mini Spine Planner
        ↓
Deterministic Spine Schema Validation
        ↓
Sonnet Semantic Spine Validation
        ↓
Aion 3.5 Mini Writer
        ↓
Semantic QA
        ↓
Bounded Local Repair when required
        ↓
Accepted English Master
        ↓
Gemini 3.8 Flash EN→TR
        ↓
Luna Narrow Translation Fidelity
        ↓
Turkish StoryArtifact
+ ProposedStoryOutcome
```

## 4. Context authority

### Deterministic authority

The following may not be delegated to JEV:
- active character / exact age;
- active world;
- current location;
- StoryIntent direct fact references;
- exact inventory membership;
- hard knowledge boundaries;
- cross-world isolation;
- privacy/internal metadata exclusion;
- revision/state identity.

### JEV authority

JEV is a semantic relevance signal for **soft enrichment only**.

Current bounded profile:
- model: `typesafe/jev-1.13`;
- probability >= 0.45 → auto enrichment;
- 0.30–0.45 → REVIEW only;
- <0.30 → omit;
- REVIEW is not sent to planner by default.

JEV does not own final context authority.

## 5. Planner authority

Current planner:
`aion-labs/aion-3.5-mini`

The planner receives no prewritten solution and no prewritten spine.

It must produce:
- concise premise;
- exactly 8 ordered beats;
- beat density;
- explicit source fact references;
- minimal transient assumptions;
- proposed StoryOutcome;
- preserved invariants.

The plan remains non-canonical until external LUMI commit logic decides otherwise.

## 6. Creativity boundary

StoryForge intentionally permits **transient creative detail**.

Allowed examples:
- “vınnn”, “tak tak”, “hımm”;
- short child dialogue;
- gestures;
- temporary chalk drawings;
- harmless momentary sensory details;
- playful comparisons.

These details are important for childlike prose and must not be eliminated merely because they are absent from Canon.

StoryForge forbids unsupported **durable** facts.

Examples:
- new permanent object color/size/features;
- new owned inventory;
- new family relationships;
- invented relationship history;
- new world facts;
- knowledge the character does not possess.

This distinction is a core StoryForge rule:

```
Transient creative detail → writer freedom
Durable canon/state attribute → context/contract authority required
```

## 7. QA and repair

Defect protocol:

```
Story
→ locate defect
→ exact span
→ LOCAL / STRUCTURAL / REPLAN
→ minimal repair
→ same-defect recheck
→ whole-story regression
→ PASS / FAIL
```

A local defect must not trigger a full rewrite when a bounded local repair is sufficient.

A clean story must not be rewritten for optional polish.

## 8. Translation

Translation starts only after the English master passes.

Translator:
`google/gemini-3.8-flash`

Translation is semantic-preserving localization, not story rewriting.

Fidelity gate:
`openai/gpt-5.6-luna`

Luna is qualified here only for narrow EN↔TR fidelity. It is not promoted as the general story-quality judge.

## 9. Planner qualification evidence

### Problem-solving

Run `36265511557`
- planner PASS;
- deterministic plan errors: 0;
- semantic plan defects: 0;
- writer produced 498-word story;
- one unsupported durable wheel attribute was detected.

Run `36265828541`
- one exact-sentence local repair;
- re-audit Sonnet: 0;
- re-audit Sol: 0;
- translation fidelity: 0 findings;
- publication-ready PASS.

### Exploration / mystery + knowledge boundary

Run `36266444475`
- planner PASS;
- GARDEN_GATE remained RUMORED;
- Deniz did not open/cross the gate;
- mystery resolved entirely on the courtyard side;
- 527 English words;
- Sonnet: 0;
- Sol: 0;
- repair: none;
- fidelity: 0;
- publication-ready PASS.

### Friendship / social relationship state

Run `36267204822`
- planner PASS;
- no invented feud/betrayal/rivalry/family tie;
- no adult mediation;
- social solution generated by planner, not supplied by fixture;
- 504 English words;
- Sonnet: 0;
- Sol: 0;
- repair: none;
- fidelity: 0;
- publication-ready PASS.

## 10. Promotion state

The profile is promoted to:

`LSF-A4-W500-v1.0-rc1`

This means:
- the components and role split are frozen enough to package;
- age-4 / ~500-word scope has meaningful multi-family evidence;
- the context→planner→writer chain has passed three materially different planner cases.

It does **not** mean Project_LUMI production integration is authorized.

Callable-package gates are now satisfied:

- entrypoint: `src.storyforge.run_storyforge`
- request schema: `storyforge-request.v1`
- result schema: `storyforge-result.v1`
- contracts blob: `9b3476825423dee3d4930852d205c58cd8a54188`
- runtime blob: `4c0ecf10289bba0627901028c167d81990221ea4`
- callable RC smoke: run `36267804926`
- smoke result: `publication_ready=true`

The callable smoke exercised, through one runtime entrypoint:

```
normalized facts
→ deterministic/JEV context builder
→ Aion Mini planner
→ plan validation
→ Aion Mini writer
→ Sonnet + Sol story audit
→ Gemini translation
→ Luna fidelity
```

Smoke evidence:
- JEV selected blue/yellow chalk as soft enrichment;
- plan validation PASS;
- final English story 489 words;
- no repair required;
- both story audits clean;
- fidelity clean;
- total measured run cost ~$0.05728;
- elapsed ~110.4 s.

Before Project_LUMI production promotion:
1. implement the Project_LUMI → `storyforge-request.v1` adapter;
2. prove that adapter preserves G2 Canon/State/knowledge/world isolation;
3. create a separate Project_LUMI AEGIS L3 integration change;
4. keep final StoryOutcome commit authority outside StoryForge.

## 11. Next implementation step

Do not add another Model Lab story benchmark now.

The next engineering boundary is the **Project_LUMI StoryForge Adapter**:

```
G2 Canon + CharacterStoryState + StoryIntent
        ↓
deterministic projection adapter
        ↓
storyforge-request.v1
        ↓
src.storyforge.run_storyforge(...)
        ↓
storyforge-result.v1
        ↓
external validation / StoryOutcome commit
```

The adapter must not add legacy/G1 fallback, dual-read, or direct StoryForge state mutation.
