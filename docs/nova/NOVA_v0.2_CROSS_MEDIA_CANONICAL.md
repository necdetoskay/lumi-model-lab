# NOVA v0.2 — Cross-media araştırma mimarisi

## Karar

NOVA, dizi analizinden farklı türlerdeki eserleri inceleyebilecek ayrı bir veri katmanına genişletildi. Önce **kaynak temelli olay örgüsü**, ardından **anlatı nasıl işliyor** analizi ve en sonda **soyut aktarılabilir mekanik** kaydedilir.

**İşleme sırası:** Hades → Outer Wilds → The Witcher 3 → Arrival → 12 Angry Men.

Bu çalışma LUMI Story Harness, production veya main dalında değişiklik yapmaz. SGU v0.1'in 40 bölümlük ilk korpusu da aynen kalır.

## Veri hiyerarşisi

1. **Work**: Eser, medya tipi, kapsam (temel oyun/ana film) ve final sınırı.
2. **Story beat**: Kaynak URL ile birlikte kronolojik önemli olay, dönüm noktası, sonuç. Medyadaki gösterim sırası ayrık bir kavramdır.
3. **Decision**: Karar ön koşulu, gerçekleşen eylem, State etkisi, karar türü, alternatif kapsamı.
4. **Narrative mechanism**: Eser bağımsız soyutlama, kaynak örneği, LUMI'ye özgün kullanım senaryosu ve koruma kuralı.
5. **Mechanic evidence**: Her bir mekaniğin hangi özgül olaydan ve hangi kaynaktan çıkarıldığını izleyen bağlantı.
6. **Source provenance**: URL, kaynak sağlayıcı, kanıt kapsamı, ilk araştırma doğrulama biçimi, CI HTTP erişim gözlemi.
7. **Quality evidence**: Gerçek deney olmadığı için henüz boş; kalite artışı kanıtsız ilan edilemez.

## Medyalar arası en önemli güvenlik ayrımı

- **Oyun seçimi** (The Witcher 3): Oyuncu eylemi gerçekten farklı dünya sonlarına ulaşabilir.
- **Sistem sonu** (Hades): Ölüp tekrar başlamak dramatik bağlama göre ilerlemeye dönüşür, tam dallanmış ana final demek değildir.
- **Bilgi koşullu ilerleme** (Outer Wilds): Dünya fiziği çoğunlukla aynı koşullarda yeniden başlarken karakterin bildikleri değişir.
- **Film karakter seçimi** (Arrival ve 12 Angry Men): İzleyici bu kararı vermez; filmde yalnız tek çizgisel olay örgüsü bulunur.

Bu dört sınıf birbirine zorla çevrilemez. Eserin karakterleri, yerleri ve özel teknolojileri soyut mekanizmadan ayrılmalıdır. Yalnız ilke ve nedensel koruma kullanılabilir.

## Kanonik dosyalar

- data/nova/v0.2/source_records: beş ayrı eserin insanca düzenlenen ilk kaynaklı araştırma kayıtları.
- data/nova/v0.2: derlenmiş works, story_beats, decisions, mechanisms, mechanic_evidence, sources JSONL ve manifest.
- docs/research/nova-cross-media: her eser için STORY, NARRATIVE_ANALYSIS, DECISIONS, SOURCES dosyaları.
- tools/nova/build_cross_media.py: kaynak JSON'dan tüm dokümanları ve JSONL'leri deterministik derleme.
- tools/nova/validate_cross_media.py: referans tutarlılığı, kapsam, doğruluk iddiaları, tür ayrımı ve kanon güvenlik duvarı.
- tools/nova/test_cross_media.py: 25 sentetik/teknik test.
- tools/nova/sqlite_cross_media.py: yerel disposable SQLite indeks.
- tools/nova/match_cross_media.py: şeffaf sözcüksel aday eşleştirici, model kalite tahmincisi değil.

## Kabul

**v0.2 araştırma veri kabulü:** Beş eser, 47 hikâye aşaması, 35 yeni mekanik, 85 sahne-mekanik kanıt bağı, 22 karar/sonuç kaydı, 25 kaynak kaydı ve 7 eserler arası benzerlik/fark bağlantısı.

**Henüz kabul edilmeyen:** Her sahnenin ikinci bağımsız editoryal doğrulaması, mekaniklerin birden çok eserde başarı gösterdiğinin kanıtı, semantik kaliteli Match, 12 özgün hikâye A/B testi, LUMI'ye production entegrasyonu.

## Tekrar kontrol

    python3 tools/nova/build_cross_media.py
    python3 tools/nova/validate_cross_media.py
    python3 tools/nova/test_cross_media.py
    python3 tools/nova/sqlite_cross_media.py
    python3 tools/nova/validate.py

Bu kontroller kalite deneyinin yerine geçmez. Herhangi bir fail halinde veri kapısı kapalıdır. Eserlerden LUMI'ye kanon veya benzersiz karakter kopyalanamaz.
