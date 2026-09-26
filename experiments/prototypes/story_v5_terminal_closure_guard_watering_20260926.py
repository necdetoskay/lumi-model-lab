from __future__ import annotations

import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from experiments.prototypes import story_v5_narrative_load_planner_20260926 as p
from experiments.prototypes.story_v5_tr_lint_copyedit_benchmark_20260925 import structured_call

SEED = 2026092720
MAX_TOKENS = 24000
FROZEN_BASELINE_RUN = 36228047493

PREMISE = (
    "Deniz bahçede Arda'ya bulduğu düzgün taşı göstermek ister ama Arda cevap vermeden eğilip uzaklaşır. "
    "Deniz onun ilgilenmediğini sanır. Biraz sonra Arda'nın devrilmek üzere olan küçük sulama kabını ayağıyla "
    "sabitlemeye çalıştığını fark eder; Deniz yanına gidip yardım eder, sonra taşı birlikte incelerler."
)

BASELINE_STORY = """# Deniz'in Taşı

Deniz bahçenin kenarında eğilmiş toprağı eşelerken elinin altında bir şey parladı. Küçük, düzgün, bir tarafı tamamen düz bir taştı bu. Deniz taşı avucuna aldı ve hemen doğruldu.

"Arda! Bak ne buldum!" diye seslendi.

Arda o anda dönüp bakmadı. Tam tersine eğildi ve birkaç adım yana kaydı, çimenlerin arasına doğru gitti. Deniz'in elindeki taşı gösterme isteği biraz söndü. Kolunu indirdi.

"İlgilenmiyor," diye düşündü Deniz.

Taşı avucunda çevirmeye başladı. Bir yüzü pürüzlüydü, öbür yüzü ise cam gibi düzdü. Deniz taşı parmaklarıyla ovuşturdu ve bir kenara oturup ona bakmaya devam etti. Arda'nın ne yaptığına pek bakmadı bile.

Biraz sonra kafasını kaldırdığında Arda'yı hâlâ aynı yerde gördü. Arda eğilmiş, ayağını uzatmış ve küçük sulama kabının kenarına bastırıyordu. Kap yana devrilmek üzereydi, içindeki su bir yandan sallanıyordu. Arda kabı ayağıyla tutmaya çalışırken elleri de kabın kulpuna uzanıyordu ama kap yine kayıyordu.

Deniz taşı cebine soktu ve Arda'nın yanına koştu.

"Tut şuradan," dedi Arda, kabın öbür tarafını göstererek.

Deniz iki eliyle kabın kenarına yapıştı. Birlikte kabı düz bir yere doğru ittiler. Kap artık sallanmıyordu.

"Neden bana bakmadın demin?" diye sordu Deniz.

Arda hâlâ kabın suyuna bakıyordu. "Kap dökülecekti," dedi. "Önce onu tutmam gerekiyordu."

Deniz bir an sessiz durdu, sonra cebindeki taşı çıkardı.

"Bak, şimdi göstereyim," dedi. "Bulduğum taş bu."

Arda elini uzattı, taşı avucuna aldı. Taşın düz yüzünü parmağıyla yokladı, sonra gözüne çok yaklaştırdı.

"Cam gibi," dedi Arda.

"Hem de bir tarafı pürüzlü," dedi Deniz, taşı geri alıp öbür yüzünü gösterdi.

İkisi taşı sırayla ellerinde çevirdiler. Güneş bahçenin üzerine düşerken taşın düz yüzünde küçük bir nokta ışıldadı. Deniz taşı biraz döndürdü, nokta kayboldu. Geri döndürünce nokta yeniden parladı.

"Bak, burda bir şey var," dedi Deniz, tırnağıyla noktayı gösterdi.

Arda taşı eline aldı, güneşe doğru kaldırdı. Nokta yine ışıldadı, sonra taş biraz dönünce söndü.

"Işık oynuyor," dedi Arda.

Deniz taşı geri aldı ve kendi elinde birkaç kez döndürdü, nokta her seferinde aynı yerde parlayıp söndü.

"Bu benim ışıklı taşım," dedi Deniz.

Arda güldü ve sulama kabına baktı. "Suyu döksek bari şuraya dökelim," dedi, kabı hafifçe eğip toprağın kuru bir köşesine su akıttı.

Deniz taşı yeniden cebine koydu, sonra elini çıkarıp taşın hâlâ orada olup olmadığını kontrol etti. Işıklı taş cepteydi, güvendeydi.

"Yarın da bakarız," dedi Deniz.

Arda başını salladı ve boş kabı yerine koydu."""

BASELINE_WORDS = 370

PAIRWISE_SYSTEM = p.PAIRWISE_SYSTEM


def render_spine(spine: list[dict]) -> str:
    return "\n".join(
        f"{i+1}. [{b.get('density','develop')}] [{b.get('function','beat')}] {b['beat']}"
        for i, b in enumerate(spine)
    )


def normalize(raw: str, a: str, b: str) -> str:
    raw = str(raw or "").upper()
    if raw == "A":
        return a
    if raw == "B":
        return b
    return "TIE"


