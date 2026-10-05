# Lighthouse Audit Decision v2 — 5 Ekim 2026

Önceki denetim gerekçesinde “No repair is needed” dediği kaydı `moderate + SCENE_REPAIR` döndürüyordu. Mevcut v21 karar mekanizması yalnız aile ve şiddete baktığından bu kayıt metin değişikliği başlatıyordu. Sorun yalnız daha iyi bir uyarı cümlesiyle çözülemez; makine sözleşmesi yanlış türde kayıtları aynı kanalda taşıyordu.

Yeni sözleşme üç ayrı kanal içerir: `blocking_findings`, `advisory_notes`, `verified_requirements`. Yalnız ilk kanal onarım girdisine dönüşür. Öneri/doğrulama kayıtlarında severity veya repair_scope alanı bulunmaz. Bir engelleyici kusur için bozulmuş gereklilik, maddi etki, geçerli span kimlikleri ve bu spanlardan birinde gerçekten bulunan kesintisiz bir alıntı zorunludur. `minor` veya `NO_REPAIR` kusur kanalında geçersizdir. Eski v21 modülleri/sözleşmesi değiştirilmedi; yeni karar modülü Lighthouse deney hattına bağlandı. Eski ham yanıtlar ve maliyetler korunur.

Kod gerekçedeki kelimeleri tarayıp olumlu ifadeleri otomatik olarak kabul etmiyor. Örneğin “no repair” anahtar kelimesine dayalı bir bypass yok. Eski kayıtlardan türetilen beş regresyon örneğinin kanal etiketleri editoryal test etiketleridir; modelin kendiliğinden doğru sınıflandırma yaptığının kanıtı değildir. Modelin yanlış kanala gerçek olmayan kusur yazması hâlâ olasıdır; canlı kontrol bunu ayrıca ölçer.

Yerelde 158 ilgili test geçti. Quote/span kanıtı, yanlış kanal alanları, gerçek ihlalin engelleyici kalması, önerilerin ek onarım yaratmaması, bütçe ve maliyet eksikliği, yetki/hash kayması ve tek tüketim sınırları kontrol edildi.

Canlı qualification aynı hikâyenin iki değişmez kaydını kullanır: son kabul edilen metin ve önceki kabul edilmiş ama üst girişe ekstra kule merdiveni/yanlış kapanış eklemiş sürüm. Modele vaka etiketi veya beklenen sonuç gönderilmez. İlkinde kabul, ikincisinde hem giriş-çıkış hem kapanış sapmasının saptanması gerekir. İki audit çağrısı; Writer, patch, çeviri ve production yazımı yok. Başlangıç maliyeti $1.4208331; tüm çağrılar tek hikâye için onaylanmış $3 toplamına dahildir. Bu iki vaka %95 başarı, seri üretim güvenilirliği veya sonraki hikâyelerin maliyetini kanıtlamaz.

Canlı sonuç ve ücret kaydedildiğinde bu belge güncellenecek.

## V2 canlı sonucu: başarısız; V3 düzeltmesi

Çalışma 37301366491, commit 59bd2698b3cc4e0705a373fe6ba88fc7bc6236f1: iki audit çağrısı, $0.077788; toplam hikâye/deney maliyeti $1.4986211. İki vaka da başarısızdı. Temiz kontrolün kusur kaydında broken_requirement=none, material_impact=none ve “No defect found here, so this entry is withdrawn” vardı; makine yine onarım olarak yorumladı. Negatif kontrol iki plan sapmasını da kaçırdı. V2 qualification **FAIL**, üretime uygunluk iddiası yok. CI'da 150 test geçti; yerel kapsamda ek kayıtlar bulunduğu için 158 test vardı. Ham cevaplar değiştirilmeden saklandı.

V3, yalnız farklı listeler istemek yerine altı bağlayıcı gerekliliği ayrı ayrı karşılaştırır. Gereklilikler onaylı planın tam kaynak alıntılarıyla İngilizce olarak projekte edildi; yeni Spine yok. Kaynak alıntısı planla uyuşmazsa inference öncesi durur. Her kontrol önce span ve alıntı kanıtını, sonra gerekçeyi, en son SATISFIED / MATERIAL_VIOLATION / UNCERTAIN kararını üretir. Kod olumlu veya advisory kayda şiddet etiketi vermez. Material violation onarım kapsamına dönüştürülür; UNCERTAIN metin değişikliğine yetki vermez. Ayrıca genel kusurlar/öneriler için sınıflandırması en sonda bulunan observations kanalı vardır. Bu sıralama modelin erken bir kusur listesine yazıp gerekçede geri çekmesine karşı tasarlandı; gerçek etkinliği canlı testte ölçülecek.

V3 yerel test kapsamı: 160 PASS. V3, aynı iki kaydı yeni sözleşme ile değerlendirir; önceki V2'nin tamamlanmış çağrıları kör retry edilmez. Önceki ücret toplam bütçeye dahildir. Qualification sonrası canlı sonuç burada kaydedilecek.
