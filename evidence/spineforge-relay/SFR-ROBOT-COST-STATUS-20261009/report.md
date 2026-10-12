# Robot hikâyesi: güncel durum ve maliyet

Q18 planı kabul edildi. İlk üç sahne kabul edildi; çalışma state’i revision 3, sıradaki sahne S4_OnarimVeTest. Dördüncü guard yanıtının ardışık olmayan kanıt seçimi nedeniyle hat durdu. Tamamlanmış hikâye ve tamamlanmış hikâye başına fiyat henüz yok. Başlangıç state’i değişmedi.

| Deneme | Bilinen gerçek maliyet (USD) | Çağrı |
| --- | ---: | ---: |
| Q13 | Bilinmiyor | 1 girişim; usage yok |
| Q14 | 0.1362735 | 1 |
| Q15 | 0.1550770 | 2 |
| Q16 | 0.1744970 | 2 |
| Q17 | 0.149573 | 2 |
| Q18 | 0.3483390 | 10 |

**Q14–Q18 bilinen toplam: $0,9637595 / 17 çağrı.** Q13 gerçek maliyeti bilinmiyor; $1,20 rezervasyonu ayrıca tutuluyor. Rezervasyon harcanmış maliyet olarak sayılmadı ve bilinmeyen maliyet sıfır kabul edilmedi. Bu toplam yalnız aynı Ada/Bora robot denemesidir; eski lighthouse/greenhouse/mosaic deneyleri dahil değildir. Tüm kapalı kayıtlar canlı ortak kayıtla eşleşti.

Q18: planlama + plan kontrolü $0,118293; sahne çağrıları $0,230046; toplam $0,348339. Bu geliştirme denemelerinin toplamıdır; tek başarılı hikâye üretim fiyatı değildir. Yeni kanıt aralığı düzeltmesi için henüz ücretli çağrı yok. Production ve merge yok.
