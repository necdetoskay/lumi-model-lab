# SERA v0.42 / SceneTrace v0.1 — Kaynak temelli sahne zaman çizelgesi (shadow-only)

**Durum:** İzole deney, gerçek model yanıtlarından *yeniden okuma*, ek model çağrısı veya üretim veri tabanı yazımı **yok**. [SceneTrace backlog #307](https://github.com/necdetoskay/lumi-model-lab/issues/307), [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).

## Neden bu katman?

Kullanıcının temel isteği: Hikâye sahnesindeki nesne, kişi, diyalog, algı, hareket, mekân, zaman, sahne sırası, fail ve ilişkilerin ileride sorgulanabilecek biçimde kaydedilmesi. Fakat **bir nesnenin metinde anılması fiziksel varlık oluşturmaz; bir hâlin tarif edilmesi yeni değişiklik olduğunu kanıtlamaz; zaman ifadesi olay zamanı olmak zorunda değildir**. SceneTrace hem görülen kanıtı hem de henüz bilinmeyenleri korur.

Bu sürüm SERA'yı yeniden inşa etmez: mevcut `sentence_ledger_v06.scanner` cümle/lexical candidate/action cue/time hint çıkarımını aynen kullanır, `real_pencil_partial_rows_v0412.replay` üzerinden **gerçek, SHA-256 ile sabitlenmiş** Haiku ödeme artefaktının v0.41.2'de bağımsız kaynak bağlamasını gösterir. v0.41.2'nin model doğrulamasını tekrarlamak dışında yeni semantik kazanım iddiası yoktur.

## Kayıt biçimi

`scene_trace_shadow_v042.build_trace` her kaynak cümlesini `scene_id`, `sentence_id`, exact `source_start/end`, `quote`, `source_sha256`, `narrative_ordinal` ile kaplar. Bu kesin **metin sırası** olarak tanımlıdır: `exact_story_second = null`, `story_time_window = null`; `02:10` gibi kaynak saatleri `TIME_EXPRESSION_MENTION` olarak ve **eylem zamanı olmadığı uyarısıyla** ayrı atomlarda saklanır.

Cümle başına ayrıntı atomları: `SOURCE_SENTENCE`, `ENTITY_REFERENCE_HINT`, `ACTION_OR_SPEECH_CUE`, `TIME_EXPRESSION_MENTION`, `PRONOUN_REFERENCE_UNRESOLVED`, `SOURCE_BOUND_MODEL_ENTITY_CANDIDATE`, `SOURCE_BOUND_MODEL_EVENT_CANDIDATE`. Her atom alıntısının orijinal cümle içinde exact `start/end` karşılığı zorunludur; bilinmeyen karakter kimliği ve fiziksel eski/yeni state doldurulmaz. Modelin önerdiği `after` veya `state_delta` alanları **yetki kazanamaz**.

Her cümle `SOURCE_ONLY_MODEL_NOT_ASSESSED`, `MODEL_ROW_SOURCE_BOUND_NONCANONICAL` veya `MODEL_ROW_QUARANTINED` durumlarından birindedir. Karantinaya alınmış satırın güvenli adaymış gibi tekrar kaydedilmesi engellenir.

## Test edilen gerçek Mara S1

Kaynak: 243 kelimelik orijinal Mara metni; SHA-256 `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`.

- **Bank:** `Teodor Vane stood beside the bench`. `candidate:bench` izlenebilir, fakat nesne dünyaya otomatik eklenmez.
- **Saat:** `his pocket watch open in his palm`. Bu, açılma olayının o anda yaşandığının kanıtı değildir. `STATIC_WATCH_DESCRIPTION_NOT_EVIDENCE_OF_OPEN_ACTION` yalnızca inceleme ipucudur.
- **Kalem:** `Vane watched the pencil move`. Kalemin hareketi anlatılırken hareket ettiren fail açık değildir. `OBSERVED_MOTION_DOES_NOT_IDENTIFY_CAUSAL_ACTOR` ipucu ve `actor_id=null` korunur.
- **Kayıtlı iddia:** Arşivdeki `02:10` ibaresi fiziksel trenin olay saatine dönüşmez.
- **Gerçek Haiku kaydı:** `s022`, `s023` source-bound candidate; `s021`, `s024` güvenli `quarantine`; diğer **24 cümle model tarafından bu pilotta incelenmedi**. SceneTrace bunun yerine 28 cümlelik *kaynak inceleme çizelgesi* sunar. Bunu tam sahne bağımsız semantik anlaması olarak sunmaz.

## Baseline vs SceneTrace

| Ölçüt | Var olan v0.41.2 kanıtı | SceneTrace v0.42 |
|---|---|---|
| Gerçek modele bağlı source-bound satır | 2 | 2; değişmedi |
| Geçersiz/karantinaya alınmış model satırı | 2 | 2; değişmedi |
| Tüm kaynak cümleleri için görünür sıralı kayıt | Cümle tarayıcıda vardı, toplu gösterim yoktu | 28/28 çizelgede |
| İncelenmemiş bağımsız model cümlesi | 24 | 24, özellikle görünür |
| Kesin hikâye saniyesi | Yok | Yok; uydurulmadı |
| Yeni doğrulanmış fiziksel state change | 0 | 0 |
| Ek ücretli çağrı/maliyet | — | **0 USD** |
| Bağımsız event recall/precision artışı | Kanıt yok | **Hâlâ kanıt yok** |
| Üretim/kanonik kayıt | Yok | Yok |

**Teknik sonuç:** İlk aşama fayda olarak *denetlenebilirlik ve hata görünürlüğü* sağlar. Daha az hata veya daha iyi bağımsız model çıkarımı henüz gösterilmiş değil. Bu nedenle `KEEP_SHADOW_ONLY_PENDING_INDEPENDENT_RECALL_MEASUREMENT`; mevcut SERA çekirdeğine şimdilik entegre edilmez.

## Nasıl kullanılacak?

`python -m experiments.sera.scene_trace_real_mara_smoke_v042 --receipt-dir <archived-v041-receipts> --json-output <trace.json> --markdown-output <timeline.md>`

Bu komut önce `real_pencil_partial_rows_v0412.replay` üzerinden orijinal ücretli evidence hash'lerini doğrular; yeni OpenRouter çağrısı yapmaz. Self-hosted CI aynı raporu JSON ve kolay okunur Markdown artefaktı olarak üretecek. `SceneTrace` sadece source/trace görünürlüğüdür; kullanıcı arayüzü ve yetkili dünya state işlemleri sonraki aşama.

## Sonraki karar kapısı

1. Aynı dondurulmuş gerçek metin ve değerlendirme alanlarında iki farklı yöntem denemek: bugünkü normal metin+extractor ile **beat sırası/interval bilgisi istenen** writer planı; gerçek bağımsız kaynak hakemleri ile aynı kurallarda ölçüm yapmak.
2. Sıra verisini mutlak zaman saniyesi gibi sunmamak; `depends_on`, `overlaps`, `story_time_range` için ayrı kanıtla doğrulama.
3. Nesne/konum/holder değişimi, diyalog, gözlem, rapor, karakter bilgisi ve çevre olayları için ayrı gerçek/aday tipleri; her state mutation reducer tarafından onaylanmadıkça HOLD.
4. Daha iyi recall/precision, daha az yanlış pozitif ve kabul edilebilir maliyet kanıtı **yoksa** SceneTrace yalnızca debug aracı olarak kalır.

**Değişmez:** Project_LUMI kanonik DB yazımı, self-reported model gold, üretim migrasyonu, yapay output token sınırı, sessiz ücretli model denemesi veya zorunlu manuel hikâye onarımı yok. Orijinal gerçek Mara S1 **HOLD**.
