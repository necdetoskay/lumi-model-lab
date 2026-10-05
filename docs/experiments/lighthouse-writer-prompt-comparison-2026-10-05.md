# Aion Writer prompt karşılaştırması — 5 Ekim 2026

## Deney tasarımı

Kullanıcı, hataları beş kategoriye ayıran kısa Writer prompt ekinin ilk üretimde hataları azaltıp azaltmadığını görmek istedi. Aynı onaylı plan, Aion modeli ve üretim ayarlarıyla iki yeni metin karşılaştırılır. Birinci metin güncel mevcut promptu, ikinci metin aynı promptun sonuna eklenen karakter kuralları, mekân/hareket, nesne sürekliliği, fiziksel eylem ve gerçek kapanış kontrolünü kullanır. Ek metin 1.507 karakterdir. Promptun geri kalanı ve user message aynıdır.

İlk tarihsel Aion çağrısı 1.400–1.800 kelime hedefiyle yapılmıştı. Kullanıcının daha sonraki kararıyla üst sınır kaldırıldı. Tarihsel metni tek kontrol kabul etmek bu değişkeni karıştıracağından iki güncel üretim yapılır. Her ikisinde minimum 1.400 kelime, üst sınır yoktur.

- Writer: aion-labs/aion-3.5-mini; temperature 0.76, max_tokens 7000; iki tek çağrı, seed yok.
- Aynı onaylı plan hash'i: 727c4f67752ad8d7a164c382d7cf7c2840203c22dbd1a48db31c1f3995078a69.
- Denetim: aynı Sonnet 5.5 modeli, aynı daha önce canlı doğrulanmış altı gereklilikli V3 sözleşmesi ve istemi. Her metin için bir bağımsız audit. Yeni 16 maddelik sözleşme bu karşılaştırmada kullanılmaz.
- Audit girdisi varyant adı, beklenen sonuç veya diğer metni içermez.
- Metinler ham üretim olarak saklanır; patch, otomatik retry, çeviri ve production yazımı yok.
- Yerel kontrol: 196 test PASS, 12.79 saniye. CI kontrolü: 188 test PASS, 14.11 saniye. Sekiz testlik fark, yerel kısmi checkout içinde bulunan önceki ek testlerden kaynaklanır.
- Başlangıç toplamı $1.7585491; tüm yeni ücretler aynı hikâye için onaylı $3 toplamına dahildir.
- Çalışma commit'i: 378005a49aa52bee140fdf750c9e9ada9620a118; run 37322302573.

## Yorumlama sınırı

Her prompt için tek örnek vardır. Model örnekleme değişkenliği nedeniyle gözlenen fark promptun genel nedensel etkisini veya başarı oranını kanıtlamaz. Model audit'indeki bulgu sayısı gerçek kusur sayısı olarak otomatik kabul edilmez; metinler ayrıca kaynak planla karşılaştırılarak okunur. Anlatımın mekanikleşmesi bir editoryal değerlendirmedir; otomatik testin ölçtüğü bir puan değildir.

## İlk çalışmadaki hata ve kayıt düzeltmesi

Çalışma 37322302573 ilk kontrol Writer çağrısında okunabilir metin alamadı: OpenRouter response did not contain structured text. Audit veya ikinci Writer çağrısı başlamadı. Bu yeni deney harness'ının hata yakalayıcısı OpenRouterCallError.trace içindeki provider gövdesini ve ücretini kaydetmedi. Bu bir kayıt hatasıdır; ilk sonuç dosyasındaki new_cost_usd=0 değeri doğrulanmış sıfır ücret anlamına gelmez. Ham ilk sonuç korunur; accounting-erratum.json eksik muhasebeyi belirtir. Kesin ücret bilinmiyor; sonraki bütçe kontrollerinde ilk çağrı için $0.04 ayrılır.

