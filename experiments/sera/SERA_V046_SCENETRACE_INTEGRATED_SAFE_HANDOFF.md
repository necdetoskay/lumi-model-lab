# SERA v0.46 — SceneTrace → v0.18 → v0.22; gerçek Mara riskinden güvenli tam sahne kapısına

**16 Ekim 2026 — deney branch’i, self-hosted, kanonik olmayan.**

## Amaç

v0.45'in önceki gerçek OpenRouter yanıtlarından kaynaklanan (ancak offline model-double ile yeniden değerlendirilen) iki SceneTrace riskini, SERA'nın mevcut üretim hattı bileşenleriyle gerçekten bir araya getirmek:

`historical v0.40/41 source-bound Gemini/Haiku replies → v0.44 challenges → v0.45 durable automatic source evaluation → v0.11 independent semantic task request / v0.18 genuine response binder → v0.22 genuine full-scene source + world evidence worker → safe termination`

**Önemli:** v0.46'nın yeni semantik cevapları ve v0.22'nin tam sahne cevapları **kontrollü, ücret gerektirmeyen test doubles** üretir. Eski gerçek model ham yanıtlarının yeniden kullanılması, yeni bağımsız model çağrısının gerçekten yapıldığı veya gerçek semantik kabul sağlandığı anlamına gelmez. Bu sürüm, mevcut fonksiyonların aynı kontrol akışında güvenli fail-close ve receipt davranışını doğrular. Gerçek hikâyenin tamamı hâlâ bağımsız modelden geçmemiştir.

## Tamamlanan kod

- `scene_trace_integrated_lab_v046.py`: gerçek Mara iki batch arşivini kaynak SHA ile doğrular. v0.45'i çağırır. Kaynak-kör, önceden modelin cevabını göstermeyen v0.11 `make_task_request` ile iki hedefli bağımsız soru hazırlar. Daha önce var olan v0.18 `_bind` ile kaynak alıntısının doğruluğunu ve `HOLD_MODEL_RESPONSE_NOT_AUTHORITY` sınırını test eder. Sonra **gerçek** v0.22 `create_preparer` tam kaynak worker'ı çağrılır.
- v0.18 bridge: her task için `contract.json`, `task_NNN.started.json`, `task_NNN.reply.json` kalıcı kayıtları; kaynak + request hash kontrolü. Completed reply restart'ta yeniden bağlanır, eksik receipt'li started request **körlemesine yeniden gönderilmez**. Bu kayıt politikası, gerçek sağlayıcı idempotency garantisi değildir.
- Tam sahne v0.22 fixture'ı model yanıtını **bilerek eksik** verir (`{"rows":[]}`). Gerçek `bind_batch` buna `SWEEP_SENTENCE_MISSING_OR_DUPLICATE` der. v0.22 `FAILED_SAFE_FINAL` üretir; üst denetleyici bunu saklar ve hiçbir zaman `SCENE_READY` veya kanonik kabul üretmez.
- `scene_trace_integrated_smoke_v046.py` ve `tests/test_scene_trace_integrated_lab_v046.py`: aynı run'ı restart'tan sonra tekrar çalıştırır; v0.45/v0.18/v0.22 geçmiş yanıt kayıtlarını yeniden kullanır; sahte kaynak alıntısı, önceki model cevabının bağımsız isteğe sızması, tam sahne eksikliği, kaybolmuş v0.18 ve v0.22 yanıtı, yeni ödeme ve yanlış world commit senaryolarını test eder.
- `.github/workflows/sera-v046-integrated-safe-handoff.yml`: yalnız **self-hosted Linux**, uygulama model çıktı token tavanı yok, GitHub secret/gerçek provider anahtarı yok, önceki ücretli artefaktlar salt okunur. Makineye bağlı gerçek provider çağrısı yok.

## Ölçülen ilk başarılı CI

[Self-hosted v0.46 #38949732425](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38949732425): **710/710 Python test PASS**. Son durum:

| Kontrol | Sonuç |
| --- | --- |
| Gerçek kaynaklı risk kartı | 2 |
| v0.45 scripted automatic repair | `SOURCE_BOUND_REPAIR_ADVISORIES_ONLY` |
| v0.18 kaynak-kör, tam alıntıya bağlı scripted semantic judge | `TWO_SOURCE_BOUND_ADVISORIES_NONCANONICAL` |
| v0.22 gerçek full-scene validator + bilerek eksik scripted yanıt | `FAILED_SAFE_FINAL` |
| v0.22 hata | `SWEEP_SENTENCE_MISSING_OR_DUPLICATE` |
| İlk çalıştırma v0.18 scripted cevap | 2 |
| İlk çalıştırma v0.22 scripted cevap | 1 |
| Tam restart, aynı provenance ve sonuç | **Evet, ek 0 callback** |
| Yeni gerçek ücretli model çağrısı | **0** |
| Gerçek/SQLite dünya durumuna yazma | **0** |
| Uygulama çıktı token sınırı | **Yok** |
| Ana branch merge | **Yok** |

V0.46'nın en önemli sonucu: **hedefli model cevaplarının kaynak alıntılarını doğrulamak, tam sahne olay/nesne kapsamını kanıtlamaya yetmez**. Bu nedenle sıradaki worker eksik veri sağladığında otomatik fail-safe sona ulaşıyor. `FAILED_SAFE_FINAL` burada **başarısız otomatik hikâye üretimidir ama başarılı güvenlik ve yeniden başlatma testidir.**

## Sınırlar ve sıradaki kapı

1. SERA'nın tam sahne v0.22 worker'ını gerçek modelle çalıştırmak ve full source event/identity recall/precision ölçmek için ayrıca maliyet/gerçek model çağrı kapsamı gerekir.
2. Mevcut scriptlenmiş judge, asıl veri bilme başarısını kanıtlamaz. v0.45 kanıt kartlarından v0.18 source-bound response üretmek, kanonik olay üretimi ya da kabul görmüş causal agent tespiti değildir.
3. Hatalar normal hikâye hattında **insan müdahalesi bekleyemez**; gerçek provider/workflow idempotent receipt, otomatik fallback, yeniden çıkarım/replan/rewrite ve final safe state zorunludur.
4. Modelin bütün hikâye için önerdiği timeline ve karakter/nesne atomlarını açıklanabilir SceneTrace olarak saklama hedefi sürer; kaynakta bulunmayan kesin zaman damgaları üretilmez.
5. **SceneTrace SHADOW ONLY.** Proje LUMI G2, ana branch, üretim servisleri, PostgreSQL/SQLite veri durumları değişmez. Orijinal Mara S1 HOLD.

İlişkili: [SceneTrace backlog #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306) · [v0.45](./SERA_V045_AUTONOMOUS_SHADOW_REPAIR.md).
