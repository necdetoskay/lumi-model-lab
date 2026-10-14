#!/usr/bin/env python3
"""NOVA v0.2 cross-media corpus compiler. Canonical inputs: five JSON source records."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/nova/v0.2"
INPUT = BASE / "source_records"
DOCS = ROOT / "docs/research/nova-cross-media"
ORDER = ("01-hades", "02-outer-wilds", "03-the-witcher-3", "04-arrival", "05-12-angry-men")


def load():
    rows = []
    for slug in ORDER:
        path = INPUT / (slug + ".json")
        if path.exists():
            rows.append(json.loads(path.read_text(encoding="utf8")))
    return rows


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value.rstrip() + "\n", encoding="utf8")


def emit_jsonl(path, rows):
    write(path, "\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows))


def render(row):
    slug = row["slug"]
    path = DOCS / slug
    source_lookup = {s["source_id"]: s for s in row["sources"]}
    def cite(ids):
        return ", ".join("[" + sid + "](" + source_lookup[sid]["url"] + ")" for sid in ids)

    story = ["# " + row["title"] + " — Hikâye ve tüm önemli sonuçlar",
             "", "**Kapsam:** " + row["scope"],
             "", "**Spoiler:** Bütün önemli olaylar ve final dâhil.",
             "", "**Yöntem:** Önce kaynak gözlemleri; soyut NOVA çıkarımları ikinci belgede. "
             "Uzun kaynak metni birebir kopyalanmaz.", ""]
    for beat in row["beats"]:
        story.extend(["## " + beat["beat_id"] + " · " + beat["title"], "",
                      beat["description"], "",
                      "Kaynak: " + cite(beat["source_ids"]), ""])
    story.extend(["## Kapanışın kapsamı", "", row["ending_scope"], ""])
    write(path / "STORY.md", "\n".join(story))

    ana = ["# " + row["title"] + " — NOVA anlatı mekanizması incelemesi", "",
           "**NOVA:** Başlatıcı olay → dönüm noktası → karakter seçimi → bedel → sonuç; kaynak gerçekleri ile "
           "eserden bağımsız aktarılabilir mekanizma ayrı tutulur.", ""]
    for a in row["analysis"]:
        ana.extend(["## " + a["mechanic_id"] + " · " + a["label"], "",
                    "**Anlatıdaki gözlem:** " + a["observed"], "",
                    "**Soyut mekanizma:** " + a["abstraction"], "",
                    "**LUMI için olası kullanım:** " + a["lumi_example"], "",
                    "**Koruma kuralı:** " + a["guardrail"], "",
                    "**Kanıt sahneleri:** " + ", ".join(a["beat_ids"]) + " · " + cite(a["source_ids"]), ""])
    ana.extend(["## Kanon ve kalite sınırı", "",
                "Bu mekanikler bir öneri havuzudur; hiçbir karakter, olay, teknoloji veya diyalog LUMI kanonuna taşınamaz. "
                "NOVA'nın hikâye kalitesini iyileştirdiği bu çalışmada test edilmedi.", ""])
    write(path / "NARRATIVE_ANALYSIS.md", "\n".join(ana))

    choices = ["# " + row["title"] + " — Kararlar, alternatifler ve State değişiklikleri", "",
               "Player choice ile senaryo karakterinin lineer seçimi birbirinden ayrıdır. "
               "Bir eserde seçim varsa bile alternatiflerin eksiksiz olmadığı yerler açıkça not edilir.", ""]
    for edge in row["decisions"]:
        choices.extend(["## " + edge["decision_id"] + " · " + edge["label"], "",
                        "**Tür:** " + edge["decision_kind"],
                        "", "**Ön koşul:** " + edge["precondition"], "",
                        "**Seçim:** " + edge["action"], "",
                        "**Sonuç / State değişimi:** " + edge["effect"], "",
                        "**Sınır / belirsizlik:** " + edge["scope_note"], "",
                        "Kaynak: " + cite(edge["source_ids"]), ""])
    write(path / "DECISIONS.md", "\n".join(choices))
    lines = ["# " + row["title"] + " — Kaynak ve denetim kaydı", "",
             "**Kaynak durumu:** Araştırma geçişinde web araması/sonuç okuması ile kontrol edildi; "
             "bu belge her URL için canlı HTTP 200 iddiasında bulunmaz.", ""]
    for s in row["sources"]:
        lines.extend(["- **" + s["source_id"] + "** — [" + s["publisher"] + "](" + s["url"] + "): " +
                      s["claim_scope"] + " (" + s["verification"] + ")"])
    lines.extend(["", "**Telif sınırı:** Alıntı veya transkript saklanmadı; metin kaynaklı Türkçe parafrazdır.", "",
                  "**Editoryal sınır:** İkinci bağımsız sahne-sahne kontrol yapılmadıkça yüzde yüz "
                  "olay doğruluğu iddia edilmez.", ""])
    write(path / "SOURCES.md", "\n".join(lines))


def compile_corpus():
    rows = load()
    works, beats, mechanisms, evidences, decisions, sources = [], [], [], [], [], []
    idx = ["# NOVA v0.2 — Eserler Arası Araştırma Kataloğu", "",
           "Hikâye → anlatı mekanizması → karar/State ayrımı. Sırayla işlenen kayıtlar:", ""]
    for row in rows:
        render(row)
        work_id = row["work_id"]
        works.append({
            "work_id": work_id, "title": row["title"], "medium": row["medium"], "scope": row["scope"],
            "version": "0.2.0", "status": "first_pass_sourced",
            "lumi_canon": False, "story_length_words": sum(len(b["description"].split()) for b in row["beats"]),
            "nonlinear": row["nonlinear"]
        })
        for b in row["beats"]:
            beats.append({"work_id": work_id, **b})
        for s in row["sources"]:
            sources.append({"work_id": work_id, **s})
        for m in row["analysis"]:
            mech_id = m["mechanic_id"]
            mechanisms.append({"work_id": work_id, **m, "quality_effect": "not_evaluated",
                               "lumi_canon": False, "version": "0.2.0"})
            for bid in m["beat_ids"]:
                evidences.append({"evidence_id": work_id + ":" + mech_id + ":" + bid,
                                  "work_id": work_id, "mechanic_id": mech_id, "beat_id": bid,
                                  "source_ids": m["source_ids"], "inference": True,
                                  "causal_quality_effect": "not_evaluated"})
        for d in row["decisions"]:
            decisions.append({"work_id": work_id, **d})
        slug = row["slug"]
        idx.extend(["- **" + row["title"] + "** (" + row["medium"] + ") — " +
                    str(len(row["beats"])) + " hikâye sahnesi, " +
                    str(len(row["analysis"])) + " mekanik, " +
                    str(len(row["decisions"])) + " karar/sonuç bağı: "
                    "[Hikâye](" + slug + "/STORY.md) · "
                    "[Analiz](" + slug + "/NARRATIVE_ANALYSIS.md) · "
                    "[Kararlar](" + slug + "/DECISIONS.md) · "
                    "[Kaynaklar](" + slug + "/SOURCES.md)"])
    idx.extend(["", "[Kanonik v0.2 mimari](../../nova/NOVA_v0.2_CROSS_MEDIA_CANONICAL.md) · "
                "[Eserler arası karşılaştırma](../../nova/NOVA_CROSS_MEDIA_COMPARATIVE_ANALYSIS.md) · "
                "[Kabul raporu](../../nova/NOVA_CROSS_MEDIA_QUALITY_AUDIT.md)", "",
                "7 eserler arası mekanik benzerlik/fark bağı ayrı source-linked araştırma katmanında tutulur.", ""])
    idx.extend(["", "**SGU v0.1 korpusu değiştirilmedi.** "
                "Buradaki cross-media dosyaları v0.2 araştırma katmanıdır; LUMI prod veya Story Harness'e otomatik aktarım yok.", "",
                "**Bağımsız hikâye A/B denemesi:** 0/12. Çevrimdışı veri kontrolleri "
                "hikâye kalite artışı kanıtı değildir.", ""])
    write(DOCS / "README.md", "\n".join(idx))
    for name, entries in (("works", works), ("story_beats", beats), ("mechanisms", mechanisms),
                          ("mechanic_evidence", evidences), ("decisions", decisions),
                          ("sources", sources)):
        emit_jsonl(BASE / (name + ".jsonl"), entries)
    manifest = {"schema_version": "0.2.0", "ingested_order": [r["work_id"] for r in rows],
                "counts": {"works": len(works), "story_beats": len(beats),
                           "mechanisms": len(mechanisms), "evidence_links": len(evidences),
                           "decisions": len(decisions), "sources": len(sources)},
                "quality_effect": "not_evaluated", "actual_story_trials": 0,
                "lumi_production_modified": False}
    write(BASE / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest


if __name__ == "__main__":
    print(json.dumps(compile_corpus(), ensure_ascii=False, indent=2))
