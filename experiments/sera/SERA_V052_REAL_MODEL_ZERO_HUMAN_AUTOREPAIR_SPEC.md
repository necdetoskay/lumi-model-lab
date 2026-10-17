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


## 17 Ekim 2026 — CI keşfi ve ücretli imzalayıcı güven izi

- **Kritik CI düzeltmesi:** Genel SERA CI yalnız `experiments/sera/tests` içindeki 757 testi yürütüyordu; ayrı dizindeki 7 v0.52 test modülü atlanıyordu. [#39032984282](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39032984282) sonrasında 757 eski + 68 yeni = **825 Python testi** gerçek self-hosted çalışmada PASS oldu; tarayıcı E2E de başarılı. Yeni workflow ayrıca en az 7 v0.52 test modülü ve en az 68 testin keşfedilmesini zorunlu tutar. Önceki `unittest.TestCase.run` çakışması ve Mara sonuç kaydındaki tanımsız `qualified_receipts` değişkeni otomatik testle bulundu ve düzeltildi.
- **İmzalayıcı anahtarı izi:** `paid_issuer_trust_v052.py`, gerçek model giriş yolunda ham Ed25519 açık anahtarı için bağımsız önceden bilinen SHA-256 izini zorunlu kılar. `authorized_mara_delegated_lane_v052.run_delegated_mara` artık `trusted_raw_key_sha256` olmadan çalışmaz. Yanlış veya eksik iz, ücretli POST ve SQLite journal oluşturulmadan reddedilir.
- **Operasyonel sınır:** `trusted_raw_key_sha256` değeri onay manifestinden, model yanıtından veya aynı güvenilmeyen istekten **alınamaz**. Güvenli dağıtım konfigürasyonu / kontrol edilen trust-store aracılığıyla ayrıca sabitlenmelidir. Uygulama seviyesinde parametre eşleştirmesi bu bağımsız dağıtım sabitlemesinin yerine geçmez. Anahtar iptali/rotasyonu, tüm worker'lar için tek yetkili durable journal ve gerçek sağlayıcı makbuzlarının maliyet/semantik doğrulaması hâlâ tamamlanacak kapılardır.
- **Kesin kanıt ayrımı:** Bu çalışmalar tamamen çevrimdışı; Mara'nın gerçek LLM ile 28 cümle otonom onarımı henüz gerçekleşmedi; Issue #309 açık ve LAB noncanonical sınırı değişmedi. Önceki Aion yetkisi SERA çağrılarına aktarılmaz. Çıktı token tavanı, manuel hikâye tamiri veya production/G2 yazımı yok.


## 17 Ekim 2026 — Tek-host güvenli ücretli çalışma alanı ve iptal denetimi

**Durum: `LOCAL_SIGNED_RUNTIME_OFFLINE_PASS / HOST_DEPLOYMENT_AND_REAL_28_SENTENCE_PAID_PROOF_PENDING`.**

- `paid_runtime_boundary_v052.py`: Ayrı dağıtım sahibinin korunan trust dosyasını okur; anahtar SHA-256 izi, değişmez journal UUID'si, tam journal yolu, makine kimliği ve iptal edilmiş `approval_id` listesi bekler. Dosya/üst dizin izinleri, symlink'ler, SQLite inode+device/path/host uyuşması kontrol edilir. Kopyalanmış veya eksik SQLite yeni bir ücretli denemeye otomatik dönüştürülmez.
- `provision_local_journal()` **yalnız bir defalık altyapı bootstrap aracıdır**, üretim hikâyesinde kullanıcı onayı / elle düzeltme kapısı değildir. İzin veren imza bu işlevde üretilemez. Hikâye worker'ı günlük oluşturamaz; önceden kayıtlı kimliği kontrol eder.
- `authorized_mara_delegated_lane_v052.py`: Kaynak ve rol kapsamına bağlı imzalı izin doğrulandıktan sonra bile her yeni provider talebinde korunan dağıtım kaynağından güncel iptal listesi ve journal kimliği tekrar okunur. İptal edilmiş `approval_id` yeni harcama başlatamaz. Ongoing koşulu değişmiş trust/journal yolu da fail-closed durur; unknown inflight **asla** kör POST tekrarına dönüşmez.
- **Kritik mimari sınır:** Bu SQLite tek-host yerel-disk tasarımıdır, *çok makineye dağılmış merkezi veritabanı* değildir. NFS/shared drive veya birbirinden habersiz ayrı worker hostları için tekil ücretli POST garantisi ileri sürülmez. Gerçek dağıtıma geçmeden önce tek otoriter host + disk kalıcılığı, erişim hakları ve yedek/restore kimliği test edilmelidir; çok-host ihtiyacında ayrı transaction-safe koordinatör/PostgreSQL gerekir. `max_observed_usd` gerçekleşmiş maliyet gözcüsüdür, provider fatura tavanı garantisi değildir.
- Korunan trust dosyası gerçek dağıtımda model worker'ın keyfi değiştiremeyeceği **salt-okunur operatör sahipli yapılandırma** olarak sağlanmalı; kodun geçirdiği offline izin testleri bu sunucu dağıtımının gerçekleştiğini **kanıtlamaz**.
- [**Self-hosted CI #39034386061**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39034386061): **SUCCESS**, 757 önceki + 88 v0.52 Python testi (8 modül) ve tarayıcı E2E. Testler no-network; model provider ücreti `0`. Güncellenen workflow minimum 88 yeni testin keşfini zorunlu kılar.
- Hâlâ gerçek SERA ücretli yetkisi/provision edilmiş trust/durable host kanıtı ve orijinal 28 cümle Mara'nın **gerçek model** üretimi + writer-revision + bağımsız full-v0.23 doğrulaması yok. Issue #309 açık, canonical/G2 ve production DB yazım yetkisi sıfır.


## 17 Ekim 2026 — Çalışan süreçte dosya değişimi ve son HTTP kapısı

- **Yarış durumu giderildi:** `ProviderJournal` artık ücretli yolda önceden kayıtlı `(st_dev, st_ino)` kimliğini **her SQLite bağlantısından önce ve sonra** kontrol edebilir. Ücretli mod `mode=rw` açar, eksik veritabanını kendiliğinden yaratmaz ve `grants`, `calls` veya `paid_runtime_identity` şeması kaybolmuşsa yeni tablo oluşturmaz. Bu kontrol ancak `open_bound_paid_journal()` ile sabitlenmiş gerçek ücretli entrypoint için uygulanır; eski laboratuvar Journal fixture'ları değişmez.
- **HTTP öncesi iptal doğrulaması:** `bind_revocation_checked_transport()` model safhasındaki kontrole ek olarak gerçek network transport çağrısı sınırında korunan iptal listesi, güven/anahtar değişimi ve journal kimliğini yeniden okur. İptal edilmiş yetki yeni provider POST yapamaz; `STARTED` olarak kayıtlı olsa bile sonuç belirsizliği ikinci POST ile onarılmaz.
- **Bağımsız süreç testi:** `test_paid_runtime_boundary_v052.py` aynı pre-provisioned tek-host SQLite günlükte dört ayrı Linux process ile aynı isteğe rakip olduğunda yalnız bir fake POST gözlenmesini sınar. Bu test provider API'sine çıkmaz.
- **CI teminatı:** Ana self-hosted workflow en az 8 modülde **94** yeni v0.52 no-network testinin keşfedilmesini zorunlu kılar. Entegrasyon commitlerinin son CI sonucu ayrıca doğrulanmalıdır.
- **Sınırlama:** Config'ten gerçek HTTP gönderimine kadar tamamen atomik *harici* iptal garantisi yoktur; dosya değişikliği son kontrolden hemen sonra gerçekleşebilir. Bu yüzden yalnız aynı-host iş yürütme ve fail-closed journal sağlanır, dağıtık exactly-once/fatura garantisi verilmez. Güven dosyası model worker'ı tarafından değiştirilebiliyorsa yalnız dosya mode ve imza izi güvenilir ayırma değildir; gerçek deployment owner/UID ve salt-okunur mount kontrolü ayrıca gereklidir.
- **Henüz kanıtlanmayan:** ayrı imzalanmış ücretli SERA izin, gerçek OpenRouter provider POST, tüm 28 cümle Mara'nın Writer/yeniden çıkarım/bağımsız v0.23 PASS sonucu, canonical G2 commit. Bunlar başarı olarak raporlanamaz.


## 17 Ekim 2026 — Orijinal Mara 28 cümle / imzalı gerçek-wire çevrimdışı karşıt testler

**Amaç:** Gerçek OpenRouter endpoint şekline sahip, ama ağ göndermeyen enjekte edilmiş model yanıtlarıyla tam Mara kaynak-sahnesinin imzalı/kalıcı ücretli istek katmanında doğru fail-safe davranışını doğrulamak. Böylece `2 cümlelik Ari` yeşili artık tek dayanak değildir.

- `test_real_wire_shape_28_sentence_mara_incomplete_evidence_is_failed_safe`: frozen Mara SHA ve 28 cümleyle gerçek `run_delegated_mara` -> imzalı `DelegatedBudget` -> gerçek HTTP Request/JSON şeması -> enjekte edilmiş tekli mock OpenRouter cevabı -> `ProviderJournal` RECEIPTED -> `v0.22` kaynak kanıtı. Model, gerekli hedef satırlarını eksik (`rows: []`) döndürdüğünde sonuç **`FAILED_SAFE_FINAL`**, `0` otomatik metin düzeltmesi, `0` G2/world yazımı, `0` yanlış tam-sahne denetimi işareti. Yeniden başlatmada **yeni POST yok**.
- `test_all_28_rows_but_no_physical_events_cannot_fake_scene_success`: `sentence_sweep_v010` planına uygun **yedi ayrı dört-cümlelik batch** ve kaynak SHA ile birebir bağlı **28/28 cümle kaydı** üreten adversarial model. Aynı model bütün fiziksel olayları, nesneleri ve nedenleri yanlışlıkla `NO_TRACKED_CHANGE` olarak boş bıraktığında `v0.22/v0.23` hattı bunu **başarı saymaz**, güvenli terminale geçer; yedi istek kalıcı RECEIPTED ve yeniden başlatmada **yeni POST yok**. Bu bilinçli eksik veri, gerçek model tarafından hazırlanmış **tam bir hikâye onarımı değildir**.
- `authorized_mara_delegated_lane_v052.py` sonuç şemasında `full_scene_qualification_gate_invoked` artık sabit `True` değil, gerçekten `controller/check_*.json` üretildiyse `True`. Eksik kanıt nedeniyle sahne denetimine hiç varılmadığında sahte PASS raporlanamaz.
- Self-hosted CI, sekiz kök v0.52 modülünde **en az 96** testi çalıştırmayı zorunlu tutar; orijinal 757 ile birlikte **853 Python testi** olur. Ağ sahte; OpenRouter fatura artışı `0`. Testlerin gerçek `mara_28_semantic_pass` olmadığını açıkça etiketleyin.
- **Sonraki P0:** Kendiliğinden ve tamamen doğru 28-cümlelik model üretimi + yazar-kanıtlı yeni SHA + her satırın yeniden çıkarımı + bağımsız `v0.23` tam sahne kanıtı; gerçek sağlayıcı denemesi için ayrı, imzalı ücretli izin ve korunmuş tek-host çalışma alanı gerekmektedir. Çıktı token tavanı, sahneye el ile müdahale ve üretim WorldState commit yetkisi verilmez.


## 17 Ekim 2026 — Modelin kendi geçerli ama eksik çıkarımını otomatik onarma

**Kapsam:** `fresh_scene_evidence_worker_v022.create_preparer(max_source_repair_attempts=1)` artık frozen Mara LAB model hattında etkindir. Bu varsayılan v0.22 davranışını başka eski hatlarda değiştirmez (`0`).

1. **Kalıcı, ücretlendirilmiş yanlış JSON/eksik satır:** `provider_json` önce sağlayıcı yanıtının makbuzunu eksiksiz kaydeder. Tamamlanmış fakat validator'dan geçemeyen cevabın ardından yeni `..._source_repair_1` isteği oluşturur. İkinci istek **yalnızca orijinal kaynak, sistem yönergeleri ve sınırlı deterministik hata kodunu** içerir; önceki model çıktısı, Writer analizi veya altın doğru cevap eklenmez. Farklı SHA ve grant ID ile aynı imzalı harcama sınırına tabidir.
2. **28/28 satır ama atlanmış fiziksel olaylar:** `sentence_sweep_v010.aggregate` çıktısındaki `SWEEP_UNACCOUNTED_ACTION_CUE`, `SWEEP_MISSING_ENTITY_HINT`, `SWEEP_UNRESOLVED_SENTENCE`, `SWEEP_UNMAPPED_EVENT`, `SWEEP_CLAIM_PROMOTED_TO_WORLD`, `SWEEP_EXPECTED_EVENT_NOT_EXTRACTED`, `SWEEP_POSSIBLY_MISCLASSIFIED` bulguları, yalnızca ilgili orijinal dört-cümlelik paketler için **kaynak-tabanlı hedefli yeni çıkarımı** tetikler. Eski model hükmü kaynak verisi olarak sunulmaz.
3. **Bounded/fail-closed:** Fazladan otomatik denemeler kaynağın SHA'sı, mevcut imzalı rolsel POST limiti, `max_model_requests` ve gözlenmiş USD limiti altında kalır. Eksik/STARTED/belirsiz ağ makbuzu yeni istekle tamamlanmaz; otomatik tekrar **yasak**. Tüm kaynak ipuçları hâlâ karşılanamıyorsa `V022_SOURCE_COVERAGE_REPAIR_EXHAUSTED` ile durur; sırf satır sayısı tam diye sahne başarılı sayılmaz.
4. **Pozitif kanıt:** `test_signed_autorepair_positive_v052.py` sahte sağlayıcıyla bozuk yanıtı yeniden çıkarır, ardından gerçek v0.21 Writer adaptörü kaynak SHAsını değiştirir, yeni kaynak kanıtlarını üretir ve v0.23 tam-sahne denetimini geçirir. Ek pozitif test ilk modelin fiziksel olayı atlamasını simüle edip aynı otomatik safhaların tekrar çalışmasını doğrular. Bu **iki cümlelik Ari** kontrolüdür; gerçek Mara semantik doğruluk kanıtı değildir.
5. **Orijinal 28 Mara karşıt kanıtı:** `test_authorized_mara_delegated_lane_v052.py` gerçek 28-cümleli source SHA ile yedi orijinal cümle paketi ve yalnız gerektiğinde kaynak-tabanlı yeni denemeleri, imzalı grant/journal + gerçek HTTP biçimi altında çalıştırır; fiziksel olayları atlayan model güvenli durdurulur ve yeniden başlatmada POST tekrarlanmaz. **Gerçek sağlayıcı LLM çağrısı, ücretlendirme ve 28-cümlelik başarılı tam onarım yapılmış değildir**.

Model **çıktı token limiti konulmadı**; `max_source_repair_attempts` model çıktı uzunluğu değil, kullanıcı onayı kapsamına bağlı ücretli yeniden istek sayısıdır. Canonical/G2/production veritabanına yazım yoktur, hikâye/JSON için manuel tamir yoktur.


## 17 Ekim 2026 — 28 cümleli kaynak kronolojisi ve zaman damgası doğruluğu

Yeni `source_chronology_v052.py`, her gerçek kaynak SHA'sı için **tam kaynak cümle sırası** ve opsiyonel bağımsız modelin kaynak-bağlı olay adaylarını kaydeder. `authorized_mara_delegated_lane_v052.py` her `proven_preparer` girişinde `source-chronology/<prose_sha>.source.json` üretir; ancak tam kanıt gerçekten hazırsa `<prose_sha>.model.json` içine `full_sweep` adaylarının kaynak açıklamalarını koyar.

**Neden:** Hikâyedeki `02:07` durmuş bir saatin göstergesi, `02:10` ise rapor/manifest içinde anlatılan saat olabilir. **Bunlar aksiyonun kanıtlanmış gerçekleşme zamanı değildir.** Bu nedenle kronoloji `source_ordinal` (metinsel sıralama) ile `action_minute=null` (gerçek zaman bilinmiyor) alanlarını ayrı tutar. Metinden kopyalanmış alıntıların codepoint [start,end) aralıkları ve tam kaynak hash'i tekrar doğrulanır. Modelin önerdiği `MOVE`, `WRITE` vb. yalnız `MODEL_CANDIDATE_UNVERIFIED` statüsündedir; fiziksel varlık, nedensellik, sahiplik veya canonical WorldState/commit iddia edilmez.

`test_source_chronology_v052.py` gerçek frozen Mara 28/28 satır bütünlüğü ve yeniden oynatımda aynı digest, yanlış aksiyon saati, çarpıtılmış olay alıntısı, eksik/çift satır ve source/world drift testlerini içerir. Mara gerçek izinli lane ayrıca kaynağın kronolojisini önceden/yeniden başlatmada saklar; kaydedilmiş nihai durum tekrar kullanılmadan önce orijinal SHA'dan yeniden üretip tarar. Böylece biri bir olaya sonradan `action_minute=130` eklese bile cached `LAB_CANDIDATE` veya cached fail record güvenilir sayılamaz.

**Sınır:** Bu kanıt, semantik hatırlama, gerçek olay zamanı, karakter/nesne ilişkileri veya Mara 28'in Writer ile başarıyla onarımı değildir. Bunlar için güvenilir fiziksel dünya kaynağı, doğrulanmış olay kimlikleri ve kaynak-bağlı model onarımı gerekir. Tüm çalışma OFFLINE/LAB; gerçek provider faturası, manuel hikâye/JSON düzenlemesi, çıktı token tavanı veya üretim veritabanı/world commit **yoktur**.


## 17 Ekim 2026 — v0.53 imzalı fiziksel başlangıç durumu ile sahne olaylarının ayrılması

**Mimari karar:** `g2_physical_pinned_reader_v036.project_pinned_physical` temel otoritedir; sahne modelinin önerdiği yeni olaylar ayrı, kaynak-bağlı ama **yetkisiz** kanıtlardır. `signed_physical_reconciliation_v053.reconcile_signed_physical_source` yalnız uygulamanın koruduğu Ed25519 açık anahtar izi, imzalı G2 fiziksel snapshot, doğrulanmış G2 scope ve **tek kullanımlık app-owned nonce** ile çalışır. Eski `v0.33` imza doğrulamasını atlayabilen callback doğrudan üretim yolu olarak çağrılmaz. İmza bir kaynak tablosunun bütünlüğünü doğrular; modelin `TRANSFER`, `MOVE`, `LEARN_FACT` vb. olay önerisini gerçek olarak kanıtlamaz.

**Read-only sonuç:** Tüm imzalı giriş karakter/nesneleri için kayıtlı `entity_id`, `location_id`, `owner_id`, `holder_id`, `worn_by_id` bilgileri ve rota adedi raporlanır. Modelin her olay adayı birebir cümle kimliği/alinti/offset ile eşleştirilir. İmzasız veya yabancı nesne `ENTITY_IDENTITY_NOT_PHYSICALLY_REGISTERED`, aktarılan/olumsuzlanan ifade `CLAIM_OR_UNCERTAIN_NOT_OBJECTIVE`, kayıtlı nesneye yönelik hareket ise `REGISTERED_BASELINE_ONLY_EVENT_NOT_ATTESTED` konumundadır. `verified_future_event_count=0`, `proposed_effect_allowed=false`, `action_minute=null`, `world_mutations_performed=0`, `canonical_commit_authorized=false` kalır. Bu ayrım modelin taslağından dünya durumuna yetkisiz geçişi engeller.

**Önemli Mara sınırı:** Mevcut 28 cümleli LAB Mara `entry_state()` bellekte yaratılmıştır; G2'nin bağımsız imzalı fiziksel snapshot'ı değildir. İlgisiz dünyaya ait **geçerli** G2 imzasını sunmak da bu Mara kaynağına fiziksel otorite kazandırmaz: `world_sha256` ve kaynak kronolojisi birebir uyuşmalıdır. Dolayısıyla bu sürüm **gerçek Mara fiziksel otorite kaynağı hazır** demek değildir; v0.53 yalnız güvenilir kaynak geldiğinde devreye girecek uzlaştırma kontratını ve fail-closed kanıtlarını kurar.

**Testler:** `test_signed_physical_reconciliation_v053.py` içinde çevrimdışı oluşturulan TEST anahtarı ve G2 fiziksel fikstürüyle; gerçek imza doğrulaması, tek-use nonce, yabancı dünya SHA reddi, aday aktarımlarının doğrulanmış olay sayılmaması, kaynaktaki iddiaların fiziksel varlık olmaması, bilinmeyen nesne kimliği, sahte alıntı, şema bozukluğu ve imzasız snapshot reddi sınanır. Testte yaratılan imzalama anahtarları gerçek sunucu trust root'u değildir. Asıl canlı G2 fiziksel kayıt ve dağıtım trust-store'ı ayrı P0 engelidir.

**Kesin kaynak/süreç kuralları:** Orijinal Mara metni hiçbir şekilde elle düzeltilmez; altın doğru cevabı model talebine verilmez; `max_tokens` ve benzeri model çıktı token tavanları kullanılmaz; ayrı SERA imzalı ücretli izin yoksa gerçek provider POST yapılmaz; production WorldState/G2 commit yok.


## 17 Ekim 2026 — Hikâye hattına dönüş: Mara kayıtlı typed facet boşluğu

Kritik hata düzeltmesi: `authorized_mara_delegated_lane_v052.py` tarafından v0.22 worker'a verilen `typed_registry` eskiden iki kategori için de `[]` idi. Oysa donmuş gerçek Mara 28 kaynak sahnesinin v0.2 entry-world'ünde zaten `vane_watch` nesnesi Vane tarafından tutuluyor, `mara_notebook` ise Mara'nın elinde. Modelin bu iki kaynağa bağlı `CLOSE` ve `WRITE` adaylarını v0.13'e sunmasına izin vermeyen boş registry, sağlam bir kaynak çıkarmasını bile yanlış biçimde devre dışı bırakıyordu.

Şimdi `registered_mara_facets(world)` yalnız zaten dünyada kayıtlı, ACTIVE OBJECT olan ve doğru sahip/tutan bağına sahip `vane_watch` = `openables`, `mara_notebook` = `documents` kabiliyetlerini bildirir. Bu kayıtlar **olay kanıtı veya model cevabı değildir**. Vane saati gerçekten kapattı mı, Mara deftere hangi tam metni ekledi, her olayın exact source span'i ve öncesi/sonrası ancak bağımsız model + typed v0.13 kontrolüyle doğrulanabilir. Bilinmeyen bench/pencil veya train arrival gerçek varlık veya fiziksel olay olarak sisteme eklenmez.

`test_mara_registered_facets_v052.py` donmuş orijinal 28 cümleyi değiştirmeden, testin kendi source-bound *simulated approval* kontrolünde (1) gözlenen saatin OPEN konumu, (2) Vane'in sonradan case'i kapatması, (3) Mara'nın deftere **kaynakta harfi harfine yazılı** içeriği eklemesi zincirini deterministik v0.13 replay ile sınar; sahte alıntıyı, iki kere uygulamayı, değişen başlangıç holder ilişkisini ve modelin kendi kendine dünya durumunu yazabilmesini reddeder. Bu **fiziksel altküme regresyon testi**dir; 28 cümleyi otomatik anlamış gerçek bir LLM veya bağımsız v0.23 FULL_SCENE PASS sonucu değildir. Testteki simülasyon onayı üretimde asla kullanılmaz.

**Aktif kilometre taşı yine aynı:** Frozen Mara 28 → otomatik Writer gerektiğinde yeni metin → yeni kaynak SHA için bağımsız tekrar çıkarım → tam v0.23 semantic/fiziksel/zamansal doğrulama → kaliteli hikâye ve zero-human restart kanıtı. Kullanıcının önceliği gereği LUMI G2 veri şeması/deploy çalışmaları ertelenmiştir. Tam hat başarılı olmadan bu altküme testini teslim veya yayın onayı olarak değerlendirmeyin.


## 17 Ekim 2026 — Frozen Mara 28/28 mekanik kaynak-kapsama kontrolü

`test_mara_28_mechanical_source_control_v052.py`, donmuş ve SHA ile sabitlenmiş orijinal Mara 28 cümlesini **yedi dörder cümlelik v0.10 paket** üzerinden `create_plan → bind_batch → aggregate` hattından geçiriyor. Testin `simulate_blind_coverage` fonksiyonu gold/elle yazılmış olay JSON'u okumaz; mevcut kaynak tarayıcısının bulduğu metinsel varlık ve fiil alıntılarından sentetik, **her biri `UNCERTAIN`** olay adayları üretir. Hiçbir aday fiziksel gerçek olarak onaylanamaz.

Bu mekanik kontrolün amacı: eksik cümle, kayıp kayıtlı/candidate nesne veya örtülmemiş `PHYSICAL_CHANGE`/`DOCUMENT_CHANGE` fiili olursa v0.10'un `SWEEP_*` bulgusu verdiğini ve doğrulama kapısının kazara bunu yok saymadığını ispatlamaktır. Ortaya çıkan `HOLD_MODEL_SEMANTICS_UNVERIFIED`, başarısızlık değil **dürüst sınır**: sentetik fiil satırları model semantik çözümlemesini veya 28/28 v0.23 sahne başarısını kanıtlamaz. İkinci test kaynak değişim fiili çıkarıldığında `SWEEP_UNACCOUNTED_ACTION_CUE` üretildiğini doğrular.

**Net sonraki adım:** aynı 28-cümle paketini gerçek bağımsız extractor çıkarsın; gerekli kayıp `bench`/`pencil` kimlikleri ile `watch`/`notebook` fiillerini belirtip Writer bunu otomatik düzeltsin; güncellenen her kaynak SHA için yeni ekstraksiyon ve bağımsız v0.23 geçişi sağlansın. Tek başına bu testlerin yeşil olması `LAB_CANDIDATE_READY` veya release demek değildir.
