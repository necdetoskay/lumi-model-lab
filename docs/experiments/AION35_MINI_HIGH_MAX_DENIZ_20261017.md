# Aion 3.5 Mini — aynı Deniz hikâyesiyle HIGH / MAX düşünme karşılaştırması

**17 Ekim 2026 · Yetki: iki Aion yazar denemesi kullanıcı tarafından onaylandı · Durum: PAID RUN BLOCKED BEFORE PROVIDER**

## Dondurulmuş deney

Aynı yaş-4 hikâyesi, aynı Deniz/balkon premise, sekiz maddelik orijinal Spine, aynı birebir yazar sistem talimatları ve aynı temperature=0.72 kullanılacak. Source eski dosyası `experiments/prototypes/aion35_mini_one_story_english_smoke_20260926.py`; **git blob SHA: `04fb04bcb3ef5e4fad59f5576e7eb363fa11fcbc`**. Her iki istekte model `aion-labs/aion-3.5-mini`.

Tek kontrollü değişken: `reasoning.effort="high"` ve `reasoning.effort="max"`; her ikisinde `reasoning.exclude=true`. OpenRouter `reasoning.effort` arayüzünü destekliyor ve Aion Labs resmî belgesinde Aion 3.5 / Mini için `low,high,max` bildirilmiş. İsteklerin **hiçbir yerinde max_tokens, max_output_tokens, max_completion_tokens veya reasoning token üst sınırı gönderilmez**.

Yazar iki özgün ham hikâyeyi oluşturacak. **Editör, hakem veya başka ücretli model çağrısı yok; hiçbir metne manuel müdahale yok.** İki metin ayrı makbuz + OpenRouter generation ID + süre + usage.reasoning_tokens (sağlayıcı döndürürse) + gerçek maliyetle kaydedilecek. Aynı olay Spine'ını ne kadar koruduğu, fiziksel kural, tekrar, yaş düzeyi, ritim ve final kendi orijinal metinleri üzerinden karşılaştırılacak. Tek örnek genelleştirilmiş istatistiksel üstünlük anlamına gelmez.

## Önceki gerçek baz çizgi

Tarih: 26 Eylül 2026, archived test `36257356137`; Aion 3.5 Mini writer draft **501 kelime**, final Sol düzeltmesiyle **470 kelime**, `publication_ready=true`. Writer kullanım 661 input / 6.337 output token; writer gözlemlenen maliyet **0,0093345 USD**; tüm önceki yazar+editör+hakem yolu **0,0374255 USD**. O testte reasoning isteği açık belirtilmemiş (sağlayıcı varsayılanı), düşünme token sayısı ayrı kaydedilmemiş. Dolayısıyla bu önceki deneme HIGH/MAX kanıtı değil.

## Hazırlanan uygulama

- `experiments/prototypes/aion35_mini_reasoning_high_max_once_20261017.py`: iki istek için eski kaynak dosyanın **git blob hash kontrolü**, eşit istemler, gerçek `reasoning.effort` farklılığı, streaming response, generation ID/usage/cost, özgün metinlerin dokunulmadan saklanması, receipt kaydı ve **tek-kullanımlık claim öncesi** ağ gönderimine izin vermeme, bilinmeyen sağlayıcı yanıtına tekrarlama yok.
- `experiments/prototypes/test_aion35_mini_reasoning_high_max_once_20261017.py`: beş offline test: sadece reasoning farklı, hiçbir output cap yok, iki mock yanıt, tek-kullanımlık ödeme talebi, reply kaybında no-repost ve grant dışında commit değişikliği reddi.
- Ayrı deney branch'i: `experiment/aion35-mini-reasoning-high-max-20261017`. Canonical/main ve üretim veritabanı değiştirilmedi.

## Önemli blokaj

**GitHub Actions workflow oluşturma çağrısı güvenlik kontrolü tarafından reddedildi.** Güvenlik engelini başka bir araç/host veya API anahtarını farklı yere aktarma yoluyla aşmadık. Bu nedenle gerçek `high` ve `max` çağrıları **henüz gönderilmedi**, sonuç ve ödenen ücret **0**. Hazırlanan Python kodu henüz CI'da denenmiş kabul edilemez; kodu sadece git commit altında kayıt altına aldık. Güvenli, yetkili bir workflow kurulum yolu sağlanmadan deneyin parasal sınırı aşılarak başlatılması yasaktır.

## Gereken güvenli son adım

Repository sahibi veya yetkili iş akışı düzenleyicisi, bağımsız branch'teki **read-only checkout + self-hosted offline test -> opt-in tek seferlik grant -> Aion 2 gerçek çağrı -> artifact** iş akışını kod incelemesinden geçirip **normal GitHub Actions workflow edit izni üzerinden** etkinleştirmeli. API anahtarı hiçbir zaman sohbet veya commit içeriğine yazılmamalı. İş akışının uygulama kodundaki ödeme limiti **iki POST** olup servis cevabı ve provider fiyatlaması değişken olduğundan mutlak dolar harcama garantisi değildir.

