from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call
from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.story_defect_detection import DEFECT_FAMILIES, segment_story

FIXTURE = Path("experiments/fixtures/lsf_spine_planner_qualification_01_20260926.json")
OUT = Path("runs/lsf-spine-planner-qualification-01/result.json")

PLANNER = "aion-labs/aion-3.5-mini"
PLAN_VALIDATOR = "anthropic/claude-sonnet-5"
WRITER = "aion-labs/aion-3.5-mini"
PRIMARY_AUDITOR = "anthropic/claude-sonnet-5"
SECONDARY_AUDITOR = "openai/gpt-5.6-sol"
TRANSLATOR = "google/gemini-3.8-flash"
FIDELITY_GATE = "openai/gpt-5.6-luna"

SEED = 2026092741

PLANNER_SYSTEM = r"""
You are the Story Planner inside LUMI StoryForge.

You receive:
- one StoryIntent,
- one minimal Story Context Packet,
- one generation profile.

Your task is to create the PLAN ONLY. Do not write story prose.

Important:
- No prewritten spine or solution has been supplied.
- Infer a simple, concrete, age-appropriate story plan from the StoryIntent and available context.
- Use only facts available in the supplied context packet for durable characters, owned inventory, locations, objects, world rules, and current state.
- Do not invent adult helpers, family members, tools, owned objects, or new canon.
- You may use ordinary transient actions, dialogue, sounds, and observations that do not create new durable canon.
- Respect all hard guards and knowledge boundaries.
- The active world follows normal everyday physics because the supplied guard says so.
- The protagonist must solve the low-stakes problem through observable action, not a narrator lesson.
- Do not include a moral.
- Do not mutate canon/state in the plan. State changes are only PROPOSED outcomes for later commit authority.
- Plan for an EXACTLY 4-year-old read-aloud story of about 500 English words.
- Keep causality concrete enough that a writer cannot hide a bad solution behind pretty prose.

Return JSON only:
{
  "premise": "one concise English premise",
  "beats": [
    {
      "id": "B1",
      "density": "brief|develop|anchor",
      "beat": "one concrete ordered beat, not prose",
      "uses_fact_ids": ["zero or more exact fact ids from context"]
    }
  ],
  "assumptions": [
    {
      "text": "minimal assumption needed by the plan",
      "type": "transient_environment|action|dialogue|none",
      "why_safe": "why this does not invent durable canon"
    }
  ],
  "expected_outcome": {
    "proposed_state_changes": [
      {
        "kind": "knowledge|position|object_state|relationship|none",
        "description": "proposed post-story change; not committed"
      }
    ],
    "preserved_invariants": [
      "important facts that must still be true after the story"
    ]
  }
}

Hard shape rules:
- exactly 8 beats, ids B1..B8 in order;
- density must be brief/develop/anchor;
- at least 3 anchor beats;
- B8 must be a concrete ending beat;
- uses_fact_ids must reference only ids present in the packet.
""".strip()

PLAN_VALIDATOR_SYSTEM = r"""
You are an independent Story Spine validator.

You receive:
- StoryIntent,
- minimal Story Context Packet,
- generation profile,
- a proposed premise + 8-beat spine + assumptions + expected outcome.

Judge the PLAN, not prose quality.

Report only serious/critical plan defects in:
- intent_alignment
- canon_state_consistency
- unavailable_object_or_character
- knowledge_boundary
- physical_causality
- event_order
- age_fit
- closure
- outcome_safety

Specific policy:
- Context packet is authoritative.
- Normal everyday physics applies.
- Do not require every available fact to be used.
- Do not penalize harmless transient dialogue/action assumptions.
- A plan may propose outcome/state changes but may not treat them as already committed.
- The plan must not smuggle in unavailable tools, adults, or durable canon.
- A good problem-solving plan should have a clear failed attempt/observation/adjustment/payoff pattern without becoming a lesson.
- Do not rewrite the plan.

Return JSON only:
{
  "valid": true,
  "counts": {"critical":0,"serious":0},
  "defects": [
    {
      "severity":"critical|serious",
      "class":"intent_alignment|canon_state_consistency|unavailable_object_or_character|knowledge_boundary|physical_causality|event_order|age_fit|closure|outcome_safety",
      "beat_ids":["B1"],
      "why":"brief evidence-based reason"
    }
  ],
  "summary":"brief"
}
""".strip()

