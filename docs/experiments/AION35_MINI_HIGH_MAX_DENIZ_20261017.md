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