Not: İki örnekle yarışma için henüz kalite kararı çıkarılamaz; karşılaştırma ancak gerçek metinler oluştuğunda başlayabilir.


## 17 Ekim 2026 — Güncel CI doğrulaması

[**Salt okunur self-hosted CI #39005594002**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39005594002): **SUCCESS, 7/7 test.** Ek testler gerçek SSE event formatının son `[DONE]` işaretini ve provider `finish_reason` değerini zorunlu kılıyor; yarım kalmış stream daha sonra geçerli hikâye sayılmıyor. Ayrı test, aynı tek-kullanımlık yetkiyle ikinci yürütmenin iki ilave POST göndermeden `FileExistsError` ile reddedildiğini doğruladı. `--dry-run` özeti orijinal istemin hash'ini ve iki payloadın yalnız `reasoning.effort` alanında ayrıldığını kanıtladı.

CI workflow: `.github/workflows/aion35-mini-high-max-offline.yml`. Bu iş akışının **API anahtarı erişimi veya ücretli gönderim adımı YOKTUR**. Güvenlik kontrolü nedeniyle kabul edilmeyen önceki credential-bearing paid workflow **kurulmadı**. Bu nedenle gerçek HIGH/MAX yanıtı = 0, gözlemlenebilir model kalitesi = henüz yok, yeni maliyet = 0 USD.

**Güvenlik önkoşulu:** Gelecekte ücretli iş akışı yetkili kişi tarafından incelenirse tek-kullanım kilidinin bütün self-hosted runner'lar için ortak ve kalıcı storage'da tutulduğu ayrıca kanıtlanmalı. Yalnız runner-local veya temizlenen `GITHUB_WORKSPACE` dizini, birden çok runner varken global idempotency garantisi vermez. Bilinmeyen faturalandırılabilir sağlayıcı sonucu otomatik tekrar gönderilemez.


## 17 Ekim 2026 — HIGH–MAX doğrulayıcı v2 (16/16 PASS)

- [**Self-hosted CI #39006205681**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39006205681): **16/16 offline test PASS**. Gerçek ağ POST'u yoktur, gerçek LLM yanıtı üretilmemiştir.
- `aion35_mini_reasoning_high_max_once_20261017.py` artık `TWO_GENUINE_PROVIDER_ANSWERS_COMPARABLE` statüsünü yalnızca **her iki özgün cevap da durdurma nedeni `stop` ile tamamlanmış, boş olmayan hikâye üretmiş, tam istenen modelden dönmüş ve iki farklı üretim kimliği kaydedilmişse** verebilir. İlk yanlış model veya kesilmiş yanıt ikinci ücretli gönderimi otomatik tetiklemez. İkinci cevap `length` nedeniyle bitmişse 2 receipt kaydedilmiş olsa da `PARTIAL_OR_FAILED_SAFE_NO_PROVIDER_RESEND` olur.
- Yeni **tamamen çevrimdışı** `experiments/prototypes/aion35_mini_high_max_offline_evaluator_20261017.py`, kullanıcı tarafından sağlanan `--input-root` içindeki dondurulmuş girdiyi ve istek SHA'larını karşılaştırır; özgün metin dosyasını provider receipt SHA ve summary SHA ile doğrular. İki üretim kimliğinin farklı olmasını ve her iki modelin de Aion 3.5 Mini olmasını zorunlu tutar.
- Rapor: high/max kelime sayısı, bitirme nedeni, toplam output token, varsa reasoning token, varsa ücret ve gecikme, max−high farkları, anahtar sözcük işaretleri, 5-gram tekrar göstergesi. **Kelimeler yalnızca lexical göstergedir; olayın gerçekleştiğini veya fiziksel nedenselliği kanıtlamaz.** Gerçek anlamsal değerlendirme olmadan `winner=UNDETERMINED_NOT_SEMANTICALLY_JUDGED`. Eksik tutar **0 USD olarak uydurulmaz**; unknown/null kaydedilir.
- Yeni 9 regresyon deneyi: tam iki yanıt, bozulmuş metin, bozulmuş model kimliği, giriş fingerprint değişimi, ilk/ikinci cevabın eksik kalması, çift generation ID, provider fallback, eksik tutar/token muhasebesi. Önceki 7 transport/idempotency testi korunur.
- Geliştirici deney kodu ve OFFLINE CI branch içinde. `main` değişmedi, sıfır world write, sıfır manuel metin düzeltme.

**Kritik kalan blokaj:** Yeni gerçek ücretli HIGH/MAX çalışmasını kuracak iş akışı güvenlik tarafından engellenmiştir. Mevcut doğrulanan iş akışı salt çevrimdışı ve secrets erişimsizdir. Global ortak/durable one-use claim kökü ve onaylı ücretli workflow olmadan sağlayıcı POST'u yapılmayacak. Bu kanıtlar **Aion HIGH ve MAX model kalitesi arasında hiçbir üstünlük göstermemektedir**.
