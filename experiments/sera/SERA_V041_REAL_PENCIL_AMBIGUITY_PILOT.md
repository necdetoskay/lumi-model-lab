# SERA v0.41 — Gerçek Mara S1 kalem hareketi belirsizliği testi

16 Ekim 2026 · **İkinci ayrı one-use gerçek model pilotu** · yalnızca kaynak tanılama

## Araştırma sorusu

Orijinal ve hash'i sabit 243 kelimelik Mara S1 sahnesi aşağıdaki gerçek cümleyi içeriyor:

> Vane watched the pencil move.

Kalemin hareketi anlatılıyor, ancak **onu kimin hareket ettirdiği**, ne zaman hareket ettiği, mevcut/önceki tutucusu ve kalıcı dünya nesnesinin kanonik kimliği kaynakta açık değil. Başarıyı "model pencil sözcüğünü buldu" şeklinde dar tanımlamayacağız; epistemik belirsizlik, doğru nesne adayı, kaynak cümlesi ve fiziksel kanıtın yetersizliği ayrı sonuçlar.

## Metot

- `real_pencil_benchmark_v041.py`: orijinal SERA v0.10 blind planını **aynı kaynak** üzerinden yeniden kullanır; v0.40'ın **bench** batch'i değil, özgün `pencil` cümlesini içeren farklı dört cümlelik batch seçer.
- Model A: `google/gemini-3.7-flash`; Model B: `anthropic/claude-haiku-4.5`. Birinin yanıtı diğerine aktarılmaz.
- Format: mevcut SERA v0.11 strict complete-JSON-fence decoder + v0.10 source binder. Ham API yanıtı **değiştirilmeden** önce arşive kaydedilir; okuyucuda güvenli JSON kod bloğu soyma yalnızca geçici analiz kopyasında yapılır. Anlam ve fiziksel doğruluk onarılmaz.
- Geçici değerlendirme: mention sayısı, `new:pencil` veya `candidate:pencil` kaynak referansı, event adayı sayısı, JSON/alıntı yapısı, model bildirilen maliyet. Bir modelin olası `MOVE`/nesne hareketi çıkarımı **otomatik olarak etkilenen kişinin doğrulandığı veya reducer eventinin yetkili olduğu anlamına gelmez**.
- Model eylemi önceden tahmin etmese de `physical_pencil_move_committable=false`, `event_subject_and_cause_verified=false`, `canonical_commit_authorized=false`. Bu pilot hiçbir gerçek veya SQLite dünya durumunu değiştirmez.

## Bütçe, güvenlik ve kayıt

- Ayrı bir `[SERA-V041-PAID-ONCE]` commit'i, yalnızca `experiments/sera/launch/sera-v041-real-pencil-one-shot.json` dosyasını değiştirmeli; **üst commit SHA'sı onaylı kodla birebir eşleşmelidir**.
- Sadece `[self-hosted, linux]` koşucusu; çalışma ilk girişinde, `run_attempt=1`. GitHub `OPENROUTER_API_KEY` secret yalnızca izin kontrollerinden **sonra** gerçek çağrı adımına geçer.
- Azami iki ücretli isteğe izin verilir; her biri tek deneme, otomatik tekrar yok. Gözlemlenen `$0.05` toplam harcama durdurma eşiği, provider'ın tek çağrı ücretine üst sınır koymaz. Başlangıçta OpenRouter bakiye ön kontrolü.
- Uygulama tarafından tanımlı **çıktı token sınırı yok**. Bilinmeyen maliyet/yanıt halinde ikinci çağrıya geçilmez.
- Kanıt `result.json` ve değiştirilmemiş `provider_reply_1/2.json` olarak run-scope artifact'ında saklanacak. Gerçek model kararı ne olursa olsun sonuçlar tanısal `HOLD`.

Kod: `experiments/sera/real_pencil_benchmark_v041.py`; offline regresyon `tests/test_real_pencil_benchmark_v041.py`; çalışma `.github/workflows/sera-v041-real-pencil-one-shot.yml`.

Bu çalışma başka modelden onay istemek, hikâye cümlesini yeniden yazmak, Origin/Saga üretmek veya Project_LUMI veritabanına yazmak değildir. Orijinal Mara S1 kanonik **HOLD** durumundadır.

[Tracking Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
