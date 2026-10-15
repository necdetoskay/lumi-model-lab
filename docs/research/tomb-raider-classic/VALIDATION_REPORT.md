# NOVA v0.6 — Tomb Raider Classic: CI doğrulama kanıtı

**Kapsam:** Altı Core Design ana oyunu (1996–2003), yalnız çevrimdışı veri araştırması.
**Tarih:** 2026-10-15
**Başlangıç commit:** 772ee4f52a897273d8c3257745948b50ba132a45
**Branch:** research/nova-tomb-raider-classic-v0.6

## Kanonik veri ve hacim

- Ana kaynak: data/nova/v0.6/source_records/tomb_raider_classic.json
- Kaynak SHA-256: 386a14384bf16909b63aa472864cb8fc9e731057e4e51264d0b1acf580074f19
- 6 eser; 21 Tomb Raider resmî yayıncı sayfası / tasarımcı görüşmesi.
- 36 kaynak bağlantılı olay; 10 zaman/anlatım bağı; 3 edisyon/ek içerik kaydı; 3 süreklilik belirsizliği.
- 19 soyut anlatı mekanizması; 54 mekanik/olay kanıt bağlantısı; 38 önceki sürüm kavram bağlantısı.

## CI sunucusunda gerçekten çalıştırılan komutlar

| Komut | Gözlenen sonuç | Exit |
|---|---|---|
| python3 tools/nova/build_tomb_raider_classic.py | 0.6.0-research-first-pass ve sayımlar doğru | 0 |
| python3 tools/nova/validate_tomb_raider_classic.py | status=PASS, errors=[] | 0 |
| python3 tools/nova/test_tomb_raider_classic.py -q | Ran 26 tests ... OK | 0 |
| python3 tools/nova/sqlite_tomb_raider_classic.py | status=PASS, foreign_key_violations=0; evidence_sources=79 | 0 |
| python3 tools/nova/validate.py | v0.1 SGU PASS | 0 |
| python3 tools/nova/smoke_test.py | 13 sentetik lexical smoke PASS; story quality trial 0 | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS | 0 |
| python3 tools/nova/test_cross_media.py -q | Ran 25 tests ... OK | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | Ran 39 tests ... OK | 0 |
| python3 tools/nova/validate_prototype.py | v0.4 PASS | 0 |
| python3 tools/nova/test_prototype.py -q | Ran 22 tests ... OK | 0 |
| python3 tools/nova/validate_tomb_raider.py | v0.5 PASS | 0 |
| python3 tools/nova/test_tomb_raider.py -q | Ran 26 tests ... OK | 0 |
| python3 -m py_compile tools/nova/{build,validate,test,sqlite}_tomb_raider_classic.py | exit 0 | 0 |

## Güven ve yorumsal sınırlar

- PASS, kaynak ID, şema, geçmiş/anı/tasarım planı ayrımı, sürüm/koleksiyon ayrımı ve SQLite ilişkilerinin doğrulanmasıdır.
- Her olayın özgün oyun görüntüsüyle ikinci bağımsız uzman kontrolü yapılmadı. Resmî yayıncı retrospektifi, özgün oyunun eksiksiz kaydı değildir.
- Resmî tasarımcı röportajlarında yayımlanmayan Angel of Darkness sahneleri anlatılabilir. C03-06 bilinçli olarak development_plan_not_game_canon biçiminde kaydedildi.
- Chronicles çerçeve anlatısı ve anılar doğrusal tarihsel nedensellik zincirine birleştirilmez.
- Bazı eserlerin ticari yeniden düzenlenmiş sürümleri ve ek içerikleri özgün altı ana oyundan ayrı sayılmadı.
- Özgün oyun sahnesi/diyaloğu/karakteri yeni hikâyeye kopyalanamaz; mekanikler yalnız genel çıkarım adayıdır.
- Gerçek hikâye üretimi veya kalite A/B denemesi yapılmadı, ücretli model çağrısı 0, LUMI production / Story Harness değişikliği 0; quality_effect=not_evaluated.
- Geçici SQLite yalnız .nova-cache altında tutulur, Git'e eklenmez.