Hata handler'ı, boş içerik dönen yanıtın da id/model/choices/usage alanlarını ve gerçek ücretini saklayacak şekilde düzeltildi. Yeni sürüm bir varyantın başarısızlığını diğerine onarım veya retry olarak taşımaz: ücret biliniyorsa bağımsız ikinci varyantı test eder; ücret bilinmiyorsa devam etmez. İlk başarısız çağrı bu kural eklenmeden gerçekleştiği için ayrı rezervle izlenir.

İkinci çalışmanın Writer request hash'leri ilk çalışmayla birebir aynı: mevcut prompt 599e20673e371fa349adbe28c25ecbad0f553a6c1571bbd13dc168bad7711596, ekli prompt 310293b4734ead9a4db6912b81a9893e88aef03144b842c392c030c5c4d6d08c. Promptlar, kaynak plan ve üretim ayarları değiştirilmedi. Yalnız hata kanıtı/muhasebe ve bağımsız vaka yürütme düzeltildi.

İkinci çalışma: 37323565414; commit ad730cacc56157c664fd688aeb1e8ed19cba24f3. Düzeltilmiş sürümün yerel testleri: 198 PASS, 13.71 saniye.

## Canlı sonuç: karşılaştırma yapılamadı

İkinci çalışmada iki Writer çağrısı da finish_reason=length, message.content=null ile sonlandı. Her ikisinde completion_tokens=7000 raporlandı. Kontrol için reasoning_tokens=7556, ekli prompt için 7562 raporlandı; bu değerler completion_tokens değerinden yüksek olduğundan sağlayıcının ham metrikleri kendi içinde tutarsızdır ve düzeltilmeden saklandı. Kesin bulgu: iki çağrı da token sınırında bitti ve hikâye metni vermedi. Bunun düşünme bütçesinin metne alan bırakmamasıyla ilişkili olması bir çıkarımdır; sağlayıcının tam davranışı henüz doğrulanmadı.

| Varyant | Okunabilir hikâye | Sonlanma | Ücret | API süresi |
|---|---|---|---:|---:|
| Güncel mevcut prompt | Yok | length | $0.01044134 | 100.122 s |
| Beş kategori ekli prompt | Yok | length | $0.0122491 | 122.857 s |

Audit çağrısı veya onarım yapılmadı. İkinci çalışmadaki iki çağrının kesin toplamı $0.02269044; bilinen bütün hikâye/geliştirme ücretlerinin toplamı $1.78123954. İlk başarısız çağrının kesin ücreti bilinmiyor. Ona ayrılan $0.04 dahil bütçede izlenen tutar $1.82123954; bu gerçek fatura toplamı iddiası değildir. Toplam muhasebe tamamlanmış olarak işaretlenemez.

CI 190 test PASS, 14.14 saniye; yerel düzeltilmiş kapsam 198 PASS. Testlerin yeşil olması modelin hikâye üretebildiğini kanıtlamadı. Sonuç COMPARISON_INCOMPLETE; hata azalması, okunabilirlik veya yeni prompt başarısı hakkında çıkarım yapılamaz.

Sıradaki teknik iş Aion'un çıktı/düşünme bütçesi davranışını teşhis etmek ve kontrollü metin üretimini geri kazanmak. Sonraki prompt karşılaştırmasında iki varyantın üretim ayarları yine eşit olmalıdır. Aynı başarısız istekleri kör retry döngüsüne sokmak geçerli çözüm değildir. Bu rapor yeni bir runtime ayarıyla başarılı üretim yapıldığını iddia etmez.

Tam provider id/model/choices/usage kayıtları ikinci çalışma klasöründeki calls.json içindedir. Özet comparison-summary.json. Artifact 11351900070 ZIP SHA256: 29b6f6dcf11061c1a3ee140d8c9f2ff2920c2ab5227cfc6e619c393c077ca9aa.

## Belgelenmiş çalışma ayarı düzeltmesi: üçüncü kontrollü deneme

