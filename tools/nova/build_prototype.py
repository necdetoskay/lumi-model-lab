#!/usr/bin/env python3
"""NOVA v0.4 Prototype 2009 source-only offline builder; no model or network calls."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"data/nova/v0.4"
SRC=BASE/"source_records/prototype_2009.json"
DOCS=ROOT/"docs/research/prototype"
EXPECTED_TABLES=("works","sources","story_events","mechanics","mechanic_evidence","prior_links")

def jsonl(name,rows):
    path=BASE/(name+".jsonl")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text("".join(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n" for x in rows),encoding="utf8")

def document(name,content):
    path=DOCS/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(content.rstrip()+"\n",encoding="utf8")

def compile_data():
    canonical=json.loads(SRC.read_text(encoding="utf8"))
    ev={row["event_id"]:row for row in canonical["story_events"]}
    evidence=[]
    prior=[]
    for m in canonical["mechanics"]:
        for anchor in m["evidence_anchors"]:
            e=ev[anchor]
            evidence.append({"evidence_id":m["mechanic_id"]+":"+anchor,
              "mechanic_id":m["mechanic_id"],"event_id":anchor,
              "work_id":"PROTOTYPE-2009","source_ids":e["source_ids"],
              "observed_event_tr":e["observed_event_tr"],
              "mechanism_inference":True,"quality_effect":"not_evaluated",
              "lumi_canon":False})
        for popid in m["related_pop_ids"]:
            prior.append({"mechanic_id":m["mechanic_id"],"prior_mechanic_id":popid,
            "link_type":"related_concept_not_equivalent","quality_effect":"not_evaluated"})
    data={"works":canonical["works"],"sources":canonical["sources"],
          "story_events":canonical["story_events"],"mechanics":canonical["mechanics"],
          "mechanic_evidence":evidence,"prior_links":prior}
    for k,rows in data.items():jsonl(k,rows)
    jsonl("quality_evaluations",[])
    jsonl("lumi_usage_history",[])
    readme="# NOVA v0.4 — Prototype (2009): Kaynaklı ilk araştırma geçişi\n\n"
    readme+="Bu çalışma hikâye üretimi veya oyun hikâyesinin kopyalanması değildir. Model/A-B değerlendirmesi yapılmadı; kalite etkisi ölçülmedi.\n\n"
    readme+="## Kapsam\n\n"
    readme+="- Yalnız 2009 Prototype; Prototype 2 farklı devam eseri olarak gelecek araştırma listesinde.\n"
    readme+="- 1 eser, "+str(len(canonical["sources"]))+" kaynak, "+str(len(ev))+" olay, "+str(len(canonical["mechanics"]))+" soyut mekanik, "+str(len(evidence))+" kanıt bağı.\n"
    readme+="- [Olay ve olayın öğrenilme sırası](EVENTS.md)\n"
    readme+="- [Mekanik adayları](MECHANICS.md)\n"
    readme+="- [Kaynak güven seviyeleri](SOURCES.md)\n"
    readme+="- [Gerçek test kanıtı](VALIDATION_REPORT.md)\n"
    readme+="- [Tomb Raider ve sonraki kaynak planı](NEXT_SOURCE_PLAN.md)\n"
    readme+="- [Süreklilik bariyeri ve sıradaki çalışmalar](FIREWALL.md)\n\n"
    readme+="**Önemli:** Oyundaki karakter kimliği sürprizi ve final anlatımı ikincil/topluluk kaynaklıdır; özgün oyun sahneleriyle bağımsız doğrulanmadı.\n"
    document("README.md",readme)
    events="# Prototype (2009) — kanıta bağlı olaylar\n\n"
    events+="Olay numarası araştırma sunum sırasıdır, zorunlu oynanış kronolojisi değildir. chronological_order isteğe bağlıdır; opsiyonel ve geçmiş olaylar doğrusal sayılmaz.\n\n"
    for e in canonical["story_events"]:
        events+="## "+e["event_id"]+" — "+e["label_tr"]+"\n\n"+e["observed_event_tr"]+"\n\n"
        events+="**Kaynaklar:** "+", ".join(e["source_ids"])+"; **güven:** "+e["evidence_strength"]+"; **rol:** "+e["narrative_role"]+".\n\n"
    document("EVENTS.md",events)
    mechanisms="# Prototype — 12 araştırma mekaniği (NOVA v0.4)\n\n"
    mechanisms+="Her soyutlama bir yorumdur; LUMI kanonu veya hikâye kalitesi artışı kanıtı değildir.\n\n"
    for m in canonical["mechanics"]:
        mechanisms+="## "+m["mechanic_id"]+" — "+m["label_tr"]+"\n\n"
        mechanisms+="**Gözlem:** "+m["observed_tr"]+"\n\n"
        mechanisms+="**Soyutlama:** "+m["abstraction_tr"]+"\n\n"
        mechanisms+="**Koruma kuralı:** "+m["guardrail_tr"]+"\n\n"
        mechanisms+="**Olay kanıtı:** "+", ".join(m["evidence_anchors"])+"; **önceki adaylar:** "+", ".join(m["related_pop_ids"])+".\n\n"
    document("MECHANICS.md",mechanisms)
    ss="# Prototype (2009) — araştırma kaynakları\n\n"
    ss+="Kaynak URL'leri araştırmada arama veya açma sonucu görüldü; burada bağımsız tam oynanış doğrulaması veya yeni HTTP-200 denetimi yapıldığı iddia edilmez.\n\n"
    for x in canonical["sources"]:
        ss+="- **"+x["source_id"]+"** ["+x["publisher"]+"]("+x["url"]+") — "+x["source_class"]+"; "+x["scope"]+".\n"
    document("SOURCES.md",ss)
    ff="# Süreklilik, bilgi ve telif bariyeri\n\n"
    ff+="\n".join(str(i)+". "+rule for i,rule in enumerate(canonical["continuity_firewall"],1))
    ff+="\n\n## Gelecek bağımsız incelemeler\n\n"
    ff+="\n".join("- "+k for k in canonical["future_research"])
    ff+="\n"
    document("FIREWALL.md",ff)
    manifest={"schema_version":canonical["schema_version"],
      "research_cutoff_date":canonical["research_cutoff_date"],
      "source_file":str(SRC.relative_to(ROOT)),
      "source_sha256":hashlib.sha256(SRC.read_bytes()).hexdigest(),
      "counts":{k:len(v) for k,v in data.items()},
      "paid_model_calls":0,"story_quality_trials":0,
      "lumi_production_modified":False,"quality_effect":"not_evaluated"}
    (BASE/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    return manifest

if __name__=="__main__":
    print(json.dumps(compile_data(),ensure_ascii=False,indent=2))
