from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import call_openrouter, count_words, parse_cost, parse_usage

WRITER_MODEL = "anthropic/claude-sonnet-5"
HOSTILE_EDITOR_MODEL = "anthropic/claude-sonnet-5"
FINAL_AUDITOR_MODEL = "openai/gpt-5.6-sol"
MIN_WORDS = 375
MAX_WORDS = 625
SOFT_BUDGET_USD = 0.102

DRAFT_SYSTEM = r"""
Sen profesyonel bir Türk çocuk kitabı yazarısın.
4 yaşındaki bir çocuğa yetişkin tarafından sesli okunacak, yaklaşık 450-550 kelimelik
özgün ve doğal Türkçe bir hikâye yaz.

Bu bir benchmark, fen dersi, bilimsel muhakeme testi veya güvenlik kontrol listesi değildir.
Okuyucu bunların hiçbirini hissetmemeli.

Öncelikler:
- Anadili Türkçe bir çocuk kitabı yazarı gibi doğal, sıcak ve akıcı dil.
- Çocuğun yaşıyla uyumlu kısa, canlı, bazen dağınık ama inandırıcı konuşmalar.
- Yetişkin karakter öğretmen/sınav görevlisi gibi davranmasın.
- Çocuğa yetişkin bilimsel muhakemesi, epistemik slogan veya ahlak dersi söyletme.
- Checklist gibi ipucu sıralama, yapay ölçüm prop'u, deney düzeneği veya açıklama blokları kullanma.
- Duyusal ayrıntı, küçük mizah, merak ve kişilik olsun.
- Güvenlik sınırlarını boilerplate olarak anlatma; doğal davranışın içinde göster.
- Sonunda mesajı açıklama, özet çıkarma.

Başlangıç:
- Deniz 4 yaşında.
- Annesiyle birlikte ara sıra küçük bir gölet ve sazlıkların bulunduğu halka açık bir doğa bahçesine gidiyor.
- Bugün gölette önceki ziyaretlerine göre daha az su olduğunu fark ediyor.
- Son günler sıcak ve kurak geçti.
- Mevsim değişiyor; bazı yapraklar renk değiştiriyor.
- Doğa kendi halinde sürüyor.
- Deniz meraklı ama dört yaşındaki bir çocuk kadar dürtüsel ve yetişkine bağımlı.
- Korkutucu tehlike, büyülü açıklama veya riskli bağımsız eylem olmasın.

Bu bilgiler arka plandır; hepsini hikâyede tek tek kullanmak zorunda değilsin.
Yalnızca bitmiş hikâyeyi yaz. İlk satır başlık, sonra boş satır.
""".strip()

AUDIT_SYSTEM = r"""
Sen sert bir Türk çocuk kitabı editörüsün.
4 yaş için sesli okunacak bu hikâyede yayına engel kusurları bul.
Prompt uyumu veya güvenlik puanı verme. Doğal Türkçe, çocuk sesi, yetişkin diyaloğu,
LLM/checklist kokusu, didaktiklik, mantık, ritim ve fiziksel anlamı kontrol et.

SADECE kısa JSON yaz. En fazla 6 sorun:
{
  "publication_ready": false,
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {"quote":"kısa alıntı","severity":"critical|serious|moderate|minor","repair":"kısa düzeltme"}
  ],
  "rewrite_instructions": ["en fazla 4 kısa talimat"]
}
Bir critical veya serious varsa publication_ready=false.
""".strip()

REPAIR_SYSTEM = r"""
Sen profesyonel Türk çocuk kitabı yazar-editörüsün.
4 yaş için yazılmış hikâyeyi editör raporuna göre yeniden düzenle.

Yama hissi verme; gerekiyorsa paragrafı baştan yaz.
- Doğal Türkçe.
- Çocuğa yetişkin muhakemesi söyletme.
- Yetişkini öğretmen gibi konuşturma.
- Bilgi bloklarını, checklist ve LLM kokusunu temizle.
- Yapay prop/ölçüm fikstürlerini çıkar.
- Duygu ve kişiliği davranışlarla göster.
- Sonunda slogan/özet/ahlak dersi olmasın.
- 400-550 kelime hedefle.
- Temel durum: Deniz 4 yaşında, annesiyle gölete gelmiş, suyun azaldığını fark ediyor.
- Küçük gündelik ayrıntılar ekleyebilirsin; yeni büyük lore/canon uydurma.

Yalnızca tam düzeltilmiş hikâyeyi yaz; ilk satır başlık olsun.
""".strip()

