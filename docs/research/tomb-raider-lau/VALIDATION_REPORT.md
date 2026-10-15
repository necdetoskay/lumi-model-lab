# NOVA v0.7 — Legend/Anniversary/Underworld: doğrulama kanıtı

**Araştırma tarihi:** 2026-10-15
**Repository:** necdetoskay/lumi-model-lab
**Araştırma branch:** research/nova-tomb-raider-lau-v0.7
**Başlangıç commit:** 7dcdc1f4830d9fce32f3c84dc12bdde94c32cae5

## Kapsam ve veri sayıları

- 3 ayrı LAU eseri, 17 resmî yayıncı kaynağı, 36 olay (her oyuna 12).
- 3 oyun kronolojisi, 16 türlenmiş olaylar arası bağ.
- 7 ayrı nesne/eşya ve durum kaydı; Mjölnir için 4 zorunlu önkoşul/sonuç bağı.
- 5 Classic (1996) ↔ Anniversary (2007) yeniden anlatım *benzerlik* bağı. Aynı kanon olayı değiller.
- 6 editoryal süreklilik sınırı (DLC ve yayımlanmamış geliştirme görüntüleri dahil).
- 18 soyut mekanik, 50 kaynaklı olay bağlantısı, v0.3–v0.6 ile 36 kavramsal ilişki.
- Kanonik girdi: data/nova/v0.7/source_records/tomb_raider_lau.json
- SHA-256: 25df2ae566e372e3f1634c4fc45369bee73d88f0331d8dfb15a980043eb20f50

## CI runner üzerinde gözlenen sonuçlar

| Komut | Gerçek çıktı | Exit |
|---|---|---:|
| python3 tools/nova/build_tomb_raider_lau.py | schema_version=0.7.0-research-first-pass; bütün kayıtlar üretildi | 0 |
| python3 tools/nova/validate_tomb_raider_lau.py | status=PASS; errors=[]; prerequisite_edges=4 | 0 |
| python3 tools/nova/test_tomb_raider_lau.py -q | Ran 30 tests ... OK | 0 |
| python3 tools/nova/sqlite_tomb_raider_lau.py | status=PASS; foreign_key_violations=0; 50 evidence + 82 evidence_sources | 0 |
| python3 tools/nova/validate.py | v0.1 PASS | 0 |
| python3 tools/nova/smoke_test.py | 13 sentetik lexical kontrol PASS; 0 gerçek hikâye kalite denemesi | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS | 0 |
| python3 tools/nova/test_cross_media.py -q | Ran 25 tests ... OK | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | Ran 39 tests ... OK | 0 |
| python3 tools/nova/validate_prototype.py | v0.4 PASS | 0 |
| python3 tools/nova/test_prototype.py -q | Ran 22 tests ... OK | 0 |
| python3 tools/nova/validate_tomb_raider.py | v0.5 PASS | 0 |
| python3 tools/nova/test_tomb_raider.py -q | Ran 26 tests ... OK | 0 |
| python3 tools/nova/validate_tomb_raider_classic.py | v0.6 PASS | 0 |
| python3 tools/nova/test_tomb_raider_classic.py -q | Ran 26 tests ... OK | 0 |

## Sınırlar

- PASS, kaynak ID ve olay bağlılığı, eserin doğru sürekliliğe ait olması, remake sınırları, kronoloji ve eşya önkoşulları ile SQLite ilişki bütünlüğünün testidir.
- Her sahnenin özgün oynanıştan ikinci bağımsız editoryal doğrulaması yapılmadı. Kaynaklar ağırlıkla resmi yayınevinin/yapımcının retrospektifleri; tüm bağlantılar ve tüm cümleler bağımsız game-file incelemesiyle test edilmedi.
- **Önemli kronoloji istisnası:** Anniversary → Legend → Underworld sırası üç *ana hikâye* arasındadır. Legend içinde daha eski çocukluk/Paraíso geri dönüşleri bulunur; evrendeki her olayı aynı otomatik sıralama ile yerleştirmek yanlıştır.
- Underworld orijinal kampanya ile Beneath the Ashes / Lara's Shadow DLC olayları birbirine eklenmedi. İlk yayınlanan oyundaki kopya ile DLC'deki ikincil karakter gelişimi ayrı araştırma gerektirir.
- 2026'da yayımlanan Legend erken geliştirme görüntüsü, 2006'da piyasaya sürülen oyunda yer almış kanonik olay olarak kaydedilmez.
- Eski ve yeni Scion maceraları ortak fikirler taşır; aynı kanon veya doğrudan aynı tarihsel olay sayılmazlar.
- Mekanikler, başka hikâyeleri iyileştireceği gösterilmiş sonuç değil, kaynaklı **araştırma adayı**dır. Özgün içerik/diyalog/karakter kopyalanamaz.
- 0 ücretli model çağrısı, 0 hikâye üretimi veya gerçek A/B testi, 0 LUMI production ya da Story Harness değişikliği; quality_effect=not_evaluated.
- SQLite yalnızca .nova-cache altında geçici ve commit dışındadır.
