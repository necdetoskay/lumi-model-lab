# Onaylı plandan denetim girdisi — v1

## Tamamlanan adım

Model Lab'da, mevcut editoryal plan alan yapısını alan ücretsiz ve deterministik bir denetim sözleşmesi derleyicisi eklendi. Önceki Lighthouse çalışma hattı ve altı İngilizce kuralla doğrulanmış canlı denetim değiştirilmedi.

Yeni derleyici karakter/bağlam gerçekleri, mekân/tehlike, korunacak sonuçlar ve onaylı netleştirmeleri; ardından her sahnenin onaylı eylemini ve son durumunu kaynak metni aynen koruyarak çıkarır. Son sahnenin sonuç alanı gerçek hikâye kapanışı olarak işaretlenir. Mevcut onaylı altı sahneden 16 denetim maddesi çıkarıldı. Okur vaadi ayrı rehberliktir; her arka plan bilgisinin sahnede anılması gerektiği varsayılmaz.

Kaynaklar Türkçe ise Türkçe kalır. Yeni İngilizce yorum, çeviri, hikâye planı veya model çağrısı yoktur. Bu yöntem anlamı otomatik olarak atomik kurallara ayırmaz; bölüm düzeyindeki gerekliliklerin doğru yorumlanması hâlâ model denetiminin işidir. Farklı Spine şemaları için ayrıca kaynak adaptörü gerekir.

## Kaynak ve onay bağı

Upstream onaylı plan hash'i derleyiciye verilir. Hash uyuşmazsa çıkarım durur. Üretilen sözleşme kaynak pointer, tam alıntı, sahne sırası, yaş ve dil içerir. Tüm sözleşme yeniden oluşturularak kontrol edilir; bir maddenin çıkarılması, değiştirilmesi veya hash'inin yeniden hesaplanması kaynak bağını geçerli kılmaz.

Hash bir kullanıcı onayı değildir. Bu deneyin hazırlama komutu mevcut approved_input() üzerinden özgün plan kaynağını ve kullanıcı onayını doğrular. Başka bir upstream adaptörü aynı onay doğrulamasını sağlamak zorundadır. Derleyici ücretli çalışma veya production yazım yetkisi vermez.

## Yeni karar prototipi

Yanıt şemasındaki gereklilik kimlikleri ve zorunlu kontrol sayısı sözleşmeden türetilir. Kimlikler karakter adına, altı sahneye veya 12 yaşa sabitlenmez. Kanıt önce, karar sonra düzeni korunur. Her kesin karar alıntı/span kanıtı ister; maddi kusur sınırlı onarım kapsamı gerektirir. SATISFIED kaydı onarım span'ı taşıyamaz. Öneriler ek düzenleme başlatmaz. Eksik, uydurma veya yinelenen kaynak kanıtı reddedilir.

UNCERTAIN, UNRESOLVED sonucuna gider; kabul veya düzenleme izni üretmez. Bu prototipte ücretli çağrı giriş noktası bulunmaz ve mevcut çalışır hatta bağlanmamıştır. Gerçek eksik eylemleri her zaman kaynak alıntısıyla kanıtlamanın mümkün olmayabileceği bu şekilde açık bırakılır.

## Doğrulama

Yerel çalıştırma: `python -m pytest -q tests/test_plan_audit_contract.py tests/test_lighthouse_*.py tests/test_spineforge_v21_*.py` — **189 PASS**, 11.06 saniye. Yeni dosyada 29 test vardır. Farklı sahne sayıları (1, 3, 10), farklı yaş ve adlar, tam kaynak kapsamı, plan/sıra değişimi, sözleşme tahrifi, kanıt doğrulama ve öneri/onarım ayrımı kontrol edildi. Bunlar yazılım testidir; modelin anlam doğruluğu kanıtı değildir.

Önceki canlı audit'in altı kontrol içeren yanıtı yeni 16 kontrol sözleşmesine kabul edilmez. Bu yanlış başarı aktarımı da test edildi. Bu aşamada yeni CI sonucu veya canlı model PASS iddiası yoktur.

Tekrar üretim: `python -m src.plan_audit_prepare`.

Çıktılar `evidence/plan-audit-contract-v1/` içinde: contract.json, response-schema.json ve preparation.json. Durum **OFFLINE_PREPARED_NOT_MODEL_QUALIFIED**. Yeni API çağrısı 0; yeni ücret $0; tek hikâye için tüm geliştirme denemelerinin toplamı $1.7585491 olarak kalır. Uzunluk minimum-only; üst sınır yok.

## Sonraki doğrulama

Aynı hikâyenin kayıtlı temiz ve plan sapmalı sürümleri yeni sözleşme ve yeni kaynak dili istemiyle canlı olarak denetlenmeli. Temiz sürüme onarım istenmemesi ve hatalı sürümün giriş/kapanış ihlallerinin bulunması şart. Bu sağlanmadan eski altı maddelik çalışma hattı yerine geçmez. Başka hikâye veya farklı Spine şeması üzerinde başarı henüz kanıtlanmadı.
