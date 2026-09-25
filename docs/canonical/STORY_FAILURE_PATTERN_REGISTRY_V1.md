# LUMI Story Failure Pattern Registry v0.1

Status: EXPERIMENTAL / evidence-derived
Date: 2026-09-25
Scope: Story writer prevention rules, deterministic lint candidates, local copy-edit guidance, and final veto semantics.

## Purpose

LUMI must not rediscover the same prose defects after every generation. Repeated human/editor/judge findings are normalized into reusable failure patterns. The registry is a prevention layer, not a giant checklist pasted verbatim into every prompt.

Runtime compilation order:

1. global narrative constraints
2. language-specific constraints
3. exact-age / age-band constraints
4. story-type constraints
5. model-specific recurrent failures

Only applicable high-value rules should be compiled into a writer prompt. Detection hints may also feed deterministic lint. Repair guidance is for local copy-edit only; it must not trigger a whole-story rewrite unless a structural/canon defect requires it.

## Severity semantics

- BLOCKER: canon, identity, knowledge, physical/causal nonsense, or unusable language.
- SERIOUS: clearly damages age fit, naturalness, continuity, or story voice.
- MODERATE: visible editorial defect; normally local repair.
- MINOR: preference/polish; not a production veto by itself.

A high count of MINOR preferences is not equivalent to a failed story.

## Core failure families

### FP-TR-001 — Adult/abstract narrator register
Applies: Turkish, especially early-child/child.
Observed examples:
- "Deniz bu cevaba razı oldu."
- "dikkatini yeniden ... verdi"
- "değerlendirdi", "gözlemledi"
Rule: Prefer observable action, speech, facial expression, or concrete behavior over abstract adult interpretation of a child's mental state.
Writer negative constraint: Do not narrate a young child's response using formal, bureaucratic, analytical, or adult cognitive vocabulary.
Lint candidates: razı oldu; dikkatini verdi; değerlendirdi; gözlemledi; kanaat.
Default severity: SERIOUS for early-child; MODERATE otherwise.

### FP-TR-002 — Literary/register mismatch
Applies: Turkish early-child.
Observed examples:
- "gerilemiş"
- "bürünür"
Rule: Vocabulary may be rich, but it must sound natural when a Turkish parent reads it aloud to the exact target age.
Writer negative constraint: Do not insert conspicuously literary/formal words into otherwise simple spoken child prose merely to sound literary.
Default severity: MODERATE.

### FP-AGE-001 — Child reasoning too adult/too clean
Applies: exact-age dependent.
Observed example:
- "orada bir taş vardı, hiç görünmüyordu, şimdi görünüyor"
Rule: Young children may notice cause/effect, but dialogue should not become a perfectly structured reasoning report.
Writer negative constraint: Do not make a four-year-old verbalize multi-step chronological or analytical reasoning with adult precision.
Default severity: SERIOUS when strongly violated.

### FP-DIALOGUE-001 — Adult becomes teacher/examiner
Applies: child stories.
Observed examples:
- "Doğru söylüyorsun. ... değil mi? Su da biraz azalmış olabilir."
- correcting imaginative "taş uçtu" with "Uçmadı, düştü sadece"
Rule: Adult dialogue should participate in the relationship and scene, not constantly validate, correct, quiz, or explain.
Writer negative constraint: Do not turn the caregiver into a teacher, answer-key, evaluator, or science explainer.
Default severity: SERIOUS when recurrent.

### FP-DIDACTIC-001 — Story becomes lesson/explanation
Applies: all child stories; strict for early-child.
Observed examples:
- explicit water-cycle/buharlaşma explanation
- explicit causal explanation of seasonal leaf color
Rule: Information should emerge through event, image, play, or brief age-natural dialogue. Story remains primary.
Writer negative constraint: Do not pause the narrative for textbook-like causal explanations or educational summaries.
Default severity: SERIOUS.

### FP-PROSE-001 — Repeated syntactic template
Applies: all.
Observed examples:
- repeated "eskisi gibi/kadar ... değildi"
- repeated before/now comparison structures
Rule: Recurrent information must use varied natural syntax and should not reveal a generation template.
Writer negative constraint: Do not reuse the same sentence skeleton for multiple observations in one short story.
Default severity: MODERATE; SERIOUS when conspicuous/recurrent.

### FP-PROSE-002 — Defensive over-explanation
Applies: all.
Observed example:
- "suyun kenarına, ama içine değil, kuru toprağa attı"
Rule: Do not narrate around imagined validator objections. Preserve only details a human storyteller would naturally mention.
Writer negative constraint: Do not add parenthetical or defensive clauses solely to prove safety, continuity, or non-contradiction.
Default severity: MODERATE.

### FP-PHYS-001 — Awkward/impossible physical action
Applies: all.
Observed examples:
- "havanın üstüne dokundu / touched the air above..."
- "ayaklarını uzattı" for taking a step
- unclear hand-swing gesture used as pointing
Rule: Every concrete action must be physically visualizable.
Writer negative constraint: Before emitting an action, ensure a reader can picture a human body performing it naturally.
Default severity: BLOCKER if nonsensical; MINOR/MODERATE if merely awkward.

### FP-NARRATOR-001 — Unnecessary adult interpretation
Applies: early-child/child.
Observed examples:
- "hiç dertleri yokmuş gibi"
- "sanki hiçbir şey değişmemiş gibi"
Rule: Prefer the visible scene over philosophical or interpretive narrator commentary.
Writer negative constraint: Do not tell the reader what a scene symbolically means when concrete action/image can carry it.
Default severity: MODERATE.

