# Lighthouse denetim ve onarım sonucu — 5 Ekim 2026

Bu hikâyede model denetimi → sınırlı onarım → yeniden denetim → durma zinciri doğrulandı. Kabul edilen metin 2.692 kelime; üst uzunluk sınırı yok. Son denetimde altı bağlayıcı gereklilik sağlandı, engelleyici bulgu kalmadı. Bir üslup önerisi saklandı ve yeni onarım başlatmadı.

## Sorun ve değişiklik

Eski denetim, “onarım gerekmez” açıklamasını moderate / SCENE_REPAIR olarak etiketleyerek gereksiz düzeltme döngüsü yaratıyordu. Yalnız kusur, öneri ve doğrulama listelerini ayıran V2 canlı testte başarısız oldu; başarısız ham yanıtlar korundu.

V3 önce onaylı planın altı gerekliliğini kaynak alıntılarıyla bağlar. Model önce metindeki span ve kesin alıntıyı, ardından gerekçeyi, en son kararını üretir. Yalnız MATERIAL_VIOLATION veya kanıtlanmış ek kusur onarımı başlatır. Öneriler metin değişikliğine dönüşmez; UNCERTAIN yeniden yazmaya yetki vermez. Kod gerekçedeki olumlu kelimeleri tarayıp otomatik kabul üretmez.

## Canlı kanıt

| Deneme | Sonuç | Çağrı | Yeni ücret |
|---|---|---:|---:|
| V2, aynı hikâyenin iki kayıtlı sürümü | İki vaka başarısız | 2 audit | $0.077788 |
| V3, temiz ve plan sapmalı sürüm | Temiz sürüm kabul; yanlış giriş ve kapanış yakalandı | 2 audit | $0.093222 |
| V3 sınırlı onarım zinciri | İki turda ACCEPT | 2 patch + 2 audit | $0.166706 |

Son zincir, qualification sırasında kaydedilmiş hatalı sürümün model denetimini doğrudan tüketti; ücretli başlangıç denetimi tekrarlanmadı. İlk onarım giriş rotasını ve son görüntüyü düzeltti, fakat dönüş ziyareti konuşmasını bıraktı. Yeniden denetim bu kalan kapanış sapmasını buldu. İkinci onarım konuşmayı kaldırdı; son denetimde altı gereklilik SATISFIED oldu. Her iki turda da izin verilen değişikliklerin dışındaki metin byte düzeyinde korundu. Kabul edilen hikâyeye elle düzeltme yapılmadı; çalışma sırasında denetim sözleşmesi ve onarım istemi değiştirilmedi.

Yerelde 160 test, son CI çalışmasında 152 test geçti. Fark, yerel kısmi checkout içinde olup uzak ağaçta bulunmayan sekiz eski testten kaynaklanır. Çalışma 37303490454 kaynak alma sırasında çalıştırıcı bağlantısını kaybetti; model adımları hiç başlamadı ve ücret oluşmadı. Yeni tüketim kimliğiyle çalışma 37303889453 başarıyla tamamlandı; supervisor ve iki geçici runner sıfır çıkış koduyla sonlandı.

## Maliyet ve süre

Son dört çağrı $0.166706 ve 35.981 saniye model süresi tuttu. Kaydedilmiş ilk negatif V3 audit dahil bu onarım yolunun beş çağrısı $0.215292 ve 48.394 saniyedir; bunlar Writer veya Spine maliyeti içermez.

Bu turdaki sekiz çağrı $0.337716 ve 81.512 saniye ekledi. Tüm geliştirme denemeleri dahil tek hikâyenin birikimli maliyeti **$1.7585491 / $3**, kalan bütçe $1.2414509. Toplam 50 çağrı ve 392.891 saniye model süresi vardır. Model süresi CI, kuyruk, geliştirme ve çalıştırıcı kurulum süresinden ayrıdır. Bu toplam üretimde hikâye başına fiyat olarak kullanılamaz.

İlk hikâyeyi aion-labs/aion-3.5-mini oluşturdu; denetim ve onarımlar anthropic/claude-sonnet-5.5 ile yapıldı. Bu tur yeni Writer çağrısı, çeviri veya production LUMI yazımı yoktur.

## Sınırlar ve sonraki çalışma

Bu sonuç tek hikâyenin iki kayıtlı sürümü ve bir onarım zinciri içindir; başka hikâyelerde %95 güvenilirlik kanıtı değildir. Altı İngilizce gereklilik bu onaylı planın kaynak alıntılarından hazırlandı; henüz genel bir otomatik plan derleyicisi yoktur. Son metinde öneri düzeyindeki üslup pürüzü korunur. Sonraki geliştirme gereklilik çıkarımını genelleştirmek ve farklı hikâyelerde ölçmektir; bu rapor böyle bir çalışmanın yapıldığını iddia etmez.

## Kayıtlar

- Kabul edilen metin: evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-06-20261005/accepted-story.txt
- Sonuç, ham çağrılar, iki audit kararı ve iki koruma kanıtı: aynı klasör.
- Toplam muhasebe: evidence/lighthouse-editorial/decision-stabilization-summary.json
- V2/V3 qualification kanıtları: evidence/lighthouse-decision-qualification/ altındaki ilgili klasörler.
- Kabul edilen metnin SHA256: e6f5699a7c124cc90b17983a677e1abb89494313161fd49f624999510209f587
- Başarılı çalışma commit'i: ffb3667f1740dfb6c70db6d4028425e2353a679a
- Artifact 11342967000 ZIP SHA256: 3cd7c83fc7ff91781c258a2418b7e7f6d7e82b009d942d7a082d76c4ac523fc3
