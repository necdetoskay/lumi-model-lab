# NOVA v0.10 — BioShock 2007: gözlenen doğrulama raporu

**Tarih:** 2026-10-16
**Araştırma branch'i:** research/nova-bioshock-v0.10
**Başlangıç commit:** a6fd590f4186545d152ad9bd37261ac29ff6e45c

## Gerçek araştırma kapsamı

- 2007 orijinal BioShock ana oyunu: 1 eser, 14 kaynak, 23 olay, 16 soyut mekanik hipotezi.
- 48 olay/mekanik kaynak bağlantısı, önceki v0.3–v0.9 mekanikleriyle 34 benzerlik bağlantısı.
- 5 gerçek durum / karakter inancı kaydı, 13 türlendirilmiş olay bağlantısı, birbirini dışlayan 2 epilog varyantı.
- 6 editoryal sınır kaydı: remastered farkı, Little Sister karar eşiği kaynak uyuşmazlığı, opsiyonel kayıt, Atlas aile iddiası, zorunlu Ryan sahnesi, devam oyunları.
- Kanonik kaynak: data/nova/v0.10/source_records/bioshock_2007.json
- SHA-256: 61279e679c65a9825f576864e8e7acc521d422918a6792757b70b6794455e929

## ci-runner üzerinde gerçekten gözlenen sonuçlar

| Komut | Çıktı | Exit |
|---|---|---:|
| python3 tools/nova/build_bioshock.py | 0.10.0-research-first-pass; 1/14/23/16/5/13/2/34/6/48 | 0 |
| python3 tools/nova/validate_bioshock.py | status=PASS; errors=[] | 0 |
| python3 tools/nova/test_bioshock.py -q | Ran 32 tests ... OK | 0 |
| python3 tools/nova/sqlite_bioshock.py | PASS; foreign_key_violations=0; 96 evidence/source links | 0 |
| python3 tools/nova/validate.py | v0.1 PASS | 0 |
| python3 tools/nova/smoke_test.py | 13 synthetic lexical smoke PASS; 0 story trial | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS | 0 |
| python3 tools/nova/test_cross_media.py -q | 25/25 PASS | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | 39/39 PASS | 0 |
| python3 tools/nova/validate_prototype.py | v0.4 PASS | 0 |
| python3 tools/nova/test_prototype.py -q | 22/22 PASS | 0 |
| python3 tools/nova/validate_tomb_raider.py | v0.5 PASS | 0 |
| python3 tools/nova/test_tomb_raider.py -q | 26/26 PASS | 0 |
| python3 tools/nova/validate_tomb_raider_classic.py | v0.6 PASS | 0 |
| python3 tools/nova/test_tomb_raider_classic.py -q | 26/26 PASS | 0 |
| python3 tools/nova/validate_tomb_raider_lau.py | v0.7 PASS | 0 |
| python3 tools/nova/test_tomb_raider_lau.py -q | 30/30 PASS | 0 |
| python3 tools/nova/validate_prototype2.py | v0.8 PASS | 0 |
| python3 tools/nova/test_prototype2.py -q | 30/30 PASS | 0 |
| python3 tools/nova/validate_prototype_comics.py | v0.9 PASS | 0 |
| python3 tools/nova/test_prototype_comics.py -q | 32/32 PASS | 0 |
| python3 -m py_compile tools/nova/{build,validate,sqlite,test}_bioshock.py | completed without error | 0 |

## Ne kanıtlandı, ne kanıtlanmadı?

- Yapısal PASS: eser kimlikleri, kaynak bağlantısı, sahne türü (zorunlu/oyuncu seçimi/opsiyonel/alternatif son), önceki mekanikler ve SQLite yabancı anahtar bütünlüğü.
- Bu analiz tüm özgün oyunu bağımsız baştan sona oynayıp ekran kaydı çıkarmadı; orijinal oyun dosyalarını veya tam transcripti audit etmedi.
- 2007 oyun tasarımcısı görüşmesi oyun dünyasının fizik kurallarına ve ahlaki gerilime ilişkin niyeti açıklar; her sahnenin bağımsız gerçek oyun logu değildir.
- Little Sister kurtarma/hasat sayısına ilişkin birebir bitiş eşiklerinde kaynaklar çelişiyor: exact numeric threshold **null** bırakıldı ve doğrudan oyun sürümü testi olmadan sabit kural yazılamaz.
- Farklı epiloglar aynı anda gerçekleşmiş evrensel tek olay değildir; farklı oyuncu sonuçlarıdır.
- Atlas'ın iddia ettiği aile anlatısı, oyuncunun bildiği iddia ile gerçek karakter geçmişini karıştırmaz.
- İki oyuna tek şema demek yanlış: BioShock 2 / Infinite ve Remastered ekleri bu pakete dahil edilmedi.
- Hikâye üretimi, gerçek story quality A/B testi veya ücretli model API çağrısı yapılmadı. LUMI production, Story Harness veya ana uygulama değişmedi. quality_effect=not_evaluated.
- SQLite dosyası .nova-cache içinde geçici tutulur ve Git'e eklenmez.
