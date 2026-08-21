Bir çocuk hikâyesi üret ve çıktıyı aşağıdaki YAML sözleşmesine TAM OLARAK uyan tek bir belge olarak ver. Bu çıktı supervised fine-tuning veri hattına makine tarafından okunacaktır; bu nedenle biçim ve uzunluk hatası kabul edilemez.

ÇIKTI KURALLARI — ZORUNLU:
- Yalnızca tek bir `yaml` kod bloğu üret. Kod bloğunun dışında hiçbir açıklama, önsöz, yorum veya sonuç yazma.
- Kod bloğunun içindeki YAML geçerli olmalı.
- Anahtar adlarını ASLA değiştirme, silme veya yeni anahtar ekleme.
- Anahtarların veri türlerini ASLA değiştirme.
- Alt çizgileri normal `_` karakteri olarak yaz. `\_` biçiminde escape ETME.
- Liste işaretlerini normal `-` olarak yaz. `\-` biçiminde escape ETME.
- TAB kullanma; yalnızca boşluk kullan.
- İç içe alanlarda aşağıdaki girintiyi birebir koru.
- `story: |` altındaki hikâyenin HER satırı iki boşluk girintili olmalı. Paragraflar arasındaki boş satırlar da blok içinde kalmalı.
- `theme` mutlaka YAML listesi olmalı; düz string yapma.
- `reasons` ve `warnings` liste olmalı; boşsa `[]` kullan.
- `training_eligible` boolean olmalı: `true` veya `false`; tırnak içine alma.
- `age_min`, `age_max`, `target_words` integer olmalı; tırnak içine alma.
- `id` boşluksuz ve yalnızca harf, rakam, `_` veya `-` karakterlerinden oluşsun.
- `source_model` alanına kendi model adını biliyorsan yaz; bilmiyorsan `unknown` yaz.

HİKÂYE GEREKSİNİMLERİ:
- Dil: Türkçe
- Hedef yaş aralığı: 6-8
- `story` alanındaki HİKÂYE METNİ EN AZ 1800 kelime olmalı.
- Tercih edilen aralık 1900-2200 kelimedir.
- 1800 kelimenin altında hikâyeyi BİTİRME.
- Emin değilsen kısa üretmek yerine mevcut sahneleri doğal biçimde geliştirerek biraz daha uzun üret.
- Uzunluğu artırırken yeni ve gereksiz yan olaylar ekleme; mevcut olay örgüsünü, diyalogları, karakter tepkilerini, gözlemleri ve mekân ayrıntılarını doğal biçimde derinleştir.
- `target_words` alanı her zaman `2000` olarak kalmalı; gerçek hikâye uzunluğunu bu alana göre kısaltma.
- Hikâye tamamlanmış olmalı; başlangıç, gelişme ve tatmin edici bir son içermeli.
- Açık bir olay örgüsü, tutarlı ana karakter ve anlamlı bir problem, gizem veya hedef bulunmalı.
- Ana karakterin kararları sonucu etkilemeli.
- Diyaloglar doğal ve yaşa uygun olmalı.
- Problem şiddetle çözülmemeli.
- Ağır korku, yetişkin temaları veya çocuk için uygunsuz içerik kullanılmamalı.
- Doğrudan didaktik/ahlak dersi veren bir kapanış kullanılmamalı.
- Gereksiz tekrar ve dolgu kullanılmamalı.
- Bilinen kitap, film, çizgi film veya telifli karakterleri kullanma; özgün karakter ve mekân üret.

UZUNLUK STRATEJİSİ — ÖNEMLİ:
Hikâyeyi tek kısa sahne gibi yazma. Doğal biçimde şu yapıyı kullan:
1. Karakter ve mekânı kuran anlamlı bir açılış.
2. Ana problem/hedefin ortaya çıkışı.
3. En az iki gelişme sahnesi: araştırma, deneme, diyalog, karar veya küçük engel.
4. Ana karakterin sonucu etkileyen bilinçli bir kararı.
5. Problemin çözümü.
6. Olayların sonucunu hissettiren sakin ve tamamlanmış bir kapanış.
Bu yapı yalnız uzunluk doldurmak için değil, yaklaşık 2000 kelimelik doğal bir hikâye ritmi oluşturmak için kullanılmalı.

AŞAĞIDAKİ ŞEMAYI BİREBİR KULLAN:

```yaml
id: generated_story_001
source_type: generated_story
source_model: "MODEL_ADI"
language: tr
title: ""
age_min: 6
age_max: 8
target_words: 2000
protagonist: ""
setting: ""
theme:
  - ""
  - ""
premise: >
  ...
constraints:
  - ""
  - ""
  - ""
story: |
  ...
suitability:
  status: pass
  reasons: []
training_eligible: true
metadata_confidence:
  title: high
  age_range: high
  protagonist: high
  setting: high
  theme: high
  premise: high
extraction_notes:
  useful_for:
    - full_story_from_brief
    - continuation
    - character_dialogue
    - scene_expansion
    - conflict_resolution
    - ending_generation
    - plan_to_prose
  warnings: []
```

ALAN ANLAMLARI:
- `protagonist`: ana karakterin adı, yaşı ve temel kişilik özelliklerini kısa biçimde açıkla.
- `setting`: ana mekânı ve atmosferi kısa biçimde açıkla.
- `theme`: 1-3 kısa tema içersin.
- `premise`: hikâyenin ana durumunu ve hedefini 1-3 cümlede açıkla.
- `constraints`: bu hikâyeye benzer bir örnek üretirken korunması gereken 2-5 önemli yazım kuralını listele.
- `story`: yalnızca tam hikâye metnini içerir; metadata veya açıklama ekleme.
- `suitability` ve `training_eligible`: yalnızca kendi öz-değerlendirmen içindir. Nihai eğitim kabul kararını harici judge pipeline'ı verecektir.
- `metadata_confidence` değerleri yalnızca `high`, `medium` veya `low` olabilir.
- `suitability.status` yalnızca `pass`, `review` veya `reject` olabilir.

ÇIKTIDAN ÖNCE SESSİZCE KONTROL ET:
1. YAML parse edilebilir mi?
2. Tüm zorunlu anahtarlar var mı?
3. Fazladan anahtar var mı? Varsa kaldır.
4. Alt çizgiler `\_` biçiminde escape edilmiş mi? Edilmişse düzelt.
5. Liste işaretleri `\-` biçiminde escape edilmiş mi? Edilmişse düzelt.
6. `theme` gerçekten liste mi?
7. `story: |` altındaki tüm hikâye satırları iki boşluk girintili mi?
8. `story` alanındaki hikâye 1800 kelimenin altında mı? Öyleyse ÇIKTI VERME; hikâyeyi mevcut sahneleri doğal biçimde geliştirerek uzat ve yeniden kontrol et.
9. Tercihen hikâye 1900-2200 kelime aralığında mı?
10. Hikâye tamamlanmış mı ve final sahnesi yarım kalmıyor mu?
11. Kod bloğu dışında herhangi bir metin var mı? Varsa kaldır.

Kelime sayısını kesin hesaplayamıyorsan güvenli tarafta kal: yaklaşık 2100-2200 kelimelik bir hikâye üretmeyi hedefle. 1800 kelimenin altında kalma.

Şimdi bu sözleşmeye uygun TEK bir özgün çocuk hikâyesi üret.