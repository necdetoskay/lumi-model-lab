"""Reproducible editorial migration of the frozen predecessor; never runs on import.

This is assistant-authored research curation, not an automatic semantic extractor.
Existing evidence and withheld decisions remain intact. Releasing changed data
requires explicit review of generated JSONL, schemas and the code release pin.
"""
from pathlib import Path

from experiments.narrative_mechanics import core as nml
from . import vault


def obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def arr(item, minimum=0, maximum=100):
    return {"type": "array", "items": item, "minItems": minimum, "maxItems": maximum, "uniqueItems": True}


def integer(low=0, high=10000):
    return {"type": "integer", "minimum": low, "maximum": high}


S = {"type": "string", "minLength": 1, "maxLength": 4000}
B = {"type": "boolean"}
H = {"type": "string", "pattern": "^[a-f0-9]{64}$"}
F = {"const": False}


def enum(*values):
    return {"type": "string", "enum": list(values)}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(nml.canonical(value) + b"\n")


def build():
    data = nml.load_release()
    schema_dir = vault.HERE / "schemas"
    evidence = obj({"source_id": S, "source_sha256": H, "start_byte": integer(),
                    "end_byte": integer(), "span_sha256": H})
    claim = obj({"claim": S, "epistemic": enum("INFERRED", "UNKNOWN"),
                 "evidence": arr(evidence, 0, 10), "limitation": S})
    profile = obj({"profile": enum("STANDARD_LAB", "GENTLE_LAB"), "age_min": integer(4, 120),
                   "age_max": integer(4, 120), "risks": arr(S), "advice": S,
                   "review": enum("ASSISTANT_PROPOSAL_HUMAN_PENDING")})
    schemas = {
      "mechanic": obj({"schema": {"const": "nova.mechanic.v1"}, "id": S, "version": {"const": 1},
        "upstream_id": S, "upstream_sha256": H, "name": S, "abstract": S, "normalized_sha256": H,
        "family": S, "source_ids": arr(S, 2, 8), "source_group": enum("sg1", "atlantis"),
        "themes": arr(enum("exploration", "friendship", "mystery", "crisis"), 1, 4),
        "status": enum("PROPOSED_LAB", "WITHHELD"), "requires": arr(S), "effects": arr(S),
        "reveal_level": integer(0, 2), "profiles": arr(profile, 1, 3),
        "analysis": obj({a: claim for a in vault.AXES}), "counterexample": S, "failure_mode": S,
        "human_review": {"const": "PENDING"}, "semantic_support_certified": F,
        "integration_authorized": F, "derivation": S}),
      "state": obj({"schema": {"const": "nova.frozen-lab-state.v1"}, "authority": {"const": "LAB_FIXTURE_NOT_PRODUCTION"},
        "source_path": S, "source_sha256": H, "facts": arr(S, 1), "authorized_features": arr(S, 1),
        "allowed_effects": arr(S, 1), "reveal_ceiling": integer(0, 2), "forbidden_terms": arr(S, 1),
        "state_commit_authorized": F}),
      "brief": obj({"schema": {"const": "nova.brief.v1"}, "id": S, "age": {"type": "integer", "enum": [4, 10, 25, 40]},
        "theme": enum("exploration", "friendship", "mystery", "crisis"), "state_sha256": H,
        "ordinal": integer(), "seed": S, "strict_novelty": B, "forbidden_risks": arr(S),
        "task": S, "max_words": integer(80, 2000), "fixture_beats": arr(S, 3, 3)}),
      "usage": obj({"schema": {"const": "nova.usage.v1"}, "id": S, "ordinal": integer(),
        "state_sha256": H, "selection_sha256": H}),
      "ballot": obj({"schema": {"const": "nova.ballot.v1"}, "sample_id": S, "story_sha256": H,
        "reviewer": S, "kind": enum("SYNTHETIC", "HUMAN"), "independent": B,
        "saw_allocation": B, "is_story_author": B,
        "scores": obj({d: integer(1, 5) for d in ("interest", "causality", "decision_cost", "character", "closure", "originality")}),
        "gates": obj({g: B for g in ("age", "canon", "state", "originality")}), "notes": S})}
    for name, schema in schemas.items():
        write(schema_dir / (name + ".schema.json"), {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema})

    templates = {t["id"]: t for t in data["templates"]}
    extracts = {e["id"]: e for e in data["extractions"]}
    sources = {s["id"]: s for s in data["archive"]["episodes"]}
    cards = {c["id"]: c for c in data["cards"]}
    # Comparisons are analogies with differences, not independent confirmation.
    related = [18, 9, 14, 15, 11, 1, 12, 10, 2, 8, 5, 7, 15, 3, 4, 17, 16, 1]
    comparison = [
      "Reddetme hakkı iki örnekte de teknik üstünlüğü sınırlar; biri yardımın biçimi, diğeri kaynağın sahipliği üzerinedir.",
      "Bilgiyi elde etmek ile taşıyabilmek farklı sınırlardır; biri zaman baskısı, diğeri kapasite bedeli kullanır.",
      "İşbirliğinin değeri davranışta görünür; ilk örnek güveni onarır, karşı örnek ittifakı bozar.",
      "Faydalı görünen şeyi kullanmak rıza gerektirir; biri sığınmacıları, diğeri fark edilmemiş paydaşları merkeze alır.",
      "Başlangıç varsayımı araştırmayı yanlış yöne iter; konum hatası ile kişiye yönelen şüphe aynı olay değildir.",
      "Farklı öznenin karar hakkı korunmalıdır; kopya kimliği ile bir topluluğun özerkliği farklı çatışmalardır.",
      "Çocukları etkileyen düzenin yeniden düşünülmesi ortak motiftir; ilk kaynağın finali tartışmalı olduğundan karşılaştırma doğrulanmış sonuç değildir.",
      "Dağıtılmış bilgi çözümü mümkün kılar; tekrar birikimi ile eşzamanlı görev sırası farklı mekaniklerdir.",
      "Yetenek veya bilgi kazanımı sınırsız yarar sağlamaz; taşıma kapasitesi ile arşivden ayrılma farklı bedeller üretir.",
      "Katkıların koordinasyonu gerekir; eşzamanlı kısıtlar zaman döngüsü olayını kopyalamayı gerektirmez.",
      "Gözlemin yeniden yorumlanması suçlamayı veya yanlış konum varsayımını boşa çıkarır; kanıt sırası farklıdır.",
      "Yerleşik açıklama ile gözlenen işlev ayrılır; tartışmalı karşı kaynağın toplumsal finali destek sayılmaz.",
      "Başarı ölçütünün dışında zarar gören paydaş bulunur; ölçülmeyen yan etki ile canlı kaynağın keşfi ayrıdır.",
      "Davranış ortak amaç söyleminden daha güçlü kanıttır; karşılaştırılan sonuçlar güven kaybı ve güven onarımıdır.",
      "Yarar sağlamak sahiplik veya kullanma hakkı vermez; görünmeyen canlı ile korunacak misafir aynı dünya kuralı değildir.",
      "Yerel olay daha uzun soruyu taşır; birinde geleceğe soru bırakılır, diğerinde geçmişteki kolaylık açıklanır.",
      "Nedensel bağ bölüm sınırını aşar; geçmişteki emeği açıklamak geleceğe tehdit bırakmaktan farklıdır.",
      "Bulmacayı çözmek ile hak kazanmak ayrılır; diğer örnekte aynı sınır yardım teklifinin reddiyle görünür olur."]
    gentle = {
      "NM-002": "Her şeyi aynı anda toplamak yerine tek bir küçük gözlemi seçtir. Bedel yalnız beklemek olsun; kayıp veya tehlike kullanma.",
      "NM-005": "Çalışmayan küçük bir oyunda önce tahmini kontrol ettir. Yeni bir gözlemle fikri değiştirsinler; korku ve tehlike olmasın.",
      "NM-010": "İki basit işi sıraya koydur; her arkadaş ayrı katkı sunsun. Acele veya tehdit yerine sırayla denemenin keyfini göster.",
      "NM-011": "Suçlama olmadan iki farklı tahmini küçük ve güvenli bir denemeyle karşılaştır. Arkadaşların birbirini dinlediği bir kapanış kur.",
      "NM-018": "Bir oyunu çözmenin eşyayı alma hakkı vermediğini göster. İzin isteyip beklemek küçük bedel olsun; sonu sıcak ve güvenli bitir."}
    themes = {
      "ethical": ["friendship", "crisis"], "resource": ["exploration", "crisis", "mystery", "friendship"],
      "epistemic": ["exploration", "mystery", "crisis", "friendship"],
      "cooperation": ["exploration", "friendship", "mystery", "crisis"],
      "identity": ["friendship", "mystery"], "legacy": ["exploration", "mystery"]}

    def ev(source_id, span):
        return {"source_id": source_id, "source_sha256": sources[source_id]["sha256"],
                "start_byte": span["start_byte"], "end_byte": span["end_byte"], "span_sha256": span["sha256"]}

    def sentence_ev(source_id, last=False):
        raw = (nml.ROOT / sources[source_id]["path"]).read_bytes()
        text = raw.decode("utf-8")
        body = text.split("## Türkçe olay özeti", 1)[1].split("## Kaynaklar", 1)[0].strip()
        sentences = body.split(". ")
        chosen = sentences[-1] if last else sentences[0]
        start = raw.index(chosen.encode())
        return {"source_id": source_id, "source_sha256": sources[source_id]["sha256"], "start_byte": start,
                "end_byte": start + len(chosen.encode()), "span_sha256": nml.sha(chosen.encode())}

    records = []
    for idx, card in enumerate(data["cards"]):
        template, extract = templates[card["id"]], extracts[card["extraction_id"]]
        sid = extract["source_id"]
        other = cards[f"NM-{related[idx]:03}"]
        other_extract = extracts[other["extraction_id"]]
        axes = {axis: {"claim": claim["claim"], "epistemic": "UNKNOWN" if claim["epistemic"] in ("UNKNOWN", "NOT_APPLICABLE") else "INFERRED",
                       "evidence": [ev(sid, span) for span in claim["spans"]],
                       "limitation": "Inherited summary-level evidence; broad spans are not independent sentence-level semantic verification."}
                for axis, claim in extract["axes"].items()}
        axes["dramatic_opening"] = {"claim": template["mechanism"]["event"], "epistemic": "INFERRED",
          "evidence": [sentence_ev(sid)], "limitation": "Summary opening supports an editorial entry hook; actual screen opening is not certified."}
        axes["outcome"] = {**axes["persistent_state"], "limitation": "Summary outcome candidate; not an accepted world-state change."}
        axes["series_arc"] = {"claim": "Series-wide persistence beyond this summary has not been independently verified.",
          "epistemic": "UNKNOWN", "evidence": [], "limitation": "Do not invent cross-episode continuity from a single summary."}
        axes["novelty"] = {"claim": comparison[idx], "epistemic": "INFERRED",
          "evidence": [ev(sid, extract["axes"]["decision"]["spans"][0]),
                       ev(other_extract["source_id"], other_extract["axes"]["decision"]["spans"][0])],
          "limitation": "Assistant comparative hypothesis between two summaries; not a historical originality claim. WITHHELD comparators remain untrusted."}
        abstract = " ".join(template["mechanism"][axis] for axis in nml.AXES)
        profiles = [{"profile": "STANDARD_LAB", "age_min": card["age_min"], "age_max": card["age_max"],
                     "risks": card["risks"], "advice": template["mechanism"]["decision"] + " " + template["mechanism"]["cost"] + " " + template["counterexample"],
                     "review": "ASSISTANT_PROPOSAL_HUMAN_PENDING"}]
        if card["id"] in gentle:
            profiles.append({"profile": "GENTLE_LAB", "age_min": 4, "age_max": 6, "risks": [],
                             "advice": gentle[card["id"]], "review": "ASSISTANT_PROPOSAL_HUMAN_PENDING"})
        records.append({"schema": "nova.mechanic.v1", "id": card["id"].replace("NM-", "NOVA-"), "version": 1,
          "upstream_id": card["id"], "upstream_sha256": nml.fingerprint(card), "name": template["name"],
          "abstract": abstract, "normalized_sha256": nml.sha(vault.normalized(abstract).encode()),
          "family": card["family"], "source_ids": sorted({sid, other_extract["source_id"]}),
          "source_group": card["source_group"], "themes": themes[card["family"]], "status": card["status"],
          "requires": card["requires"], "effects": card["effects"], "reveal_level": card["reveal_level"],
          "profiles": profiles, "analysis": axes, "counterexample": template["counterexample"],
          "failure_mode": template["failure_mode"], "human_review": "PENDING", "semantic_support_certified": False,
          "integration_authorized": False, "derivation": "Migrated from frozen NML release; assistant-added comparative hypotheses and gentle profiles. No human certification."})
    vault.DATA.mkdir(parents=True, exist_ok=True)
    (vault.DATA / "vault.v1.jsonl").write_bytes(b"".join(nml.canonical(r) + b"\n" for r in records))
    source = "data/specifications/generator_v2/06_age7_8_canon_constraints.yaml"
    state = {"schema": "nova.frozen-lab-state.v1", "authority": "LAB_FIXTURE_NOT_PRODUCTION", "source_path": source,
      "source_sha256": nml.sha((nml.ROOT / source).read_bytes()),
      "facts": ["Only Lina, Bora and Mira are named protagonists.", "Bora is good at finding directions; Mira understands mechanisms.",
                "The lighthouse and research area are safe and permitted.", "Lina cannot solve the problem alone.",
                "No new powers or world rules may be introduced.", "Observe, find the route, understand the mechanism, operate together."],
      "authorized_features": ["observation", "cooperation", "local_rules", "consent", "limited_resources", "recorded_history", "distinct_perspectives"],
      "allowed_effects": ["knowledge_candidate", "relationship_candidate", "resource_candidate", "obligation_candidate"],
      "reveal_ceiling": 1, "forbidden_terms": ["Stargate", "Atlantis", "Wraith", "Goauld", "Goa'uld", "O'Neill", "Sheppard", "McKay", "Teyla", "Tealc", "Teal'c", "ZPM", "nanite", "öldür", "intihar"],
      "state_commit_authorized": False}
    write(vault.DATA / "state.v1.json", state)
    tasks = {
      "exploration": ("Güvenli fener alanındaki işaretleri izleyerek gözlem düzeneğini bulup birlikte çalıştırın.",
        ["Lina, Bora ve Mira güvenli fener bahçesindeki işaretlere baktı.", "Bora yolu gösterdi. Mira düzeneği inceledi; iki işaret farklı yönleri gösteriyordu.", "Lina gözlemlerini paylaştı. Üçü birlikte düzeneği çalıştırdı ve buldukları yolu not etti."]),
      "friendship": ("Gözlem düzeneğinde görev paylaşımı konusunda farklı isteyen üç arkadaşın izin ve birlikte karar verme sorununu çözün.",
        ["Lina, Bora ve Mira fener bahçesinde aynı oyunu oynamak istedi.", "Bora yolu bulmuştu, Mira düzeneği incelemişti. Ama herkes önce kendi fikrinin denenmesini istiyordu.", "Lina arkadaşlarına yer açtı. Üçü sırayla katkı verip düzeneği birlikte çalıştırdı."]),
      "mystery": ("İki gözlem işaretinin neden uyuşmadığını güvenli bir karşılaştırmayla açıklayın; sihirli veya yeni dünya kuralı eklemeyin.",
        ["Fener bahçesinde Lina iki farklı işaret gördü. Bora ve Mira da merak etti.", "Bora işaretlerin gösterdiği yolu izledi. Mira düzeneğe baktı; hangi sıranın doğru olduğunu henüz bilmiyorlardı.", "Lina gördüklerini bir araya getirdi. Üçü doğru sırayı deneyip düzeneği çalıştırdı; küçük soruları cevap buldu."]),
      "crisis": ("Gözlem oyunu için zaman sınırlı: güvenli alanda öncelik seçip üç katkıyla düzeneği çalıştırın. 4 yaşta yalnız bekleme ve sıra değişikliği kullanın.",
        ["Lina, Bora ve Mira fener bahçesindeki gözlem oyununa hazırlandı.", "Bora yolu seçti, Mira düzeneği inceledi. Her şeyi birden denemeye zamanları yetmiyordu.", "Lina tek bir küçük deneme önerdi. Üç arkadaş düzeneği birlikte çalıştırdı ve kalan oyunu sonraya bıraktı."])}
    briefs = []
    for age in (4, 10, 25, 40):
        for theme, (task, beats) in tasks.items():
            briefs.append({"schema": "nova.brief.v1", "id": f"B{age:02}-{theme}", "age": age, "theme": theme,
              "state_sha256": nml.fingerprint(state), "ordinal": len(briefs)+10, "seed": "nova-pilot-v1",
              "strict_novelty": True, "forbidden_risks": ["loss", "identity_uncertainty"] if age <= 10 else [],
              "task": task + (" Use simple, reassuring language." if age == 4 else " Match emotional and linguistic complexity to the target reader age."),
              "max_words": {4: 150, 10: 450, 25: 750, 40: 750}[age], "fixture_beats": beats})
    write(vault.DATA / "briefs.v1.json", briefs)
    files = {p.relative_to(vault.HERE).as_posix(): nml.sha(p.read_bytes())
             for p in [vault.DATA / "vault.v1.jsonl", vault.DATA / "state.v1.json", vault.DATA / "briefs.v1.json", *sorted(schema_dir.glob("*.json"))]}
    release = {"schema": "nova.release.v1", "upstream_release": nml.RELEASE_SHA256, "files": files,
               "source_commit": nml.ARCHIVE_COMMIT, "integration_authorized": False}
    write(vault.DATA / "release.v1.json", release)
    print("NOVA release SHA256:", nml.sha((vault.DATA / "release.v1.json").read_bytes()))


if __name__ == "__main__":
    build()
