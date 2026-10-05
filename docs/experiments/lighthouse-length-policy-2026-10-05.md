# Fener denemesi — uzunluk politikası değişikliği

2026-10-05: Kullanıcı üst kelime sınırının kaldırılmasını istedi.
Yeni politika en az 1.400 İngilizce kelime; üst kelime sınırı yok.
Kelime sayısı ölçülür, uzun bir metin yalnız uzunluğu nedeniyle reddedilmez.
Gereksiz tekrar, düşük tempo ve açıklama fazlalığı editoryal kalite konusudur.
7.000 çıktı tokenı, maliyet eşikleri ve tek sahne/40 span onarım sınırı korunur.
Bu teknik sınırlar, sınırsız uzunlukta çıktı garantisi vermez.

Kaynak plan belgesindeki 1.400–1.800 aralığı tarihsel olarak korunur;
güncel Writer girdisindeki target_words/length_policy ve prompt bu aralığı
uzunluk bakımından geçersiz kılar. Diğer plan koşulları değişmez.

Önceki 2.531 kelimelik denemenin REJECT_RUNTIME kaydı değiştirilmez.
O koşuda Sonnet denetimi yapılmadığı için yeni politika hikâyeyi otomatik
olarak kabul edilmiş saymaz. Ücretli yetki tüketilmiştir; bu değişiklik
yeni model çağrısı yetkisi değildir. Yeni hazırlık hash'leri çevrimdışı üretilir.
