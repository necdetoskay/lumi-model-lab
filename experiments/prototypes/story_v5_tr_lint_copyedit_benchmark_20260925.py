from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.english_story_pipeline import call_structured_json_with_retry
from src.generate import call_openrouter, count_words, parse_cost, parse_usage
from src.story_failure_prompt_compiler import render_writer_negative_prompt
from src.story_voice_prompt_compiler import render_natural_author_prompt, render_positive_voice_prompt

WRITER_MODEL = "anthropic/claude-sonnet-5"
COPY_EDITOR_MODEL = "openai/gpt-5.6-sol"
FINAL_AUDITOR_MODEL = "openai/gpt-5.6-sol"
BENCHMARK_EDITOR_MODEL = "anthropic/claude-sonnet-5"

DRAFT_SYSTEM = r"""
Sen profesyonel bir Türk çocuk kitabı yazarısın.
4 yaşındaki bir çocuğa bir yetişkin tarafından sesli okunacak yaklaşık 475-525 kelimelik
özgün bir Türkçe hikâye yaz.

Bu metin doğrudan Türkçe yazılmış gibi duyulmalı. Ders, deney, reasoning benchmark,
güvenlik listesi veya AI çıktısı hissi vermemeli.

Ana ilkeler:
- Deniz gerçekten dört yaşında gibi konuşsun: kısa, canlı, bazen dağınık, meraklı.
- Anne sıcak bir insan gibi konuşsun; öğretmen/sınav görevlisi gibi çocuğun cevabını
  doğrulamasın, bilimsel sonuç çıkarmasın.
- Somut eylem yaz; "dikkatini verdi", "razı oldu", "değerlendirdi", "gözlemledi" gibi
  yetişkin/soyut anlatıcı fiillerinden kaçın.
- "gerilemiş", "bürünür" gibi yazınsal/resmî kelimeleri ancak gerçekten doğal geliyorsa kullan.
- Aynı "eskisi gibi/kadar ... değildi" veya önce/şimdi karşılaştırma kalıbını tekrarlama.
- Önceki cümlelerle çelişmemek için "ama içine değil", "sadece baktı" gibi açıklayıcı
  savunma cümleleri ekleme.
- Çocuğun hayal gücünü anne hemen düzeltmesin; mümkünse oyuna katılsın.
- Güvenlik davranışı gerekiyorsa doğal eylem içinde göster, kural metni gibi anlatma.
- Bir cümleyi sesli okuyan ebeveynin kendiliğinden yeniden ifade etmek isteyeceği
  kadar uzun veya yapay kurma.
- Finalde mesaj, ders, slogan veya "yine geliriz ve öğreniriz" tipi jenerik özet verme.
- Sıcaklık, mizah, küçük sürpriz ve Deniz'e özgü davranış olsun.
- 375 kelime hard minimumdur; güvenli üretim hedefi 475-525 kelimedir. Hikâyeyi 375 sınırına yakın bitirme.

Başlangıç dünyası:
- Deniz 4 yaşında.
- Evde en sevdiği küçük mavi oyuncak arabasını bulamıyor.
- Arabayı en son salon ile kendi oyun alanı arasında kullandığını hatırlıyor; kayıp nesnenin yeri önceden kesinleştirilmesin.
- Deniz annesiyle evin içinde arıyor ama aramayı asıl Deniz'in somut gözlemleri, küçük denemeleri ve çocukça fikirleri ilerletsin.
- Anne cevabı bilmesin, dedektif/öğretmen gibi soru listesi sormasın ve çözümü Deniz'e vermesin; oyuna ve aramaya doğal biçimde eşlik etsin.
- Arama sırasında küçük bir yanlış iz, komik bir nesne veya beklenmedik bir keşif olabilir.
- Çözüm basit fiziksel mantığa uysun; nesne açıklanamaz biçimde ortaya çıkmasın.
- Final kayıp eşyanın bulunmasıyla duygusal ders özetine dönüşmesin; Deniz'e özgü somut bir davranış veya kısa replikle bitsin.
- Korkutucu kaybolma, suçlama, ceza, tehlikeli tırmanma veya yetişkin gibi sistematik muhakeme olmasın.

Bunlar arka plan gerçekleridir. Hepsini tek tek kullanmak zorunda değilsin.
Yalnızca bitmiş hikâyeyi yaz. İlk satır başlık olsun.
""".strip()

