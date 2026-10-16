# SERA v0.47 — Gerçek v0.22 fallback + v0.20 otomatik yeniden yazım (shadow lab)

**Tarih:** 16 Ekim 2026 · Branch: `experiment/sera-scene-state-v0-1-20261015` · Test: [CI #38954533957](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38954533957) **SUCCESS, 718/718 Python testi**.

## Karar bağlamı

v0.46, önceki **gerçek** Mara Gemini/Haiku risk kartlarını v0.45 hedefli kaynak sorgulaması → mevcut v0.18 source-binder → mevcut v0.22 full scene worker üzerinden geçirdi; tam sahneye `{"rows":[]}` verildiğinde beklenen biçimde `FAILED_SAFE_FINAL` ile durdu. Bu başarısız örneği "onarım tamamlandı" diye göstermedik.

v0.47, mevcut SERA'nın aynı modülleri üzerinde **başarılı bir kurtarma yolunu** ispatlar: tam alınmış ama geçersiz bir model yanıtından sonra başka modele otomatik geçiş, ardından gerektiğinde sahnenin otomatik yeniden yazılması ve yeni kaynak üzerinden tekrar çıkarılması, kaynak-kanıt kontrolü, kaydedilmiş yanıtların yeniden kullanılması.

**Sınır:** Bu sürümde iki cümlelik **sentetik Ari/kutu** kontrol örneği ve test sağlayıcısı kullanılır. Gerçek Mara S1 28 cümlesi, canlı model kalitesi, gerçek semantik hatanın bağımsız düzeltilebilirliği, üretim G2 ve yeni bir ücretli OpenRouter çağrısı **kanıt kapsamının dışındadır**. v0.46 gerçek Mara `HOLD` durumu aynen korunur.

## Mevcut altyapının gerçek kullanım yolları

`scene_trace_full_fallback_v047.py` mevcut `fresh_scene_evidence_worker_v022.create_preparer`, `artifact_scene_checker_v021.create_checker`, `unattended_scene_rewrite_v020.execute`, ve `scene_trace_shadow_v042.build_trace` modüllerini doğrudan çağırır. Bunların güvenlik kontrollerini veya durum sözleşmelerini taklit eden yalancı PASS fonksiyonları kullanılmaz.

İlk ekstraktör `synthetic/sweep-independent` geçerli provider envelope içinde **kasıtlı geçersiz cümle dizisi** `{"rows":[]}` üretir. Model yanıtı alınmış ve makbuzlanmış olduğundan v0.22 aynı orijinal kaynak-kör istemi farklı `synthetic/v047-independent-extractor-fallback` model double'ına geçirir. Yedek model v0.22 testlerinde kullanılan kaynak-bağlı olay çıkarım sözleşmesini uygulayarak uygun iki cümle cevabı üretir. v0.22 bağımsız full sweep, semantic ve typed kanıtlarını hazırlar; v0.21 checker ve v0.20 controller sonucu yeniden denetler. Kanonik yayın yetkisi verilmez.

Controller'ın ilk kaynak `Ari looked at the box. Ari closed the box.` sürümünde gerçek v0.21 kapıları düzeltme gerektirdiğinde **scriptlenmiş yazıcı** değişmiş metin `Ari saw the box open. Ari closed the box.` döndürür; v0.20 yazıcı makbuzunu (test amaçlı simüle edilmiş) bağlayarak ikinci sahne çıkarımını yeni source SHA ile yapar. Bu deney dışına sahne yeniden yazma izni çıkmaz.

## CI'dan doğrulanmış dört senaryo

| Senaryo | İstek sayısı (simüle) | Yedek ekstraktör çağrısı | Yeniden yazım | Sona erişim |
| --- | ---: | ---: | ---: | --- |
| Geçersiz ilk model, geçerli ikinci model | 3 | 1 | 0 | `SCENE_CANDIDATE_READY_NONCANONICAL` |
| Hatalı ilk sahne, fallback + otomatik rewrite + tekrar kontrol | 6 | 2 | 1 | `SCENE_CANDIDATE_READY_NONCANONICAL` |
| Her iki sağlayıcı da makbuzlanmış geçersiz sonuç verdi | 2 | 1 | 0 | `FAILED_SAFE_FINAL` |
| İlk çağrı yanıtsız, potansiyel faturalandırma belirsiz | 1 | 0 | 0 | `FAILED_SAFE_FINAL` |

Bütün senaryolar tamamlandıktan sonra aynı kontrol kayıtları üzerinden yeniden çalıştırıldı ve **tüm ikinci çalıştırmalarda 0 yeni callback/model/yazar işlemi** görüldü. Eski kaynak ile yeni kaynağın full-scene evidence dosyaları ayrı source hash'lerde kaldı. İki kaynak için de SceneTrace iki kaynak cümlesi oluşturdu; uygulama tarafından uydurulmuş kesin olay saniyesi, kanonik olay yetkisi veya fiziksel state delta yok.

## Güvenlik sınırı

- `OPENROUTER_API_KEY` kullanılmaz, gerçek API çağrısı **0**, gerçek maliyet **0 USD**. Simüle edilerek provider `usage.cost` alanına yazılan tutarlar **gerçek harcama değildir**.
- Sadece önceden eksiksiz ve geçerli provider zarfıyla saklanan **geçersiz** yanıt için farklı model fallback denenebilir. Kayıp/yanıtsız zarf için ikinci faturalanabilir çağrı başlatılmaz; terminal güvenli sonlandırma vardır.
- Source SHA ile kanıt dosyası, writer revision, modeli doğrulayan source-span ve v0.21 checker ayrı kalır.
- Hiçbir durumda Project_LUMI DB ya da SQLite world state yazılmaz; dünyaya canonical commit verilmez, insanın üretim hattında elle düzeltme yapması gerekmiyor.
- Hiçbir uygulama kaynaklı **model output token sınırı** tanımlanmaz.
- İki cümlelik sentetik fixture v0.47'nin "tam sahne" kavramının kapsamıdır. Mara S1 için 28 cümlede gerçek modelin tam source event recall/precision başarısı **kanıtlanmadı**.

## Sıradaki kabul kapısı

Yeni bir sürümde gerçek Mara S1'in 28 cümlesini tam kapsayan **bağımsız kaynak-kör model çıkarımı** ve mevcut otomatik repair mekanizmasının ücretli/gerçek yanıtlarıyla test edilmesi gerekir; bu çalışma ayrı maliyet ve provider güvenlik izniyle planlanmalıdır. v0.46'nın gerçek 8 cümlelik risk taban çizgisiyle karşılaştır, provider receipt/idempotent reconciliation denetimi yap, hatalı state transition/UNKNOWN actor üretimini bağımsız doğrula. Sonuçlar iyi çıkmadan SceneTrace'i çekirdek SERA pipeline'ına bağlama. Orijinal Mara S1 hâlâ **HOLD**.

## Kanıtlar

[Self-hosted CI #38954533957](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38954533957) · Artefakt `sera-v047-recovery-shadow-evidence-38954533957` ID `12070082061`, `proof.json` dört senaryonun koşumunu ve yeniden başlatma ispatını içerir.

Backlog: [SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