FINAL_AUDIT_SYSTEM = r"""
Sen bağımsız kör son yayın denetçisisin.
4 yaş için Türkçe sesli okuma hikâyesinde yalnız yayına engel kusurları ara:
anlamsız/doğal olmayan Türkçe, yetişkin muhakemesi, didaktik diyalog,
LLM/checklist kokusu, ciddi mantık/fizik hatası.

SADECE kısa JSON yaz. En fazla 5 sorun:
{
  "publication_ready": false,
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {"quote":"kısa alıntı","severity":"critical|serious|moderate|minor","repair":"kısa düzeltme"}
  ],
  "scores": {"turkish":1,"age4":1,"read_aloud":1,"literary":1,"no_llm_smell":1},
  "summary":"tek kısa cümle"
}
Skorlar 1-10. Bir critical veya serious varsa publication_ready=false.
""".strip()


def meta(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "cost": parse_cost(body).model_dump(mode="json"),
        "usage": parse_usage(body).model_dump(mode="json"),
    }


def usd(m: dict[str, Any] | None) -> float:
    if not m:
        return 0.0
    return float(((m.get("cost") or {}).get("usd")) or 0.0)


def compact_audit(
    *,
    api_key: str,
    model: str,
    system: str,
    story: str,
    seed: int,
    max_tokens: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=system,
        user_prompt=json.dumps({"exact_age": 4, "story": story}, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=seed,
        request_class="judge",
        max_parse_attempts=1,
    )
    m = meta(body)
    m["parse_failures"] = failures
    return parsed, m


def surface_errors(story: str) -> list[str]:
    errors: list[str] = []
    wc = count_words(story)
    if wc < MIN_WORDS:
        errors.append(f"below_word_budget:{wc}<{MIN_WORDS}")
    if wc > MAX_WORDS:
        errors.append(f"above_word_budget:{wc}>{MAX_WORDS}")
    if re.search(r"[A-Za-zÇĞİÖŞÜçğıöşü]+[’']s\b", story):
        errors.append("english_possessive_artifact")
    return errors


def audit_fails(audit: dict[str, Any], story: str) -> bool:
    c = audit.get("counts") or {}
    return (
        not bool(audit.get("publication_ready"))
        or int(c.get("critical", 0) or 0) > 0
        or int(c.get("serious", 0) or 0) > 0
        or bool(surface_errors(story))
    )


def write_story(
    *,
    api_key: str,
    system: str,
    user_payload: str,
    seed: int,
    temperature: float,
) -> tuple[str, dict[str, Any]]:
    story, body, _ = call_openrouter(
        api_key=api_key,
        model=WRITER_MODEL,
        system_prompt=system,
        user_prompt=user_payload,
        temperature=temperature,
        max_tokens=None,
        seed=seed,
        request_class="scene_story",
        structured_output=False,
    )
    return story.strip(), meta(body)


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    started = time.perf_counter()
    costs: dict[str, Any] = {}
    repair_rounds: list[dict[str, Any]] = []

    story, costs["draft"] = write_story(
        api_key=api_key,
        system=DRAFT_SYSTEM,
        user_payload="Hikâyeyi şimdi yaz.",
        seed=202609261,
        temperature=0.72,
    )
    original_story = story

    audit, costs["audit_1"] = compact_audit(
        api_key=api_key,
        model=HOSTILE_EDITOR_MODEL,
        system=AUDIT_SYSTEM,
        story=story,
        seed=202609262,
        max_tokens=1800,
    )

    if audit_fails(audit, story):
        before = story
        story, costs["repair_1"] = write_story(
            api_key=api_key,
            system=REPAIR_SYSTEM,
            user_payload=json.dumps(
                {
                    "story": story,
                    "audit": audit,
                    "surface_errors": surface_errors(story),
                },
                ensure_ascii=False,
            ),
            seed=202609263,
            temperature=0.35,
        )
        repair_rounds.append({
            "round": 1,
            "before_word_count": count_words(before),
            "after_word_count": count_words(story),
            "audit": audit,
        })

    final_audit, costs["final_audit_1"] = compact_audit(
        api_key=api_key,
        model=FINAL_AUDITOR_MODEL,
        system=FINAL_AUDIT_SYSTEM,
        story=story,
        seed=202609264,
        max_tokens=2200,
    )

    running_usd = sum(usd(v) for v in costs.values())

    if audit_fails(final_audit, story) and running_usd < 0.070:
        before = story
        story, costs["repair_2"] = write_story(
            api_key=api_key,
            system=REPAIR_SYSTEM,
            user_payload=json.dumps(
                {
                    "story": story,
                    "audit": final_audit,
                    "surface_errors": surface_errors(story),
                    "instruction": "Yalnız kalan kusurları temizle; metni gereksiz yere yeniden karmaşıklaştırma.",
                },
                ensure_ascii=False,
            ),
            seed=202609265,
            temperature=0.25,
        )
        repair_rounds.append({
            "round": 2,
            "before_word_count": count_words(before),
            "after_word_count": count_words(story),
            "audit": final_audit,
        })
        final_audit, costs["final_audit_2"] = compact_audit(
            api_key=api_key,
            model=FINAL_AUDITOR_MODEL,
            system=FINAL_AUDIT_SYSTEM,
            story=story,
            seed=202609266,
            max_tokens=2200,
        )

    total_usd = sum(usd(v) for v in costs.values())
    final_surface_errors = surface_errors(story)
    counts = final_audit.get("counts") or {}
    publication_ready = (
        bool(final_audit.get("publication_ready"))
        and int(counts.get("critical", 0) or 0) == 0
        and int(counts.get("serious", 0) or 0) == 0
        and not final_surface_errors
    )

    result = {
        "protocol": "story-v5-tr-direct-sonnet-quality-loop.v3",
        "models": {
            "writer": WRITER_MODEL,
            "hostile_editor": HOSTILE_EDITOR_MODEL,
            "blind_final_auditor": FINAL_AUDITOR_MODEL,
            "repair_writer": WRITER_MODEL,
        },
        "exact_age": 4,
        "target_words": 500,
        "translation_stage": False,
        "direct_turkish": True,
        "original_story": original_story,
        "original_word_count": count_words(original_story),
        "repair_rounds": repair_rounds,
        "final_story": story,
        "final_word_count": count_words(story),
        "final_surface_errors": final_surface_errors,
        "final_audit": final_audit,
        "publication_ready": publication_ready,
        "costs": costs,
        "total_cost_usd": round(total_usd, 9),
        "soft_budget_usd": SOFT_BUDGET_USD,
        "within_soft_budget": total_usd <= SOFT_BUDGET_USD,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".story.txt").write_text(story + "\n", encoding="utf-8")
    output.with_suffix(".outcome.json").write_text(
        json.dumps(
            {
                "protocol": result["protocol"],
                "publication_ready": publication_ready,
                "original_word_count": result["original_word_count"],
                "final_word_count": result["final_word_count"],
                "repair_round_count": len(repair_rounds),
                "final_surface_errors": final_surface_errors,
                "final_audit": final_audit,
                "costs": costs,
                "total_cost_usd": result["total_cost_usd"],
                "within_soft_budget": result["within_soft_budget"],
                "elapsed_seconds": result["elapsed_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "publication_ready": publication_ready,
        "repair_round_count": len(repair_rounds),
        "original_word_count": result["original_word_count"],
        "final_word_count": result["final_word_count"],
        "final_surface_errors": final_surface_errors,
        "final_counts": final_audit.get("counts"),
        "final_scores": final_audit.get("scores"),
        "total_cost_usd": result["total_cost_usd"],
        "within_soft_budget": result["within_soft_budget"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