COPY_EDIT_SYSTEM = r"""
Sen Türkçe çocuk kitabı son kopya editörüsün.
Sana tüm hikâye DEĞİL, deterministik lint'in yakaladığı kısa alıntılar ve yakın bağlamları verilecek.

Görevin:
- yalnız gerçekten sorunlu olan alıntıları düzeltmek,
- hikâyenin olayını, karakterlerini ve anlamını değiştirmemek,
- yeni sahne veya fikir eklememek,
- 4 yaş sesli okuma Türkçesini doğal hale getirmek.

SADECE JSON:
{
  "replacements": [
    {
      "old": "source_quote alanındaki metinle birebir aynı",
      "new": "lokal ve doğal düzeltme",
      "reason": "çok kısa"
    }
  ]
}

Her finding için düzeltme şart değil. Yanlış pozitifse atla.
old değeri source_quote ile birebir eşleşmeli.
""".strip()

FINAL_VETO_SYSTEM = r"""
Sen bağımsız son yayın VETO denetçisisin.
Bu bir "daha güzel nasıl yazılır" egzersizi değildir. Sadece gerçekten yayına engel olan
kusurları ara.

Hedef: 4 yaş, yetişkin tarafından Türkçe sesli okuma.

FAIL nedenleri:
- anlamsız veya fiziksel olarak ciddi biçimde tuhaf cümle
- belirgin bozuk/doğal olmayan Türkçe
- 4 yaş çocuğunun bariz yetişkin/analitik muhakemesi
- yetişkinin belirgin öğretmen/sınav görevlisi diyaloğu
- görünür checklist/benchmark/AI kalıbı
- ciddi mantık veya süreklilik problemi
- aynı yapının rahatsız edici tekrarı

Yalnız stil tercihi ("ben başka kelime seçerdim") FAIL değildir.

SADECE JSON:
{
  "publication_ready": false,
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {"quote":"birebir kısa alıntı","severity":"critical|serious|moderate|minor","why":"kısa","repair":"lokal düzeltme"}
  ],
  "scores": {"turkish":1,"age4":1,"read_aloud":1,"literary":1,"no_llm_smell":1},
  "summary":"tek cümle"
}
Bir critical veya serious varsa publication_ready=false. Sadece moderate/minor varsa
metin publication_ready=true olabilir.
""".strip()

BENCHMARK_AUDIT_SYSTEM = r"""
Gerçek bir ücretli çocuk hikâyesi uygulamasında yayınlanacak metni sert ama adil biçimde
değerlendir. Sırf kusur bulmak için kusur uydurma.

Hedef:
- tam yaş 4
- yetişkin tarafından sesli okunacak
- doğal Türkçe çocuk edebiyatı

Cümle cümle ara:
- doğal olmayan Türkçe ve register kayması
- yetişkin dili/soyut anlatıcı dili
- 4 yaş için fazla düzenli muhakeme
- öğretmen gibi yetişkin diyaloğu
- tekrar eden sözdizimsel kalıplar
- gereksiz açıklama / safety boilerplate
- fiziksel veya mantıksal tuhaflık
- LLM/checklist kokusu
- klişe veya zayıf kapanış
- sesli okumada tökezleme
- karakterin işlevsel ve kişiliksiz kalması

SADECE JSON:
{
  "verdict": "YAYINA_HAZIR|KUCUK_EDIT|CIDDI_EDIT|YENIDEN_YAZ",
  "counts": {"critical":0,"serious":0,"moderate":0,"minor":0},
  "defects": [
    {"quote":"birebir kısa alıntı","type":"...","severity":"critical|serious|moderate|minor","why":"...","repair":"..."}
  ],
  "scores": {
    "turkish_naturalness":1,
    "sentence_quality":1,
    "age4":1,
    "dialogue":1,
    "character":1,
    "flow":1,
    "read_aloud":1,
    "literary":1,
    "emotional":1,
    "originality":1,
    "no_llm_smell":1,
    "publication_readiness":1
  },
  "parent_trust_risks":["en fazla 5 gerçek risk"],
  "professional_gap":"kısa açıklama",
  "top_three_changes":["..."]
}
Skorlar 1-10. Kusur yoksa uydurma.
""".strip()

