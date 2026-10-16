# SERA v0.48 — Tam gerçek Mara S1 deneyi: 28/28 kaynak kapsamı, ücretli çalıştırma kilitli

**Durum 16 Ekim 2026:** Hazırlık kodu ve self-hosted CI **başarılı**, henüz yeni ücretli OpenRouter çağrısı yapılmadı. Bu sürüm SceneTrace v0.42–0.47 *shadow-only* laboratuvar katmanının sonraki adımıdır; Project_LUMI/G2 yayını değildir.

## Neyi değiştirdik?

İlk gerçek Mara S1 pilotları v0.40 ve v0.41 her model için yalnızca dört kaynak cümlesi (toplam 8/28) değerlendirdi. v0.48, **aynı dondurulmuş** 243 kelimelik kaynak metnin SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03` değerini koruyarak mevcut `sentence_sweep_v010.create_plan` ile **7 adet dört-cümleli bağımsız batch** oluşturur. İki bağımsız model, 14 planlı deneme:

1. `google/gemini-3.7-flash`
2. `anthropic/claude-haiku-4.5`

Her model yalnızca orijinal kaynak cümlesini/bağlamını görür; önceki yazar notu, diğer model cevapları, hakem gold listesi verilmez. Zamansal alanlar için model tarafından kesin olay saniyesi uydurulmasına veya kaynakta olmayan fiziksel fail/world state değişikliklerine kanonik yetki verilmez.

## Güvenli çalıştırma sözleşmesi

- Yeni kod: `real_full_scene_blind_v048.py`; **varsayılan çalıştırma yalnız manifest**, ağ çağrısı sıfır.
- Offline testler: `tests/test_real_full_scene_blind_v048.py`. Kaynak tüm 28 cümle/7 batch/14 model isteği olarak sayılıyor. V0.11 tam JSON ayrıştırıcı, yalnız nonsemantic `mention.reason` onarıcısı, v0.41.2 **bireysel source-span karantinası**, v0.43 kritik watch/pencil risk ipuçları yeniden kullanılıyor.
- Tam alınmış ama hatalı kaynak cümlesi, **yalnız ilgili satır** karantinada. Cümle ID/set kaybı gibi batch şeması hatasında dört satırın hepsi karantinada; model kaynak bilgisi olmayan satırları yalandan tamamlamıyoruz.
- `SOURCE_BOUND_NONCANONICAL` yalnız **alıntı bağlandı** anlamına gelir; semantic correctness / recall / precision ölçümünün veya G2 yayın yetkisinin yerine geçmez. Her model/cümle `SOURCE_BOUND_NONCANONICAL`, `QUARANTINED` ya da `NOT_SAMPLED` olarak görünür; 28/28 iki model kapsasa dahi `story_ready_for_g2_commit=false`.
- **En fazla 14 planlı ücretli deneme**, kaynak bazında **gözlemlenen maliyet stop 0,25 USD**, çağrı öncesi erişilebilir kredi için en az 0,35 USD preflight. Bunlar toplam fatura garantisi değil; ücret model yanıtı sonrası gözlemlenebilir ve son gönderilen isteğin maliyeti stop eşiğini aşabilir. Bir yanıt alınıp raw receipt yazılmadan hiçbir JSON yorumlanmaz.
- Bilinmeyen / karşılığı kaydedilmeyen çağrı sonucu için **kör yeniden POST veya otomatik ücretli düzeltme yok**; sonraki çağrılar da durdurulur. Kaynağı doğrulanmış ücretli makbuzdan yeniden analiz mümkündür. Gerçek kullanıcı bütçesi ve provider politika değişiklikleri ayrı doğrulama gerektirir.
- Çıkış-token tavanı **yok**; canonical WorldState/EventGraph yetkisi, G2/SQLite/Project_LUMI DB yazısı **yok**; ana branch merge **yok**.

## Ayrı ücretli izin neden zorunlu?

Önceki iki gerçek pilotta kullanılan yönetilen kural gereği **hazırlığı bitirmek, yeni ücretli koşuya otomatik izin vermez**. `launch/sera-v048-fullscene-paid-once.json` dosyası **bilerek oluşturulmadı**. Dolayısıyla ücretli workflow'un push-path tetikleyicisi çalışamaz. Gerçek koşunun açılması için, kullanıcının açık onayı üzerine `authorized=true`, tam kaynak ve 7 batch request SHA listesi, iki model, 14 deneme, 0,25 USD gözlemlenen maliyet stop ve **tam önceki kod commit SHA** içeren tek kullanımlık manifest **ayrı bir commit** olarak eklenmeli. Bu commit **yalnız bu dosyayı değiştirmeli** ve `[SERA-V048-PAID-ONCE]` işaretini taşımalı.

`.github/workflows/sera-v048-full-mara-one-use-paid.yml` yalnız böyle bir grant commit'inde self-hosted olarak çalışır; `github.run_attempt == 1`, tek-use concurrency, `HEAD^` parent code pin ve tek değişen dosya kontrolü uygulanır. Sağlayıcı API anahtarı yalnız bu kapıdan sonra aktarılır. Kullanıcı onayı alınmadan sözleşme yetkili olarak işaretlenemez.

## Doğrulanmış kanıt

- [Ön doğrulama CI 38955555493](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38955555493) — **SUCCESS, 726/726 Python testi**, `SERA_V048_FULL_MARA_PRELAUNCH_SCOPE_PASS_NO_BILLING`.
- Artefakt: `sera-v048-full-mara-dry-preflight-38955555493` — immutable kaynak ID, 7 batch SHA ve model scope JSON. **0 yeni provider çağrısı, 0 gerçek USD**, 0 DB yazısı.
- [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306) · [SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307).

## Kabul kıstası

Gerçek grant sonrası dahi ham 14 yanıt var diye hikâye başarılı denemez. Ölçülecek: model başına bağımsız source-bound cümle sayısı, tam/karantina/eksik durumları, kaynakta olmayan satır/kopya alıntı, sahne olay/söz/nesne candidate dağılımı, statik saat geçişi ve kalem nedensel faili uydurulması dahil riskler, kaynak bazlı iki model anlaşmazlıkları, gerçek provider maliyet/gecikme. Gerçek semantik doğruluğun ölçülmesi için ayrıca bağımsız kaynak-only değerlendirme gerekir. Otomatik gerçek semantik düzeltme çalışmadı; Mara S1 **HOLD**, SceneTrace **SHADOW ONLY** kalır.
