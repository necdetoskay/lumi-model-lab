# NOVA v0.5 — Tomb Raider Survivor: gerçek çevrimdışı test kanıtı

**Tarih:** 2026-10-15
**Repository:** necdetoskay/lumi-model-lab
**Araştırma branch:** research/nova-tomb-raider-survivor-v0.5
**Başlangıç commit:** 965fb4c4145688152c8b81d5337f1981120a0d2c

## Kayıt kapsamı

- 3 ayrı Survivor oyunu ve 3 ek edisyon/yayın kaydı; edisyonlar ayrı ana hikâye sayılmaz.
- 18 resmî yayıncı retrospektifi / mekanik tanıtımı kaydı; 37 olay (2013: 12, Rise: 12, Shadow: 13).
- 9 yorumlanmış karakter durum aşaması; oyunlar arası 10 ilişki; 18 soyut mekanik adayı.
- 59 mekanik/olay kanıt bağlantısı; NOVA v0.3 ve v0.4 mekanikleriyle 46 kavramsal bağ.
- Kanonik girdi: data/nova/v0.5/source_records/tomb_raider_survivor.json
- Kaynak SHA-256: d50dc6b5624749557ed4d1a5318447b1467831f9bb21e1d69f31016776d1a154

## CI sunucusunun gözlenen test çıktıları

| Komut | Gözlenen çıktı | Exit |
|---|---|---:|
| python3 tools/nova/build_tomb_raider.py | deterministic schema_version 0.5.0-research-first-pass, 3/18/37/9/10/3/18/59/46 | 0 |
| python3 tools/nova/validate_tomb_raider.py | status=PASS, errors=[] | 0 |
| python3 tools/nova/test_tomb_raider.py -q | Ran 26 tests ... OK | 0 |
| python3 tools/nova/sqlite_tomb_raider.py | status=PASS; foreign_key_violations=0; events=37; evidence=59; links=10 | 0 |
| python3 tools/nova/validate.py | v0.1 PASS; 40 SGU episodes, 21 mechanisms | 0 |
| python3 tools/nova/smoke_test.py | v0.1 structural PASS; synthetic lexical cases=13 PASS, story trials=0 | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS; 5 works, 35 mechanisms | 0 |
| python3 tools/nova/test_cross_media.py -q | Ran 25 tests ... OK | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS; 19 works, 34 temporal connections | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | Ran 39 tests ... OK | 0 |
| python3 tools/nova/validate_prototype.py | v0.4 PASS; 16 events, 12 mechanisms | 0 |
| python3 tools/nova/test_prototype.py -q | Ran 22 tests ... OK | 0 |
| python3 -m py_compile tools/nova/{build,validate,test,sqlite}_tomb_raider.py | exit 0 | 0 |

## Testlerin sınırı

- Bu PASS sonuçları veri yapısının, kaynak ID bağlantılarının, edisyon ayrımının, ileri zaman yönlü eser bağlantılarının ve varsayım etiketlerinin iç tutarlılığını gösterir.
- Resmî yayıncı yazılarını web arama sonuçlarından okuduk; yeni tam oynanış kaydı, bağımsız ikinci editoryal denetim veya her URL için HTTP 200 doğrulaması yapılmadı.
- Oyunlar arası tematik karşılaştırmalar inference=true ile işaretli ve kanonik neden-sonuç iddiası değildir.
- Mekanik soyutlamaları, oyunların özgün karakter/sahne/diyaloglarının yeniden kullanılmasına izin vermez.
- Yalnız çevrimdışı veri derleme, doğrulama ve geçici SQLite indeksleme yapıldı. Hikâye üretimi, gerçek A/B denemesi, ücretli model çağrısı, LUMI production ve Story Harness entegrasyonu yapılmadı; quality_effect=not_evaluated.
- Geçici SQLite .nova-cache dizinindedir, Git commit kapsamına dahil edilmez.