WRITER_SYSTEM = r"""
You are an experienced English children's story writer.

Write a warm, natural read-aloud story for an EXACTLY 4-year-old child using the supplied validated premise and 8-beat STORY SPINE.

The spine is a plan, not prose. Preserve:
- event order,
- causal solution,
- object continuity,
- character availability,
- hard guards,
- concrete ending.

Do not add:
- adults or family members,
- new tools or durable objects not in context,
- new canon,
- a moral/lesson,
- narrator explanations of the lesson.

Use simple concrete language, short dialogue, playful sound where natural, and observable actions.

The story must stay within normal everyday physics.

Length:
- target about 500 English words
- preferred 475-525
- hard 375-625
- do not finish below 375.

Return only the finished English story. First line must be the title.
""".strip()

AUDIT_SYSTEM = r"""
You are a strict publication-blocker auditor for one finished English read-aloud story for an EXACTLY 4-year-old child.

You receive the authoritative StoryIntent, Context Packet, validated Spine and finished story.

Evaluate every canonical semantic family:
- physical_feasibility
- causal_logic
- state_continuity
- epistemic_order
- spatial_consistency
- temporal_consistency
- response_causality
- closure_integrity
- canon_integrity

Report ONLY serious or critical semantic defects.

Also enforce:
- story must materially follow the validated spine;
- no unavailable durable object/person may appear as a solution;
- normal everyday physics;
- StoryIntent direct references and guards must not be contradicted;
- outcome may be narrated as story consequence, but no unrelated durable canon may be invented;
- no adult solves the problem;
- do not report mere style/polish issues.

Return JSON only:
{
  "evaluations":[
    {
      "family":"physical_feasibility",
      "present":false,
      "severity":null,
      "repair_scope":null,
      "span_ids":[],
      "reason":"brief evidence-based reason"
    }
  ]
}
""".strip()

TRANSLATION_SYSTEM = r"""
You are a professional literary translator specializing in English -> Turkish children's read-aloud stories for EXACTLY age 4.

Translate the supplied accepted English story into natural Turkish.

THIS IS TRANSLATION, NOT REWRITING.

Preserve:
- all characters and objects,
- event order,
- physical problem and solution,
- state continuity,
- dialogue meaning,
- causal relations,
- ending,
- absence of moralizing.

Do not add/remove plot events, tools, helpers, canon, motivations, or lessons.
Keep names unchanged.
Use natural contemporary Turkish, short speakable sentences, and natural sound effects.

Return only the finished Turkish story.
""".strip()

FIDELITY_SYSTEM = r"""
You are a strict bilingual EN->TR semantic fidelity gate for a children's read-aloud story.

Report ONLY serious or critical translation defects:
- omission
- addition
- character_shift
- object_shift
- state_shift
- causal_shift
- knowledge_shift
- ending_shift

Compare source and translation. Ignore harmless stylistic restructuring.

Return JSON only:
{
  "findings":[
    {
      "severity":"serious|critical",
      "class":"omission|addition|character_shift|object_shift|state_shift|causal_shift|knowledge_shift|ending_shift",
      "source_quote":"short exact EN quote",
      "translation_quote":"short exact TR quote",
      "why":"brief reason"
    }
  ],
  "fidelity_clean":true
}
""".strip()