SUSPICIOUS_PATTERNS = [
    ("adult_register", re.compile(r"\b(razı oldu|dikkatini (?:yeniden |tekrar )?.{0,30}?verdi|gözlemledi|değerlendirdi|kanaat|dolayısıyla|nitekim)\b", re.I)),
    ("literary_register", re.compile(r"\b(gerilemiş|bürün(?:dü|ür|müş|mek)|teşkil|müteakip)\b", re.I)),
    ("defensive_exposition", re.compile(r"\b(ama içine değil|sadece baktı|dokunmadı,? sadece|özellikle dokunmadı)\b", re.I)),
    ("teacher_praise", re.compile(r"\b(iyi düşündün|doğru düşündün|çok iyi gözlem|güzel gözlem|işte bu yüzden)\b", re.I)),
    ("generic_closure", re.compile(r"\b(yine geliriz,? (?:ve )?gör(?:eceğiz|ürüz)|bir dahaki sefere yine bakarız|bakmaya devam edeceğiz)\b", re.I)),
    ("didactic_science", re.compile(r"\b(buharlaşıp gitti|buhar taneleri|güneş azalınca renkleri de değişiyor)\b", re.I)),
    ("adult_narrator_comment", re.compile(r"\b(hiç dertleri yokmuş gibi|sanki hiçbir şey değişmemiş gibi)\b", re.I)),
    ("age4_abstract_phrase", re.compile(r"\bsonbahar yaprağım oldu\b", re.I)),
    ("cliche_happy_ending", re.compile(r"\byüzünde kocaman bir gülümseme vardı\b", re.I)),
]

def meta(body: dict[str, Any]) -> dict[str, Any]:
    return {
        "cost": parse_cost(body).model_dump(mode="json"),
        "usage": parse_usage(body).model_dump(mode="json"),
    }

def usd(m: dict[str, Any] | None) -> float:
    if not m:
        return 0.0
    return float(((m.get("cost") or {}).get("usd")) or 0.0)

def structured_call(*, api_key: str, model: str, system: str, payload: Any, seed: int, max_tokens: int, request_class: str = "judge") -> tuple[dict[str, Any], dict[str, Any]]:
    parsed, body, _, failures = call_structured_json_with_retry(
        api_key=api_key,
        model=model,
        system_prompt=system,
        user_prompt=json.dumps(payload, ensure_ascii=False),
        temperature=0.0,
        max_tokens=max_tokens,
        seed=seed,
        request_class=request_class,
        max_parse_attempts=1,
    )
    m = meta(body)
    m["parse_failures"] = failures
    return parsed, m

def write_story(*, api_key: str) -> tuple[str, dict[str, Any]]:
    failure_constraints = render_writer_negative_prompt(
        language="tr",
        exact_age=4,
        story_type="adventure",
        target_words=500,
        max_rules=12,
    )
    positive_voice = render_positive_voice_prompt(language="tr", exact_age=4, max_rules=8)
    natural_author = render_natural_author_prompt(language="tr", max_rules=10)
    writer_system = DRAFT_SYSTEM + "\n\n" + positive_voice + "\n\n" + natural_author + "\n\n" + failure_constraints
    story, body, _ = call_openrouter(
        api_key=api_key,
        model=WRITER_MODEL,
        system_prompt=writer_system,
        user_prompt="Hikâyeyi şimdi yaz.",
        temperature=0.72,
        max_tokens=None,
        seed=202609271,
        request_class="scene_story",
        structured_output=False,
    )
    return story.strip(), meta(body)

