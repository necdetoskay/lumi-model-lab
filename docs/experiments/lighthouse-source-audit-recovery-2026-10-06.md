# Kayıtlı kaynak denetimi — 6 Ekim 2026

Önceki kuyruk işi 37370235996 daha sonra çalıştı: QUALIFICATION_FAILED.
Alternatif hosted iş 37371216752 iptal edildi, artifact üretmedi. Bu nedenle eski
"kuyrukta, sıfır yeni çağrı" checkpoint'i güncel değildir.

İndirilen artifact: 11369913973; ZIP SHA-256:
`a78d8764f4eed97236f2ed0c7971bfa2d2c6e445c839f5250853d1293b068bae`.
Orijinal yedi dosya LIGHTHOUSE-SOURCE-ADJUDICATION-01-20261005 altında değişmeden korunur.

İki denetim çağrısı $0.14304; bilinen model toplamı $2.56949486.
Bilinmeyen eski çağrı rezervi $0.04, önceki çalıştırıcı ihtiyat payı $0.10 korunur:
bütçe hesabı $2.70949486 / $3. Gerçek faturanın tam uzlaştırıldığı iddia edilmez.

## Gözlenen hata

Hatalı metinde kordon (S008/S196) ve final (S199/S200) yakalandı; Duru'nun
S177'deki yarım kat konumu kaçırıldı. Temiz kontrol de reddedildi: denetçi kaynakta
olmayan "uzun merdiven" ve "kordon limanda kaldı" çıkarımları yaptı. Temiz metnin
S005/S120/S197 dizisi kopan parçanın bilekte kalmasını, sonra cebe konmasını anlatır;
S212 son cümlede kordonla oynama ve yetişme eylemini birlikte taşır.
Onarım başlamadı; hikâye metinleri değişmedi.

## Yeni sürüm

Eski deneme dosyaları değiştirilmeden source_adjudication_v2 ve yeni istem eklendi.
- 74 kaynağın her biri için kontrol edildi kaydı zorunlu. Eksik/tekrar/yabancı ID reddedilir.
- Her bulgu kendi kaynak cümlesine birebir bağlı kanıt alıntıları taşır.
- İç süreklilik iddiası en az iki farklı kaynak durumu gerektirir. Plan sapması kaynak
  madde numarasına bağlanır. Kanıt cümleleri otomatik olarak onarım kapsamına girmez.
- Önceki modelin gerekçe ve etiketleri yeni girdiden çıkarılır; tüm plan ve hikâye korunur.
- Temiz kontrol başarısız olursa ikinci denetime dahi ücret harcanmaz.
- İki kontrol geçmeden patch yok. Patch sonrası tam denetim, metin dışı değişmezlik ve
  mevcut $3 tavanı korunur. Yeni Writer yok; LUMI production yazımı yok.

Yerel geniş test: 276 PASS / 22.49 s. Ardından eklenen bir uçtan uca sentetik test
ayrıca çalıştırılır. Bunlar anlamsal kalite kanıtı değildir. İstem bu kayıtlı örneklerden
öğrenilerek düzenlendiğinden, başarı durumunda bile bağımsız hikâyelerde genelleme iddiası yok.

Yeni deneme öncesi durum: hazır; canlı v2 sonucu henüz yok. Model çağrısı başına
rezerv kontrolü yeterli bütçe yoksa durur. Eski başarısız çağrılar yeniden çalıştırılmaz.
