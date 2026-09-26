from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.english_scene_plan_smoke import build_labeled_brief
from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import count_words, parse_cost, parse_usage
from src.schemas import StorySpec
from experiments.prototypes import story_v5_whole_draft_prototype as whole
from experiments.prototypes import story_v5_narrative_load_planner_20260926 as nl
from experiments.prototypes import story_v5_narrative_load_planner_cohort_b_20260926 as cohort
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

ARCHITECT_MODEL = "openai/gpt-5.6-sol"
WRITER_MODEL = "anthropic/claude-sonnet-5"
JUDGE_MODEL = "openai/gpt-5.6-sol"
SEED_BASE = 2026092710

ARCHITECT_WITH_NARRATIVE_LOAD = (
    whole.ARCHITECT_PROMPT
    + r"""

NARRATIVE LOAD CONTRACT — integrate this into the SAME architecture call:
- Quality and causal coherence are primary; requested word count is a soft planning signal, not a reason to add filler.
- For a short exact-age-4 read-aloud story, keep the macro SceneGraph compact. Do NOT turn 8-12 functional beats into 8-12 micro-scenes.
- Across the complete SceneGraph, create enough distinct functional beats to form a natural chain of setup -> progression -> payoff -> resolution.
- Each beat must add a new observation, action, decision, consequence, social shift, complication, test, or payoff. Do not split one semantic event into multiple beats merely to increase length.
- One main arc is mandatory.
- At most one supporting micro-thread is allowed, and only if the premise naturally benefits from it.
- A supporting micro-thread must arise from the same environment, existing object, existing relationship, or natural condition; have setup -> friction/change -> convergence; change an observation/decision/constraint/payoff; and rejoin the main arc.
- Omit the supporting thread if removing it would change nothing except length.
- Never invent a named character, new relationship canon, durable world fact, important persistent item, or independent solution merely to create narrative load.
- Once the main arc establishes a causal rule, a supporting thread may test or expose it but must not weaken it, replace it, or invent a late hidden condition solely to delay payoff.
- Preserve committed item/action state. Do not complete an action and later undo it merely to reuse a prop.
- For exact-age-4, avoid adult-style reasoning chains, didactic explanation, complex subplot logic, and unsafe independent behavior.
- Prefer strengthening the main arc over adding a supporting thread.
- The final resolution must remain concrete, story-specific, and non-didactic.
- EPISTEMIC ORDER: if a misunderstanding drives the story, do not reveal the decisive explanatory evidence before the misunderstanding has formed. Once decisive evidence resolves it, do not return to or repeatedly explain the same misunderstanding.
- RESPONSE CAUSALITY: do not confuse inability to respond with inability to hear/see. Busy hands or urgent action may delay a reply but do not by themselves cause sensory failure.
- ECONOMY AFTER RESOLUTION: after the core misunderstanding or causal question is resolved, advance to cooperative action/payoff instead of restating the explanation in narration, dialogue, and thought.
- CAUSAL STATE MUST BE EXECUTABLE: if metadata says condition X produces effect Y, later scenes must not delay or soften Y when X is satisfied unless an explicit pre-existing condition explains it.

Also return optional top-level metadata:
"narrative_load": {
  "supporting_thread_used": false,
  "supporting_thread_description": "",
  "main_causal_rule": "",
  "committed_state_constraints": [""]
}
"""
).strip()

PAIRWISE_SYSTEM = nl.PAIRWISE_SYSTEM

SELECTED = [
    cohort.FIXTURES[0],
    cohort.FIXTURES[2],
    cohort.FIXTURES[3],
]


def make_spec(fixture: dict) -> StorySpec:
    family = fixture["family"]
    return StorySpec(
        title_hint=None,
        age_min=4,
        age_max=4,
        language="tr",
        target_words=500,
        narrative_family=family,
        reading_mode="READ_ALOUD",
        relative_length_class="STANDARD",
        protagonist="Deniz, 4 yaşında; meraklı ama yaşına uygun biçimde somut gözlem ve basit eylemlerle ilerler.",
        setting="Premise içinde verilen gündelik ortam; yalnız mevcut nesne ve koşulları kullan.",
        theme="Merak, dikkat ve doğal çocuk ajansı; ders veya slogan olmadan.",
        premise=fixture["premise"],
        constraints=[
            "Doğal Türkçe ve yetişkin tarafından sesli okumaya uygun ritim.",
            "Yeni named character, kalıcı canon, ilişki veya önemli eşya icat etme.",
            "Ana problemi yetişkin çözmesin.",
            "Hikâyeyi sırf kelime sayısı için uzatma.",
            "Kurulan neden-sonuç kuralını ve tamamlanmış eylem/eşya durumlarını koru.",
        ],
    )