def split_sentences(text: str) -> list[str]:
    body = text.split("\n\n", 1)[-1]
    chunks = re.split(r"(?<=[.!?])(?:[”\"])?\s+(?=[A-ZÇĞİÖŞÜ“\"])", body)
    return [x.strip() for x in chunks if x.strip()]

def nearby_context(story: str, quote: str, radius: int = 140) -> str:
    i = story.find(quote)
    if i < 0:
        return quote
    return story[max(0, i-radius):min(len(story), i+len(quote)+radius)].strip()

def deterministic_lint(story: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(kind: str, quote: str, why: str) -> None:
        key = (kind, quote)
        if not quote or key in seen:
            return
        seen.add(key)
        findings.append({
            "kind": kind,
            "source_quote": quote,
            "why": why,
            "context": nearby_context(story, quote),
        })

    for kind, pattern in SUSPICIOUS_PATTERNS:
        for m in pattern.finditer(story):
            add(kind, m.group(0), f"Şüpheli çocuk-edebiyatı register/pattern: {kind}")

    sentences = split_sentences(story)
    for s in sentences:
        wc = count_words(s)
        if wc >= 27:
            add("long_readaloud_sentence", s, f"Sesli okuma için uzun cümle: {wc} kelime")

    eskisi = [s for s in sentences if re.search(r"\beskisi\b|\bher zamanki\b|\bönceki\b", s, re.I)]
    neg_compare = [s for s in eskisi if re.search(r"\bdeğil(?:di|miş|se)?\b|\bkadar\b|\bgibi\b", s, re.I)]
    if len(neg_compare) >= 2:
        for s in neg_compare:
            add("repeated_before_after_structure", s, "Aynı önce/şimdi karşılaştırma yapısı birden çok kez kullanılmış")

    normalized_starts: list[tuple[str, str]] = []
    for s in sentences:
        words = re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü']+", s.casefold())
        if len(words) >= 3:
            normalized_starts.append((" ".join(words[:3]), s))
    counts = Counter(x[0] for x in normalized_starts)
    for start, s in normalized_starts:
        if counts[start] >= 3:
            add("repeated_sentence_opening", s, f"Aynı üç kelimelik cümle başlangıcı {counts[start]} kez kullanılmış")

    for pattern, kind, why in [
        (r"\baya(?:ğını|klarını) uzattı\b", "physical_action_check", "Fiziksel hareket kulağa yapay gelebilir; bağlam kontrol edilmeli"),
        (r"\b(?:bu|o) cevaba\b", "adult_narrator_register", "Çocuk anlatısında soyut cevap-değerlendirme dili olabilir"),
        (r"\bikna ol", "adult_narrator_register", "Çocuk anlatısında yetişkin zihinsel durum ifadesi olabilir"),
    ]:
        for m in re.finditer(pattern, story, re.I):
            add(kind, m.group(0), why)

    return findings

def apply_replacements(story: str, replacements: list[dict[str, Any]]) -> tuple[str, list[dict[str, str]]]:
    out = story
    applied: list[dict[str, str]] = []
    for r in replacements:
        old = str(r.get("old") or "")
        new = str(r.get("new") or "")
        if old and new and old in out and old != new:
            out = out.replace(old, new, 1)
            applied.append({"old": old, "new": new})
    return out, applied

def local_copy_edit(*, api_key: str, story: str, findings: list[dict[str, Any]], seed: int) -> tuple[str, dict[str, Any], list[dict[str, str]]]:
    if not findings:
        return story, {"cost":{"usd":0.0},"usage":{},"skipped":True}, []
    compact = [
        {
            "kind": f["kind"],
            "source_quote": f["source_quote"],
            "why": f["why"],
            "context": f["context"],
        }
        for f in findings[:14]
    ]
    parsed, m = structured_call(
        api_key=api_key,
        model=COPY_EDITOR_MODEL,
        system=COPY_EDIT_SYSTEM,
        payload={"exact_age":4, "findings":compact},
        seed=seed,
        max_tokens=1200,
    )
    edited, applied = apply_replacements(story, parsed.get("replacements") or [])
    return edited, m, applied

def final_veto(*, api_key: str, story: str, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    return structured_call(
        api_key=api_key,
        model=FINAL_AUDITOR_MODEL,
        system=FINAL_VETO_SYSTEM,
        payload={"exact_age":4,"story":story},
        seed=seed,
        max_tokens=1600,
    )

def benchmark_audit(*, api_key: str, story: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return structured_call(
        api_key=api_key,
        model=BENCHMARK_EDITOR_MODEL,
        system=BENCHMARK_AUDIT_SYSTEM,
        payload={"exact_age":4,"story":story},
        seed=202609276,
        max_tokens=3500,
        request_class="editorial_audit",
    )

def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runs/story_v5_prototype/result.json")
    args = parser.parse_args()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required")

    marker_path = Path("experiments/triggers/story-v5-tr-lint-copyedit-benchmark-20260925.json")
    marker = json.loads(marker_path.read_text(encoding="utf-8")) if marker_path.exists() else {}
    if marker.get("mode") == "AUDIT_ONLY":
        story_path = Path(str(marker["story_path"]))
        story = story_path.read_text(encoding="utf-8").strip()
        started = time.perf_counter()
        audit, audit_meta = benchmark_audit(api_key=api_key, story=story)
        result = {
            "protocol": "story-v5-tr-sonnet-lint-local-edit-v1-audit-only",
            "story_source": str(story_path),
            "final_story": story,
            "final_word_count": count_words(story),
            "external_benchmark_audit": audit,
            "external_benchmark_cost": audit_meta,
            "evaluation_cost_usd": round(usd(audit_meta), 9),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        output.with_suffix(".story.txt").write_text(story + "\n", encoding="utf-8")
        output.with_suffix(".outcome.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "external_verdict": audit.get("verdict"),
            "external_counts": audit.get("counts"),
            "external_scores": audit.get("scores"),
            "evaluation_cost_usd": result["evaluation_cost_usd"],
            "elapsed_seconds": result["elapsed_seconds"],
        }, ensure_ascii=False, indent=2), flush=True)
        return

    started = time.perf_counter()
    production_costs: dict[str, Any] = {}

    draft, production_costs["draft"] = write_story(api_key=api_key)
    lint_before = deterministic_lint(draft)

    edited, production_costs["copy_edit_1"], applied_1 = local_copy_edit(
        api_key=api_key,
        story=draft,
        findings=lint_before,
        seed=202609272,
    )
    lint_after_copy = deterministic_lint(edited)

    audit_1, production_costs["final_veto_1"] = final_veto(
        api_key=api_key,
        story=edited,
        seed=202609273,
    )

    final_story = edited
    veto_repairs: list[dict[str, str]] = []
    counts = audit_1.get("counts") or {}
    needs_veto_repair = (
        int(counts.get("critical",0) or 0) > 0
        or int(counts.get("serious",0) or 0) > 0
        or not bool(audit_1.get("publication_ready"))
    )

    final_audit = audit_1
    if needs_veto_repair and audit_1.get("defects"):
        defect_findings = [
            {
                "kind":"final_veto_defect",
                "source_quote":str(d.get("quote") or ""),
                "why":str(d.get("why") or d.get("repair") or ""),
                "context":nearby_context(final_story, str(d.get("quote") or "")),
            }
            for d in audit_1.get("defects") or []
            if d.get("quote")
        ]
        final_story, production_costs["copy_edit_2"], veto_repairs = local_copy_edit(
            api_key=api_key,
            story=final_story,
            findings=defect_findings,
            seed=202609274,
        )
        final_audit, production_costs["final_veto_2"] = final_veto(
            api_key=api_key,
            story=final_story,
            seed=202609275,
        )

    lint_final = deterministic_lint(final_story)
    final_counts = final_audit.get("counts") or {}
    length_ok = 375 <= count_words(final_story) <= 625
    publication_ready = (
        bool(final_audit.get("publication_ready"))
        and int(final_counts.get("critical",0) or 0) == 0
        and int(final_counts.get("serious",0) or 0) == 0
        and length_ok
    )

    production_usd = sum(usd(v) for v in production_costs.values())

    external_audit_error = None
    try:
        external_audit, external_meta = benchmark_audit(api_key=api_key, story=final_story)
    except Exception as exc:
        external_audit = {
            "verdict": "AUDIT_ERROR",
            "counts": {},
            "defects": [],
            "scores": {},
            "parent_trust_risks": [],
            "professional_gap": "",
            "top_three_changes": [],
        }
        external_meta = {"cost": {"usd": 0.0}, "usage": {}, "failed": True}
        external_audit_error = f"{type(exc).__name__}: {exc}"
    evaluation_usd = usd(external_meta)

    result = {
        "protocol":"story-v5-tr-sonnet-lint-local-edit-v1",
        "models":{
            "writer":WRITER_MODEL,
            "copy_editor":COPY_EDITOR_MODEL,
            "final_veto":FINAL_AUDITOR_MODEL,
            "external_benchmark_editor":BENCHMARK_EDITOR_MODEL,
        },
        "exact_age":4,
        "target_words":500,
        "translation_stage":False,
        "full_rewrite_after_draft":False,
        "draft_story":draft,
        "draft_word_count":count_words(draft),
        "lint_before":lint_before,
        "copy_edit_1_applied":applied_1,
        "lint_after_copy":lint_after_copy,
        "final_veto_initial":audit_1,
        "copy_edit_2_applied":veto_repairs,
        "final_story":final_story,
        "final_word_count":count_words(final_story),
        "length_gate":{"min_words":375,"max_words":625,"passed":length_ok},
        "lint_final":lint_final,
        "final_veto":final_audit,
        "publication_ready":publication_ready,
        "production_costs":production_costs,
        "production_cost_usd":round(production_usd,9),
        "external_benchmark_audit":external_audit,
        "external_benchmark_cost":external_meta,
        "external_benchmark_error":external_audit_error,
        "evaluation_cost_usd":round(evaluation_usd,9),
        "experiment_total_cost_usd":round(production_usd+evaluation_usd,9),
        "elapsed_seconds":round(time.perf_counter()-started,3),
    }

    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    output.with_suffix(".story.txt").write_text(final_story+"\n",encoding="utf-8")
    output.with_suffix(".outcome.json").write_text(
        json.dumps({
            "protocol":result["protocol"],
            "publication_ready":publication_ready,
            "draft_word_count":result["draft_word_count"],
            "final_word_count":result["final_word_count"],
            "lint_before_count":len(lint_before),
            "copy_edit_1_count":len(applied_1),
            "lint_final_count":len(lint_final),
            "final_veto":final_audit,
            "external_benchmark_audit":external_audit,
            "production_cost_usd":result["production_cost_usd"],
            "evaluation_cost_usd":result["evaluation_cost_usd"],
            "experiment_total_cost_usd":result["experiment_total_cost_usd"],
        },ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "publication_ready":publication_ready,
        "draft_word_count":result["draft_word_count"],
        "final_word_count":result["final_word_count"],
        "lint_before_count":len(lint_before),
        "copy_edit_1_count":len(applied_1),
        "lint_final_count":len(lint_final),
        "final_veto_counts":final_audit.get("counts"),
        "final_veto_scores":final_audit.get("scores"),
        "external_verdict":external_audit.get("verdict"),
        "external_counts":external_audit.get("counts"),
        "external_scores":external_audit.get("scores"),
        "production_cost_usd":result["production_cost_usd"],
        "evaluation_cost_usd":result["evaluation_cost_usd"],
        "experiment_total_cost_usd":result["experiment_total_cost_usd"],
        "elapsed_seconds":result["elapsed_seconds"],
    },ensure_ascii=False,indent=2),flush=True)

if __name__ == "__main__":
    main()
