# SERA v0.40.1 — İlk gerçek model kanıtlarının ücretsiz yeniden doğrulanması

**16 Ekim 2026 · Gerçek OpenRouter kanıtı · Kanonik olmayan yalnızca-okuma analiz**

## Arka plan

SERA v0.40 pilotu, gerçek Mara S1 sahnesindeki daha önce atlanan `bench` nesnesini içeren dört cümlelik aynı kaynağı bağımsız Gemini 3.7 Flash ve Claude Haiku 4.5 modellerine birer kez gönderdi.

Kaynak SHA-256: `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`.

Kaynak gerçek model çalışması: [GitHub run 38936451931](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38936451931), artifact ID `12061516509`. Her iki model gerçekten çağrıldı. Bildirilen toplam ücret **$0.01637775** (Gemini $0.00796875; Haiku $0.008409). Gerçek model pilotunda sıfır kanonik ve üretim veritabanı yazması.

## Neden Haiku önce HOLD aldı?

Haiku tam bir JSON nesnesini `json` etiketli Markdown kod bloğuna sarmıştı. İlk v0.40 analizcisi doğrudan `json.loads(content)` çağırdığı için yanıt `Expecting value: line 1 column 1` hatasıyla reddedilmişti. Bu tek başına semantik başarısızlık kanıtı değildir.

v0.40.1 yeni parser yazmaz: SERA'nın mevcut `haiku_evidence_recovery_v011.parse_json_model_reply` fonksiyonunu aynen kullanır. Yalnızca **tam**, başka metin içermeyen kod bloğu soyulur; içerideki alanlar veya anlam değiştirilmez. Ardından eski v0.10 `bind_batch` ve `summarize_partial` her modele sıfır yeni çağrıyla yeniden uygulanır.

Tüm `result.json`, `provider_reply_1.json`, `provider_reply_2.json` dosyaları gerçek run'daki **tam SHA-256 hash'leriyle sabitlenmiştir**; başka run, yeni/yabancı model cevabı, response ID, yanlış kaynak hash'i veya doğrulanmamış maliyet karıştırılamaz.

## Bağımsız yeniden bağlama sonuçları

| Gözlem | Gemini 3.7 Flash | Claude Haiku 4.5 |
| --- | --- | --- |
| Yanıt JSON biçimi | Doğrudan JSON | Tam JSON kod bloğu; güvenli soyma |
| Kaynak cümlesi bağlama | Geçti | Geçti, biçim düzeltmesinden sonra |
| Nesne/karakter mention adayı | 13 | 9 |
| Olay adayı | 3 | 6 |
| `bench` geçerli kaynağa bağlandı | Evet | Evet |
| Anlamsal altın referans / tam recall | **Kanıtlanmadı** | **Kanıtlanmadı** |
| Sonuç | `SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD` | `SOURCE_BOUND_CANDIDATES_SEMANTIC_HOLD` |

**Kritik ayrım:** Geçerli cümle alıntısı, olayın *gerçekten bir geçiş* olduğunu kanıtlamaz. Haiku dördüncü cümlede "his pocket watch open in his palm" (zaten açık saat) betimlemesinden `CHANGE_STATE` üretmiş. Kaynaktaki statik sıfatı, olay anında açma eylemi sanmış **olabilir**. Bağımsız kontrol `V0401_STATIC_WATCH_DESCRIPTION_MAY_BE_FALSE_TRANSITION` uyarısı üretir. Bu kesin semantik GOLD hükmü değildir; fiziksel geçmiş ve net geçiş kanıtı olmadan reducer olayına dönüşmemelidir. Gemini aynı cümle için `TEXTURE` ve sıfır olay döndürmüştür. Modeller arasında olay aday sayısı farkı güvenilirlik farkı için araştırma sinyalidir; daha fazla olay = daha iyi recall anlamına gelmez.

## Otomasyon ve kayıt

`real_blind_receipt_replay_v0401.py` model çağrısı **yapmaz**; yalnızca daha önce arşivlenmiş yanıtları açar ve sabit kaynak üzerinden test eder.

`sera-v0401-real-receipt-replay.yml` yalnızca **self-hosted Linux** üzerinde GitHub Actions artifact'ını indirir; `OPENROUTER_API_KEY` kullanmaz, model POST veya retry yoktur. [CI 38937487848](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38937487848) **SUCCESS**. 669/669 Python testleri; yeniden bağlama artefaktı `sera-v0401-actual-receipts-replay-38937487848` (ID `12061837024`).

Bu başarı, gerçek hikâye hattının bağımsız semantik anlamayı çözdüğü anlamına **gelmez**. SERA fiziki dünya G2 yetkisi, tam sahne kapsaması, sayısal recall/precision ve üretim yazma yetkisi hâlâ YOK. Gerçek Mara S1 **HOLD** durumundadır. Origin/Saga geliştirmeleri ayrı tutulmuştur.

## Sıradaki güvenilirlik kapısı

- **Fiziksel statiklik → geçiş ayrımı:** Betimlenen sahiplik/konum/açıklık durumu ile metinde gerçekten gerçekleşen eylemi ayıran bağımsız kontrol. Bir durumun cümlede görülmesi, `CHANGE_STATE` yazılması için yeterli değildir.
- **Kaynakta atlanmış olay/nesne riskleri:** Objektif fixture/insan yazılmış kaynak bazlı değerlendirme örnekleriyle, model yanıtını GOLD kabul etmeden ölçüm. Etiketler yalnızca test hedefidir, canlı onay değil.
- **Ayrı ücretli onayla büyüme:** Aynı dondurulmuş gerçek Mara metninin kalem (`pencil`) bölümüne ve sonra tam sahneye genişleme. Ödeme/kesinti geri dönüşü olmadan bir modele sessizce otomatik yeniden istek gönderilmeyecek.
- **Gölge dünya, kanonik olmayan:** Kaynak/epistemik/nedensellik doğrulaması sonrası v0.37 SQLite simülasyonuna denenebilir; şüpheli Haiku `CHANGE_STATE` olayını kabul etmeyeceğiz.

Tracking: [Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
