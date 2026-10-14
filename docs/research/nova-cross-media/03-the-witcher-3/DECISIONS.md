# The Witcher 3: Wild Hunt (2015) — Kararlar, alternatifler ve State değişiklikleri

Player choice ile senaryo karakterinin lineer seçimi birbirinden ayrıdır. Bir eserde seçim varsa bile alternatiflerin eksiksiz olmadığı yerler açıkça not edilir.

## W-D01 · Botchling'i adlandırma veya öldürme

**Tür:** player_choice_method_branch

**Ön koşul:** Kayıp aile araştırmasında isim verilmemiş bebeğin botchling'i ortaya çıkmıştır.

**Seçim:** Dea adı verilip lubberkin'e çevirmek VEYA botchling'i öldürüp kanıyla fal ritüeli yapmak.

**Sonuç / State değişimi:** investigation_method değişir; baron_grief_response ve belirli diyaloglar etkilenir; ana Baron finali bu seçimle tek başına belirlenmez.

**Sınır / belirsizlik:** Metot dalı ile daha sonraki sonuç dalı farklı Quest State alanlarıdır.

Kaynak: [W-S3](https://www.witcher.tools/quests/family-matters)

## W-D02 · Whispering Hillock ruhunu yok etme

**Tür:** player_choice_world_state_branch

**Ön koşul:** Yerleşik ana görev akışında ruhla karşılaşılır.

**Seçim:** Ruhun kalbini yok etmek veya kandırarak öldürmek.

**Sonuç / State değişimi:** hillock_spirit=destroyed; downwarren=spared; crookback_children=remain_with_crones; anna=alive_but_traumatized; baron=alive_seeks_help.

**Sınır / belirsizlik:** Çocukların yazgısı ciddi kayıptır; bu dal basitçe 'iyi' olarak etiketlenmez.

Kaynak: [W-S4](https://www.witcher.tools/quests/the-whispering-hillock), [W-S5](https://www.witcher.tools/endings/bloody-baron), [W-S7](https://www.pcgamer.com/the-witcher-3-family-matters-best-ending-choices/)

## W-D03 · Whispering Hillock ruhunu serbest bırakma

**Tür:** player_choice_world_state_branch

**Ön koşul:** Yerleşik ana görev sıralamasında ruhu çıkarma ritüeli uygulanır.

**Seçim:** Ruhu at bedenine geçirerek serbest bırakmak.

**Sonuç / State değişimi:** hillock_spirit=freed; crookback_children=escape; downwarren=massacred; anna=dead_after_curse; baron=suicide.

**Sınır / belirsizlik:** Görevi çok erken sırada farklı tetikleme varyantlarına dair rehberlerde ayrıntı uyuşmazlığı vardır; bu sonuç standart sıralama içindir.

Kaynak: [W-S4](https://www.witcher.tools/quests/the-whispering-hillock), [W-S5](https://www.witcher.tools/endings/bloody-baron)

## W-D04 · Erken sıralama varyantının güven sınırı

**Tür:** player_quest_order_variant_uncertain

**Ön koşul:** Ruhla Crones ve köy arayışından önce karşılaşma olasılığı.

**Seçim:** Oyuncu görevlerin alışılmış sırasını değiştirir.

**Sonuç / State değişimi:** possible_quest_flag_variant=requires_independent_reproduction; no_unconditional_outcome_claim=true.

**Sınır / belirsizlik:** Bazı rehberler sonuç farkı bildirir, fakat erken sıranın koşulları tutarlı değil; test edilmemiş birleşim kesin kurala çevrilmez.

Kaynak: [W-S5](https://www.witcher.tools/endings/bloody-baron), [W-S7](https://www.pcgamer.com/the-witcher-3-family-matters-best-ending-choices/)

## W-D05 · Ciri'nin özgüvenini destekleyen tercihlerin birikmesi

**Tür:** player_relationship_state_branch

**Ön koşul:** Geralt Ciri'yle final öncesi kilit olaylarda konuşur ve eylemlerde bulunur.

**Seçim:** Onun kararlarına güven göstermek veya onu sürekli bastırmak; birden fazla sahnede tercihte bulunmak.

**Sonuç / State değişimi:** ciri_support_outcome=accumulates; ciri_survival=conditional_on_aggregate.

**Sınır / belirsizlik:** Bir tek anlık tercih ana finali belirliyor denemez; özgün bayraklar ve eşik ihtiyatlı yorumlanır.

Kaynak: [W-S6](https://witcher-games.fandom.com/wiki/The_Witcher_3_decision_checklist), [W-S8](https://game8.co/games/Witcher3/archives/280867)

## W-D06 · Ciri'nin Witcher veya Empress yolu

**Tür:** player_multi_state_ending

**Ön koşul:** Ciri White Frost'tan sağ çıkar; İmparator Emhyr'le görüşmesi ve siyasetin gidişi ayrıca belirlenir.

**Seçim:** Emhyr'e gidilmesi/gidilmemesi ve savaşın sonuçlarıyla ilgili önceki seçimlerin birleşimi.

**Sonuç / State değişimi:** main_ending=ciri_witcher_or_empress; condition=relationship_survival_plus_politics.

**Sınır / belirsizlik:** Tragik üçüncü son ancak destekleyici seçimler olumsuz olduğunda görülür; ayrıntılı sayısal eşik resmi olmayan rehberden geliyorsa otomatik kod kuralı değildir.

Kaynak: [W-S2](https://en.wikipedia.org/wiki/The_Witcher_3%3A_Wild_Hunt), [W-S6](https://witcher-games.fandom.com/wiki/The_Witcher_3_decision_checklist), [W-S8](https://game8.co/games/Witcher3/archives/280867)
