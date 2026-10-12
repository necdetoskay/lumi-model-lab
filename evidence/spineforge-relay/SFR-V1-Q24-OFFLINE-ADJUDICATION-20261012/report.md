# Q24: metin hatası, state hatası ve kontrol hatasının ayrılması

Bu rapor mevcut kayıtların Codex tarafından ücretsiz okunmasına dayanır. İnsan tarafından onaylanmış golden veri, model karşılaştırması veya otomatik PASS değildir. Q24 reddi ve başlangıç state’i aynen korunur. Yeni hikâye/tamir/model çağrısı yapılmadı.

## Somut sonuç

İkinci metinde okunabilir ve sonu olan bir hikâye var: iki arkadaş kanonu oluşturan not ve iade kaydını araştırıyor, ayracı atlastan bulup çıkarıyor, Cem’in masumiyetini kabul edip ikisi de özür diliyor. Bu okuma, son state’in doğru veya bütün kalite koşullarının karşılanmış olduğunu kanıtlamaz. “Hikâye yazılamadı” ile “state ve kontrol doğrulanamadı” ayrı sonuçlardır.

Son fiziksel hareket açık: **“Nisa, ayracı çıkarıp avucunda tuttu.” → “Atlası dikkatlice rafa geri yerleştirdi.” → “Kırmızı ayracı okuyacağı kitabın doğru sayfasına yerleştirdi.”** Ayracın ucu dışarıda kalabilir; bu, ayraç kitapta mı sorusunu belirsiz yapmaz.

Fakat son kitap ilk state’te ayrı bir nesne değil. Çıkarım ayraç için `container=null`, Nisa için elde ayraç envanteri yazıyor. Bu tam bir son state değil. Sorun hem yeni nesne temsilinin eksikliği hem çıkarımın yanlış kaydıdır. Sahiplik, elde tutma ve kitap içinde bulunma aynı ilişki değildir. Bir kitap ekleme politikası olmadan doğru kanonik container üretilemez; `null` ile geçiştirilemez.

Kontrol kanıtı da hatalı: R0343, eleştirilen hatıra yerine önceki “emin değiliz” konuşmasını; R0535, ayracın bulunması yerine hazırlık defterini arama bölümünü gösteriyor. Kaynak hash’i ve geçerli aralık kimliği, iddianın o cümleyle desteklendiği anlamına gelmiyor.

İlk kontrol “atlası masaya veya kitap yığınına bırak” dedi. Yazar bunu yaptı. Son kontrol aynı ayrıntıyı uydurma diye reddetti. Bu, yazarın talimata uymamasının kanıtı değildir; tamir ölçütünün değişmesidir.

## Sekiz bulgunun ayrı değerlendirmesi

| Bulgu | Değerlendirme |
|---|---|
| A1-F1 | İlk aramada fiziksel ayracı arayıp notu okumamak mümkündür. Açıklama önerisi yararlı; mantıksal imkânsızlık kanıtlanmıyor. R0236 aramayı göstermiyor. |
| A1-F2 | Nisa atlası iade rafına bıraktığını hatırlıyor; donmuş kanonda iade eden Cem. Aradaki hareket açıklanmıyor. İlk metinde gerçek süreklilik açığı var; R0357 yalnız iade kaydını gösteriyor, Nisa hatırasını göstermiyor. |
| A1-F3 | Doğrudan ders cümlesi üslup tercihidir. Artık tamam ifadesi donmuş without instant intimacy yükümlülüğü açısından tartışılabilir; anında yakınlık ile özrü kabul etmek aynı şey değildir. Bu kısıt özgün kullanıcı özetinde değil, deney seed yükümlülüğünde eklenmiş. |
| A1-F4 | Ayraç son kitapta fakat container blue_atlas: gerçek state hatası. Son atlas konumu açık değil. Cem, Çünkü ben koymuştum ve unutmuştum sözünü doğrudan duyuyor: bilgi edinmedi itirazı yanlış. Nisa/Eren → Cem güvenini, Cem’in incinmişliğiyle karıştırmak ilişki yönü hatasıdır; masumiyetin kanıtlanması onların güvenini artırabilir. |
| A2-F1 | İlk kontrol leave it on the table or in the book stack önerdi. İkinci metin bu öneriyi izliyor. Son kontrol aynı ayrıntıyı invented unsupported detail diye reddediyor. Yeni belirleyici ipucu icat edilmiyor; hafıza not okunduktan sonra geliyor. Yığından Cem’e geçiş anlatıcı tarafından açıkça anlatılıyor. R0343 hatıra bölümünü göstermiyor. |
| A2-F2 | Cem önce incindiğini söylüyor, susuyor ve duraksıyor; sonra etkinliğe katılıyor. Oturmak tek başına instant intimacy kanıtı değildir. Masumiyetin söylenmesinden sonra özür dilemekte nesnel sıra hatası yok; rapor Kanıtım olmadan sözünü yanlışlıkla sahne 5’e yerleştiriyor, söz sahne 6’da. |
| A2-F3 | Metin ayracı çıkarıp avucunda tuttuğunu, atlası rafa geri koyduğunu ve ayracı okuyacağı kitaba yerleştirdiğini açıkça söylüyor. Ucun dışarıda kalması kitap içinde bulunmayı çelişkili yapmaz. Hangi kanonik kitap olduğu ayrı bir state kimliği problemidir. |
| A2-F4 | State container null ve inventory elde ayraç; terminal metin kitap içinde ayraç. Bunlar tam uyuşmuyor. Birçok çıkarım yanlış aralıkları kanıt diye gösteriyor. R0535 kurtarma yerine defter aramasını gösteriyor. Cem bilgi/duygu değerlerinin yalnız açık sözle kurulabileceği şartı aşırı katıdır; davranış da kanıt olabilir. State kesinliğini aşan çıkarımlar ayrıca işaretlenmelidir. |

## Yeni para harcamadan gereken kararlar

1. Kontrol bulgusu, ihlal ettiği gerçek request/canon şartını ve iddiayı destekleyen doğru cümleyi taşımalı. Üslup önerisi kesin tutarlılık hatasıyla aynı veto değildir. Bu rapor otomatik veto kaldırmıyor; sınıflandırma henüz çalışma taslağıdır.
2. Tamirde verilen önerinin uygulanması, sonraki kontrolde aynı gerekçeyle yeniden hata sayılamaz. Yeni gerçek çelişki bulunursa ayrı gösterilmelidir.
3. Hikâyenin anlatılmasına izin verilen sıradan nesneler ile state’teki kapalı nesne listesi uyuşmalı. Önce yeni nesne kimliği ve sahiplik/elde tutma/container anlamları açıkça kararlaştırılmalı; üretimde tek hikâyeye özel kitap ekleme hilesi yapılmamalı.
4. Bu kaydedilmiş cümleler ve state örnekleri, tartışmalı ve açık örnekler olarak ayrılıp insan onayından sonra golden veri olabilir. Şimdi guard yanlış-pozitif oranı veya model üstünlüğü hesaplanamaz.

Bu incelemede runtime, prompt, state, eski qualification ve bütçe kayıtları değiştirilmedi. Yeni ücretli koşu önerilmiyor. İlk ölçüm hedefi: aynı metin üzerinde doğru kanıt aralığı, aynı tamir ölçütü ve terminal container temsilini ücretsiz doğrulamak.
