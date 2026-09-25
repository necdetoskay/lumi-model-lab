from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import call_openrouter, count_words, parse_cost, parse_usage

WRITER_MODEL = "anthropic/claude-sonnet-5"
FINAL_AUDITOR_MODEL = "openai/gpt-5.6-sol"

DRAFT_SYSTEM = r"""
Sen profesyonel bir Türk çocuk kitabı yazarısın.

4 yaşındaki bir çocuğa bir yetişkin tarafından sesli okunacak, yaklaşık 500 kelimelik
özgün bir Türkçe hikâye yaz.

Bu bir benchmark, ders, deney, bilimsel muhakeme testi veya güvenlik kontrol listesi DEĞİLDİR.
Okuyucuya bunların hiçbirini hissettirme.

Öncelikler:
- Doğal, yaşayan, anadili Türkçe bir çocuk kitabı dili.
- Kısa ama tekdüze olmayan cümleler.
- Çocuğun yaşıyla uyumlu merak, duygu ve konuşma.
- Karakterlerin işlev değil insan gibi hissettirmesi.
- Somut duyular, küçük şaşırtıcı ayrıntılar, sıcaklık ve kişilik.
- Hikâyenin doğal akışı; gerekli gerçekleri checklist gibi sıralama.
- Bilimsel sonucu çocuğun ağzından yetişkin diliyle söyletme.
- Ebeveyni öğretmen veya sınav görevlisi gibi konuşturma.
- Güvenlik sınırlarını görünür boilerplate cümleleriyle tekrar etme.
- Yapay ölçüm araçları, test fikstürleri veya sırf kanıt olsun diye yerleştirilmiş prop kullanma.
- Belirsizlik varsa doğal davranış ve merakla göster; "henüz her şeyi bilmiyoruz" gibi yetişkin epistemik sloganları kullanma.
- Sonunda ahlak dersi veya özet çıkarma.

Başlangıç dünyası:
- Ana karakter Deniz, 4 yaşında.
- Deniz annesiyle birlikte Riverside Wetland Garden benzeri halka açık küçük bir sulak alan bahçesini ara sıra ziyaret ediyor.
- Deniz bugün sığ göletin önceki ziyaretlerinden daha az su içerdiğini fark ediyor.
- Son günler sıcak ve kurak geçti.
- Mevsim değişiyor; bazı yaprakların rengi dönüyor.
- Bölgede sazlıklar ve küçük canlılar var; doğa kendi halinde sürüyor.
- Deniz meraklı ama dört yaşındaki bir çocuk kadar bağımlı ve dağınık düşünebilir.
- Hikâyede korkutucu tehlike, büyülü açıklama, vahşi yaşamı rahatsız etme veya çocuğun tek başına riskli bir işe girişmesi olmasın.
- Deniz'in merakı küçük ve nazik bir eyleme dönüşebilir; bunun nasıl olacağına sen doğal biçimde karar ver.

Önemli:
Yukarıdaki dünya bilgilerini tek tek hikâyeye sokmak zorunda değilsin. Bunlar arka plan gerçekleridir.
İyi hikâye için gereksiz olan ayrıntıları kullanma.

Yalnızca bitmiş hikâyeyi döndür:
İlk satır başlık, ardından boş satır ve hikâye.
""".strip()

AUDIT_SYSTEM = r"""
Sen Türkçe çocuk edebiyatı konusunda acımasız bir yayın editörüsün.
Metni savunma. Prompt uyumu, güvenlik veya benchmark başarısı için puan verme.
Yalnızca gerçek bir ücretli çocuk hikâyesi ürününde yayın kalitesini değerlendir.

Hedef: 4 yaş, yetişkin tarafından sesli okuma.

Özellikle ara:
- anlamsız veya fiziksel olarak tuhaf eylem
- doğal olmayan Türkçe / çeviri kokusu
- cümle düşüklüğü veya yapay sözdizimi
- 4 yaş çocuğunun ağzında yetişkin muhakemesi
- öğretmen/sınav görevlisi gibi yetişkin diyaloğu
- checklist / benchmark / LLM kokusu
- gereksiz açıklama, tekrar, özetleme
- yapay prop veya sırf ipucu olsun diye konmuş ayrıntı
- işlevsel, kişiliksiz yan karakter
- zayıf ritim, sesli okumada takılma
- didaktik mesaj, ahlak dersi
- neden-sonuçta aşırı iddia
- yaşa uygun olmayan soyutluk
- doğal olmayan kapanış

JSON dışında hiçbir şey yazma.

Şema:
{
  "publication_ready": false,
  "verdict": "YAYINA_HAZIR|EDITORYAL_DUZELTME|YENIDEN_YAZ",
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {
      "quote": "...",
      "type": "...",
      "severity": "critical|serious|moderate|minor",
      "why": "...",
      "repair": "..."
    }
  ],
  "strengths": ["..."],
  "rewrite_instructions": ["..."]
}

Kusurları ortalama puan içinde eritme. Bir tek ciddi yapay cümle bile ayrıca raporlanmalıdır.
""".strip()

