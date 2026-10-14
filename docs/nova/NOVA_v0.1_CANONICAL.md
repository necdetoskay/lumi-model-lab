# NOVA v0.1.0 — Bağımsız araştırma mimarisi

**NOVA:** Narrative Observation, Validation & Abstraction.

## Çalışma hattı

**Analyze → Abstract/Validate → Vault → Match → Evaluate**

- **Analyze:** Bölümün başlatıcı olayı, dönüm noktası, karakter seçimi, gerçek bedeli ve sonuç açık kaynak URL ile kaydedilir.
- **Abstract/Validate:** Olaydan eserler arasında yeniden kullanılabilecek anlatı mekanizması çıkarılır; gözlem ile yorum ayrıdır ve her mekanik için uygulama koruması vardır.
- **Vault:** Sürümlü JSONL kaynak dosyaları; works, episodes, analyses, mechanics, mechanic_evidence, evaluations ve usage_history. SQLite yalnız bu verilerden yerel yeniden üretilebilir arama indeksidir.
- **Match:** Şimdilik sözcük tabanlı, açıklanabilir aday getirici vardır. Semantik uygunluk veya hikâye kalitesini tahmin ettiğini iddia etmez.
- **Evaluate:** 12 farklı gerçek senaryoda baz hat ile NOVA desteğinin kör A/B değerlendirmesi henüz yapılmadı.

## Şu anda doğrulanan

Stargate Universe 2 sezon × 20 yayın parçası = 40 NOVA analizi, 21 soyut anlatı mekanizması, 80 kaynak kanıt bağı. 18 mekanikte birden fazla bölüm örneği var, 3 mekanik tek örnekli adaydır. Çoklu kaynak örneği etki kanıtı değildir.

SG-1'in 214 ve Atlantis'in 100 özetlik araştırma arşivleri başka araştırma dallarında mevcuttur. Bu 314 bölüm **henüz NOVA Vault'a içe alınmış değildir**.

## Kanonik sınırlar

1. Dizi olayı LUMI evreni için kanon veya kural değildir.
2. Mekaniğin yeniden kullanımı soyut düzeydedir; isimler, teknolojiler, sahneler yeni hikâyelere kopyalanmaz.
3. Mekanik ile her bölüm arasında ayrıca kanıt bağlantısı ve kaynak izi bulunur.
4. Kaynak doğrulaması içerik editoryal ikinci görüşün yerine geçmez.
5. Kalite etkisi henüz test edilmedi: bütün mekaniklerde quality_effect=not_evaluated.
6. Araştırma değişikliği Story Harness'a, üretim hattına ve production'a taşınmaz.
7. Eval kullanım geçmişi, gerçek bağımsız çalışma olmadan doldurulmaz.

## Maliyetsiz tekrar komutları

~~~bash
python3 tools/nova/validate.py
python3 tools/nova/smoke_test.py
python3 tools/nova/build_sqlite.py
python3 tools/nova/match.py "eski düşmanlar ortak tehdit nedeniyle ittifak kuruyor"
~~~

Bu komutların PASS sonucu yalnız veri/matcher sözleşmesini gösterir; 12 gerçek senaryoda kalite kazanımı değildir.