def plan(key: str, spec: StorySpec, system: str, seed: int) -> tuple[dict, dict]:
    brief = build_labeled_brief(spec)
    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=key,
        model=ARCHITECT_MODEL,
        system_prompt=system,
        user_prompt="Create the story architecture.\n\nSTORY BRIEF\n" + brief,
        temperature=0.2,
        max_tokens=None,
        seed=seed,
        request_class="story_plan",
    )
    errors = whole.validate_plan(parsed, spec)
    if errors:
        raise RuntimeError("PLAN_INVALID:" + ",".join(errors))
    return parsed, {
        "parse_failures": failures,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
    }


def write(key: str, spec: StorySpec, plan_obj: dict, seed: int) -> tuple[dict, dict]:
    brief = build_labeled_brief(spec)
    extra = plan_obj.get("narrative_load")
    user = (
        "STORY BRIEF\n"
        + brief
        + "\n\nIMMUTABLE STORY CONTRACT\n"
        + json.dumps(plan_obj["story_contract"], ensure_ascii=False, indent=2)
        + "\n\nDYNAMIC SCENE GRAPH\n"
        + json.dumps(plan_obj["scenes"], ensure_ascii=False, indent=2)
    )
    if isinstance(extra, dict):
        user += "\n\nNARRATIVE LOAD METADATA\n" + json.dumps(extra, ensure_ascii=False, indent=2)
    user += (
        "\n\nTARGET TOTAL WORDS: 500 (SOFT)."
        "\nQuality, causality, age fit and natural completion are more important than hitting the number."
        "\nDo not invent new events merely to reach length."
        "\nTreat NARRATIVE LOAD METADATA as immutable execution constraints when present."
        "\nDo not delay an established causal effect once its stated conditions are satisfied."
        "\nDo not undo a committed item/action state."
        "\nKeep epistemic order: do not reveal decisive evidence early, and do not repeat a resolved misunderstanding."
        "\nDistinguish perceiving from responding: busy hands do not by themselves prevent hearing or seeing."
        "\nAfter resolution, move to concrete action/payoff rather than re-explaining the same fact."
    )

    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=key,
        model=WRITER_MODEL,
        system_prompt=whole.WHOLE_DRAFT_PROMPT,
        user_prompt=user,
        temperature=0.6,
        max_tokens=None,
        seed=seed,
        request_class="scene_story",
    )
    errors = whole.validate_draft(parsed, plan_obj)
    if errors:
        raise RuntimeError("DRAFT_INVALID:" + ",".join(errors))
    story = whole.assemble_story(parsed)
    return {
        "draft": parsed,
        "story": story,
        "word_count": count_words(story),
    }, {
        "parse_failures": failures,
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost": parse_cost(body).model_dump(mode="json"),
    }


