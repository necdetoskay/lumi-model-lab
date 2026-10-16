# SERA v0.45 — SceneTrace kanıt kartından kaynak-kör otomatik tekrar çıkarımı (offline lab)

**16 Ekim 2026 / İzole branch / NONCANONICAL / Gerçek ücretli model yanıtından kaynaklanan riskler, fakat yeniden çıkarımda sadece scriptlenmiş yanıtlar.**

## Amaç ve gerçek ölçüm

v0.44, kaynak alıntısına bağlı iki gerçek model sorununa hangi kanıtın eksik olduğunu açıklıyordu. v0.45 bunun üzerine **otomatik çalışan, günlüklenen, yeniden başlatılabilen** deneysel bir yeniden değerlendirme denetleyicisi ekler. Hedef, aynı hikâye içinde bir insanın hata düzelten operatör olması değildir.

Girdi olarak SHA-256 doğrulanmış iki önceki ücretli çalışma ([Gemini/Haiku bench](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38936451931) ve [Gemini/Haiku pencil](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38938438488)) yeniden açılır; v0.43 ve v0.44 kaynak/span denetimleri kullanılarak Haiku `s004` ve Gemini `s022` risk kartları hazırlanır.

Bu sürümde **gerçek sağlayıcıya yeni model isteği gönderilmez**. `synthetic_source_only_double`, gerçekten çıkarılan kaynak cümlelerini alan kontrol edilebilir, maliyetsiz bir *sahte sağlayıcıdır*. Dolayısıyla otomatik **protokol ve güvenlik** testi yapıldı; ücretli gerçek modelin semantik bağımsız yeterliliği kanıtlanmadı.

## Akış

1. `scene_trace_evidence_challenge_v044.compare_receipts` önceki gerçek sağlayıcı yanıtlarının SHA/sözleşme/source span kontrolünü yapar. `scene_trace_autorepair_v045.prepare_challenges`, mevcut gerçek iki risk kartını kabul eder.
2. Her risk için modelin **önceki yanıtını veya hangi olay türünü önerdiğini görmeyen**, yalnız orijinal hedef cümle, cümle ID, kaynak SHA ve genel gözlem-eylem ayırma talimatı içeren *bağımsız* JSON isteği hazırlanır.
3. `request_policy.enforce_no_output_token_limit` çağrılır. Uygulama tanımlı model çıktı token tavanı yoktur.
4. Model-double yanıtı sonradan değerlendirilmeden **önce** `started.json` ve `reply.json` olarak ayrı yazılır; tamamlanmış yanıt restart'ta tekrar kullanılabilir. Başlamış fakat kaydı olmayan istek **yeniden gönderilmez**.
5. Mevcut `haiku_evidence_recovery_v011.parse_json_model_reply` ile tam JSON/tek tam JSON kod bloğu ayrıştırılır; ardından **tam kaynak cümlesi**, `actor_id=null`, `transition_proven=false` ve izinli dar değerlendirme türü kontrol edilir. Yanlış bir fail, uydurma alıntı veya modelin kanon iddiası reddedilir.
6. Kontrollü hatalı kalem yanıtı üzerine makine ikinci defa **kaynak temelli yeniden çıkarım** yapar; aynı yanıtı bekletmez ya da insan düzeltmesi istemez.
7. Denemeler tükenirse terminal `FAILED_SAFE_FINAL`; başarılı olursa yalnız `SOURCE_BOUND_REPAIR_ADVISORIES_ONLY`, sonraki iş `AUTO_INDEPENDENT_EVENT_REEXTRACTION_THEN_REVALIDATE`. **Hiçbir durumda WorldState/EventGraph commit veya gerçek G2 kanonik yetki yoktur.**

## Gerçek kanıtlar ile laboratuvar testi

[Self-hosted GitHub CI #38948392449](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38948392449): **SUCCESS, 703/703 Python testleri**. İki gerçek kaynak risk kartına karşı 3 scriptlenmiş cevap: saat ilk cevapta tam kaynak bağlı, kalem ilk cevapta sahte alıntı/uydurma fail nedeniyle reddedildi, kalem ikinci cevapta kaynak bağlı gözlem adayı verdi.

Test edilen negatif yollar: sahte kaynak SHA/span, ilk deneme sonrası geçerli kaydın tekrar kullanılması, bitmiş final tekrarında sıfır yeni çağrı, terminal geri dönüş, devamında bilinmeyen/yanıtsız istek için **no blind resend**, yanlış fiziksel hareket ve modelin kendini yetkilendirmesi. Başarısız koşullarda yanlış nesne/karakter/state yazımı **0**.

CI artefakt: `sera-v045-real-risk-offline-repair-38948392449` (ID `12066833126`); `durable-worker/contract.json`, istek başlangıç/yanıt makbuzları, `final.json`, üst sonuç dosyası.

## Önemli sınırlar

- v0.45'in gerçek çalışma yolu **scriptlenmiş cevapla sınırlı**; gerçek Gemini/Haiku'ya otomatik yeniden çıkarım, yeni bir ücretli onarım, tam sahne replan/rewrite veya yayınlama yapılmadı.
- Callback sahte sağlayıcıdır. Yerine gerçek OpenRouter transport koymak için **bağımsız yetki, maliyet politikası, güvenli provider receipt/reconciliation ve idempotent kurtarma** gerekir; v0.45 journali provider tarafı idempotency kanıtı değildir.
- Model-double sonuçları gerçek bir bağımsız semantik hakem veya full recall gold değildir. Dar kaynak kuralları dışında kalan fiziksel hatalar tespit edilememiş olabilir.
- Scriptlenmiş uygun değerlendirme yalnızca adaydır; **gerçek fiziksel eylem onayı değil**. Beklenen `STATIC_STATE_DESCRIPTION` veya `OBSERVED_MOTION_CAUSE_UNKNOWN` sonucu kaynağı kontrol etmek için bir test politikasıdır; modelin bunu söylemesi dünya gerçeği için yeterli değil.
- Yalnız iki önceki gerçek provider batch'inde 8/28 kaynak cümlesi değerlendirilmiştir, 20 cümlede gerçek bağımsız model değerlendirmesi yoktur.
- App model çıktı token sınırı, zorunlu manuel onarım, Project_LUMI DB migration/deploy, `main` merge, kanonik state ya da deneysel SQLite yazımı **yok**.

## Sonraki hedef

v0.46: mevcut gerçek `semantic_recovery_v018` ve `fresh_scene_evidence_worker_v022` kaynak-kör görev hazırlama/birleştirme sözleşmeleriyle SceneTrace'i tek bir entegre, **receipt/idempotency güvenlik kapısından geçen** sandbox deneyinde test et. Sahne yeniden çıkarımı, bağımsız denetim, hedefli repair ve terminal sonuçları sağlamadığı sürece mevcut akışın ilerlemesi kanonik kabul edilemez. Karşılaştırmalı gerçek kaynak gold ve Beat/relative time A/B için ayrıca küçük, ücretli izne bağlı pilot gerekecek.

**Karar:** SceneTrace hâlâ `SHADOW ONLY`; mevcut SERA v0.39–v0.44 çekirdeği ve orijinal Mara S1 HOLD korunuyor. [Backlog #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
