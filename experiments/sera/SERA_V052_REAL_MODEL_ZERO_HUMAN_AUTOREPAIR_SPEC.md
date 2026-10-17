# SERA v0.52 — Gerçek-model, sıfır-insan Mara S1 uçtan uca otonom onarım

**17 Ekim 2026 | EXPERIMENT / SHADOW ONLY | Status: SPECIFIED / NOT LIVE-PROVEN**

## Ön koşullar ve gerçek durum

- v0.51 [mimari](./SERA_V051_FULL_SCENE_REVALIDATION_HANDOFF.md) ve [self-hosted CI #38998048487](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38998048487) ile 749/749 offline PASS; Mara için **28 cümlenin gerçek modellerce başarıyla otomatik onarıldığı kanıtlanmadı**.
- v0.48'deki 14 gerçek Gemini/Haiku yanıtının kaydı duruyor. Daha sonra `v0.50` ve `v0.51` onarım yanıtları **scripted provider double**. Bu testlerin hiçbirini `real_model_pass` olarak raporlamak yasaktır.
- `v0.51.handoff` kaynak sözleşmesinde bilinçli olarak `transport=SYNTHETIC_SCRIPTED_NO_OPENROUTER_API`, yer tutucu API anahtarı ve `repair_model_was_real=false` bulunduruyor. Bunu gizlice gerçek çağrıya çevirmek yerine **yeni v0.52 real-path** ayrı kanıt ve güvenlik sınırıyla kurulmalı.
- Aion HIGH/MAX için ayrı bir çalışmada harcanmış tek kullanımlık çağrı yetkisi **SERA'ya aktarılamaz**. SERA model provider harcaması için ayrı açık onay ve doğrulanmış kimlik gerekir.

## v0.52 uygulama hedefi

Esas ölçüm “scripted testi geçti” değil, **dondurulmuş Mara 28 cümlelik S1 kaynak sahnesinin gerçekten model tarafından kaynak bağlı hatalarının düzeltilip tam bağımsız sahne denetiminden geçmesi** olacak. Bir sahnenin doğrulanması yine canonical WorldState/G2 commit yetkisi değildir.

1. **Kaynak sabitliği.** Mara orijinal prose SHA `EXPECTED_SHA`, world revision SHA, tekil job/grant ID ve provider politikası immutable kontrat. Modelin ilk cevabına aynı sahnenin daha önceki test yanıtı veya gold etiketleri sızdırılmayacak.
2. **Tam sahne kaynak-kör gerçek extraction.** v0.22 `create_preparer` gerçek registered models üzerinden her cümle için sentence sweep, independent semantic ve typed facet kanıtını üretir; her provider POST'un önce persistent STARTED, sonra tam cevap/envelope/generation ID makbuzu saklanır. İlk eksik cevap sahne kapısını geçemez. 
3. **Bağımsız sahne denetimi.** v0.21 `create_checker` ve v0.20 `execute` eksik cümle, yanlış kaynak quote, yanlış aktör/nesne/hareket, nedensellik/temporal bilginin uydurulması gibi kusurları ayırır. V0.23+ qualified full-scene checks dahil olmadan STRUCTURAL_READY sonuç yalnız provisionaldır.
4. **Gerçek yazar otomatik onarım.** Yalnızca kaynakla kanıtlı, v0.20 modelin doğrulanmış kusurları için v0.21 `create_writer` çağrılır. Model yazar sahnenin bütünüyle yeni metnini döndürür; önceki gerçeklere sadık kalmak zorunda; editör/insan metin JSON değiştiremez. Unresolved local defect fallback veya safe stop olabilir, ancak false PASS yasaktır.
5. **Yeni sahnenin sıfırdan kontrolü.** Her prose SHA değişiminden sonra v0.22–v0.23–v0.21 kanıtları sıfırdan oluşur; eski source-bound alıntılar taşınamaz. Bütün model/transport/rewrite/idempotency/cost receipts ve otomatik karar grafiği immutable olarak raporlanır.
6. **Kanonik sınır.** v0.52 yalnız `LAB_CANDIDATE_NONCANONICAL` / `FAILED_SAFE_FINAL` / `INCOMPLETE_EVIDENCE_HOLD` verebilir; production DB, WorldState, saga, G2 write **0**. Gold precision/recall, yanlış-PASS ve eserin insan/bağımsız değerlendirmesi ayrı release gate.

## Geliştirme sırası / acceptance checklist

- [ ] P0: Real-path provider adapter + one-use explicit grant, model allowlist, shareable durable receipt idempotency ve preflight; **API anahtarı koda/günlüğe yazılmaz**.
- [ ] P1: Tam 28 cümle real-model blind extraction smoke; yanıtları ayrı tamamlanmış makbuzlarla sakla; kaynak/prose SHA/actor alias doğrula.
- [ ] P2: Bağımsız checker + automatic writer + yeni source SHA ile tam 28 cümle yeniden extraction/recheck; önceki truth/sweep'leri taşıma.
- [ ] P3: Kopan SSE, süresi dolan token, provider 429/503, bozuk JSON, alternatif model, aynı grant replay, WorldState drift, sahte alıntı gibi adversarial offline testler.
- [ ] P4: Şartsız self-hosted CI proof ve ayrı yetkilendirilmiş maliyetli **bir** gerçek Mara denemesi. İlk ücretli istekten sonra kaydı olmayan bilinmeyen yanıt kör tekrar edilmez. Yeniden deneme yalnız mevcut makbuzu GET-only uzlaştıran destekli yol varsa mümkündür.
- [ ] P5: Gerçek hikâye bütünlüğü SERA semantik gold ve source-level gözden geçirme; 0 false canonical writes. Bu, `production ready` ilanı değildir.

## Değişmez kullanıcı şartları

**Hiçbir manuel hikâye/prose/JSON/gold düzeltmesi. LLM için uygulama tanımlı çıktı token sınırı yok.** Kontrol amaçlı ücretli istek sayısı ve harcama gözcüsü ise faturalandırılabilir çalıştırma güvenliği için ayrı, kabul edilebilir mekanizmalardır. Gözlenen sağlayıcı maliyeti önceden kesin dolar üst limiti garantisi sayılmayacak. GitHub Actions sadece self-hosted runner üzerinde çalışacak.

Bu belge **v0.52 spesifikasyonudur; gerçek-model uçtan uca başarı veya ücretli çalıştırma tamamlandı iddiası değildir**.

## 17 Ekim 2026 — v0.52 somut uygulama / dürüst kanıt sınırı

**Yeni durum:** `OFFLINE_MODEL_ADAPTER_WIRED / REAL_PROVIDER_MARA_PENDING`.

- `scene_qualified_model_lane_v052.py` yeni shadow lane içinde **gerçek modülleri** birleştirir: bağımsız kaynak-kör çıkarım `v0.22`, kaynak-bağlı otomatik model-yazar adaptörü `v0.21`, **zorunlu `v0.23` full-scene qualification**, otomatik sahne loop `v0.20`. Bu katman yalnız **injected `synthetic/v052-*` provider** kabul eder; production secret/env key okumaz, canlı POST göndermez. Yeni gerçek-provider grant gate henüz devreye alınmadı.
- `test_scene_qualified_model_lane_v052.py`: 8 yeni test (2 cümle Ari'de kendi kendine yeniden yazım + zorunlu full-v0.23 yeniden doğrulama; orijinal 28 cümle Mara eksik kaynak kanıtı fail-safe; sahte gerçek modelin offline yola alınmaması; SHA/WorldState drift; belirsiz yanıt ile durdurma ve replay; 0 rewrite; sahte canonical truth; hiçbir model output-token ceiling).
- [**Tüm SERA regresyon CI #39008646674**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39008646674): ilk deterministic suite **757/757 PASS** (eski 749 + yeni 8).
- `scene_qualified_smoke_v052.py`: kendi kendine tekrar yürütülebilir synthetic kanıt. Ari S1 1 otomatik yeniden yazımdan sonra **full v0.23 noncanonical candidate**; Mara S1 **tam dondurulmuş 28 cümle** ama sentetik model eksik full source yanıtı verdiği için **`FAILED_SAFE_FINAL`**. Her iki ayrı sahnede tekrar başladığında 0 ek model callback. 0 üretim DB/world write, 0 manuel metin/JSON tamiri, 0 yeni ücretli provider.
- [**Özel v0.52 self-hosted CI #39008745878**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39008745878): **SUCCESS: 8/8 focused tests + smoke**. Artefakt `sera-v052-qualified-shadow-39008745878` ID `12091816849`, net durum `SYNTHETIC_ARI_QUALIFIED_MARA_28_FAILED_SAFE`; **Ari'nin iki cümlelik sentetik başarısı Mara'nın 28 cümlelik gerçek başarı iddiası değildir**.

**Sıradaki gerçek blokaj P0/P1:** yalnız ayrı açık ücretli yetkiyle kullanabileceğimiz, global durable single-use grant ve provider makbuz korumasıyla gerçek model transport yolu. Ardından Mara'nın 28 cümlesinin gerçekten tam kaynak-kör çıkarımı → bağımsız doğrulama → model-written rewrite → *yeni SHA üzerinden* tekrar çıkarım/doğrulama. Gold semantic quality ve G2 state yetkisi bu sürümde verilmez. Aion HIGH/MAX önceki ücretli izni SERA için kullanılamaz; model çıktı token sınırı yine yasak.


## 17 Ekim 2026 — P0 dinamik imzalı bütçe / kaynak soy ağacı (deneysel)

**Durum: `DELEGATED_BUDGET_OFFLINE_PROVEN_PARTIAL / REAL_MARA_PAID_PROOF_PENDING`.**
Bu durum gerçek modelle tamamlanmış 28 cümlelik onarım iddiası değildir.

- `delegated_paid_budget_v052.py`: bağımsız Ed25519 imzasına bağlı tek Mara işi; ilk scene/source/world/policy SHA ve dört model rolü; rol bazında çağrı kotası, toplam POST kotası, raporlanmış maliyet gözcüsü, azami yeniden yazım derinliği. Atomik SQLite `BEGIN IMMEDIATE` ile tam istek parmak izi başına kalıcı tahsis; STARTED/unknown veya maliyeti belirsiz herhangi bir önceki deneme yeni harcamayı keser. Gözlenen harcama eşiği **garanti edilmiş fatura tavanı değildir**.
- `delegated_provider_bridge_v052.py`: önceki sahne revision SHA'dan sonraki sahneye geçiş yalnızca receipted Writer generation ID + birebir source/prose doğrulamasıyla açılır; elle değiştirilmiş revizyon, desteklenmeyen model ve token çıktı tavanı reddedilir.
- `authorized_mara_delegated_lane_v052.py`: gerçek `v0.22` kaynak-kör çıkarım, `v0.23` tam sahne doğrulaması, `v0.21` otomatik Writer ve `v0.20` otomatik döngüye bounded delegation bağlantısı; kronolojik scene SHA değişiklikleri için yeni kanıt zorunlu. Normal CI hiçbir provider POST yapmaz.
- `receipt_summary()`: ham sahne/prose veya kimlik bilgisi yayımlamadan provider generation ID, model, gerçek input/output token, varsa reasoning token, varsa gecikme ve provider-reported cost; `RECEIPTED_PRICED` olmayan kayıtlara scene ready hakkı verilmez.
- [14 offline delegated budget testinin bulunduğu CI #39029533548](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39029533548) **SUCCESS**. Sonraki revizyon ve entegrasyon commitlerinin self-hosted CI sonuçları ayrıca doğrulanmalı; eski green sonuç sonraki commit için kanıt sayılmaz.

**Çözülmesi gereken güvenlik/ürün kapıları:** (1) trusted Ed25519 public-key kaynağının dağıtım tarafından sabitlenmesi ve anahtar iptali/rotasyonu, (2) tüm worker'ların aynı sağlam kalıcı journal ve kilitleri kullanmasının üretim düzeyinde kanıtı, (3) yanlış/kırık provider response ve çok aşamalı Writer→new SHA→fresh qualified check testlerinin en güncel committe PASS olması, (4) ayrık tek kullanımlık SERA ödeme izniyle gerçek model denemesi; ayrıca gerçek provider generation/maliyet/kaynak-semantiği verilerinin bağımsız doğrulanması. Hiçbir manuel metin/JSON düzeltmesi, çıktı token ceiling, canonical/G2/production write yetkisi yok. Issue #309 açık kalacak.
