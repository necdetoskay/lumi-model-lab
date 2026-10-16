# SERA v0.49 — Gerçek Mara 14 makbuzdan 26 otomatik kaynak-kör onarım görevi

**16 Ekim 2026 | Branch:** `experiment/sera-scene-state-v0-1-20261015` | **SHADOW ONLY, NO WORLD/G2 AUTHORIZATION.**

## Amaç ve gerçek durum

v0.48'in tek kullanımlık gerçek sağlayıcı deneyi [#38957808652](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38957808652) 28 Mara S1 cümlesini 7 dört-cümlelik gruba ayırdı; Gemini 3.7 Flash ve Claude Haiku 4.5 ile toplam **14 gerçek API yanıtı** ve **0,10590625 USD gözlemlenen maliyet** üretti. Gerçek event-semantik doğruluğu kanıtlanmadı.

Gözlemlenen bulgular:
- Gemini **28/28** cümleyi exact source-span'a bağladı; Haiku **23/28** bağladı.
- Haiku s006, s014, s018, s021, s024 cevapları **`SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE`** sebebiyle karantina.
- 23 ortak source-bound cümleden **21'inde farklı önerilen olay imzası** var: s001, s002, s003, s004, s005, s007, s008, s009, s011, s012, s013, s015, s016, s017, s019, s020, s022, s025, s026, s027, s028.
- Önceki hatalardan iki risk var: Haiku s004, saatin zaten açık oluşunu `CHANGE_STATE` gibi yorumlamış olabilir; Gemini s022 gözlemlenen kalem hareketi için `MOVE` üretmiş. Bu ikisi semantik **uyarı**, bağımsız olarak kanıtlanmış nihai hüküm değil.

## v0.49'un yaptığı gerçek işler

1. **Makbuz bütünlüğü:** `result.json` SHA256 `91bb4ddc72c6c104ee3322808e08e3a9cdda40a95a460225f4a3717680adad64` sabit; 14 ayrı `provider_reply_01..14.json` ham dosyası önceki `receipt_sha256` ile kontrol ediliyor. Kaynak fingerprint, batch request SHA, model/receipt ID, yanıtın bittiği durum, maliyet ve kişi/çıkarım raporları mevcut `real_full_scene_blind_v048.assess_received` ile **yeniden hesaplanıp** arşiv özetiyle karşılaştırılıyor.
2. **Kapsam matrisi:** 5 kaynak alıntısı karantinası + 21 model ayrışması = 26 benzersiz cümle-görevi. Hiçbir eksik cümle "incelendi" yapılmıyor; iki risk kaydı kendi ilgili görevlerine bağlı.
3. **Kaynak-kör sorular:** Mevcut `semantic_risks_v011.make_task_request` kullanılıyor. Model talebine yalnız **tam kaynak cümlesi, kaynak SHA, görev ID ve genel fiziksel/nedensel soru** gidiyor. Önceki Gemini/Haiku cevabı, risk kodu, istenen doğru yanıt veya gold etiket asla verilmiyor.
4. **Gerçek yanıt bağlama kodu:** Mevcut `semantic_recovery_v018._bind` bağımsız soru yanıtını kaynak alıntısına bağlayabiliyor. Bunu doğrulamak için **26 scriptlenmiş yanıt** kullanılıyor, gerçek sağlayıcı gönderimi yapılmıyor. Bunlar yalnız `SOURCE_BOUND_MODEL_ADVISORIES_NONCANONICAL` durumunda kalıyor.
5. **Restart güvenliği:** `started`, `reply`, `request_sha256` ve kaynak kimliği saklanıyor. Tam kayıt yeniden çalıştırıldığında **0 yeni callback**, started ama makbuz yoksa **`FAILED_SAFE_FINAL`**. Sahte kaynak alıntısı reddediliyor; fiziksel dünya değişikliği veya kanonik yayın başlatılmıyor.
6. **Kullanıcı istediği politika:** Üretim akışında elle hikâye düzeltme/olay tasdik etme zorunluluğu yok; belirsiz kaynak ve kötü yanıt makineye ait fail-safe durumuna düşüyor. Output-token tavanı **kullanılmıyor**.

## Self-hosted CI kanıtı

[**SERA v0.49 #38959739074 — SUCCESS, 733/733 tests**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38959739074).

- 14 eski gerçek makbuzun yeniden kontrolü, 26 otomatik kör görev oluşturulması, 26 adet kaynak-bağlı sentetik cevap ve bunların **26/26 ayrı replay** doğrulaması.
- Artefakt: **`sera-v049-real-mara-26-blind-recovery-tasks-38959739074`**, ID **`12071663511`**. `work_orders.json`, `contract.json`, 26 adet `task_*.request.json`, scriptlenmiş response makbuzları ve `proof.json`.
- **Yeni gerçek model isteği 0, yeni gerçek maliyet 0 USD, kanonik commit 0, G2/SQLite dünya DB yazısı 0.**

## Doğruluk sınırları

**Önemli:** Source-bound ≠ fiziksel olayın doğru anlaşılması. 26 görev üretildi ama 5 karantina satırı **yeni gerçek modelle yeniden çıkarılmadı**, 21 ayrışma **yeni bağımsız gerçek modelle çözümlenmedi**. 26 scriptlenmiş cevap sentetik ve genel `UNCERTAIN` durumundadır; bunları real-LLM semantik düzeltme başarısı olarak raporlamak doğru değildir.

Model mutabakatı gold/gerçeklik değildir. Mevcut gerçek Mara S1 hikâyesi **HOLD**; herhangi bir yeni canonical approval, otomatik final dünya olayı veya üretim sürüm birleştirmesi yok. Kullanıcıdan ücretli onay alınmadan yeni OpenRouter çağrısı başlatılmaz.

## Sonraki uygulama adımı

v0.50'de **ayrı yetkilendirilmiş gerçek bağımsız kaynak-kör re-extraction** bu 26 görevi otomatik çalıştırabilir. Gerçek makbuzları kaynak/kimlik için güvenli saklayıp 5 karantinayı *yeniden* doğrulamadan kaldırmamak; 21 ayrışmayı otomatik bağımsız semantik hüküm ile karşılaştırmak; gerekirse v0.22 tam sahne ve v0.20 rewrite/replan döngüsüne yalnız gerçek, yeterli kanıtla geçmek gerekir. Model yargısı tek başına world commit yetkisi almamalı; bütün sahne yeniden kontrol edilmeli. Ücretli model sayısı/bütçesi ve kaynak kilidi ayrıca belirlenmelidir.

## Kod ve takip

- `experiments/sera/real_mara_recovery_queue_v049.py`
- `experiments/sera/real_mara_recovery_smoke_v049.py`
- `experiments/sera/tests/test_real_mara_recovery_queue_v049.py`
- `.github/workflows/sera-v049-real-mara-recovery-shadow.yml`
- [SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306)
