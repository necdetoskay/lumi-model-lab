"""Research-only evidence precision audit and assistant-authored review proposals.

These annotations never replace the frozen vault or certify human/source truth.
"""
from experiments.narrative_mechanics import core as nml
from . import vault

# Text anchors are from the already frozen, user-supplied secondary corpus.
# They are research evidence, never generator-facing advice.
PROPOSALS = [
    ("NOVA-011", "atlantis:S01E05", "decision", "OBSERVED_SUMMARY_EVENT",
     "İnceleme, kişinin eşyalarına yöneltilir; kaynak tarafsız ve rızaya dayalı deney yapıldığını söylemez.",
     "Bates gizlice McKay'den Teyla'nın eşyalarını incelemesini ister."),
    ("NOVA-011", "atlantis:S01E05", "reveal", "OBSERVED_SUMMARY_EVENT",
     "İhanet varsayımının yerine dışarıdan izlenme açıklaması gelir.",
     "Teyla hiçbir bilgi sızdırmamıştır; düşman sinyali izleyerek aynı gezegenlere gelmektedir."),
    ("NOVA-011", "atlantis:S01E05", "persistent_state", "LOCAL_OUTCOME_ONLY",
     "Güven onarımı bir çabadır; tamir edilmiş ilişkinin sonraki bölümlerde sürdüğü kanıtlanmaz.",
     "Weir ve Teyla kırılan güveni onarmaya çalışırken Sheppard yeni tutsağından düşman toplumunu öğrenmeye hazırlanır."),
    ("NOVA-015", "atlantis:S01E09", "conflict", "OBSERVED_SUMMARY_EVENT",
     "Enerji kullanımı görünmeyen bir topluluğa zarar verir; kaynak tarafsız bir rezerv değildir.",
     "Atmosferdeki sis aslında bilinçli enerji varlıklarından oluşan bir uygarlıktır. Stargate'in her çalıştırılması onların bir bölümünü öldürmektedir."),
    ("NOVA-015", "atlantis:S01E09", "decision", "OBSERVED_SUMMARY_EVENT",
     "Kullanımdan vazgeçme sözü açık bir karakter kararıdır.",
     "Weir ve arkadaşları bu enerji kaynağını artık kullanmayacaklarına söz verir."),
    ("NOVA-015", "atlantis:S01E09", "outcome", "LOCAL_OUTCOME_ONLY",
     "Yerel dönüş gerçekleşir; bunun sonraki bölümlerde uygulanmış kalıcı kullanım yasağı olduğu ayrıca doğrulanmalıdır.",
     "Ekip gerçek bedenlerinde uyanır ve Atlantis'e döner."),
    ("NOVA-018", "atlantis:S01E16", "reveal", "OBSERVED_SUMMARY_EVENT",
     "Teknik başarı kaynak üzerinde hak sağlamaz; teslimi reddeden farklı bir aktör vardır.",
     "Allina aslında Kadimlerin bıraktığı görevi sürdüren yeni kardeşliğin üyesidir; yabancıların Dünya'dan geldiğini bildiği için ZPM'yi onlara vermez."),
    ("NOVA-018", "atlantis:S01E16", "decision", "ADAPTATION_NOT_OBSERVED_CHOICE",
     "Kaynak zorunlu geri dönüş tarif eder. Şablondaki gönüllü izin görüşmesi araştırmacının uyarlamasıdır, gözlenen karar değildir.",
     "Ekip enerji kaynağına ulaşmasına rağmen onu alamadan Atlantis'e dönmek zorunda kalır."),
    ("NOVA-018", "atlantis:S01E16", "series_arc", "LOCAL_PROMISE_NOT_CONFIRMED_ARC",
     "Yaklaşan kuşatma için yerel süre baskısı kurulur; sonraki bölümdeki gerçekleşme bu kayıtta doğrulanmaz.",
     "Sensörler üç büyük kovan gemisinin yaklaşık iki hafta içinde şehre varacağını gösterir.")
]


def anchor(data, quote):
    needle = quote.encode("utf-8")
    if not needle or data.count(needle) != 1:
        raise nml.Invalid("REVIEW_ANCHOR_NOT_UNIQUE")
    start = data.index(needle)
    return {"start_byte": start, "end_byte": start + len(needle), "span_sha256": nml.sha(needle)}


def audit(rows, upstream, root=nml.ROOT):
    episodes = {s["id"]: s for s in upstream["archive"]["episodes"]}
    by_id = {r["id"]: r for r in rows}
    coverage = []
    for row in rows:
        wide = [name for name, claim in row["analysis"].items()
                if any(e["end_byte"]-e["start_byte"] > 800 for e in claim["evidence"])]
        unknown = [name for name, claim in row["analysis"].items() if claim["epistemic"] == "UNKNOWN"]
        coverage.append({"mechanic_id": row["id"], "wide_span_axes": wide, "unknown_axes": unknown,
                         "human_review": row["human_review"], "status": row["status"]})
    proposals = []
    for mid, sid, axis, relation, claim, quote in PROPOSALS:
        if sid not in by_id[mid]["source_ids"] or axis not in vault.AXES:
            raise nml.Invalid("REVIEW_LINEAGE")
        source = episodes[sid]
        data = nml.safe_path(root, source["path"]).read_bytes()
        if nml.sha(data) != source["sha256"]:
            raise nml.Invalid("REVIEW_SOURCE_CHANGED")
        proposals.append({"mechanic_id": mid, "mechanic_sha256": nml.fingerprint(by_id[mid]),
                          "source_id": sid, "source_sha256": source["sha256"], "axis": axis,
                          "relation": relation, "claim": claim, "evidence": anchor(data, quote),
                          "reviewer_kind": "ASSISTANT_EDITORIAL", "human_review": "PENDING",
                          "limitation": "Evidence is a frozen secondary summary, not independently verified screen/transcript truth."})
    return {"schema": "nova.source-review.v1", "scope": "RESEARCH_ONLY", "vault_release_sha256": vault.RELEASE_SHA256,
            "mechanics_audited": len(rows), "coverage": coverage, "narrow_proposals": proposals,
            "narrowed_mechanics": len({p["mechanic_id"] for p in proposals}),
            "source_quality_status": "NOT_CERTIFIED", "semantic_support_certified": False,
            "active_vault_changed": False, "integration_authorized": False,
            "wide_span_threshold_bytes": 800,
            "threshold_note": "Review triage heuristic only; short evidence does not prove semantic support."}


def run(directory):
    rows, upstream, _ = vault.load()
    report = audit(rows, upstream)
    path = nml.freeze(directory, "source-review", report)
    return {"status": "REVIEW_PROPOSALS_RECORDED", "report": str(path),
            "mechanics_audited": len(rows), "narrowed_mechanics": report["narrowed_mechanics"],
            "source_quality_status": report["source_quality_status"]}
