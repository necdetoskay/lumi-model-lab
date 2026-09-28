# Living Universe Saga + Episodic Story Architecture v2

Status: **PROPOSED / MODEL-LAB-ONLY / PRODUCTION INTEGRATION FORBIDDEN**  
Canonical owner: **LUMI Model Lab**  
Supersedes for new experiments: the weak “Saga as sparse breadcrumb only” interpretation of `CHARACTER_NARRATIVE_BLUEPRINT_V1` while preserving its agency, reveal-ceiling and non-canon-future guarantees.  
Related canon: `LONG_HORIZON_SAGA_LAB.md`, `LUMI_STORYFORGE_AGENT_V1.md`, `STORY_DEFECT_DETECTION_AND_BOUNDED_REPAIR_V1.md`.

## 1. Product north star

LUMI is not a one-shot personalized story generator.

The target experience is a persistent, living narrative universe in which the user’s character:

- exists in a world that remembers;
- discovers places, people, objects, mysteries and consequences that persist;
- participates as an active role-playing protagonist rather than a passive observer;
- receives episodes that are individually satisfying but also contribute to longer arcs;
- can pursue, ignore, delay, abandon or accidentally create Sagas;
- can be surprised repeatedly without the system forgetting what previously mattered.

Canonical north-star statement:

> LUMI must make the user feel that their character exists inside a world that can surprise them for a very long time without forgetting meaningful past events.

The product value is **generated continuity**, not merely generated text.

## 2. Model Lab boundary

This architecture is qualified entirely in `lumi-model-lab`.

Until the story-production line is evidence-backed and promotion-ready:

- do not modify Project_LUMI production behavior;
- do not integrate experimental Saga/episode contracts into Project_LUMI;
- do not mutate production Canon, World, CharacterStoryState or Saga state;
- do not use production user data as an uncontrolled experiment source.

A future Project_LUMI integration requires a separate AEGIS L3 design and explicit handoff.

Paid model experiments are allowed when they produce useful evidence. Spend is not the optimization target; **reliable story quality is**.

## 3. Why the current A12 experiment failed

The A12 experiment exposed a distinction the current pipeline did not enforce strongly enough:

```text
language age != premise age != narrative age != interest age
```

A story can contain age-12 vocabulary while its core premise is suitable for a much younger reader.

Example failure signature:

```text
Target: age 12

Core premise:
toy dinosaur must cross a blanket swamp
→ string fails
→ cardboard succeeds

Language complexity: relatively high
Narrative/premise maturity: under-target
Result: PRODUCT FAIL / REPLAN
```

Increasing word count, technical vocabulary or sentence complexity does not repair a weak premise.

A structurally weak or under-age premise is not a LOCAL repair. It requires **REPLAN before prose generation**.

## 4. Three persistent narrative engines

The long-term architecture separates three responsibilities.

### 4.1 World Engine

Owns the authoritative answer to:

- what exists;
- what has been discovered;
- what is only rumored;
- what the character knows;
- what changed because of previous stories;
- what physical/world rules apply;
- which locations, NPCs, items, factions and phenomena are reusable.

The World Engine is not a story writer.

### 4.2 Saga Engine

Owns long-horizon narrative possibility:

- major goals;
- mysteries;
- Saga anchors;
- milestone graph;
- unresolved truths;
- optional branches;
- side Sagas;
- personal arcs;
- relationship arcs;
- world arcs;
- latent/emergent Saga seeds.

The Saga Engine must create durable direction without pre-writing a mandatory future.

### 4.3 Episode Engine

Owns the current reading session.

It chooses a satisfying episode from:

- current character/world state;
- active and eligible Saga material;
- recent episode history;
- reader/development profile;
- pacing needs;
- opportunity;
- available creative permission.

An Episode may advance a Main Saga, a Side Saga, a relationship/personal arc, world exploration, or no Saga at all when that is narratively correct.

## 5. Character creation output

Character creation should produce more than Origin + one vague Saga goal.

The Model Lab target is:

```text
Origin
+ Present Situation
+ Narrative Core
+ Current World Relationship
+ Main Saga Goal
+ Saga Spine Graph
+ Initial Mysteries
+ Initial Open Threads
+ Latent Side-Saga Seeds
+ Initial Opportunity Space
```

### 5.1 Main Saga spine

Initial guidance for a long-lived character:

- 1 primary Saga goal;
- approximately 5–7 major Saga anchors;
- approximately 15–30 meaningful milestones across the graph;
- multiple possible entry routes where appropriate;
- optional/dormant branches;
- unresolved truths that do not need to be fixed at character creation.

Counts are guidance, not hard production quotas. Quality outranks count.

### 5.2 Milestone is not Episode

A milestone is a meaningful Saga/world/character state condition.

An Episode is one lived adventure.

Therefore:

```text
1 milestone may be reached in episode 3, 5, 10 or never.
1 episode may touch zero, one or multiple eligible milestones.
```

The system must never equate `milestone_index == episode_number`.

### 5.3 Milestones should describe state, not scripts

Bad milestone:

> Episode 5: Deniz goes to the cave and finds the key.

Better milestone:

> Deniz obtains credible evidence that a key linked to the main mystery is hidden somewhere in the northern region.

Possible realization paths may include:

- a cave;
- a rumor;
- an expedition log;
- an NPC;
- a symbol;
- an abandoned camp;
- a rival group;
- another emergent event.

This preserves strong direction without removing generative freedom.

## 6. Saga graph, not linear quest list

The Saga Spine is a directed possibility graph.

```text
ORIGIN
  ↓
ANCHOR A
  ├─ M1
  ├─ M2
  └─ M3
       ↘
        ANCHOR B
       ↗       ↘
     M4         M5
                  ↓
               ANCHOR C
```

Requirements:

- no mandatory single route by default;
- user may ignore Saga for many Episodes;
- dormant branches can recover naturally;
- invalidated future branches may be rewoven;
- already committed/revealed facts cannot be rewritten;
- future choices are never committed before the user/character makes them.

The desired model is:

```text
fixed anchors
+ flexible connective tissue
+ unresolved truths
```

## 7. Multiple concurrent Sagas

The character must not be trapped inside one Main Saga.

The runtime may contain concurrent layers such as:

- Main Saga;
- Side Saga;
- World Mystery;
- Relationship Arc;
- Personal Arc;
- Faction/Region Arc;
- Emergent Saga created from an Episode outcome.

A new clue may create a Side Saga rather than forcing Main Saga progression.

A Main Saga may remain dormant for many Episodes without being treated as failure.

This is required for pacing and to avoid repetitive quest-chain behavior.

## 8. Generated continuity

The system should create new content without resetting history.

Examples of desired long-range callbacks:

- an NPC helped in Episode 7 matters again in Episode 40;
- an apparently minor object from Episode 3 becomes meaningful later;
- a decision changes which faction or location becomes available;
- a discovered place remains on the map;
- a rumor becomes confirmed or disproved;
- a previous failure changes a later opportunity.

The world should **grow**, not randomly regenerate.

Random novelty without continuity is not a living universe.

## 9. Creative permission envelope

The current story context must distinguish:

```text
CANONICAL FACTS
what is already true

CREATIVE PERMISSION ENVELOPE
what the current architecture is allowed to invent
```

This is required because an overly restrictive context can trap a strong story model inside mundane available objects.

The envelope may authorize creation of temporary or proposed:

- locations;
- NPCs;
- rumors;
- artifacts;
- environmental events;
- mysteries;
- factions;
- transient scene details;
- world-expansion candidates.

Creation permission does not grant Canon authority.

New durable facts remain proposed until validated/committed externally.

## 10. Roleplay requirement

Personalization is not achieved by inserting the character’s name into prose.

Every accepted Episode Spine must establish:

- the character’s role in the situation;
- a meaningful objective;
- meaningful agency;
- consequences influenced by character action/choice;
- discoveries the character can own;
- a world that reacts coherently to the character.

The character must be a participant, not merely a camera.

## 11. Wonder / ordinary-world transcendence

A LUMI Episode should normally provide something the user cannot trivially experience in ordinary life.

This may be:

- an unknown island;
- a deep-sea expedition;
- a lost civilization;
- another planet;
- an ancient city;
- a hidden laboratory;
- a historical period;
- an extraordinary but physically plausible expedition;
- a high-fantasy realm;
- a complex social/mystery situation unavailable to the reader.

This does not require fantasy.

Canonical principle:

> The imaginative reward must be larger than ordinary daily-life simulation unless the selected narrative mode explicitly calls for intimate/everyday storytelling.

## 12. Developmental / reader maturity model

Age adaptation must not mean vocabulary scaling alone.

At minimum distinguish:

- premise maturity;
- narrative complexity;
- reading/language complexity;
- conceptual complexity;
- interest fit.

For younger users, exact/developmental age strongly constrains all five.

For adults, exact chronological age becomes less important than reader profile, genre, tone, sophistication, pacing and thematic preference.

Initial Model Lab expansion path:

```text
start: age 12
then: 14 → 16 → 18
then adult reader profiles through mature adult / ~60
```

No age/profile is promoted by inference from another profile.

## 13. Age-12 starting standard

The first qualification target is age 12 because it exposed the current weakness clearly.

Age-12 stories must not pass merely because they contain advanced vocabulary.

A strong age-12 Episode should generally support materially higher levels of:

- curiosity/mystery;
- multi-step causality;
- character agency;
- consequences;
- uncertainty;
- escalation;
- competing constraints/trade-offs;
- meaningful discovery;
- less predictable resolution;
- richer world interaction.