Aion'un 5 Ekim 2026 tarihinde okunan resmi API referansı, `max_tokens` sınırının düşünme ve görünen metin tarafından ortak kullanıldığını; düşünme sınırı tüketirse boş içerik ve `length` dönebileceğini açıkça belirtiyor. Akışsız çağrıda 125 saniyelik yanıt sınırı var; sunucu üretimi sürdürüp ücretlendirebilir. Uzun çağrılar için akışlı yanıt öneriliyor. Kaynak: https://www.aionlabs.ai/docs/api-reference/ . OpenRouter model endpoint kataloğunda Aion 3.5 Mini maksimum completion sınırı 32.768 token: https://openrouter.ai/api/v1/models/aion-labs/aion-3.5-mini/endpoints .

Üçüncü denemede iki varyant da aynı `max_tokens=16384`, `stream=true`, `stream_options.include_usage=true` ve mevcut `reasoning.effort=low`, `reasoning.exclude=true`, temperature 0.76 ayarlarını kullanır. Promptlar ve onaylı plan değiştirilmez. Bu teknik token tavanı, hikâyeye kelime sayısı üst sınırı koymaz. Tarihsel 7.000 token sınıfını yeniden normalizasyonla kullanıp 16.384 sınırını yanlışlıkla geri düşürmemek için ayrı tek çağrılık transport eklenmiştir; eski runtime profilleri değişmemiştir.

Akış tamamlanmadan kesilirse eldeki görünür metin, id ve usage korunur; bildirilmemiş ücret sıfır varsayılmaz. Gizli düşünme içeriği ve API headers saklanmaz. Yerel 202 test PASS / 13.27 saniye. Üçüncü çalışma commit'i 013cae960772f807e9846c30ed310731fa427c97; run 37329261958. Manifestteki değişmeyen dosyalar remote ile aynı; değişen/yeni dosyalar ayrı commit'te donduruldu ve yedi dosyanın remote blob hash'leri doğrulandı.

Üçüncü çalışmanın başlangıç bilinen ücret toplamı $1.78123954; ilk kayıtsız çağrı rezervi $0.04. Her Writer için $0.06, her audit için muhafazakâr girdi/çıktı tahminiyle bütçe kontrolü yapılır. En çok iki Writer ve iki audit; onarım ve otomatik retry yoktur. Üretim sonucu henüz bu bölümde iddia edilmez.

## Üçüncü sonuç ve son desteklenen tavan denemesi

Üçüncü çalışmada iki Writer da 16.384 completion token, boş görünen içerik ve `length` ile bitti. Kontrol $0.02357894 / 271.567 s; ekli prompt $0.02363222 / 304.084 s. Toplam yeni $0.04721116 / 575.651 s. Hiç audit başlamadı. Sağlayıcının reasoning sayıları yine completion sayısını aşıyor (17.388 ve 16.668); ham değerler korunuyor. Akışın çalışması tek başına metin üretimini düzeltmedi. CI 194 PASS / 14.55 s. Artifact 11354346656 SHA256 fe56d056b34e8e93c4dc7cd3003551601a8997bc564e00e7c09e49b1ad14317c.

Dördüncü kontrollü çift, resmi maksimum 32.768 completion token ve ayrıca `reasoning_effort=low` kullanır; birleşik `reasoning.effort=low` korunur. OpenRouter bu üst düzey parametreyi de belgeler: https://github.com/OpenRouterTeam/docs/blob/main/api_reference/parameters.mdx . Önceki ayarın sağlayıcıda yok sayıldığı kanıtlanmış değildir; bu yeni ayar uyumluluk teşhisidir. İki varyantın kaynak/promptları aynı ve diğer parametreleri eşit. 16.384 tavanındaki başarısızlığın ardından belgesiz bir sınır icat edilmez. Yeni başlangıç kesin ücret $1.8284507, kayıtsız ilk çağrı rezervi $0.04; Writer başına $0.10 bütçe rezervi. Modelin desteklenen en büyük tavanında da görünür metin dönmezse aynı karşılaştırmayı daha yüksek tavan veya kör tekrarlarla sürdürmek geçerli değildir.