REPAIR_SYSTEM = r"""
Sen profesyonel bir Türk çocuk kitabı yazar-editörüsün.
Sana 4 yaş için yazılmış bir Türkçe hikâye ve sert editoryal kusur raporu verilecek.

Görevin metni yamalamak değil; gerekiyorsa paragraf veya sahneyi yeniden yazarak
kusurları gerçekten ortadan kaldırmak.

Kurallar:
- Hikâyenin temel durumu ve ana karakteri Deniz korunsun.
- Doğal Türkçe kullan.
- 4 yaş çocuğuna yetişkin bilimsel muhakemesi söyletme.
- Yetişkini öğretmen/sınav görevlisi gibi konuşturma.
- Checklist, benchmark, güvenlik boilerplate'i ve açıklayıcı özet kokusunu sil.
- Yapay ölçüm prop'larını veya sırf kanıt için konmuş ayrıntıları doğal ayrıntılarla değiştir.
- Somut duyular, oyun, şaşkınlık, küçük duygu ve karakter kişiliği ekleyebilirsin.
- Yeni canon/lore uydurma; küçük gündelik ayrıntılar serbest.
- Metni yaklaşık 450-600 kelime aralığında tut.
- Finalde mesajı açıklama; hikâyenin kendisi taşısın.

Yalnızca tam düzeltilmiş hikâyeyi döndür. İlk satır başlık olsun.
""".strip()

FINAL_AUDIT_SYSTEM = r"""
Sen bağımsız son yayın kalite denetçisisin.
4 yaş için Türkçe, yetişkin tarafından sesli okunacak bir hikâyeyi kör biçimde değerlendir.
Önceki taslağı, önceki editör raporunu veya model kimliğini bilmiyorsun.

Aşağıdakilerden herhangi biri varsa publication_ready=false:
- critical veya serious düzeyde tek bir kusur
- bariz anlamsız cümle
- doğal olmayan Türkçe / çeviri kokusu
- belirgin LLM/checklist/benchmark hissi
- 4 yaş çocuğunun belirgin yetişkin muhakemesi
- didaktik yetişkin diyaloğu
- fiziksel/mantıksal ciddi hata

JSON dışında hiçbir şey yazma:
{
  "publication_ready": false,
  "verdict": "YAYINA_HAZIR|EDITORYAL_DUZELTME|YENIDEN_YAZ",
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {"quote":"...","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair":"..."}
  ],
  "native_turkish_score": 1,
  "age4_score": 1,
  "read_aloud_score": 1,
  "literary_score": 1,
  "llm_smell_score": 1,
  "summary": "..."
}

Skorlar 1-10. llm_smell_score için 10 = yapay zekâ kokusu yok, 1 = çok belirgin.
""".strip()


def cost_meta(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "cost": parse_cost(body).model_dump(mode="json"),
        "usage": parse_usage(body).model_dump(mode="json"),
    }


def structured_call(
    *,
    api_key: str,
    model: str,
    system: str,
    payload: dict[str, Any],
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=system,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=None,
        seed=seed,
        request_class="judge",
    )
    meta = cost_meta(body)
    meta["parse_failures"] = failures
    return parsed, meta


def usd(meta: dict[str, Any] | None) -> float:
    if not meta:
        return 0.0
    value = ((meta.get("cost") or {}).get("usd"))
    return float(value or 0.0)