A deliberately simple premise may still be valid if the selected mode calls for it, but it must not masquerade as a high-maturity adventure through difficult wording.

## 14. Episodic SaaS model

The primary consumption unit is an **Episode**, not a 10,000-word monolithic story.

Product metaphor:

```text
Universe
  ↓
Saga / Season
  ↓
Arc
  ↓
Episode
```

A subscriber should experience a continuing personal series rather than a monthly pile of disconnected generated stories.

### 14.1 Episode satisfaction rule

Every Episode must provide a local payoff.

It may still leave:

- an open mystery;
- a Saga hook;
- an unresolved relationship;
- a new region;
- a discovered artifact;
- a consequence.

But it must not feel like arbitrary truncation.

### 14.2 Initial reading-session guidance

For age-12 lab work, begin with roughly 15–20 minute standard Episodes.

Provisional test bands:

- quick: ~1,200–1,600 words;
- standard: ~1,600–2,500 words;
- long: ~2,500–3,500 words;
- special/finale: ~3,500–5,000 words.

These are experimental reading-session targets, not permanent global limits.

Narrative density and satisfaction outrank raw word count.

## 15. Story Spine architecture

Story production must be architected before drafting.

Target flow:

```text
Character + World + Saga State
        ↓
Reader / Development Profile
        ↓
StoryIntent / Opportunity
        ↓
Premise Architect
        ↓
Premise Quality Gate
        ↓
Episode Spine Architect
        ↓
Spine Quality Gate
        ↓
StoryContract
        ↓
Writer
        ↓
Story Age / Product Gate
        ↓
Defect Audit
        ↓
Bounded Repair / Replan
        ↓
Translation
        ↓
Fidelity
        ↓
StoryArtifact + ProposedOutcome
```

A poor premise must not reach the expensive prose-generation stages.

## 16. Candidate spine selection

A single generated plan is not sufficient for high-reliability production.

The lab should test generation of multiple materially different candidate spines, for example A/B/C, followed by a qualified selector/judge.

The selector must support:

```text
ACCEPT(candidate)
or
REJECT_ALL → regenerate
```

It must not automatically choose the highest-scoring bad candidate.

## 17. Spine quality dimensions

At minimum evaluate separately:

- premise strength;
- age/development maturity;
- reader interest fit;
- roleplay strength;
- immersion;
- wonder/discovery;
- objective clarity;
- meaningful stakes;
- opposition;
- mystery/curiosity;
- escalation;
- reversal;
- meaningful choice;
- climax/payoff;
- consequence;
- Saga potential;
- world-expansion value;
- Canon/state compatibility;
- non-repetition with recent Episodes.

Do not collapse all dimensions into one unqualified average.

A critical failure in a protected dimension can force REJECT even if other scores are high.

## 18. Repair policy

Retain the three-level defect policy:

### LOCAL
Examples:
- typo;
- mistranslated phrase;
- isolated continuity wording;
- single physical detail.

Action: minimal prose repair.

### STRUCTURAL
Examples:
- weak escalation;
- missing causal bridge;
- localized sequence problem;
- climax needs bounded restructuring.

Action: bounded structural repair and re-audit.

### REPLAN
Examples:
- premise too young;
- no meaningful roleplay;
- no wonder when adventure mode requires it;
- trivial stakes;
- wrong Saga direction;
- unacceptable reader-interest mismatch;
- Episode is filler with no product value.

Action: discard/rebuild premise or spine. Do not polish the prose.

## 19. Background narrative enrichment

A background system may prepare future narrative possibility while the user is absent.

Permitted non-canonical outputs include:

- latent quests;
- possible NPC arcs;
- possible world events;
- Saga cross-links;
- rumor chains;
- future location candidates;
- mystery candidates;
- relationship-development possibilities;
- milestone enrichment.

All such outputs remain:

`PROPOSED | LATENT`

until activated and validated.

The background system must not silently advance user-dependent Canon.

User absence must not cause irreversible character choices or hidden mandatory progression.

## 20. Knowledge isolation and reveal ceilings

The full Saga graph is system knowledge, not character knowledge.

The character may know only bounded projections such as:

- a rumor;
- a symbol;
- partial coordinates;
- an NPC claim;
- a map fragment;
- an unexplained artifact.

Hidden future truth must not leak to the Episode writer.

Runtime projection must preserve reveal ceilings and Character knowledge state.

## 21. Story evidence and tracing

Every paid or qualification run must preserve enough evidence to understand both technical and product failure.

At minimum:

