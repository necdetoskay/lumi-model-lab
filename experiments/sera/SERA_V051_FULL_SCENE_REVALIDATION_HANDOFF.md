# SERA v0.51 — Otomatik onarımdan tam sahne kanıtına güvenli geçiş

**17 Ekim 2026 | Deney branch'i: `experiment/sera-scene-state-v0-1-20261015` | SHADOW ONLY | İnsan tamiri YOK**

## Amaç

v0.50 tek tek 5 karantina cümlesini yeniden çıkarıp 21 model ayrışmasını kaynak-kör inceleme sözleşmesine bağlamıştı. Bu düzeyde kaynakla uyumlu cevabı doğrudan sahnenin fiziksel gerçeği saymak hatalıdır. v0.51, **v0.50 işleyicisinin gerçek çıktısını aynı orijinal kaynak SHA'ya bağlayıp**, otomatik şekilde mevcut **v0.22 tam kaynak çıkarımı → v0.21 bağımsız sahne denetimi → v0.20 sahne yeniden yazımı/yeniden denetleme** hattından geçirir.

Önceki onarım adaylarının hiçbirini tam 28 cümlelik kapsama kanıtı olarak sisteme enjekte etmez. Her yeni sahne sürümü ayrı source SHA ve world SHA ile tekrar doğrulanmalıdır; modelin kanıtı veya mutabakatı tek başına G2 izin kaynağı değildir.

## Gerçek kullanılan bileşenler

- `scene_full_handoff_v051.py`: `real_mara_recovery_queue_v049.verified_real_receipts` ile eski 14 gerçek yanıtı yeniden doğrular; `build_work_orders` ile 5 + 21 görev üretir; `automated_row_recovery_v050.execute` ile insan müdahalesi olmadan targeted düzeltme ve kaynak-kör danışmanlık adayları oluşturur.
- **Sıkı kaynak kapısı:** Kaynak SHA, v0.50 çıktı schema/status, tam 26 görev hesabı, truth/canonical alanlarının false olması ve world write 0 doğrulanmadan tam sahneye geçilmez. v0.50 `FAILED_SAFE_FINAL` aşamasında erkenden durursa tamamlanmamış görevleri 'tamamlandı' saymadan tam sahne sağlayıcısına hiçbir istek göndermez.
- `fresh_scene_evidence_worker_v022.create_preparer`: Tam orijinal hikâyenin bütün cümlelerini kaynak-kör biçimde ve kalıcı makbuzla yeniden çıkarmayı dener. Bu deneyde sağlayıcılar **scripted OFFLINE**, ücretli gerçek API değildir. Tam çıkarım başarısızsa status `FAILED_SAFE_FINAL`.
- `artifact_scene_checker_v021.create_checker` ve `unattended_scene_rewrite_v020.execute`: Tam sahne kanıtı hazırsa sahne bağımsız yeniden denetlenir; gerçek kusur tespit edilirse insan müdahalesi olmadan yazıcı çağrısı, yeni source SHA ve tekrar v0.22/v0.21 kontrolü yapılır. Kanıt yoksa bir sahneyi 'düzeldi' varsayıp yazıcı çalıştırılmaz; güvenli sonlandırma uygulanır.
- v0.50 ve v0.22/v0.20 makbuz checkpoint'leri yeniden başlatmada kullanılır. Bilinmeyen faturalandırılabilir provider isteği kör tekrar edilmez, dünya veritabanına yazılmaz; normal hikâye akışına manuel JSON düzeltmesi, review veya retry kuyruğu eklenmez.
- Hem 'tamir başarılı' hem 'replan gerekli' çıktılarını doğru kaynakla ele alır, fakat bunların hiçbirinin kendi başına gerçeklik yetkisi yoktur.

## Deney kanıtları

