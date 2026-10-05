# Kaydedilmiş teslimatları otomatik işleme — 5 Ekim 2026

İki gerçek Aion çıktısı ve iki kayıtlı Sonnet denetimi, yeni model çağrısı veya çalışma sırasında elle düzeltme olmadan metin artifact'ına ve REPAIR kararına ulaştı. Bu bir kaydedilmiş yanıtları tekrar çalıştırma kanıtıdır; yeni canlı üretimin veya %95 genel başarının kanıtı değildir. Hikâyeler kalite kabulü almadı.

| Varyant | Kelime | Tam kopya | Otomatik alıntı düzeltmesi | Karar |
|---|---:|---:|---:|---|
| Mevcut prompt | 2.100 | 1 | 0 | REPAIR |
| Beş kategori ekli prompt | 2.663 | 3 → 1 | S109 alıntı bağı | REPAIR |

story_delivery.normalize_marked_story, sadece tam başlık/sahne dizisi ve her tam kopya birebir eşleştiğinde tekrarları ayırır. Farklı bitiş, kısmi taslak, bilinmeyen sahne veya sıra farkı reddedilir. Satır sonları ve içerideki metin değiştirilmez. Kopya konumları ve her kopyanın SHA-256 değeri saklanır. Tekrarın model veya stream kaynaklı olduğu bu kayıtlarla belirlenemedi.

UTF-8 gelecekteki transportta açıkça ayarlanmış durumda. Eski bozuk SSE kayıtları, yalnızca açık latin1_decoded_utf8_sse kaynağı verilince tersine çevrilir; otomatik kodlama tahmini yok. Her düzeltmede birebir round-trip doğrulanır. Yeni UTF-8 girdisi olduğu gibi korunur.

audit_citation_projection, sadece SATISFIED kontrolünde, alıntı kaynakta tek parçaya birebir uyuyor ve önceden işaretlenen parçanın hemen yanında aynı paragrafta bulunuyorsa eksik span ID'sini ekler. Metin, alıntı, gerekçe, değerlendirme ve repair_span_ids değişmez. MATERIAL_VIOLATION veya UNCERTAIN alıntısı taşınmaz. Uydurma, belirsiz, uzak veya farklı paragrafa ait alıntı reddedilir. Kaynak response değiştirilmez; türev ve düzeltme kanıtı ayrı saklanır. Eski katı denetim kararı bu türevi tekrar doğrular.

Replay ayrıca Writer'ın gerçek isteğini kayıtlı girdiye, kullanıcı mesajındaki planı güncel onaylı plana, stop sonucunu sağlayıcı gövdesine, audit girdisini kendi kaynak metnine ve planına hash ile bağlar. Eski plan, değiştirilmiş sağlayıcı gövdesi veya yarım yanıt işlemden geçmez. Sonraki aşama kaynağı iki hikâyede de önceki okuma nüshasının SHA-256 değeriyle aynıdır. Anlamsal hikâye onarımı yoktur.

Bir ek kayıt bağı sorunu da düzeltildi: kapanmış Writer deneyi başlangıç bütçesini değişen comparison-summary.json dosyasından doğruluyordu. Artık kendi değişmez üçüncü deneme result.json kaydını kullanır. Değişen rapor offline testi bozmaz; değişmez ücret kaydı bozulursa durur. Eski ücretli yetki hash'i yeni runtime'a taşınmaz ve bu çalışmada ücretli workflow tetiklenmez.

Yerel kontrol: 233 PASS / 20.89 s. Yeni teslimat, alıntı ve replay kontrolleri hem gerçek kayıtları hem farklı taslak, yanlış alıntı ve kaynak drift negatiflerini kapsar. Kaydedilmiş replay PASS, 0 yeni API çağrısı, $0 yeni maliyet. Tüm kaynak dosya hash'leri runtime-manifest.json içinde.

Bilinen hikâye/geliştirme ücreti $1.95169086, kaydı eksik ilk çağrı rezervi $0.04, bütçede izlenen toplam $1.99169086 olarak kaldı. Toplam gerçek fatura hâlâ tamamlanmış değil. Production LUMI yazımı ve çeviri yok.

Sınır: yeni adaptörler replay hattına bağlandı; canlı ücretli üretim hattına henüz bağlanıp doğrulanmadı. Sonnet'in mevcut altı kontrolü kordon sürekliliği ve Duru konumu gibi bazı kaynak okumada saptanan kusurları eksik yakalıyor. Teslimatın otomatik geçmesi denetçinin içerik kapsamını tamamlamaz. Sıradaki iş, aynı değişmez temiz/bozuk metinlerle bu denetim kapsamını doğrulamak; Writer'ı tekrar çalıştırmak gerekmiyor.