- full input profile/state projection;
- Saga/Opportunity context actually supplied;
- candidate premises/spines;
- selected/rejected candidates and reasons;
- exact model/profile identities;
- raw outputs;
- normalized outputs;
- token usage;
- cost;
- latency per stage;
- failure stage;
- full generated English story even on FAIL when available;
- translated story when translation was reached;
- exact defect family;
- paragraph/sentence/span mapping;
- exact quote and deterministic offsets when available;
- repair before/after evidence;
- final verdict.

Generated test stories must be surfaced for human inspection. A PASS/FAIL number alone is insufficient evidence of product quality.

## 22. Reliability target

The long-term goal is a story-production system that produces the requested class of story with approximately **95% or better operational/product reliability**, with bounded repair handling recoverable defects.

For Spine qualification specifically, the lab target should evolve toward:

- >=95% acceptable Story Spine on the governed qualification set after allowed bounded replan attempts;
- 0 critical Canon violations;
- 0 protected reveal violations;
- 0 critical agency violations;
- no accepted under-target developmental premise;
- no accepted empty/filler episode in adventure-oriented profiles.

The exact statistical confidence/promotion rule must be frozen before claiming the target is met.

## 23. Aion and model neutrality

Aion 3.5 Mini currently remains a candidate Story Architect/Writer because of its narrative/roleplay orientation, but the architecture must remain model-neutral.

Do not blame or promote a model based on a weak upstream premise.

A fair writer test requires:

- strong accepted premise;
- strong accepted spine;
- correct age/reader profile;
- sufficient creative permission;
- correct Saga/world projection.

Only then may writer quality be attributed to the model/profile.

## 24. First qualification mission

The next major Model Lab mission is **Story Spine Reliability starting at age 12**.

Before broad age expansion:

1. complete durable tracing;
2. formalize Saga Spine + Episode Spine schemas;
3. produce one strong age-12 Character/World fixture with a 15–30 milestone Saga graph;
4. qualify premise/spine gating;
5. generate 3–5 sequential Episodes from the same persistent character;
6. verify each Episode is satisfying independently;
7. verify Saga continuity without forcing Saga every Episode;
8. verify meaningful callbacks/state persistence;
9. inspect every generated story manually;
10. only then expand toward additional ages/reader profiles.

## 24A. Human creative-judge authority during Model Lab qualification

During the current Model Lab phase, the human operator is the final creative-quality authority for high-leverage narrative artifacts.

Mandatory human review checkpoints include at minimum:

- Origin;
- Present Situation / Narrative Core;
- Main Saga Goal;
- Saga anchors;
- milestone graph;
- latent Side-Saga seeds;
- hidden mysteries / reveal structure;
- candidate Premises selected for paid drafting;
- initial Episode Spines;
- full generated qualification Episodes.

Automated judges may:

- detect defects;
- score bounded dimensions;
- compare candidates;
- flag age mismatch;
- flag weak roleplay, wonder, agency, stakes or Saga potential;
- recommend ACCEPT / REVISE / REJECT.

They do **not** replace the human product judgment during this qualification phase.

The assistant/reviewer must provide an independent assessment rather than simply echoing the operator's opinion. When disagreeing, it should state the disagreement and evidence plainly.

Human review outcomes are:

`APPROVE | REVISE | REJECT`

No artifact that requires a human checkpoint may advance to the next expensive qualification stage without `APPROVE`.

Each review packet should surface the complete artifact, not only scores or summaries, together with:

- what is strong;
- what is weak;
- age/reader fit;
- roleplay/immersion quality;
- wonder/discovery quality;
- agency/stakes;
- Saga coherence and long-horizon potential;
- risks of repetition or premature reveal;
- the assistant's independent recommendation and reasons.

This human gate is a Model Lab qualification control. A future production product may automate more of these decisions only after sufficient evidence proves the automated judge is reliable.

## 25. Promotion boundary

No result from this architecture authorizes Project_LUMI changes.

Promotion from Model Lab requires a separate evidence-backed decision showing that:

- Story Spines are reliably strong;
- episodic generation remains coherent across repeated runs;
- living-universe state creates measurable narrative value;
- character agency and hidden-information boundaries remain protected;
- StoryForge repair/replan behavior is reliable;
- model/cost/latency behavior is measured;
- the system is materially better than isolated one-shot personalized stories.

Only after that decision may a separate Project_LUMI integration design begin.

## 26. Canonical summary

The core hierarchy is:

```text
Character Origin
      ↓
Living World
      ↓
Character Saga Spine / Quest Graph
      ↓
Active Saga + Side/Personal/World Arcs
      ↓
Opportunity / StoryIntent
      ↓
Premise
      ↓
Episode Spine
      ↓
StoryContract
      ↓
Draft / Audit / Repair
      ↓
Episode Outcome
      ↓
Persistent State
      ↓
next Episode
```

The goal is not infinite text.

The goal is an **open-ended personal adventure whose continuity, discovery, consequences and imagination remain worth returning to**.
