# Q25 kabul politikası ve nesne ilişkileri taslağı

Mevcut Q24 anotasyonu, genel kabul politikasıyla ayrı şemalı bir state taslağına dönüştürüldü. Yeni kitap için `new_<kaynak-kimliği>` kullanılıyor. Ayraç kitabın içinde, kitap ayraç içeriyor, atlas boş; Nisa’nın doğrudan elde tuttuğu ayraç yok. Ayracın Nisa’ya aitliği korunuyor. İlk seed byte’ları ve Q24 reddi değişmiyor.

Yeni sıradan nesneler varsayılan olarak kapalıdır. Bu çevrimdışı örnekte `EXPERIMENTAL_DRAFT_ONLY` kapsamında açıkça açıldı. Yeni belirleyici ipucu, aktör ve dünya/topoloji kuralı bu kapsamın dışında kalır. Kaynak/kimlik/ilişki hataları önceki representation gate’inde engellenir.

Sahiplik, konum, container ve doğrudan holder için KNOWN / UNKNOWN / NONE ayrılır. Kitabın sahibi bilinmiyor; bu “sahibi yok” demek değildir. “Okuyacağı kitap” ifadesinden sahiplik uydurulmaz. Konum da çözülmemiştir; ilk odadan otomatik çıkarılmaz. Politika UNKNOWN alanlara izin verebilir veya bunları engelleyebilir; belirsizliği gizleyemez.

Sonuç `ELIGIBLE_DRAFT`: yalnız yapısal politika ve nesne ilişkileri için uygun taslak. `state_commit_authorized=false`, `semantic_support_certified=false`, kapsam `OBJECT_RELATIONS_ONLY_NOT_FULL_STORY_STATE`. Genel property/knowledge/goal/threads/obligations bu işlemde metinden çıkarılmaz. İlk seed’deki found=false gibi property değerleri korunmuş, terminal doğruluğu onaylanmamıştır. Bu dosya eski StoryState şemasına dönüşüm veya tam kabul edilmiş son state değildir; revision alanı yoktur.

Yeni kitabın klasik ObjectState.owner alanına null sıkıştırılmıyor; ayrı draft şeması unknown durumunu açıkça taşıyor. Kanonik state şemasına uyarlama ve gerçek semantik extraction gereklidir. İki aynı mention’ın aynı nesne olup olmadığını otomatik çözmez.

Ücretli çağrı yok. Üretim commit’i yok. Adaylar için semantik destek/rol kontrolü, tam state coverage ve kanonik kayıt yetkisi henüz bekleniyor. Önceki kanıtlar değiştirilmedi; eski STATE_MODEL_GAP raporu yerine yeni tarihsel sonuç yazılmadı.
