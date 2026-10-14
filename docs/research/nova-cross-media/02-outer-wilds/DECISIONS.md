# Outer Wilds (2019) — Kararlar, alternatifler ve State değişiklikleri

Player choice ile senaryo karakterinin lineer seçimi birbirinden ayrıdır. Bir eserde seçim varsa bile alternatiflerin eksiksiz olmadığı yerler açıkça not edilir.

## O-D01 · Keşif sırasını oyuncu seçer

**Tür:** player_choice_nonexclusive_order

**Ön koşul:** İlk uçuş sonrası güneş sisteminin çoğu bölgesi erişime açıktır.

**Seçim:** Oyuncu hangi gezegene ne zaman gideceğini seçer.

**Sonuç / State değişimi:** visited_locations ve known_facts değişir; dünya fiziği aynı kurallarla çalışır.

**Sınır / belirsizlik:** Keşif sırası tekil alternatif kanon final yaratmaz; ipucu sürekliliği önemlidir.

Kaynak: [O-S1](https://www.mobiusdigitalgames.com/outer-wilds.html), [O-S2](https://blog.playstation.com/archive/2019/10/08/explore-a-solar-system-that-resets-every-22-minutes-in-the-outer-wilds-out-this-month)

## O-D02 · Bilgi koşullu son yol

**Tür:** knowledge_gated_player_action

**Ön koşul:** Koordinatlar, warp çekirdeği ve Vessel rotası öğrenilmiş olmalıdır.

**Seçim:** Gelişmiş warp çekirdeği Destiny değil Nomai Vessel'e götürülür.

**Sonuç / State değişimi:** ash_twin_loop_active=false; final_route_available=true; death_can_be_permanent=true.

**Sınır / belirsizlik:** Bu eylem Nomai'nin planladığı Göz yolculuğu; çekirdek önce çıkarıldığında ölüm finali açılır.

Kaynak: [O-S3](https://outerwilds.fandom.com/wiki/Ash_Twin_Project), [O-S5](https://outerwilds.fandom.com/wiki/Endings)

## O-D03 · Ana kanonik son

**Tür:** player_final_action

**Ön koşul:** Vessel çalışır, koordinatlar girilir ve Evrenin Gözü'ne ulaşılır.

**Seçim:** Oyuncu final kozmik karşılaşmasını tamamlar.

**Sonuç / State değişimi:** main_ending_seen=true; cosmic_resolution=new_universe_implied; system_preserved=false.

**Sınır / belirsizlik:** Kayıp gezegenleri kurtarma sonucu üretilmez; yeni evrenin karakterlerinden güncel dünya State çıkarılmaz.

Kaynak: [O-S4](https://outerwilds.fandom.com/wiki/Eye_of_the_Universe), [O-S5](https://outerwilds.fandom.com/wiki/Endings)

## O-D04 · Alternatif son ekranları

**Tür:** player_failure_or_alternate_termination

**Ön koşul:** Ana yoldan sapma veya döngüyü kapatmış olma.

**Seçim:** Ölmek, çekirdek çıkarıldıktan sonra başka yerde beklemek ya da gerçeklik paradoksu oluşturmak.

**Sonuç / State değişimi:** termination_variant_seen=true; main_ending_seen=false.

**Sınır / belirsizlik:** Yalnız kaynakta doğrulanmış koşullar saklanır; DLC sonları bu korpusa katılmaz.

Kaynak: [O-S5](https://outerwilds.fandom.com/wiki/Endings)
