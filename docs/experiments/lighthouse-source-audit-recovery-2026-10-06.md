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

## Canlı v2 sonucu ve sıfır maliyetli devam kontrolü

Run 37409932527, kod 7757fcb2bb7aa7248c93084765d6ca4c3295b6f5:
sunucuda **265 test PASS / 25.65 s**. Model adımı REJECT_RUNTIME.
Artifact 11389013055, ZIP SHA-256
`31750f9b1b7b535f6e63434f0e716a7659b873e486cb44ac8e9c33d16e666fd9` doğrulandı.

Temiz kontrol çağrısı 27,259 giriş + 2,500 çıkış tokenı kullandı; çıkışın 2,087'si
reasoning tokenıydı. `finish_reason=length`, JSON eksik: sonuç kabul edilemez.
Eksik JSON tamamlanmadı veya olumlu sonuç olarak kullanılmadı. Hatalı metin denetimi
ve patch hiç başlamadı. Bu tur bir çağrı: **$0.079518**. Bilinen model toplamı
**$2.64901286**, eski rezervlerle bütçe hesabı **$2.78901286 / $3**.

Çıkış tavanını 2,500'e düşürmek bu model için yetersizdi; bu bir çalıştırma ayarı
hatasıdır. Sonraki ayrı deneme 03 için AUDIT=6,000, PATCH=3,500 hazırlandı. Ayrıca
ilk çağrıdan önce iki zorunlu kontrolün rezervini birlikte kontrol eden kapı eklendi;
yarım qualification'a ücret harcanmasını önler. Bu sınırlar başarı garantisi değildir.

Bu yeni hazırlık sıfır model çağrısıyla **BUDGET_BLOCKED** verdi: iki zorunlu kontrol
rezervi $0.416736; toplam gerekli bütçe $3.20574886, daha onarım dahil değil.
Mevcut tavan yükseltilmedi. Deneme 03'ün kaydı ücretli sonuç değil, sıfır maliyetli
preflight sonucudur. Yeni izin olmadan $3 üzerinde hiçbir çağrı yetkisi yoktur.

İlgili son test grubu: v2/v3 toplam 9 PASS. İki yeni test, kayıtlı yarım yanıtın
kabul edilmediğini ve bütçe duruşunda tek bir model çağrısı bile olmadığını doğrular.

Kalan iş: toplam deney tavanı yeterliyse aynı iki kontrolü tam yanıt bütçesiyle
çalıştırmak; yalnız ikisi geçerse bölgesel otomatik onarım ve tam yeniden denetim.
Kordon/Duru yakalama başarısı veya hikâye onarımı tamamlandı denmiyor. Sonraki deneme
için önerilen toplam tavan $4'tür; önceki $3 yetkisi bunu kapsamaz.
