# Robot hikâyesi: güncel durum ve maliyet

Q19 planı kabul edildi. İlk dört sahne kabul edildi; çalışma state’i revision 4, sıradaki sahne S5_DecisionMove. Beşinci guard çağrısı gönderilmeden önce hesaplanan $0,150578 üst sınırı, izin verilen $0,15 sınırını aştığı için hat durdu. Tamamlanmış hikâye ve tamamlanmış hikâye başına fiyat henüz yok. Başlangıç state’i değişmedi.

| Deneme | Bilinen gerçek maliyet (USD) | Çağrı |
| --- | ---: | ---: |
| Q13 | Bilinmiyor | 1 girişim; usage yok |
| Q14 | 0.1362735 | 1 |
| Q15 | 0.1550770 | 2 |
| Q16 | 0.1744970 | 2 |
| Q17 | 0.149573 | 2 |
| Q18 | 0.3483390 | 10 |
| Q19 | 0.3693698 | 11 |

**Q14–Q19 bilinen toplam: $1,3331293 / 28 çağrı.** Q13 gerçek maliyeti bilinmiyor; $1,20 rezervasyonu ayrıca tutuluyor. Rezervasyon harcanmış maliyet olarak sayılmadı ve bilinmeyen maliyet sıfır kabul edilmedi. Bu toplam yalnız aynı Ada/Bora robot denemesidir; eski lighthouse/greenhouse/mosaic deneyleri dahil değildir. Tüm kapalı kayıtlar canlı ortak kayıtla eşleşti.

Q19: planlama + plan kontrolü $0,0967208; sahne çağrıları $0,272649; toplam $0,3693698. Bu geliştirme denemelerinin toplamıdır; tek başarılı hikâye üretim fiyatı değildir. Yeni kanıt aralığı hattının Q19 ücretli denemesi 11 çağrı / ,3693698 olarak bu toplama dahildir. Production ve merge yok.
