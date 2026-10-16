# SERA v0.48 — Mara S1 28-cümle gerçek Gemini/Haiku blind model deneyi: sonuç

**16 Ekim 2026 · SHADOW ONLY · SOURCE-BOUND ≠ SEMANTIC TRUTH · NO WORLD/G2 COMMIT**

## Deney ve doğrulama

- Onaylı 28 kaynak cümle / 7 ayrı dört-cümlelik kaynak-kör batch / 2 gerçek model, toplam 14 istek.
- Model listesi: `google/gemini-3.7-flash` ve `anthropic/claude-haiku-4.5`. Önceki Writer/diğer model sonucu bu isteklerde yoktur.
- Özgün Mara S1 kaynak SHA-256: `80304dbab7a8ed66501e5f3b1f773719f4f6a624a14c2eb03ef39160df686a03`. Kaynağa tek yeni cümle eklenmedi.
- [**Gerçek self-hosted CI #38957808652 — SUCCESS**](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38957808652): 726/726 test, 14 gerçek deneme ve **14 özgün, tam alınmış ham sağlayıcı yanıtı**, 14 ayrı sağlayıcı generation ID'si. Artefakt `sera-v048-full-28-real-model-once-38957808652`, ID `12071052906`.
- Kontrol: arşivdeki tüm `provider_reply_01.json`–`provider_reply_14.json` dosyalarının SHA-256 içeriği `result.json.receipts[].receipt_sha256` ile doğrulandı; model, kaynak ve makbuz kaydı bağlandı, tüm sağlayıcı yanıtlarının `provider_complete` alanı `true`, tüm cost alanları mevcut.
- Ücretli ilk izin koşumu [#38957407736](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38957407736), grant varlığını yanlışlıkla reddeden hazırlık testi nedeniyle **API/sağlayıcı adımına ulaşmadan** durdu: 0 gerçek sağlayıcı denemesi. Test düzeltilip [ön doğrulama #38957593200](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38957593200) yeşil olduktan sonra, **yeni grant yolu ve yeni code-parent SHA** ile tek kullanımlık izin commit'i `4683f240f7a81d727f72d68ffed3bd46f320f2bb` üzerinden gerçek çalışma yapıldı. Önceki harcama girişimi yeniden kullanılmadı.

## Gerçek sağlayıcı kapsamı

| Ölçüm | Gemini 3.7 Flash | Claude Haiku 4.5 |
| --- | ---: | ---: |
| Gönderilen batch | 7 | 7 |
| Makbuzlu gerçek cevap | 7 | 7 |
| Alıntısı ve span'i kaynakla bağlanan satır | **28 / 28** | **23 / 28** |
| Karantinaya alınan satır | **0** | **5** |
| Hiç istek yapılmamış satır | **0** | **0** |
| Kaynak-bağlı olay adayı | 30 | 24 |
| Dar fiziksel risk politikası bayrağı | 1 | 1 |
| Gerçek harcama | **0,05918325 USD** | **0,046723 USD** |
| Ortalama istem-yanıt süresi (uygulama gözlemi) | **12,19 sn** | **9,22 sn** |

**Toplam gerçek gözlemlenen maliyet: 0,10590625 USD** (onaylanan **0,25 USD gözlemlenen harcama stop** altında). Toplam uygulama tarafından ölçülen 14 istem-yanıt gecikmesi **149,891 sn**. Bu süre CI başlangıç/bitiş farkı veya sahne son-kullanıcı gecikmesinin tamamı değildir.

Haiku'nun **5** alıntı kaynak hatası: `s006`, `s014`, `s018`, `s021`, `s024`; aynı bağlayıcı `SWEEP_QUOTE_NOT_IN_TARGET_SENTENCE` ile yalnız bu cümleleri karantinaya aldı. Özellikle eski pencil pilotunda da `s021` ve `s024` karantinadaydı. Sistem alıntıları sessizce düzelterek yeni model kanıtı uydurmadı.

## İki bağımsız gerçek modelin karşılaştırması

**23 cümlenin** her iki modelde de kaynak-bağlı aday verisi mevcut. Olay imzası karşılaştırmasında:
- **21/23**: en az bir olay `kind/epistemic/effect/entity_refs` kombinasyonu farklı.
- **2/23**: belirtilen alanlarda aday olay imzaları eşleşti.
- Farkların ilk ayrışan bileşene göre ayrımı: **8 olay türü**, **5 etki**, **5 epistemik sınıflandırma**, **3 varlık referansı**.
- Eşleşme **doğruluk ispatı değildir**. Farklılık da tek başına bir modelin hangi noktada hata yaptığını göstermez; bağımsız semantik test gerektirir.
- 28 cümlenin **tamamının her iki modelde kaynak-bağlı olma** koşulu **başarısız** (`source_complete_candidate_binding_all_models=false`).

### Gerçek fiziksel hata riski tekrarları

1. **Haiku s004**: `his pocket watch open in his palm` kaynakta statik olarak açık duran saati anlatıyor. Model `CHANGE_STATE` adayı da önerdi; dar politika `STATIC_WATCH_PREDICATE_MISREAD_AS_TRANSITION_RISK` döndürdü. Bunun gerçek bir açma eylemi olduğu ispatlanmadı.
2. **Gemini s022**: `Vane watched the pencil move` gözlemdir; hareketin **neden/kim tarafından** yapıldığı cümleden kesin olarak çıkmaz. Model `MOVE` adayı önerdi; dar politika `PENCIL_MOTION_OBSERVED_BUT_CAUSAL_ACTOR_UNKNOWN` döndürdü.

Bu iki durum önceki gerçek pilotlarda da vardı; v0.48'de **yeni bir hata keşfi** iddiası değildir. Dar tespit kodunun yalnızca iki işaret üretmesi, öteki 26 cümlenin semantik olarak doğru olduğunu kanıtlamaz. Model kaynak alıntısını doğru kopyalasa bile fiziksel nedenselliği uydurabilir.

## Hattın güvenlik ve yetenek durumu

`FOURTEEN_REAL_RECEIPTS_NONCANONICAL` **gerçek provider isteği, arşiv, hash, kaynak-quote ve cümle kapsamının ölçümüne** işaret eder; `STORY_ACCEPTED` / `CANONICAL_READY` değildir.

- **0** yeni otomatik ücretli repair/retry, **0** kanonik WorldState/EventGraph/G2 commit, **0** üretim/SQLite lab DB yazısı, **0** uygulama tarafından konmuş output token tavanı.
- 5 eksik Haiku cümlesi ve 21 olay imzası farkı için **makine yönetimli hedefli kaynak-kör yeniden çıkarım**, makbuzlu ayrı yetkilendirilmiş model fallback, kaynak boyunca bağımsız hakem, fiziksel nedensellik/STATE-DELTA denetimi ve en sonda tüm-sahne yeniden doğrulama gerekli.
- Kaybolmuş veya belirsiz sağlayıcı çağrısı körlemesine tekrar gönderilemez. Bu 14 çağrıda böyle bir belirsizlik görülmedi; `outstanding_request_may_have_billed=false`.
- Story engine çekirdeği, G2 üretim DB ve `main` değiştirilmedi. Gerçek Mara S1 halen **HOLD**, SceneTrace **SHADOW ONLY**.
- Yeni gerçek ücretli onarım çağrısı için **ayrı kod-sabit, tek seferlik maliyet yetkisi** gerekir; otomatik hikâye hattında ise kullanıcıya elle cümle düzeltme yaptırılması önerilmez.

## Hedef — v0.49

Bu 14 gerçek makbuzu tekrar ücret ödemeden kullanarak `s006/s014/s018/s021/s024` için **otomatik, kaynak-kör, hedefli repair iş kuyruğu** ve 21 ayrışma için iki-model karar değil **bağımsız zaman/nedensellik kanıt sorguları** üretmek. İstenmeyen gerçek ücretli test başlatılmasın; yeni model cevabı geldiğinde tam kaynak yeniden karşılaştırılsın, düzelmeyen her fiziksel aday `FAILED_SAFE_FINAL` veya aday-HOLD ile güvenli sonlansın. Semantik doğruluk ve G2 yetkisi bu aşamada verilmez.

[SceneTrace #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) · [SERA Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306).
