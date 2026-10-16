# NOVA v0.12 — BioShock Infinite (2013): gerçek test raporu

**Tarih:** 2026-10-16
**Branch:** research/nova-bioshock-infinite-v0.12
**Başlangıç commit:** 9637de1710fa9bfc27ac3ea266778574fa5155d4

## Kaynak / veri / sınırlar

- 1 orijinal 2013 ana oyun; 17 kaynak; 33 olay; 20 mekanik hipotezi; 60 olay/mekanik bağlantısı.
- 7 dünya, 10 kimlik varyantı, 9 öznel bilgi/dünya gerçeği, 6 oyuncu seçim kapsamı.
- 19 türlenmiş olay bağı, önceki BioShock çalışmalarına 8 olay karşılaştırması, önceki 149 mekanikten 41 kavramsal bağlantı.
- 10 editoryal uyarı; 0 bağımsız tam orijinal oynanış audit.
- Kanonik kaynak: data/nova/v0.12/source_records/bioshock_infinite_2013.json
- SHA-256: 6bf2a80e556850cd43111206eb668a6f765d084c72a0319a4e3313be0c5cc920

## Gerçekten gözlenen komutlar — ci-runner

| Kontrol | Sonuç | Exit |
|---|---|---:|
| build_bioshock_infinite.py | 0.12.0-source-first-pass; tüm JSONL/manifest üretildi | 0 |
| validate_bioshock_infinite.py | PASS, errors=[] | 0 |
| test_bioshock_infinite.py -q | Ran 40 tests ... OK | 0 |
| sqlite_bioshock_infinite.py | PASS; foreign_key_violations=0, 120 evidence/source bağlantısı, 149 prior mekanik | 0 |
| validate.py ve smoke_test.py | v0.1 PASS, 13 sentetik lexical smoke | 0 |
| v0.2 validate_cross_media.py + test_cross_media.py | PASS, 25/25 | 0 |
| v0.3 validate_prince_of_persia.py + test_prince_of_persia.py | PASS, 39/39 | 0 |
| v0.4 validate_prototype.py + test_prototype.py | PASS, 22/22 | 0 |
| v0.5 validate_tomb_raider.py + test_tomb_raider.py | PASS, 26/26 | 0 |
| v0.6 validate_tomb_raider_classic.py + test_tomb_raider_classic.py | PASS, 26/26 | 0 |
| v0.7 validate_tomb_raider_lau.py + test_tomb_raider_lau.py | PASS, 30/30 | 0 |
| v0.8 validate_prototype2.py + test_prototype2.py | PASS, 30/30 | 0 |
| v0.9 validate_prototype_comics.py + test_prototype_comics.py | PASS, 32/32 | 0 |
| v0.10 validate_bioshock.py + test_bioshock.py | PASS, 32/32 | 0 |
| v0.11 validate_bioshock2.py + test_bioshock2.py | PASS, 40/40 | 0 |
| python3 -m py_compile dört yeni araç | PASS | 0 |

## Açık kanıt ve araştırma borçları

- PASS veri bütünlüğü, bilgi/kimlik ve dünya ayrımı, kaynak referansı ve negatif test sözleşmelerini doğrular. Özgün tüm 2013 oyun dosyaları ve tam oynanış görüntüsü bağımsız incelenmedi.
- Yazar görüşmesi tasarım niyetidir, teknik oynanış gözleminin yerine geçmez. Dönemin rehberlerinin bazı komplo, zaman ve kimlik yorumları çıkarımdır.
- Booker ve Comstock alternatif varyantlardır. Anna/Elizabeth yeniden isimlenen kişi, Chen Lin A/B farklı dünyalarda farklı fiziksel durumdadır. Luteceler standart biyolojik ikiz olarak kodlanmaz.
- Finkton'daki farklı dünyalar arasında ölmüş bir kişinin yeniden yaşaması, önceki dünyada ölümün iptali anlamına gelmez.
- Seçilen kolye veya lokal oyuncu eylemi alternatif ana oyun finali değildir. Savaşta açılan Tear ile bütün sahnenin başka evrene geçmesi ayrı olay türleridir.
- Finale ilişkin tüm evrenlerin otomatik silindiği yorumu ve postcredit kapanışı mutlak nesnel kanon olarak modellenmez.
- Burial at Sea bölümleri ve Clash in the Clouds ana oyunun bu çalışma kapsamında değildir. Rapture ziyareti önceki oyun ve DLC olaylarının otomatik birleşmesi anlamına gelmez.
- Ücretli model API çağrısı 0, hikâye kalite A/B 0, LUMI production/Story Harness değişikliği 0, kalite etkisi not_evaluated.
- Geçici SQLite yalnız .nova-cache içinde ve Git commit dışında.