[**Self-hosted CI #38998048487**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38998048487) **SUCCESS: 749/749 Python testi**. Ek negatif güvenlik testi, replan/failed durumda sahte semantik veya kanonik yetki yükseltmesini de reddeder.

1. **Gerçek Mara S1 geçmiş makbuzları:** v0.48'deki 14 gerçek model yanıtı ve geçmiş gözlemlenen 0,10590625 USD doğrulanır. Orijinal 28 cümledeki beş satır sorunu ve 21 ayrışma için **28 sentetik onarım/inceleme çağrısı (iki fallback)** yapılır. Ardından gerçek v0.22 koduna tam sahne için bilerek **eksik, tam makbuzlanmış iki sentetik model cevabı** verilir. Yetersiz full-scene coverage → `FAILED_SAFE_FINAL`; sahne için gerçek bağımsız kanıt olmadığından writer **0 çağrı**, G2/WorldState değişikliği **0**, yeniden başlatmada yeni callback **0**. Bu, başarının değil **güvenli zorunlu kanıt kapısının** testidir.
2. **İki cümlelik Ari/kutu kontrolü:** Ayrı bir **test-only, kontrollü kaynak-bağlı stage** çıkışı kullanılır; v0.50'nin gerçek Mara çıktısıymış gibi gösterilmez. Gerçek v0.22 worker → gerçek v0.21 checker → gerçek v0.20 controller **bir otomatik sentetik rewrite** yapar, yeni cümlelerden kanıt üretir ve `SCENE_CANDIDATE_READY_NONCANONICAL` sonucuna varır. Yeniden başlatmada model ve writer çağrısı **0**. Bu kontrol gerçek Mara 28-cümle başarısını veya gerçek LLM doğruluğunu kanıtlamaz.
3. Ek güvenlik: farklı source SHA ve world revision, task/provenance drift, tamamlanmamış 26 görev, gerçeklik statüsü sahteciliği ve eksik provider makbuzunun tekrar gönderilmesi engellenir. Durumlar otomatik `FAILED_SAFE_FINAL` ile kapanabilir; insan hikâye tamiri gerekmez.

Kanıt artefaktı `sera-v051-original-real-mara-full-scene-handoff-38998048487` (ID `12087353278`), `proof.json`, v0.50 kaynak-bağlı görev ve receipt kayıtları, v0.22/v0.20 tam sahne kontrol raporlarını içerir.

**v0.51 sıfır yeni ücretli model isteği, sıfır yeni USD, sıfır SQLite/G2 world write, sıfır main merge, sıfır uygulama tanımlı output token tavanı.**

## Henüz kanıtlanmayanlar

- Gerçek Mara S1, 28 cümle için yeni bağımsız **gerçek modellerin** doğru fiziksel olay çıkarımı: **UNPROVEN**.
- v0.50'deki 5 kaynağa yanlış atıflı Haiku satırının **gerçek LLM ile** onarılması: **UNPROVEN**.
- 21 gerçek model olay ayrışmasının fiziksel hakikate göre çözülmesi: **UNPROVEN**.
- Kaybolmuş canlı provider isteği için provider generation ID/GET bazlı authenticated reconciliation: bu deneyde **UNPROVEN**.
- Gerçek dünyaya G2 kanonik commit, M3 ve dünya durumuna transaction yazımı: **NOT AUTHORIZED**.

**Mara S1 HOLD, SceneTrace SHADOW ONLY.**

## Sonraki otomatik kapı (v0.52)

v0.51 tam sahne kontrolünü sonraki **kaynak-kör tam gerçek model çıkarımı, hedefli yeniden çıkarım ve bağımsız karşı kanıt** ile güvenli bağlamak; provider destekli reconciliation, dinamik retry/servis maliyet guard'ları ve replan döngüsünü gerçek model alıntılarıyla otomatik doğrulamak. Tek kullanımlık v0.48 ücretli araştırma izni daha önce tüketilmiştir; yeni gerçek çağrılar için ayrı açık harcama yetkisi gerekir. Ancak **hikâye üretimini manuel düzeltme/onay şartına bağlamayacağız**.

[SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
