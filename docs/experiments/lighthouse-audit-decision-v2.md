# Lighthouse Audit Decision v2 — 5 Ekim 2026

Önceki denetim gerekçesinde “No repair is needed” dediği kaydı `moderate + SCENE_REPAIR` döndürüyordu. Mevcut v21 karar mekanizması yalnız aile ve şiddete baktığından bu kayıt metin değişikliği başlatıyordu. Sorun yalnız daha iyi bir uyarı cümlesiyle çözülemez; makine sözleşmesi yanlış türde kayıtları aynı kanalda taşıyordu.

Yeni sözleşme üç ayrı kanal içerir: `blocking_findings`, `advisory_notes`, `verified_requirements`. Yalnız ilk kanal onarım girdisine dönüşür. Öneri/doğrulama kayıtlarında severity veya repair_scope alanı bulunmaz. Bir engelleyici kusur için bozulmuş gereklilik, maddi etki, geçerli span kimlikleri ve bu spanlardan birinde gerçekten bulunan kesintisiz bir alıntı zorunludur. `minor` veya `NO_REPAIR` kusur kanalında geçersizdir. Eski v21 modülleri/sözleşmesi değiştirilmedi; yeni karar modülü Lighthouse deney hattına bağlandı. Eski ham yanıtlar ve maliyetler korunur.

Kod gerekçedeki kelimeleri tarayıp olumlu ifadeleri otomatik olarak kabul etmiyor. Örneğin “no repair” anahtar kelimesine dayalı bir bypass yok. Eski kayıtlardan türetilen beş regresyon örneğinin kanal etiketleri editoryal test etiketleridir; modelin kendiliğinden doğru sınıflandırma yaptığının kanıtı değildir. Modelin yanlış kanala gerçek olmayan kusur yazması hâlâ olasıdır; canlı kontrol bunu ayrıca ölçer.

Yerelde 158 ilgili test geçti. Quote/span kanıtı, yanlış kanal alanları, gerçek ihlalin engelleyici kalması, önerilerin ek onarım yaratmaması, bütçe ve maliyet eksikliği, yetki/hash kayması ve tek tüketim sınırları kontrol edildi.

Canlı qualification aynı hikâyenin iki değişmez kaydını kullanır: son kabul edilen metin ve önceki kabul edilmiş ama üst girişe ekstra kule merdiveni/yanlış kapanış eklemiş sürüm. Modele vaka etiketi veya beklenen sonuç gönderilmez. İlkinde kabul, ikincisinde hem giriş-çıkış hem kapanış sapmasının saptanması gerekir. İki audit çağrısı; Writer, patch, çeviri ve production yazımı yok. Başlangıç maliyeti $1.4208331; tüm çağrılar tek hikâye için onaylanmış $3 toplamına dahildir. Bu iki vaka %95 başarı, seri üretim güvenilirliği veya sonraki hikâyelerin maliyetini kanıtlamaz.

Canlı sonuç ve ücret kaydedildiğinde bu belge güncellenecek.