def meta_cost(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    c = meta.get("cost")
    if isinstance(c, dict) and isinstance(c.get("usd"), (int, float)):
        return float(c["usd"])
    if isinstance(c, (int, float)):
        return float(c)
    return 0.0


def packet_fact_ids(packet: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("deterministic_core", "jev_selected_enrichment"):
        for row in packet.get(key) or []:
            fid = str(row.get("id") or "")
            if fid:
                ids.add(fid)
    return ids


def deterministic_plan_check(plan: dict[str, Any], allowed_fact_ids: set[str]) -> list[str]:
    errors: list[str] = []
    premise = plan.get("premise")
    if not isinstance(premise, str) or not premise.strip():
        errors.append("missing_premise")

    beats = plan.get("beats")
    if not isinstance(beats, list) or len(beats) != 8:
        errors.append("beats_must_equal_8")
        beats = beats if isinstance(beats, list) else []

    expected_ids = [f"B{i}" for i in range(1, 9)]
    actual_ids = [str(x.get("id") or "") for x in beats]
    if actual_ids != expected_ids:
        errors.append(f"beat_ids_invalid:{actual_ids}")

    anchors = 0
    for beat in beats:
        density = str(beat.get("density") or "")
        if density not in {"brief", "develop", "anchor"}:
            errors.append(f"density_invalid:{beat.get('id')}:{density}")
        if density == "anchor":
            anchors += 1
        text = str(beat.get("beat") or "").strip()
        if not text:
            errors.append(f"empty_beat:{beat.get('id')}")
        refs = beat.get("uses_fact_ids") or []
        if not isinstance(refs, list):
            errors.append(f"fact_refs_not_list:{beat.get('id')}")
            continue
        unknown = sorted(set(str(x) for x in refs) - allowed_fact_ids)
        if unknown:
            errors.append(f"unknown_fact_refs:{beat.get('id')}:{unknown}")

    if anchors < 3:
        errors.append(f"anchors_lt_3:{anchors}")

    outcome = plan.get("expected_outcome")
    if not isinstance(outcome, dict):
        errors.append("missing_expected_outcome")
    return errors


def normalize_audit(payload: dict[str, Any], valid_ids: set[str]) -> list[dict[str, Any]]:
    rows = payload.get("evaluations")
    if not isinstance(rows, list):
        raise RuntimeError("evaluations_missing")
    seen = set()
    findings = []
    for row in rows:
        fam = str(row.get("family") or "")
        if fam not in DEFECT_FAMILIES or fam in seen:
            raise RuntimeError(f"family_invalid_or_duplicate:{fam}")
        seen.add(fam)
        present = row.get("present")
        if not isinstance(present, bool):
            raise RuntimeError(f"present_invalid:{fam}")
        if not present:
            continue
        sev = str(row.get("severity") or "")
        if sev not in {"serious", "critical"}:
            raise RuntimeError(f"severity_invalid:{fam}:{sev}")
        spans = [str(x) for x in (row.get("span_ids") or [])]
        if not spans or not set(spans).issubset(valid_ids):
            raise RuntimeError(f"span_invalid:{fam}:{spans}")
        findings.append({
            "family": fam,
            "severity": sev,
            "span_ids": spans,
            "repair_scope": row.get("repair_scope"),
            "reason": str(row.get("reason") or "").strip(),
        })
    if seen != set(DEFECT_FAMILIES):
        raise RuntimeError(f"families_missing:{sorted(set(DEFECT_FAMILIES)-seen)}")
    return findings


def audit_story(
    *,
    api_key: str,
    model: str,
    fixture: dict[str, Any],
    plan: dict[str, Any],
    story: str,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    seg = segment_story(story)
    payload, meta = structured_call(
        api_key=api_key,
        model=model,
        system=AUDIT_SYSTEM,
        payload={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
            "validated_spine": plan,
            "story_segments": seg,
        },
        seed=seed,
        max_tokens=2800,
        request_class="editorial_audit",
    )
    return normalize_audit(payload, {x["id"] for x in seg}), meta


def main():
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    started = time.perf_counter()

    allowed_fact_ids = packet_fact_ids(fixture["context_packet"])

    plan, planner_meta = structured_call(
        api_key=key,
        model=PLANNER,
        system=PLANNER_SYSTEM,
        payload={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
            "generation_profile": fixture["generation_profile"],
        },
        seed=SEED,
        max_tokens=None,
        request_class="story_planning",
    )

    deterministic_plan_errors = deterministic_plan_check(plan, allowed_fact_ids)

    validator, validator_meta = structured_call(
        api_key=key,
        model=PLAN_VALIDATOR,
        system=PLAN_VALIDATOR_SYSTEM,
        payload={
            "story_intent": fixture["story_intent"],
            "context_packet": fixture["context_packet"],
            "generation_profile": fixture["generation_profile"],
            "proposed_plan": plan,
            "deterministic_plan_errors": deterministic_plan_errors,
        },
        seed=SEED + 1,
        max_tokens=2200,
        request_class="editorial_audit",
    )

    counts = validator.get("counts") or {}
    plan_semantic_clean = (
        bool(validator.get("valid"))
        and int(counts.get("critical", 0) or 0) == 0
        and int(counts.get("serious", 0) or 0) == 0
    )
    plan_pass = not deterministic_plan_errors and plan_semantic_clean

    story = None
    writer_cost = 0.0
    writer_usage = None
    story_words = None
    length_pass = False
    primary_findings = None
    primary_meta = None
    secondary_findings = None
    secondary_meta = None
    english_pass = False
    translation = None
    translator_cost = 0.0
    translator_usage = None
    fidelity_result = None
    fidelity_meta = None
    fidelity_pass = False

    if plan_pass:
        story, writer_body, _ = call_openrouter(
            api_key=key,
            model=WRITER,
            system_prompt=WRITER_SYSTEM,
            user_prompt=json.dumps({
                "story_intent": fixture["story_intent"],
                "context_packet": fixture["context_packet"],
                "validated_plan": plan,
                "generation_profile": fixture["generation_profile"],
            }, ensure_ascii=False),
            temperature=0.72,
            max_tokens=None,
            seed=SEED + 2,
            request_class="teacher_story_medium_reasoning",
            structured_output=False,
        )
        writer_cost = float(parse_cost(writer_body).usd or 0.0)
        writer_usage = parse_usage(writer_body).model_dump(mode="json")
        story_words = count_words(story)
        length_pass = 375 <= story_words <= 625

        primary_findings, primary_meta = audit_story(
            api_key=key, model=PRIMARY_AUDITOR, fixture=fixture,
            plan=plan, story=story, seed=SEED + 3
        )
        secondary_findings, secondary_meta = audit_story(
            api_key=key, model=SECONDARY_AUDITOR, fixture=fixture,
            plan=plan, story=story, seed=SEED + 4
        )
        english_pass = (
            length_pass
            and not primary_findings
            and not secondary_findings
        )

    if english_pass and story is not None:
        translation, trans_body, _ = call_openrouter(
            api_key=key,
            model=TRANSLATOR,
            system_prompt=TRANSLATION_SYSTEM,
            user_prompt=story,
            temperature=0.2,
            max_tokens=None,
            seed=SEED + 5,
            request_class="translation",
            structured_output=False,
        )
        translator_cost = float(parse_cost(trans_body).usd or 0.0)
        translator_usage = parse_usage(trans_body).model_dump(mode="json")

        fidelity_result, fidelity_meta = structured_call(
            api_key=key,
            model=FIDELITY_GATE,
            system=FIDELITY_SYSTEM,
            payload={
                "source_language": "en",
                "target_language": "tr",
                "exact_age": 4,
                "source_story": story,
                "translation": translation,
            },
            seed=SEED + 6,
            max_tokens=1800,
            request_class="editorial_audit",
        )
        blocking = [
            x for x in (fidelity_result.get("findings") or [])
            if str(x.get("severity") or "") in {"serious", "critical"}
        ]
        fidelity_pass = bool(fidelity_result.get("fidelity_clean")) and not blocking

    costs = {
        "planner": meta_cost(planner_meta),
        "plan_validator": meta_cost(validator_meta),
        "writer": writer_cost,
        "primary_story_audit": meta_cost(primary_meta),
        "secondary_story_audit": meta_cost(secondary_meta),
        "translator": translator_cost,
        "fidelity_gate": meta_cost(fidelity_meta),
    }
    costs["total"] = sum(costs.values())

    result = {
        "schema_version": "lsf-spine-planner-qualification-01-result.v1",
        "profile": fixture["profile"],
        "source_context_builder_run": fixture["source_context_builder_run"],
        "models": {
            "planner": PLANNER,
            "plan_validator": PLAN_VALIDATOR,
            "writer": WRITER,
            "primary_story_auditor": PRIMARY_AUDITOR,
            "secondary_story_auditor": SECONDARY_AUDITOR,
            "translator": TRANSLATOR,
            "fidelity_gate": FIDELITY_GATE,
        },
        "story_intent": fixture["story_intent"],
        "context_packet": fixture["context_packet"],
        "planner_output": plan,
        "deterministic_plan_errors": deterministic_plan_errors,
        "plan_validation": validator,
        "plan_pass": plan_pass,
        "english_story": story,
        "english_word_count": story_words,
        "length_pass": length_pass,
        "primary_findings": primary_findings,
        "secondary_findings": secondary_findings,
        "english_pass": english_pass,
        "turkish_translation": translation,
        "fidelity_result": fidelity_result,
        "fidelity_pass": fidelity_pass,
        "publication_ready": plan_pass and english_pass and fidelity_pass,
        "cost_usd": costs,
        "writer_usage": writer_usage,
        "translator_usage": translator_usage,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT.parent / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if story:
        (OUT.parent / "english.txt").write_text(story + "\n", encoding="utf-8")
    if translation:
        (OUT.parent / "turkish.txt").write_text(translation + "\n", encoding="utf-8")

    print(json.dumps({
        "plan_pass": plan_pass,
        "deterministic_plan_errors": deterministic_plan_errors,
        "plan_validation": validator,
        "english_word_count": story_words,
        "length_pass": length_pass,
        "primary_findings": primary_findings,
        "secondary_findings": secondary_findings,
        "english_pass": english_pass,
        "fidelity_pass": fidelity_pass,
        "publication_ready": result["publication_ready"],
        "cost_usd": costs,
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