def main() -> None:
    load_dotenv()
    key = os.environ["OPENROUTER_API_KEY"]
    started = time.perf_counter()

    plan, plan_meta = structured_call(
        api_key=key,
        model=p.PLANNER_MODEL,
        system=p.PLANNER_SYSTEM,
        payload={
            "exact_age": 4,
            "reading_mode": "READ_ALOUD",
            "nominal_target_words": 500,
            "story_family": "emotional_development",
            "premise": PREMISE,
            "constraints": {
                "quality_over_word_count": True,
                "supporting_thread_optional": True,
                "preserve_epistemic_order": True,
                "distinguish_perception_from_response": True,
                "do_not_infer_sensory_failure_from_busy_hands": True,
                "do_not_invent_physical_inability": True,
                "closure_is_terminal": True,
                "no_post_closure_action": True,
            },
        },
        seed=SEED,
        max_tokens=MAX_TOKENS,
        request_class="editorial_audit",
    )
    spine = plan.get("spine") or []
    if not (8 <= len(spine) <= 12):
        raise RuntimeError(f"planner_spine_size_invalid:{len(spine)}")

    story, body, payload = call_openrouter(
        api_key=key,
        model=p.WRITER_MODEL,
        system_prompt=p.WRITER_SYSTEM,
        user_prompt=(
            f"KONU:\n{PREMISE}\n\n"
            f"HİKÂYE OMURGASI:\n{render_spine(spine)}\n\n"
            "Bu omurgayı doğal bir çocuk hikâyesine dönüştür."
        ),
        temperature=0.72,
        max_tokens=MAX_TOKENS,
        seed=SEED + 1,
        request_class="teacher_story_medium_reasoning",
        structured_output=False,
    )

    candidate = {
        "story": story,
        "word_count": count_words(story),
        "usage": parse_usage(body).model_dump(mode="json"),
        "cost_usd": float(parse_cost(body).usd or 0.0),
        "request_payload": payload,
    }

    forward, fmeta = structured_call(
        api_key=key,
        model=p.JUDGE_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": "emotional_development",
            "premise": PREMISE,
            "story_A": BASELINE_STORY,
            "story_B": story,
        },
        seed=SEED + 2,
        max_tokens=MAX_TOKENS,
        request_class="editorial_audit",
    )
    reverse, rmeta = structured_call(
        api_key=key,
        model=p.JUDGE_MODEL,
        system=PAIRWISE_SYSTEM,
        payload={
            "exact_age": 4,
            "story_family": "emotional_development",
            "premise": PREMISE,
            "story_A": story,
            "story_B": BASELINE_STORY,
        },
        seed=SEED + 3,
        max_tokens=MAX_TOKENS,
        request_class="editorial_audit",
    )

    fw = normalize(forward.get("winner"), "frozen_baseline", "guarded_candidate")
    rv = normalize(reverse.get("winner"), "guarded_candidate", "frozen_baseline")
    if fw == rv:
        consensus = fw
    elif fw == "TIE" and rv != "TIE":
        consensus = rv
    elif rv == "TIE" and fw != "TIE":
        consensus = fw
    else:
        consensus = "INCONCLUSIVE"

    planner_cost = float(((plan_meta.get("cost") or {}).get("usd")) or 0.0)
    judge_cost = (
        float(((fmeta.get("cost") or {}).get("usd")) or 0.0)
        + float(((rmeta.get("cost") or {}).get("usd")) or 0.0)
    )

    result = {
        "experiment": "story-v5-terminal-closure-guard-watering-v1",
        "frozen_baseline_run": FROZEN_BASELINE_RUN,
        "provider_max_tokens_ceiling": MAX_TOKENS,
        "provider_ceiling_is_not_story_length_target": True,
        "exact_age": 4,
        "nominal_target_words": 500,
        "premise": PREMISE,
        "planner_output": plan,
        "baseline": {
            "story": BASELINE_STORY,
            "word_count": BASELINE_WORDS,
            "source": f"run:{FROZEN_BASELINE_RUN}",
        },
        "guarded_candidate": candidate,
        "word_delta": candidate["word_count"] - BASELINE_WORDS,
        "pairwise_forward": forward,
        "pairwise_reverse": reverse,
        "normalized_winners": {
            "forward": fw,
            "reverse": rv,
            "consensus": consensus,
        },
        "guard_contract": [
            "preserve epistemic order",
            "distinguish perception from response",
            "do not infer sensory failure from busy hands",
            "do not invent physical inability absent from premise",
            "terminal closure is the final new action",
            "no post-closure prop convergence",
        ],
        "cost_usd": {
            "planner": planner_cost,
            "writer": candidate["cost_usd"],
            "judges": judge_cost,
            "total": round(planner_cost + candidate["cost_usd"] + judge_cost, 6),
        },
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    out = Path("runs/story-v5-terminal-closure-guard-watering")
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "guarded-candidate.txt").write_text(story + "\n", encoding="utf-8")
    (out / "planned-spine.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "baseline_words": BASELINE_WORDS,
        "candidate_words": candidate["word_count"],
        "word_delta": result["word_delta"],
        "forward": fw,
        "reverse": rv,
        "consensus": consensus,
        "cost_usd": result["cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
