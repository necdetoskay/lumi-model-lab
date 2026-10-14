# NOVA'nın hikâye kalitesine etkisi — 12 senaryolu deney planı

**Durum:** 0/12, henüz gerçek hikâye kalite deneyi çalıştırılmadı. Bu dosya yalnız plan ve kabul sınırıdır.

## Karşılaştırılacak koşullar

- **A / Baz hat:** Aynı giriş State, yaş, konu, model/prompt sürümü ve bütçe; NOVA bilgisi olmadan bağımsız hikâye.
- **B / NOVA:** Yalnız kanıt bağlantılı 1–2 soyut mekanik ve koruma kuralı eklenir. Öykünün diğer tüm koşulları sabit kalır.

12 özgün senaryo; kaynak saati, ayrılan ekip, liderlik çatışması, aile ilişkisi, güven krizi, bedelli fedakârlık, yanılsama, rakip ittifakı, etik bedel, gecikmiş sonuç, tehdit uyarlaması ve karakter olgunlaşmasını kapsayacak.

**Metodoloji:** Başlangıçta bütçe/araç/model/doküman sürümünü dondur. Test başladıktan sonra bütün 12 sonlanana kadar hikâye hataları için prompt, model, kod, mekanik veya kalite kurallarında düzeltme yapma. Yalnız güvenlik ve bütçe ihlalinde fail-closed STOP. Denemeler A/B koşulları görünmeyecek biçimde kör değerlendirilir.

**Ölçümler:** Yaşa uygunluk, nedensellik, karakter davranışı, yaratıcı özgünlük, zaman/mekân/state tutarlılığı, kapanış ve okur tatmini. Her denemenin model, token, maliyet, karar ve karşılaştırılabilir hash ledger'ı saklanır.

**Karar:** Önceden tanımlanan başarı eşiği ve anlamlı kalite artışı görülmeden NOVA, LUMI Story Harness ya da production hattına alınamaz.

**Şu anki 13/13 sözcük eşleştirme smoke testi**, A/B hikâye testi değildir; 12 gerçek hikâye testinin yerini almaz.
