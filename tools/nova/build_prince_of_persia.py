#!/usr/bin/env python3
"""NOVA PoP v0.3 offline compiler. Source records are canonical; JSONL/Markdown derived."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"data/nova/v0.3"
SRC=BASE/"source_records"
DOCS=ROOT/"docs/research/prince-of-persia"

def raw(name):
    return json.loads((SRC/name).read_text(encoding="utf8"))

def jsonl(name, rows):
    p=BASE/(name+".jsonl")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text("".join(json.dumps(r,ensure_ascii=False,sort_keys=True)+"\n" for r in rows),encoding="utf8")

def doc(path, value):
    p=DOCS/path
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(value.rstrip()+"\n",encoding="utf8")

def compile_data():
    c=raw("prince_of_persia_catalog.json")
    t=raw("warrior_within_temporal.json")
    m=raw("prince_mechanics.json")
    works=c["works"]; sources=c["sources"]
    bysource={x["source_id"]:x for x in sources}
    event={e["event_id"]:e for e in t["events"]}
    beats=[]
    for w in works:
        for i,b in enumerate(w["beats_tr"],1):
            beats.append({"beat_id":w["work_id"]+":B"+str(i),"work_id":w["work_id"],"ordinal":i,
                          "observed_event_tr":b,"source_ids":w["source_ids"],
                          "editorial_stage":"sourced_first_pass"})
    bybeat={b["beat_id"]:b for b in beats}
    evidence=[]
    for x in m["mechanics"]:
        for key in x["evidence_anchors"]:
            if key in event:
                e=event[key];refs=e["source_ids"];wid=t["work_id"];obs=e["observed_fact_tr"]
            else:
                b=bybeat[key];refs=b["source_ids"];wid=b["work_id"];obs=b["observed_event_tr"]
            evidence.append({"evidence_id":x["mechanic_id"]+":"+key,
                             "mechanic_id":x["mechanic_id"],"work_id":wid,"anchor_id":key,
                             "source_ids":refs,"observed_fact_tr":obs,
                             "mechanism_inference":True,"quality_effect":"not_evaluated",
                             "lumi_canon":False})
    cross=[{"from_id":x["mechanic_id"],"to_existing_id":old,
            "relation":"related_research_not_equivalent","quality_effect":"not_evaluated"}
           for x in m["mechanics"] for old in x["related_cm_ids"]]
    data={
        "works":works, "supplementary_releases":c["secondary_releases"],"sources":sources,
        "story_beats":beats,"temporal_events":t["events"],"temporal_locations":t["locations"],
        "temporal_edges":t["edges"],"ending_branches":t["ending_branches"],
        "mechanics":m["mechanics"],"mechanic_evidence":evidence,"cross_corpus_links":cross,
    }
    for k,v in data.items():jsonl(k,v)
    jsonl("quality_evaluations",[])
    jsonl("lumi_usage_history",[])
    header=("# NOVA Prince of Persia v0.3 — Araştırma Kataloğu\n\n"
            "Korpus özgün Türkçe kaynak parafrazlarından oluşur. Bütün kayıtlar ilk editoryal geçiştir. "
            "Yayınlanmış oyun, farklı platform senaryosu, DLC, VR, port, remake, film ve iptal edilmiş yapım birbirinden ayrılır. "
            "Hikâye üretimi veya LUMI entegrasyonu yapılmadı.\n\n")
    header+="## İncelenen ayrı hikâye/oyun birimleri\n\n| Eser | Yıl | Süreklilik | Analiz |\n|---|---:|---|---|\n"
    for w in works:
        slug=w["work_id"].lower()
        header+="- " if False else ""
        header+="| ["+w["title"]+"](works/"+slug+".md) | "+str(w["year"])+" | "+w["family"]+" | "+w["status"]+" |\n"
        sub="# "+w["title"]+" ("+str(w["year"])+") — NOVA kaynaklı ilk anlatı\n\n"
        sub+="**Süreklilik:** "+w["family"]+". **Durum:** "+w["status"]+". Ana hikâyeyi ikinci bir editör henüz bağımsız doğrulamadı.\n\n"
        sub+="## Hikâye\n\n"+w["story_overview_tr"]+"\n\n## Olay akışı\n\n"
        sub+="\n".join(str(i)+". "+s for i,s in enumerate(w["beats_tr"],1))+"\n\n"
        sub+="## Anlatı işaretleri\n\n"+", ".join(w["mechanic_tags"])+"\n\n## Kaynaklar\n\n"
        sub+="\n".join("- ["+bysource[s]["publisher"]+"]("+bysource[s]["url"]+")" for s in w["source_ids"])+"\n\n"
        sub+="Bu eserin mekanik çıkarımları yorumdur; kaynak evren LUMI kanonu değildir.\n"
        doc("works/"+slug+".md",sub)
    header+="\n## Yeniden yayımlar, mobil oyunlar, uyarlamalar ve iptal edilenler\n\n"
    for x in c["secondary_releases"]:
        header+="- **"+x["title"]+" ("+str(x["year"])+")** — "+x["class"]+": "+x["note_tr"]+"\n"
    header+="\n## Derinlemesine araştırma\n\n"
    header+="- [Warrior Within çift geçişli olay haritası](WARRIOR_WITHIN_TIME_MODEL.md)\n"
    header+="- [7 tarihsel mekânın zaman durumu](TEMPORAL_LOCATIONS.md)\n"
    header+="- [Yeni mekanik adayları](MECHANICS_INDEX.md)\n"
    header+="- [Süreklilik koruma kuralları](CONTINUITY_FIREWALL.md)\n"
    header+="- [Doğrulama kanıtı](VALIDATION_REPORT.md)\n"
    header+="- [Kaynak listesi](SOURCES.md)\n\n"
    header+="Bütün kalite_effect alanları not_evaluated; gerçek hikâye A/B testi 0, model çağrısı 0.\n"
    doc("README.md",header)

    td="# Warrior Within — Olay zamanı, gösterim zamanı ve dünya varyantı\n\n"
    td+="İlk yolculuktaki geçmiş olayıyla Sand Wraith biçiminde yeniden görülen olay birbirinden ayrıdır. "
    td+="ISLAND_PAST ve ISLAND_PRESENT yalnız oyun içi bağıl çağ adlarıdır. Aynı zaman diliminde bulunan iki Prens örneği aynı bilgiye sahip değildir.\n\n"
    td+="## Birinci geçiş\n\n"
    td+="Prens, Dahaka'nın takipten kurtulmak için Zaman Adası'na gelir. Geçitlerle geçmişe gidip Kaileena'nın yardımıyla kuleleri açar. "
    td+="Kimliği bilinmeyen Sand Wraith'i gözler; Dahaka'nın onu öldürdüğünü sanır. Kaileena'nın Zaman İmparatoriçesi olduğunu öğrenir, "
    td+="onu geçmişte öldürerek engellemek istediği Kumlar'ın yaratılışına istemeden sebep olur. Bugüne dönünce Dahaka hâlâ peşindedir.\n\n"
    td+="## İkinci geçiş\n\n"
    td+="Prens eski asker yazısıyla öğrendiği maskeyi takıp Sand Wraith'e dönüşür. Eski kendisinin yaşadığı mekânlara yeniden gelir. "
    td+="Seyircinin gizemli figür sanarak gördüğü kişi, başka bir zamanda hareket eden Prens'in kendisidir. "
    td+="Dahaka'nın karşısına çıkılan kavşakta ilk gözlenen sonuçtan farklı olarak genç Prens yakalanır; maskeli örnek kurtulur. "
    td+="Kaileena'yı geçmişte öldürmek yerine bugüne taşır. Water Sword'un olup olmadığı iki gerçek finalin ayrımını oluşturur.\n\n"
    td+=("**ÖNEMLİ WATER SWORD KRONOLOJİSİ:** W24, tematik anlatı haritasında finalin önkoşulu olarak sona yakın numaralandırılmıştır; "
         "bu sıra zorunlu oynanış kronolojisi değildir. Dokuz sağlık yükseltmesini macera boyunca toplayan oyuncu, "
         "Water Sword'u Maskeyi takmadan önce **geçmişteki Hourglass Chamber'da** alabilir. "
         "Bu, W23'ten sonraki bugünde bulunacak bir eşya değildir. "
         "İlk geçişin bilgisi ile sonuca bağlı opsiyonel inventory State birbirinden ayrı tutulmuştur.\n\n")
    td+="## Olay haritası: oyuncunun öğrendiği sırayla\n\n"
    td+="| Olay | Sahne / somut gözlem | Çağ | Dünya varyantı | Bilgi taşıyıcısı |\n|---|---|---|---|---|\n"
    for e in t["events"]:
        td+="| "+e["event_id"]+" | "+e["label_tr"]+" — "+e["observed_fact_tr"]+" | "+e["epoch"]+" | "+e["worldline_variant"]+" | "+e["actor_version"]+" |\n"
    td+="\n## Aynı zaman kavşağındaki farklı sonuçlar\n\n"
    for key in ("SLOT_WRAITH_FIRST","SLOT_WRAITH_TOWER","SLOT_DAHAKA_INTERCEPTION","SLOT_KAILEENA_FATE"):
        group=[x for x in t["events"] if x["time_slot_id"]==key]
        td+="### "+key+"\n\n"
        for x in group:
            td+="- "+x["event_id"]+" ("+x["worldline_variant"]+"): "+x["observed_fact_tr"]+"\n"
        td+="\n"
    td+=("## Kanonik finalin çift önkoşulu\n\n"
         "Kanonik final iki ayrı nedenin birlikte sağlanmasını gerektirir: "
         "**W23** ile Kaileena bugüne getirilir; **W24** geçmişte Water Sword edinimini kaydeder. "
         "İkisi de **W26** kavşağında birleşir ve W27 üzerinden W28 kanonik devamına ulaşılır. "
         "Water Sword edinimi zorunlu olay sırası değildir; olay indeksi gerçek oyun kronolojisi gibi kullanılmaz. "
         "W25 standart bitişinden W28 kanonik devamına bağlantı kurulamaz.\n\n")
    td+="## Sonların önkoşulları\n\n"
    for b in t["ending_branches"]:
        td+="### "+b["branch_id"]+"\n\nKoşul: "+b["condition"]+". Kanonik devam: "+str(b["canonical_for_next_game"])+".\n\n"
        td+="State: "+", ".join(b["state_outcome"])+". "+b["note"]+"\n\n"
    td+="## Kaynak ve sınırlama\n\n"
    td+="[Ubisoft geliştirici retrospektifi](https://news.ubisoft.com/en-gb/article/3oAqiLg5k7GazIw5OWYTO2/prince-of-persia-creating-the-sands-of-time-trilogy) · "
    td+="[GameSpot walkthrough](https://www.gamespot.com/articles/prince-of-persia-warrior-within-walkthrough/1100-6115082/) · "
    td+="[Warrior Within olay örgüsü](https://en.wikipedia.org/wiki/Prince_of_Persia:_Warrior_Within).\n\n"
    td+="Dahaka'nın her çelişkiyi çözme algoritması kaynaktan kesin olarak çıkarılamaz; yorumlar fizik kanunu yapılmaz.\n"
    doc("WARRIOR_WITHIN_TIME_MODEL.md",td)

    loc="# Warrior Within — Geçmiş ve bugünde 7 fiziksel mekân\n\n"
    for x in t["locations"]:
        loc+="## "+x["label_tr"]+"\n\n**Geçmiş:** "+x["past_state_tr"]+"\n\n"
        loc+="**Bugün:** "+x["present_state_tr"]+"\n\n**Koruma:** "+x["guardrail_tr"]+"\n\n"
    doc("TEMPORAL_LOCATIONS.md",loc)

    mec="# NOVA Prince of Persia — 22 soyut anlatı mekaniği adayı\n\n"
    mec+="Her çıkarım, kanıt olayına bağlanır; kalite artışı veya evren kanonu iddiası yoktur.\n\n"
    for x in m["mechanics"]:
        mec+="## "+x["mechanic_id"]+" — "+x["label_tr"]+"\n\n"
        mec+="**Gözlem:** "+x["observed_tr"]+"\n\n**Soyutlama:** "+x["abstraction_tr"]+"\n\n"
        mec+="**Koruma kuralı:** "+x["guardrail_tr"]+"\n\n"
        mec+="**Kanıt:** "+", ".join(x["evidence_anchors"])+". **NOVA v0.2 karşılıkları:** "+", ".join(x["related_cm_ids"])+".\n\n"
    doc("MECHANICS_INDEX.md",mec)

    guards=[
      "Klasik seri, Sands üçlemesi, 2008 yeniden başlangıcı, The Lost Crown ve Rogue aynı dünya tarihi değildir.",
      "Forgotten Sands PC/konsol, Wii, PSP ve DS sürümleri dört farklı hikâyedir; hiçbirini ötekine sahte port olarak bağlama.",
      "Warrior Within Kaileena'nın kurtulduğu Water Sword sonundan The Two Thrones'a geçer; öteki son kanon değildir.",
      "The Two Thrones'da Vezir'in yaşaması eski zaman çizgisiyle çelişki değil, değişmiş geçmişin devamıdır.",
      "Sand Wraith ayrı kişi değil, Prens'in zaman yolculuğu etmiş örneğidir; örnek başına konum, bilgi ve yaşam durumu ayrıdır.",
      "Geçmişte Kaileena'nın ölmesiyle bugünde ölmesi aynı tarihsel sonucu üretmez.",
      "Maskeli sahnenin ilk gözlemi ve revize tarih sonucu iki bağımsız worldline olarak tutulur.",
      "Remake ve portları aynı olaylardan çift kanıt üretmekte kullanma; VR yan eserinin tam üçleme kanonu olduğunu varsayma.",
      "30 Ocak 2026'da iptal edilen Sands of Time Remake yayınlanmış kaynak değildir.",
      "İncelenen kaynak eserlerin özgün olayları LUMI'ye kopyalanamaz; mekanikler sadece kaynaklı araştırma adayıdır.",
      "Mekaniklerin hikâye kalite etkisi sınanmamıştır; user story harness, model ve production'a dokunma."
    ]
    doc("CONTINUITY_FIREWALL.md","# Prince of Persia — Süreklilik ve nedensellik bariyeri\n\n"+
        "\n".join(str(i)+". "+s for i,s in enumerate(guards,1)))
    doc("SOURCES.md","# NOVA Prince of Persia — Kaynak listesi\n\nWeb araştırması metni veya arama sonucu görülmüştür; tek tek HTTP 200 ya da editoryal ikinci onay iddiası yoktur.\n\n"+
        "\n".join("- **"+x["source_id"]+"** — ["+x["publisher"]+"]("+x["url"]+")" for x in sources))
    counts={k:len(v) for k,v in data.items()}
    manifest={"schema_version":"0.3.0","research_date":"2026-10-15",
              "source_files":[str(p.relative_to(ROOT)) for p in sorted(SRC.glob("*.json"))],
              "counts":counts,
              "hashes":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in sorted(SRC.glob("*.json"))},
              "quality_effect":"not_evaluated","story_quality_trials":0,"lumi_production_modified":False,
              "new_paid_model_calls":0}
    (BASE/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return manifest

if __name__=="__main__":
    print(json.dumps(compile_data(),ensure_ascii=False,indent=2))