def needs_repair(audit: dict[str, Any]) -> bool:
    counts = audit.get("counts") or {}
    return (
        not bool(audit.get("publication_ready"))
        or int(counts.get("critical", 0) or 0) > 0
        or int(counts.get("serious", 0) or 0) > 0
    )


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    started = time.perf_counter()

    draft, draft_body, _ = call_openrouter(
        api_key=api_key,
        model=WRITER_MODEL,
        system_prompt=DRAFT_SYSTEM,
        user_prompt="Hikâyeyi şimdi yaz.",
        temperature=0.72,
        max_tokens=None,
        seed=202609251,
        request_class="scene_story",
        structured_output=False,
    )
    draft = draft.strip()
    draft_meta = cost_meta(draft_body)

    first_audit, first_audit_meta = structured_call(
        api_key=api_key,
        model=WRITER_MODEL,
        system=AUDIT_SYSTEM,
        payload={"exact_age": 4, "story": draft},
        seed=202609252,
    )

    repaired = False
    repair_meta = None
    final_story = draft

    if needs_repair(first_audit):
        final_story, repair_body, _ = call_openrouter(
            api_key=api_key,
            model=WRITER_MODEL,
            system_prompt=REPAIR_SYSTEM,
            user_prompt=json.dumps(
                {
                    "exact_age": 4,
                    "story": draft,
                    "editorial_audit": first_audit,
                },
                ensure_ascii=False,
            ),
            temperature=0.38,
            max_tokens=None,
            seed=202609253,
            request_class="scene_story",
            structured_output=False,
        )
        final_story = final_story.strip()
        repair_meta = cost_meta(repair_body)
        repaired = True

    final_audit, final_audit_meta = structured_call(
        api_key=api_key,
        model=FINAL_AUDITOR_MODEL,
        system=FINAL_AUDIT_SYSTEM,
        payload={"exact_age": 4, "story": final_story},
        seed=202609254,
    )

    all_costs = {
        "draft": draft_meta,
        "hostile_audit": first_audit_meta,
        "repair": repair_meta,
        "blind_final_audit": final_audit_meta,
    }
    total_usd = sum(usd(m) for m in all_costs.values() if m)

    final_counts = final_audit.get("counts") or {}
    accepted = (
        bool(final_audit.get("publication_ready"))
        and int(final_counts.get("critical", 0) or 0) == 0
        and int(final_counts.get("serious", 0) or 0) == 0
    )

    result = {
        "protocol": "story-v5-tr-direct-sonnet-quality-loop.v1",
        "models": {
            "writer": WRITER_MODEL,
            "hostile_editor": WRITER_MODEL,
            "repair_writer": WRITER_MODEL if repaired else None,
            "blind_final_auditor": FINAL_AUDITOR_MODEL,
        },
        "exact_age": 4,
        "target_words": 500,
        "draft_word_count": count_words(draft),
        "final_word_count": count_words(final_story),
        "direct_turkish": True,
        "translation_stage": False,
        "draft_story": draft,
        "first_audit": first_audit,
        "repair_performed": repaired,
        "final_story": final_story,
        "final_audit": final_audit,
        "publication_ready": accepted,
        "costs": all_costs,
        "total_cost_usd": round(total_usd, 9),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output.with_suffix(".story.txt").write_text(final_story + "\n", encoding="utf-8")
    output.with_suffix(".outcome.json").write_text(
        json.dumps(
            {
                "protocol": result["protocol"],
                "publication_ready": accepted,
                "repair_performed": repaired,
                "draft_word_count": result["draft_word_count"],
                "final_word_count": result["final_word_count"],
                "first_audit_counts": first_audit.get("counts"),
                "final_audit": final_audit,
                "costs": all_costs,
                "total_cost_usd": result["total_cost_usd"],
                "elapsed_seconds": result["elapsed_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "publication_ready": accepted,
        "repair_performed": repaired,
        "draft_word_count": result["draft_word_count"],
        "final_word_count": result["final_word_count"],
        "first_audit_counts": first_audit.get("counts"),
        "final_audit_counts": final_audit.get("counts"),
        "final_scores": {
            "native_turkish": final_audit.get("native_turkish_score"),
            "age4": final_audit.get("age4_score"),
            "read_aloud": final_audit.get("read_aloud_score"),
            "literary": final_audit.get("literary_score"),
            "llm_smell": final_audit.get("llm_smell_score"),
        },
        "total_cost_usd": result["total_cost_usd"],
        "elapsed_seconds": result["elapsed_seconds"],
    }, ensure_ascii=False, indent=2), flush=True)

    # A literary FAIL is evidence, not an infrastructure failure.


if __name__ == "__main__":
    main()