def compare(key: str, fixture: dict, a: str, b: str, seed: int) -> tuple[dict, float]:
    result, meta = structured_call(
        api_key=key,
        model=JUDGE_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": fixture["family"],
            "premise": fixture["premise"],
            "story_A": a,
            "story_B": b,
        },
        seed=seed,
        max_tokens=None,
        request_class="editorial_audit",
    )
    return result, float(((meta.get("cost") or {}).get("usd")) or 0.0)


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def usd(meta: dict) -> float:
    return float(((meta.get("cost") or {}).get("usd")) or 0.0)


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()
    cases = []
    total = 0.0

    for i, fixture in enumerate(SELECTED):
        spec = make_spec(fixture)
        seed = SEED_BASE + i * 100

        baseline_plan, baseline_plan_meta = plan(key, spec, whole.ARCHITECT_PROMPT, seed)
        nl_plan, nl_plan_meta = plan(key, spec, ARCHITECT_WITH_NARRATIVE_LOAD, seed)

        baseline_story, baseline_writer_meta = write(key, spec, baseline_plan, seed + 1)
        nl_story, nl_writer_meta = write(key, spec, nl_plan, seed + 1)

        forward, c1 = compare(
            key, fixture, baseline_story["story"], nl_story["story"], seed + 2
        )
        reverse, c2 = compare(
            key, fixture, nl_story["story"], baseline_story["story"], seed + 3
        )

        fw = normalize(forward.get("winner"), "baseline_architect", "narrative_load_architect")
        rv = normalize(reverse.get("winner"), "narrative_load_architect", "baseline_architect")
        if fw == rv:
            consensus = fw
        elif fw == "TIE" and rv != "TIE":
            consensus = rv
        elif rv == "TIE" and fw != "TIE":
            consensus = fw
        else:
            consensus = "INCONCLUSIVE"

        case_cost = (
            usd(baseline_plan_meta)
            + usd(nl_plan_meta)
            + usd(baseline_writer_meta)
            + usd(nl_writer_meta)
            + c1
            + c2
        )
        total += case_cost

        cases.append({
            "family": fixture["family"],
            "premise": fixture["premise"],
            "baseline": {
                "plan": baseline_plan,
                "plan_meta": baseline_plan_meta,
                "story": baseline_story,
                "writer_meta": baseline_writer_meta,
            },
            "narrative_load": {
                "plan": nl_plan,
                "plan_meta": nl_plan_meta,
                "story": nl_story,
                "writer_meta": nl_writer_meta,
            },
            "word_delta": nl_story["word_count"] - baseline_story["word_count"],
            "normalized_winners": {
                "forward": fw,
                "reverse": rv,
                "consensus": consensus,
            },
            "pairwise_forward": forward,
            "pairwise_reverse": reverse,
            "cost_usd": case_cost,
        })

    wins = {
        "baseline_architect": 0,
        "narrative_load_architect": 0,
        "TIE": 0,
        "INCONCLUSIVE": 0,
    }
    summary = []
    for case in cases:
        consensus = case["normalized_winners"]["consensus"]
        wins[consensus] = wins.get(consensus, 0) + 1
        meta = case["narrative_load"]["plan"].get("narrative_load") or {}
        summary.append({
            "family": case["family"],
            "baseline_scenes": len(case["baseline"]["plan"]["scenes"]),
            "narrative_load_scenes": len(case["narrative_load"]["plan"]["scenes"]),
            "baseline_beats": sum(len(x.get("beats") or []) for x in case["baseline"]["plan"]["scenes"]),
            "narrative_load_beats": sum(len(x.get("beats") or []) for x in case["narrative_load"]["plan"]["scenes"]),
            "supporting_thread_used": meta.get("supporting_thread_used"),
            "baseline_words": case["baseline"]["story"]["word_count"],
            "narrative_load_words": case["narrative_load"]["story"]["word_count"],
            "word_delta": case["word_delta"],
            "forward": case["normalized_winners"]["forward"],
            "reverse": case["normalized_winners"]["reverse"],
            "consensus": consensus,
        })

    result = {
        "experiment": "story-v5-existing-architect-narrative-load-integration-v2",
        "goal": "fold narrative-load contract into the existing Narrative Architect without a mandatory extra model hop",
        "architect_model": ARCHITECT_MODEL,
        "writer_model": WRITER_MODEL,
        "judge_model": JUDGE_MODEL,
        "exact_age": 4,
        "target_words": 500,
        "fixtures": len(cases),
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": round(sum(c["word_delta"] for c in cases) / len(cases), 2),
        "cases": cases,
        "total_cost_usd": round(total, 6),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-existing-architect-narrative-load-integration")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for case in cases:
        family = case["family"]
        (out / f"{family}-baseline.txt").write_text(
            case["baseline"]["story"]["story"] + "\n", encoding="utf-8"
        )
        (out / f"{family}-narrative-load.txt").write_text(
            case["narrative_load"]["story"]["story"] + "\n", encoding="utf-8"
        )

    print(json.dumps({
        "summary": summary,
        "consensus_wins": wins,
        "mean_word_delta": result["mean_word_delta"],
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
