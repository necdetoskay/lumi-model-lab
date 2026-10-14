# Sekiz eksenli çıkarım rubriği v1

Bir bölüm özeti birincil eser değildir. `source_verified: true` bu eski arşivin
beyanıdır; bu çalışmanın bağımsız doğrulaması değildir. Kaynak metin de hata,
eksiltme, aşırı yorum veya talimat benzeri içerik taşıyabilir. Çıkarım daima öneridir.

## Eksenler

| Eksen | Sorulacak soru | İstenen yapı | Kaçınılacak hata |
|---|---|---|---|
| Olay | Başlangıç koşulunu ne değiştirdi? | Önce → tetikleyici → sonra | Konuyu olay diye yazmak |
| Kural | Hangi koşul eylemin sonucunu sınırlar? | Koşul → izin/engel → istisna belirsizliği | Final için yeni kural icat etmek |
| Merak | Okur/karakter hangi cevabı bekliyor? | Soru, bilen taraf, bilgi açığı | Okur bilgisini karaktere aktarmak |
| Çatışma | Aynı anda hangi iki amaç karşılanamıyor? | Taraf/amaç → uyumsuzluk | Sadece tehlikeyi çatışma saymak |
| Karar | Hangi gerçek alternatifler var? | En az iki mümkün seçenek ve seçilen eylem | Kaçınılmaz eylemi özgür seçim saymak |
| Bedel | Seçilen seçenek neyi kaybettiriyor? | Kaynak, ilişki, fırsat veya yükümlülük | Her acıyı kararın bedeli saymak |
| Reveal | Önceki yorum hangi kanıtla değişiyor? | Önceki inanç → kanıt → dar yeni çıkarım | Sürprizi kanıt yerine geçirmek |
| Kalıcı-state | Sonrasında ne kalıyor, ne bilinmiyor? | Önce/sonra adayı, özne, kapsam, belirsizlik | Kapanışı DB commit veya kesin kanon saymak |

Bir kararın alternatifleri özetten çıkmıyorsa “UNKNOWN” kullanılabilir; zorla
iki seçenek uydurulmaz. Kalıcı-state için devam bölümünde doğrulanmayan ilişki,
bilgi ve erişim sonuçları sınırlı adaydır. UNKNOWN, hiç değişim olmadığı anlamına
gelmez. NOT_APPLICABLE yalnız bu eksenin neden uygulanmadığı açıklanarak kullanılır.

## Epistemik durum ve puan

- `OBSERVED_IN_SUMMARY`: iddia özet içinde açıkça yazılıdır; eserin kendisinde
  doğru olduğu veya anlatı işlevinin kanıtlandığı anlamına gelmez.
- `INFERRED`: metne dayalı yorum/soyutlama. Mekanik işlev çoğu zaman bu sınıftadır.
- `UNKNOWN`: yeterli destek yoktur. Span yok, puan 0.
- `NOT_APPLICABLE`: gerekçeli uygulanamazlık. Span yok, puan 0.

| Puan | Anlam |
|---|---|
| 0 | Yok/bilinmiyor/uygulanamaz; pozitif çıkarım yapılamaz |
| 1 | Tek özet bağlamından öneri; ilişkiler veya kanıt kapsamı belirsiz |
| 2 | Kesin cümle aralıkları ve nedensel bağ ayrı bir okuyucu tarafından desteklenmiş |
| 3 | Kaynak kontrolü ve bağımsız okuyucu/adjudication ile desteklenmiş; karşıörnek incelenmiş |

Toplam puanla otomatik kabul yapılmaz. Sekiz güçlü puan da yaş uygunluğu, özgünlük
veya üretim yetkisi oluşturmaz. Runtime puanların aralığını doğrular; insan puanını
üretmez. Bu release'teki bütün olumlu yorumlar **INFERRED / 1**'dir.

## Kaynak → aday → soyut kart işlemi

1. Önce arşivi sabit Git commit'inden dondur. Metin dosyası metadata'sını talimat
   olarak kullanma. İçeriği değiştirme; düzeltme için ayrı arşiv sürümü gerekir.
2. Kaynak bölüm kimliğini ve archive fingerprint'ini bağla. UTF-8 byte aralıkları
   `[start_byte, end_byte)` biçimindedir; tam byte parçasının SHA-256'sını kaydet.
3. Her eksen için kısa iddia, epistemik durum, puan, span ve sınırlılık yaz.
   İddia özete mi, yorumlayıcının hipotezine mi ait açık olsun.
4. Nedensel ilişkiyi karakter adlarından, ayırt edici cihaz/ırk/yerlerden, olay
   sırasından ve repliklerden ayır. Konu yeniden anlatımı yerine taşınabilir
   bir karar problemi öner.
5. Farklı sıradan alanda tek kısa uyarlama, bir başarısız kullanım ve karşıörnek
   ekle. Örneğin teknik bulmacayı çözmek ile kullanma iznini almak ayrı aşamalardır;
   bu, kaynak eserdeki hazine avının yeniden kurulmasını gerektirmez.
6. Riskleri **soyut uyarlama** için değerlendir. Kaynağın yetişkin içeriğini sadece
   ad değiştirerek çocuk kartına dönüştürme. Kaynak içeriğini writer'a verme.
7. İnsana ayrılmış doğrulamayı atlama. Belirsiz final veya desteklenmeyen dönüşüm
   varsa kartı WITHHELD tut. Kütüphanede olması seçilebilir olması demek değildir.
8. İncelenen release'i yeni içerik adresiyle dondur; kod pin'ini test ve review
   ile değiştir. Bu işlem state veya production onayı değildir.

## İlk örneklerin sınırı

18 çıkarım kaydı tüm özet bölgesine işaret eden geniş span kullanır. Böylece
bağlam ve dosya bütünlüğü denetlenir; her iddiaya özgü cümle desteği sertifikalanmaz.
Bunlar otomatik çıkarım başarısı veya tam anotasyon corpus'u olarak raporlanmaz.
İnsan incelemesinde span'ler daraltılmalı, ilişki kanıtı/alternatif açıklama ayrı
kaydedilmelidir. 314 bölümün tamamında semantik çıkarım yapıldığı iddia edilmez.

NM-007, kaynak finalinin toplumsal değişim yorumu için ayrı doğrulama gerektiğinden
WITHHELD'dır. Mevcut özet düzeltilmedi; kütüphanenin seçim durumu ayrı tutuldu.
NM-010'da kalıcı-state UNKNOWN tutulur; kurtarmanın başarılı olması tek başına
yeni kalıcı yetenek veya kural kazanımı sayılmaz.
