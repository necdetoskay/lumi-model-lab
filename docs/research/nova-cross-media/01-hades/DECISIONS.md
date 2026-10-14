# Hades (2020) — Kararlar, alternatifler ve State değişiklikleri

Player choice ile senaryo karakterinin lineer seçimi birbirinden ayrıdır. Bir eserde seçim varsa bile alternatiflerin eksiksiz olmadığı yerler açıkça not edilir.

## H-D01 · Kaçış başarısızlığı ve hub'a dönüş

**Tür:** system_progression_not_alt_ending

**Ön koşul:** Zagreus yeraltında bir kaçış denemesi sırasında düşmanlardan ya da çevresel bir tehlikeden yenilgi alır.

**Seçim:** Ölüm sonrası saraya yeniden doğar.

**Sonuç / State değişimi:** run_position=house; run_attempt+=1; remembered_encounters ilerler; bazı ilişkiler ve açılan konuşmalar korunur.

**Sınır / belirsizlik:** Bütün güçlerin ve kaynakların aynı şekilde kalması iddia edilmez; kalıcılık türleri ayrılmalıdır.

Kaynak: [H-S1](https://www.supergiantgames.com/blog/hades-updates/), [H-S5](https://www.originstory.show/episodes/greg-kasavin)

## H-D02 · Yüzey zaferi ve dönüş kısıtı

**Tür:** system_progression

**Ön koşul:** Baba aşılmış, Persephone'ye varılmıştır.

**Seçim:** Zagreus konuşur ancak yeraltına bağlı doğası nedeniyle kalamaz.

**Sonuç / State değişimi:** mother_known=true; meeting_count+=1; surface_stay_limited=true.

**Sınır / belirsizlik:** Tek bir kaçış tüm ana öyküyü sonlandırmaz; çoklu dönüş koşulludur.

Kaynak: [H-S2](https://en.wikipedia.org/wiki/Hades_(video_game)), [H-S3](https://hades.fandom.com/wiki/Persephone)

## H-D03 · Ana öykü sonu

**Tür:** system_progression

**Ön koşul:** Persephone'yle birçok ziyaret ve anlatısal koşul tamamlanmıştır.

**Seçim:** Persephone Charon ile saraya geri döner.

**Sonuç / State değişimi:** persephone_at_house=true; hades_relation_status=reconciling; escape_purpose=security_testing.

**Sınır / belirsizlik:** Ana final ile daha sonra açılacak tanrılarla barışma bölümü birbirinden ayrılır.

Kaynak: [H-S2](https://en.wikipedia.org/wiki/Hades_(video_game)), [H-S3](https://hades.fandom.com/wiki/Persephone)

## H-D04 · İlişkisel epilog

**Tür:** relationship_gated

**Ön koşul:** Tanrılarla ilgili bağ ve konuşma koşulları karşılanır.

**Seçim:** Zagreus davetleri ulaştırır; tanrılar sarayda bir araya gelir.

**Sonuç / State değişimi:** olympian_family_reconciliation=true; epilogue_seen=true.

**Sınır / belirsizlik:** Her ilişki yan öyküsünün tamamlanması mecburiyeti çıkarılmamalı; bilinen rehber koşulları esas alınır.

Kaynak: [H-S4](https://hades.fandom.com/wiki/Epilogue_Guide), [H-S2](https://en.wikipedia.org/wiki/Hades_(video_game))