### FP-ENDING-001 — Generic LLM happy ending
Applies: all.
Observed examples:
- "yüzünde kocaman bir gülümseme vardı"
- generic "yine geliriz/göreceğiz"
Rule: End on a story-specific image, action, line, unresolved curiosity, or earned emotional beat.
Writer negative constraint: Do not close with generic smiling, lesson-learned, everything-is-fine, or "we will come again" formulas.
Default severity: MODERATE.

### FP-CHAR-001 — Character exists only to service information
Applies: all.
Rule: Child questions/actions must arise from personality, desire, play, fear, curiosity, or current scene—not merely to cue exposition.
Writer negative constraint: Do not make the protagonist ask exactly the question the story needs so another character can deliver information.
Default severity: SERIOUS when recurrent.

### FP-CANON-001 — Invented canon-relevant identity
Applies: G2 StoryContract/ContextPack.
Observed benchmark behavior:
- writer invented Grandma/Mama/Ms. Rosa/Ms. Lee when ContextPack did not authorize identities.
Rule: Writer may not create canon-relevant named/relational NPC identity when the contract does not supply or explicitly authorize it.
Writer negative constraint: Never invent a named or relationship-bearing persistent character to fill missing context.
Default severity: BLOCKER.

### FP-TR-003 — Translationese / source-prose contamination
Applies: translated or multilingual paths.
Observed example:
- English "touched the air above the painted marker" became unnatural Turkish rather than being rejected upstream.
Rule: Translation cannot rescue nonsensical source prose; source semantic sanity and target-language naturalness are separate gates.
Writer/translator negative constraint: Do not preserve source syntax when it produces unnatural target-language action or word order.
Default severity: BLOCKER for nonsense; SERIOUS for obvious translationese.

### FP-AGE-002 — Abstract metaphor beyond target age
Applies: exact-age dependent.
Observed examples:
- overly abstract causal metaphors or polished phrases attributed to age 4.
Rule: Metaphor is allowed when concrete, playful, and immediately graspable; avoid abstract conceptual layering.
Writer negative constraint: For age 4, keep metaphor concrete and one layer deep.
Default severity: MODERATE/SERIOUS.

### FP-SAFETY-001 — Safety boilerplate leaks into prose
Applies: child stories.
Rule: Safety constraints govern events, but should not read like policy text.
Writer negative constraint: Show safe behavior naturally; do not insert explicit safety lectures unless the scene itself calls for them.
Default severity: MODERATE.

### FP-LENGTH-001 — Target-length miss
Applies: all.
Observed: 361 words for target 500 with ±25% policy; minimum is 375.
Rule: Word budget is deterministic and must be checked independently from literary judging.
Writer negative constraint: Stay inside the supplied hard word interval; do not end early merely because the narrative can technically close.
Default severity: BLOCKER for qualification/delivery when outside hard interval.

### FP-STRUCT-001 — Premature closure / incomplete long-form arc
Applies: long-form.
Historical evidence includes local-model runs closing hundreds of words before a 1600–2400 target.
Rule: Long stories require enough event progression; word count must not be padded with repetition, but early closure is not acceptable.
Writer negative constraint: Do not resolve the central arc before the contracted progression has been earned.
Default severity: BLOCKER for qualification.

### FP-STRUCT-002 — Repetition/loop padding
Applies: long-form.
Rule: Never satisfy length by restating observations, dialogue, or scene beats.
Writer negative constraint: Each paragraph/scene must change state, reveal something, deepen character, or advance the active thread.
Default severity: SERIOUS/BLOCKER when extensive.

## Writer prompt compiler policy

Do NOT paste this registry wholesale into the writer prompt.

For each generation:
- select applicable rules by language, exact age, story type, and model;
- prioritize BLOCKER/SERIOUS plus recurrent model-specific MODERATE patterns;
- compile concise behavior-level negative constraints;
- cap negative constraints so they do not dominate creative instructions;
- include positive counterpart behavior where useful;
- keep detection regex/examples out of the writer prompt unless a model repeatedly needs one short example.

Recommended prompt sections:
1. StoryContract / canon
2. exact-age voice
3. narrative intent
4. positive craft guidance
5. compact failure-aware constraints
6. hard length interval

## Gate ownership

Writer prevention:
- all applicable patterns.

Deterministic lint:
- lexical/register patterns
- repeated sentence structures
- word range
- known generic endings
- suspicious safety/expository phrases
- obvious duplicate/repetition patterns

Local copy-editor:
- lint hits and auditor-provided exact spans only.

Final veto:
- BLOCKER
- unresolved SERIOUS
- canon/knowledge contradiction
- nonsensical physical action
- unusable Turkish
- hard length violation

Final veto must NOT fail a story solely because an editor prefers a different synonym or stylistic option.

## Learning loop

Every externally supplied human/editor analysis must be normalized before becoming a rule:
1. preserve exact evidence quote;
2. classify into an existing failure family when possible;
3. create a new family only when behavior is genuinely distinct;
4. mark language/age/story/model scope;
5. record recurrence count;
6. promote to writer negative constraint only after repeated evidence or one BLOCKER-class failure;
7. promote to deterministic lint only when detection can be precise enough to avoid excessive false positives;
8. retain provenance to the run/story/audit.

This registry is append-only at the evidence level. Rules may be revised, merged, or scoped more narrowly as counter-evidence accumulates.
