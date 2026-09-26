from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, parse_cost, parse_usage
from experiments.prototypes import story_spine_refined_recipe_20260926 as base
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

WRITER_REQUEST_CLASS = "teacher_story_medium_reasoning"
MAX_WRITER_ATTEMPTS = 2

def writer_call(api_key: str, user_prompt: str):
    story, body, payload = call_openrouter(
        api_key=api_key,
        model=base.WRITER_MODEL,
        system_prompt=base.WRITER_SYSTEM,
        user_prompt=user_prompt,
        temperature=0.72,
        max_tokens=None,
        seed=None,
        request_class=WRITER_REQUEST_CLASS,
        structured_output=False,
    )
    return {
        "story": story,
        "scan": base.scan(story),
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost_usd": float(parse_cost(body).usd or 0.0),
        "request_payload": payload,
    }

def main():
    load_dotenv()
    api_key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    spine_text = "\n".join(
        f"{i+1}. [{beat['density']}] {beat['beat']}"
        for i, beat in enumerate(base.STORY_SPINE)
    )
    base_user_prompt = (
        f"KONU:\n{base.PREMISE}\n\n"
        f"HİKÂYE OMURGASI:\n{spine_text}\n\n"
        "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
    )

    attempts = []
    first = writer_call(api_key, base_user_prompt)
    first["attempt"] = 1
    first["reason"] = "initial"
    attempts.append(first)

    selected = first if first["scan"]["length_pass"] else None

    if selected is None:
        words = first["scan"]["word_count"]
        retry_prompt = (
            base_user_prompt
            + "\n\nYENİ DENEME KURALI:\n"
            + f"Önceki bağımsız deneme {words} kelime çıktı ve hard 375-625 aralığını kaçırdı. "
              "Önceki metni düzeltme, uzatma veya kopyalama. Aynı konu ve aynı omurgadan sıfırdan yeni bir hikâye yaz. "
              "Yeni olay/canon ekleme. Bu yeni draft 375 kelimenin altında bitmemeli; doğal hedef yine 475-525 kelimedir."
        )
        second = writer_call(api_key, retry_prompt)
        second["attempt"] = 2
        second["reason"] = "fresh_regeneration_after_hard_length_failure"
        attempts.append(second)
        if second["scan"]["length_pass"]:
            selected = second

    writer_cost = sum(item["cost_usd"] for item in attempts)

    result = {
        "experiment": "story-writer-bounded-regeneration-v1",
        "premise": base.PREMISE,
        "story_spine": base.STORY_SPINE,
        "writer_policy": {
            "request_class": WRITER_REQUEST_CLASS,
            "reasoning_effort": "medium",
            "provider_token_cap": None,
            "max_attempts": MAX_WRITER_ATTEMPTS,
            "retry_trigger": "hard_length_failure_only",
            "retry_mode": "fresh_regeneration_not_expansion",
            "selection": "first_hard_length_pass",
        },
        "writer_attempts": attempts,
        "selected_attempt": selected["attempt"] if selected else None,
        "writer_hard_pass": selected is not None,
        "editor_called": False,
        "final_acceptance_called": False,
        "publication_ready": False,
        "cost_usd": {"writer_total": writer_cost},
    }

    if selected is not None:
        draft = selected["story"]
        before = selected["scan"]
        edit, edit_meta = structured_call(
            api_key=api_key,
            model=base.EDITOR_MODEL,
            system=base.EDITOR_SYSTEM,
            payload={
                "exact_age": 4,
                "target_words": 500,
                "preferred_range": [475, 525],
                "hard_range": [375, 625],
                "story_spine": base.STORY_SPINE,
                "deterministic_scan": before,
                "story": draft,
            },
            seed=202610121,
            max_tokens=None,
            request_class="editorial_audit",
        )
        final_story, applied, skipped = base.apply_repairs(
            draft, edit.get("repairs") or []
        )
        after = base.scan(final_story)

        final_audit, final_meta = structured_call(
            api_key=api_key,
            model=base.FINAL_JUDGE_MODEL,
            system=base.FINAL_SYSTEM,
            payload={
                "exact_age": 4,
                "hard_range": [375, 625],
                "preferred_range": [475, 525],
                "story_spine": base.STORY_SPINE,
                "story": final_story,
            },
            seed=202610122,
            max_tokens=None,
            request_class="editorial_audit",
        )
        counts = final_audit.get("counts") or {}
        publication_ready = (
            after["length_pass"]
            and int(counts.get("critical", 0) or 0) == 0
            and int(counts.get("serious", 0) or 0) == 0
            and bool(final_audit.get("publication_ready"))
        )

        editor_cost = float(((edit_meta.get("cost") or {}).get("usd")) or 0)
        final_cost = float(((final_meta.get("cost") or {}).get("usd")) or 0)
        result.update({
            "editor_called": True,
            "final_acceptance_called": True,
            "selected_draft": draft,
            "selected_draft_scan": before,
            "editor_repairs": edit.get("repairs") or [],
            "applied_repairs": applied,
            "skipped_repairs": skipped,
            "final_story": final_story,
            "final_scan": after,
            "final_acceptance": final_audit,
            "publication_ready": publication_ready,
        })
        result["cost_usd"].update({
            "editor": editor_cost,
            "final_acceptance": final_cost,
        })

    result["cost_usd"]["total"] = sum(result["cost_usd"].values())
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)

    out = Path("runs/story-writer-bounded-regeneration")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for attempt in attempts:
        (out / f"attempt-{attempt['attempt']}.txt").write_text(
            attempt["story"] + "\n", encoding="utf-8"
        )
    if selected is not None:
        (out / "final.txt").write_text(
            result["final_story"] + "\n", encoding="utf-8"
        )

    print(json.dumps({
        "attempt_word_counts": [a["scan"]["word_count"] for a in attempts],
        "attempt_hard_pass": [a["scan"]["length_pass"] for a in attempts],
        "attempt_preferred_pass": [a["scan"]["preferred_length_pass"] for a in attempts],
        "selected_attempt": result["selected_attempt"],
        "final_words": (result.get("final_scan") or {}).get("word_count"),
        "publication_ready": result["publication_ready"],
        "cost_usd": result["cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
