# SERA v0.50 — İnsansız cümle onarımı ve kaynak-kör bağımsız inceleme

**16 Ekim 2026 | SHADOW LAB | kullanıcı kuralı: manuel tamir YOK**

## Temel sözleşme

Üretim hikâye hattının normal çalışması insan tarafından cümle veya JSON düzeltmesi, olay onayı, model seçimi, tekrar deneme, devam komutu veya yeniden planlama istememelidir. Sistem algılama, bağımsız yeni çıkarım, yanıt doğrulaması, yedek model, tam sahne recheck ve gerektiğinde replan/rewrite adımlarını kendisi yürütmelidir. Bilinmeyen faturalandırılabilir yanıtlar asla kör tekrar gönderilmez. Kanıt tamamlanamazsa FAILED_SAFE_FINAL ve sıfır dünya yazısı geçerlidir.

## Uygulanan v0.50 bileşenleri

- automated_row_recovery_v050.py: v0.49'un gerçek v0.48 makbuzlarıyla doğrulanmış 26 görevini tüketir. 5 görev için tek orijinal kaynak cümlesini ayrı yeniden çıkarım istemine dönüştürür; 21 model ayrışmasını önceki model kararını göstermeden kaynak-kör incelemeye gönderir.
- Tam alınmış ve kaydedilmiş yanlış yanıt için otomatik başka model fallback; yeni yanıt SERA v0.41.2 gerçek bind_batch izolasyonu veya v0.18 bağımsız source binder ile doğrulanır. Sadece tek hedef cümlenin geçerli kaynak satırı kanıt olur; binder'daki maskeli üç diğer satır asla sahne kapsama kanıtı yapılmaz.
- v0.21 mevcut durable provider journal ile started/response makbuzları saklanır. Tam makbuz varsa cache yeniden kullanılır; makbuz yoksa ağ isteği tekrar gönderilmez. Aynı modelin iki bağımsız model diye gösterilmesi, değişmiş kaynak ve sahte alıntı reddedilir.
- İki model de kaynak bağlamayı başaramıyorsa otomatik REPLAN_REQUIRED_NONCANONICAL durumu ortaya çıkar. Kaynak adayları bağlanmışsa SOURCE_CANDIDATES_READY_FOR_FULL_REEXTRACTION_NONCANONICAL olur. İkisi de fiziksel hikâye gerçekliğini veya kanonik yayın iznini temsil etmez.
- Sonraki tam sahne değerlendirmesi mevcut v0.22 evidence worker / v0.21 checker / v0.20 rewrite controller ile bağımsız yeniden gerçekleştirilmeli. Bu sürüm söz konusu tam-sahne aşamasının başarıyla tamamlandığını iddia etmez.

## Gerçek kanıt ile scriptlenmiş kontrol ayrımı

Gerçek v0.48 Mara pilotu: 28 kaynak cümle, 14 ücretli Gemini/Haiku makbuzu, 0,10590625 USD önceki toplam, Haiku 5 karantina ve 21 model anlaşmazlığı. Makbuzlar SHA ile kontrol ediliyor.

Self-hosted CI 38963749101: SUCCESS, 740/740 test. Bu sürümde 5 sentetik tek-cümle yeniden çıkarımı, 21 sentetik kaynak-kör inceleme, 2 otomatik farklı-model fallback, restartta 0 yeni callback doğrulandı. İzleme artefaktı sera-v050-26-auto-repairs-real-provenance-38963749101 (ID 12073403564).

Yeni gerçek provider çağrısı 0, ek ücret 0 USD, dünya/G2/SQLite yazısı 0, output token sınırı yok. Yeni gerçek modelin 5 satır hatasını düzelttiği veya 21 anlamsal ayrışmanın nihai çözüldüğü iddia edilmez. Mara S1 HOLD ve SceneTrace SHADOW ONLY devam eder, main branch değişmedi.

## Bundan sonraki otomatik kapı

v0.51: Bu onarımlardan sonra bağımsız tam sahne kanıt üretimi, sahnenin kontrolü, gerekirse replan ve rewrite zinciri; tümü makine yönetimli, tekrar başlatmaya dayanıklı ve güvenli durdurmalı olmalı. Yeni ücretli araştırma çağrıları için önceden açık mali izin politikası gerekir; bu, üretim kullanıcılarının cümleleri elle düzeltmesi anlamına gelmez.

[CI 38963749101](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38963749101) · [SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306)
