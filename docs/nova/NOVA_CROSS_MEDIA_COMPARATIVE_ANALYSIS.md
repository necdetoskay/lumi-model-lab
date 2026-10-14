# NOVA — Beş eserden çıkarılan karşılaştırmalı anlatı dersleri

Bu belge film/oyun hikâyelerini birbiriyle karıştırmak yerine, aynı soruya hangi farklı yanıtı verdiklerini karşılaştırır. Yorumlar deneysel kalite etkisi iddiası değildir.

## 1. Tekrar: Hades karşısında Outer Wilds

**Hades:** Karakterin fiziksel başarısızlığı anıları, konuşmaları ve sosyal ilişkileri tamamen silmez. Kişiler önceki denemelere tepki verir. Mekanik CM01 ve CM02'nin ana sorusu, karakterin bir önceki denemeden ne öğrendiği ve kimin buna tanık olduğudur.

**Outer Wilds:** Dış evrenin fizik döngüsü aynı kalırken oyuncunun bilgisi değişir. Dünya bilgiyi otomatik bilmez. CM08 ve CM09'un sorusu, yeni bilginin hangi yerin anlamını değiştirdiğidir.

**LUMI kullanımı:** Hikâyede bir başarısızlık sonrası StoryState farkı açık olmalı. Bilinen yer, keşfedilmemiş yer, karakterin bildiği şey, söylenti ve NPC'nin bildiği şey ayrı tutulmalıdır. İki oyunu aynı 'geri dönüş' sistemi gibi görüp kalıcı nesneleri keyfi silmek doğru değildir.

## 2. Seçim: The Witcher 3 karşısında Hades

**The Witcher 3:** Bir karar, çocuklar, köy, Anna ve Baron gibi çok sayıda kişinin gelecekteki durumunu farklı biçimde değiştirebilir. CM16–CM21 geçici diyalog farkıyla gerçek dünya dalının ayırt edilmesini gerektirir.

**Hades:** İlişki ve görev koşullarıyla yeni diyalog veya epilog açılabilir; ancak bir roguelike denemesi otomatik olarak başka bir ana olay örgüsü yaratmaz. CM05 ve CM06 ilişki koşullarına göre kapanış kazandırır.

**LUMI kullanımı:** decision_kind değeri player_choice_world_state_branch, relationship_gated ve system_progression gibi açık tiplere ayrılmalı. İşlenmiş sonuç geriye dönük olarak değiştirilmemeli. Bir karakterin başka yerdeki durumu değişmişse bunu tetikleyen karar ledger'da bulunmalı.

## 3. Zamansal bilgi: Outer Wilds karşısında Arrival

**Outer Wilds:** Döngüde olay sırası fiziksel bakımdan başa döner, yalnız kayıt taşıyan kişilerde yeni bilgi kalır. CM09 ile epistemik State güncellenir.

**Arrival:** Olayların karakter ve dünya içindeki kronolojik sırası ile izleyiciye sunuluş sırası farklıdır. CM23 ve CM28 için aynı sahne 'önce izletilmiş' ama 'sonra yaşanmış' olabilir.

**LUMI kullanımı:** WorldTime, story_event_time, presentation_order ve known_by(character) ayrılmalıdır. Bunları tek tarih alanına zorlamak gerekçesiz öngörü ve fiziksel süreklilik hatası yaratır. NOVA v0.2 bunları kavramsal olarak işaretledi; üretim State sözleşmesini henüz değiştirmedi.

## 4. Kanıt ve anlam: Arrival karşısında 12 Angry Men

**Arrival:** Çok anlamlı tek bir kelimenin yanlış çevrilmesi toplumsal kriz yaratır. CM24, bilgiyi bağlam ve çeviri güvencesiyle ayırır.

**12 Angry Men:** Tek delilin tanıktan gelmesi onun doğru olduğu anlamına gelmez; bıçak örneği, yürüme süresi ve gözlük izi makul şüphe yaratır. CM30 ve CM31, delilden çıkarılan iddianın güven derecesini değiştirir.

**LUMI kullanımı:** Bir söylenti ile somut gözlem aynı epistemik güçte kaydedilmemeli. Anlatıcının bildiğiyle karakterin sandığı ayrıldığında daha tutarlı gizem ve adalet hikâyeleri üretilebilir.

## 5. Kapanış türleri ve yaş uygunluğu

**Hades:** Aileye kavuşma ana son, geniş ailenin barışı epilog.
**Outer Wilds:** Evreni kurtarmak yerine sona anlam vermek.
**The Witcher 3:** Bir final yerine ilişki ve siyasi State'e bağlı çoklu sonuç.
**Arrival:** Büyük tehlikenin çözümüyle karakterin acılı kişisel geleceğinin bilerek kabulü.
**12 Angry Men:** Katilin kimliğini kesin öğrenmeden hukuki makul şüphe standardına ulaşma.

**LUMI kullanımı:** Her hikâye mutlu bitecek diye bedelleri silme; ancak 4 yaş hikâyesine ağır kayıp, suç, travma veya kozmik yok oluş mekaniklerini doğrudan kopyalama. Yaş uygunluğu ve güvenli anlatım kabul kapısının konusudur.

## 6. Aday mekanikleri gerçek işe dönüştürme şartı

Mekanik önce Vault'tan bağımsızca alınır; sonra kaynak eser karakterleri ve teknolojileri çıkarılarak yeni State/tema için gerekçe ve kullanım koruması yazılır. Karakterin bilmediği bilgi veya olay sonunda kaybolan bedel, kanon doğrulama testinde reddedilmelidir.

**Bu belge gelecekteki 12 senaryolu A/B hikâye testlerinin gerekçeli hipotez havuzudur; başarılı sonuç raporu değildir.**
