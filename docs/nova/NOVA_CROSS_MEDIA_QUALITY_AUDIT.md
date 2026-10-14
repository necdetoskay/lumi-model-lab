# NOVA v0.2 — Cross-media kabul raporu

**Araştırma dalı:** research/nova-crossmedia-v0.2

| Kabul başlığı | Sonuç |
|---|---:|
| Önerilen sıra ile işlenen eser | 5/5 |
| Hades temel oyun | Hikâye + mekanik + koşullu final kayıtlı |
| Outer Wilds temel oyun | Hikâye + bilgi akışı + ana ve alternatif bitişler |
| The Witcher 3 temel oyun | Ana öykü + Bloody Baron ayrıntılı seçenek haritası |
| Arrival 2016 | Film öyküsü + bilgi sunuluşu / kronoloji |
| 12 Angry Men 1957 | Film öyküsü + makul şüphe / tek mekân gerilimi |
| Kaynaklı hikâye aşaması | 47 |
| Anlatı mekanizması adayı | 35 |
| Mekanizma↔sahne kanıt bağlantısı | 85 |
| Karar ve sonuç kaydı | 22 |
| Kaynak tanımı | 25 |
| Eserler arası açık benzerlik/fark karşılaştırması | 7 |
| Kaynakların CI'dan HTTP 200 dönenleri | 16 |
| Kaynakların CI'dan 403 dönenleri | 8 |
| CI'dan diğer yanıt | 1 (IMDb HTTP 202) |
| Yapısal/kaynak bağlantı testi | PASS |
| Offline unittest | 25/25 PASS |
| SQLite indeks ve yabancı anahtarlar | PASS |
| SGU v0.1 önceki doğrulayıcı | PASS |
| Gerçek 12 senaryolu kalite A/B | 0/12 — YAPILMADI |
| LUMI Story Harness, main ve production | DEĞİŞMEDİ |
| OpenRouter/API maliyeti | 0 yeni çağrı |

## Kaynak doğrulama gerçeği

25 kaynağın hepsi araştırma sırasında metin veya ilgili web arama sonuçları üzerinden gerekçelendirildi; ancak bir kısmı bağlı CI sunucusunun doğrudan erişimini engelliyor. 403 erişim reddi kaynağın yanlış olduğunu kanıtlamaz ve HTTP 200 diye raporlanmaz. Kalıcı ölçüm dosyası data/nova/v0.2/SOURCE_HTTP_CHECK.json altında saklanır.

## Kabulün kesin sınırı

Bu rapor referans bütünlüğünü, özet/analiz dosyalarının varlığını, tür bazlı karar ayrımını, State önkoşul alanlarını, mekanik kaynak bağlarını ve tekrar üretilebilirliği test eder. Olayların tek tek bağımsız uzman doğrulaması ve yeni üretilen hikâyelerde kalite kazanımı ayrıca gereklidir.

Yapısal kontrollerin başarılı olması üretime terfi izni değildir. Bir mekanizmanın LUMI'ye alınması için sabit deney koşullarında sonuç veren 12 bağımsız senaryolu karşılaştırmanın tamamlanması gerekir.
