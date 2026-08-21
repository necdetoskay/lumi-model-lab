Bir çocuk hikâyesi üret. Çıktın hem hikâyeyi hem de yapılandırılmış metadata alanlarını içersin. Bu çıktı daha sonra supervised fine-tuning eğitim verisine dönüştürülecektir.

Yalnızca geçerli YAML üret. Markdown code fence, açıklama, önsöz veya YAML dışı hiçbir metin yazma.

Gereksinimler:
- Dil: Türkçe
- Hedef yaş aralığı: 6-8
- Hedef uzunluk: yaklaşık 2000 kelime
- Hikâye tamamlanmış olmalı; başlangıç, gelişme ve tatmin edici bir son içermeli.
- Açık bir olay örgüsü, tutarlı ana karakter ve anlamlı bir problem/gizem/hedef bulunmalı.
- Ana karakterin kararları sonucu etkilemeli.
- Diyaloglar doğal ve yaşa uygun olmalı.
- Şiddet, ağır korku, yetişkin temaları ve doğrudan didaktik/ahlak dersi veren kapanış kullanılmamalı.
- Gereksiz tekrar ve dolgu kullanılmamalı.
- Bilinen kitap, film, çizgi film veya telifli karakterleri kullanma; özgün karakter ve mekân üret.

Çıktı şeması tam olarak şu alanları içersin:

id: generated_story_001
source_type: generated_story
source_model: "MODEL_ADI_BURAYA"
language: tr
title: ""
age_min: 6
age_max: 8
target_words: 2000
protagonist: ""
setting: ""
theme: ""
premise: >
  ...
constraints:
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

Kurallar:
- id her hikâye için benzersiz olsun.
- source_type her zaman generated_story olsun.
- language her zaman tr olsun.
- story alanında yalnızca hikâye metni bulunsun.
- suitability.status yalnızca pass, review veya reject olsun.
- metadata_confidence değerleri yalnızca high, medium veya low olsun.
- training_eligible ve suitability senin öz-değerlendirmen içindir; nihai eğitim kabul kararını harici kalite pipeline'ı verecektir.
