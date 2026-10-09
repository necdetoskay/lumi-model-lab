# Q21: kod değişmeden yeni hikâye deneyi

**Sonuç: REJECT_NON_CONVERGENT. Hikâye oluşmadı.**

İlk plan, sahne içi sıralama listelerine başka sahnelerin olaylarını yazdığı için reddedildi. Mevcut tek plan düzeltmesi bu referansları kaldırdı; ancak zaten takip edilen atlas ve ayracı bulmak için LOCATE uzamsal işlemini kullandı. LOCATE, takip edilmeyen bir nesneyi ilan edilmiş bir mekâna yerleştirmek içindir. Atlasın rafı ve ayracın içindeki kitap, bu topolojide mekân kimlikleri değildir.

Bu seed hattında bütün nesneler takip edilirken planlama şeması LOCATE seçeneğini hâlâ sunuyor. Gözlenen sorun planlama sözleşmesindedir; sahne yazarı ve Sonnet kontrolü hiç çağrılmadı. Diğer anlamsal koşullar henüz değerlendirilmedi.

| Ölçüm | Sonuç |
| --- | --- |
| İlk seferde başarı | Hayır |
| Kod değiştirmeden tamamlanma | Hayır |
| Kod/prompt/model/ayar değişikliği | Yok; kaynaklar Q20 ile aynı |
| Plan düzeltmesi | 1; ikinci plan da reddedildi |
| Yazılan/kabul edilen sahne | 0 / 0 |
| Başlangıç state’i | Korundu; revision 0 |
| Ücretli çağrı / maliyet | 2 / $0,1551995 |
| Üçüncü deneme veya retry | Yok |

Bu deney kod/contract değiştirilerek veya yeni bir deneme ile kurtarılmadı. Ham yanıtlar ve iki reddin aynı kodla yeniden üretilmesi kaydedildi. Bir robot hikâyesinin tamamlanmış olması, farklı taleplerde güvenilir genel başarıyı henüz kanıtlamıyor. Production ve merge yok.
