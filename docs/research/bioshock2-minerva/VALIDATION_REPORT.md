# NOVA v0.11 — BioShock 2 ve Minerva’s Den: kaynak ve test kanıtı

**Tarih:** 2026-10-16
**Repository:** necdetoskay/lumi-model-lab
**Branch:** research/nova-bioshock2-minerva-v0.11
**Başlangıç commit:** aa0b38e939b5336cde2d7a2971c9077db9c8a8b9

## Kaynak veri ve hacim

- 2 ayrı anlatı eseri: BioShock 2 (2010, özgün ana oyun) ve Minerva's Den (2010, bağımsız hikâye DLC).
- 19 kaynak; 30 olay (ana oyun 18, DLC 12); 18 soyut anlatı mekaniği.
- 47 kanıt bağlantısı; önceki mekaniklerle 36 kavramsal bağlantı; BioShock 2007 olaylarına 6 ilişkisel bağlantı.
- 4 ayrı karar ekseni (Little Sisters, Grace, Stanley, Gil), 3 niteliksel final sınıfı.
- 8 öznel bilgi / doğrulanabilir dünya durumu ayrımı, 16 olay bağlantısı ve 6 nesne/beden/erişim kaydı.
- 8 editoryal sınır ve 18 süreklilik kuralı.
- Kaynak: data/nova/v0.11/source_records/bioshock2_minerva_2010.json
- Kaynak SHA-256: 274da6aaab17c89a5b8c1605374a8bfbb4b7a6714b8f9834580252ff4e9cfbed

## CI runner üzerinde gerçekten çalıştırılmış denetimler

| Komut | Gözlenen sonuç | Exit |
|---|---|---:|
| python3 tools/nova/build_bioshock2.py | manifest 0.11.0-research-first-pass; tüm kayıtlar üretilmiş | 0 |
| python3 tools/nova/validate_bioshock2.py | status PASS, errors=[] | 0 |
| python3 tools/nova/test_bioshock2.py -q | Ran 40 tests ... OK | 0 |
| python3 tools/nova/sqlite_bioshock2.py | PASS, foreign_key_violations=0; evidence_sources=83 | 0 |
| python3 tools/nova/validate.py | v0.1 PASS | 0 |
| python3 tools/nova/smoke_test.py | v0.1 13 sentetik lexical smoke PASS (gerçek hikâye değerlendirmesi değil) | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS | 0 |
| python3 tools/nova/test_cross_media.py -q | 25/25 OK | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | 39/39 OK | 0 |
| python3 tools/nova/validate_prototype.py | v0.4 PASS | 0 |
| python3 tools/nova/test_prototype.py -q | 22/22 OK | 0 |
| python3 tools/nova/validate_tomb_raider.py | v0.5 PASS | 0 |
| python3 tools/nova/test_tomb_raider.py -q | 26/26 OK | 0 |
| python3 tools/nova/validate_tomb_raider_classic.py | v0.6 PASS | 0 |
| python3 tools/nova/test_tomb_raider_classic.py -q | 26/26 OK | 0 |
| python3 tools/nova/validate_tomb_raider_lau.py | v0.7 PASS | 0 |
| python3 tools/nova/test_tomb_raider_lau.py -q | 30/30 OK | 0 |
| python3 tools/nova/validate_prototype2.py | v0.8 PASS | 0 |
| python3 tools/nova/test_prototype2.py -q | 30/30 OK | 0 |
| python3 tools/nova/validate_prototype_comics.py | v0.9 PASS | 0 |
| python3 tools/nova/test_prototype_comics.py -q | 32/32 OK | 0 |
| python3 tools/nova/validate_bioshock.py | v0.10 PASS | 0 |
| python3 tools/nova/test_bioshock.py -q | 32/32 OK | 0 |

## Bu PASS sonucu neyi gösterir?

- Kaynak dosyası/manifest bütünlüğünü, kaynak ID’lerini, olay türünü, ana oyun–DLC ayrımını, geri dönüşlerle bugünkü kişisel kimliği ve önceki NOVA mekaniklerine ilişkin bağlantıları test eder.
- SQLite geçici indeksinde 0 yabancı anahtar ihlali, 2 ayrı eser ve 131 önceki mekanik kaydı bulunur.
- Yanlış/eksik fiziksel önkoşulun yorum bağı olarak düzeltilmesi de veri modelinin fail-closed kontrolünün bir örneğidir.
- Delta’nın 1958 geçmişiyle 1968 ana dönemi ve iki ayrı anlatının yayın tarihi birbirine karıştırılmaz.
- Yetişkinlerin bağışlanması ve Little Sister seçimlerinin Eleanor’un davranışına ve farklı epilog parçalarına etkisi ayrı izlenir.
- Minerva's Den’in Porter, Sigma, Thinker kimlikleri ve Pearl taklidi farklı öznel/bedensel nesnelerdir.

## Sınırlamalar ve açıklıklar

- Özgün 2010 sürümünü baştan sona oynayıp tam video/oyun dosyası denetimi yapmadık. 2K, Xbox resmi açıklamaları ve lisanslı Prima rehberi güçlü kaynaklar; GameFAQs rehberleri kısmen Remastered/Collection temellidir.
- Minerva’s Den olaylarında ikincil rehber/ansiklopedi referanslarına dayanan yorumlar vardır; bu referanslar uzmanlarca yapılmış ikinci bağımsız oyun auditinin yerini tutmaz.
- DLC olaylarının Delta ana kampanyasıyla tam saat/gün hizalaması ispatlanmadı; yalnız aynı Rapture dönemi genel ilişkisi belirtilir.
- Üç epilog ana sınıftır; bütün kombinasyonların sayısal koşulları ve ara sahneler tek tek bağımsız oynanıp doğrulanmadı.
- Karakterin zihnindeki geçmiş, radyo sesinin kaynağı ve biyolojik beden sahipliği ayrı bilgi katmanlarıdır.
- Oyuncunun birini öldürebilmesi, karakterin bunu kanonik olarak kesin yapmış olduğunu göstermez.
- Soyut anlatı mekanikleri hikâye kalitesini artırdığı gösterilmiş bilimsel sonuçlar değildir; quality_effect=not_evaluated.
- 0 ücretli model çağrısı, 0 hikâye üretimi/kalite A/B testi, 0 LUMI production veya Story Harness değişikliği. SQLite yalnız .nova-cache altında tutulur ve Git'e eklenmez.
