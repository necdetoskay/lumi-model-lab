# NOVA v0.4 — Prototype 2009: Gerçek doğrulama kanıtı

**Tarih:** 2026-10-15

**Kapsam:** 2009 Prototype için ilk kaynaklı araştırma geçişi. Hikâye üretimi veya editoryal uzman denetimi değildir.

## Kaydedilen veri

- 1 eser, 9 kaynak, 16 kaynakla bağlantılı gözlem kaydı
- 12 soyut anlatı mekaniği, 30 kanıt bağlantısı, PoP v0.3 ile 20 kavramsal bağlantı
- Dört olay kaydı bilinçli biçimde düşük güven seviyesinde işaretli: PRT-E12, PRT-E13, PRT-E14, PRT-E16
- Manifest üçlü değil, tek Prototype kanonik JSON dosyasının SHA-256'sını tutar.

## Bağlı ci-runner üzerinde gözlenen komutlar

| Komut | Gözlenen sonuç | Exit |
|---|---|---:|
| python3 tools/nova/build_prototype.py | manifest, 1/9/16/12/30/20 kayıt | 0 |
| python3 tools/nova/validate_prototype.py | status=PASS, errors=[] | 0 |
| python3 tools/nova/test_prototype.py -q | Ran 22 tests ... OK | 0 |
| python3 tools/nova/validate.py | v0.1 PASS, 40 bölüm/21 mekanik | 0 |
| python3 tools/nova/smoke_test.py | 13 sentetik lexical case, PASS; story trial=0 | 0 |
| python3 tools/nova/validate_cross_media.py | v0.2 PASS, 35 mekanik | 0 |
| python3 tools/nova/test_cross_media.py -q | Ran 25 tests ... OK | 0 |
| python3 tools/nova/validate_prince_of_persia.py | v0.3 PASS, 34 zamansal bağ | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | Ran 39 tests ... OK | 0 |

Testler kaynak ve verinin yapısal tutarlılığını inceler, oyun öyküsünün bütün ayrıntılarının doğru olduğuna veya yeni hikâyelerin kalitesini artıracağına ilişkin bağımsız bir ispat değildir. Yeni ücretli API çağrısı, gerçek A/B denemesi, LUMI production veya Story Harness işlemi yapılmadı.

Kaynak URL'lerinin varlığı kaynak metni veya oynanışın eksiksiz ikinci editoryal kontrolünün yapıldığı anlamına gelmez. Topluluk ve üçüncül kaynaklar düşük güven olarak işaretlendi. Bu rapor üretim ortamında canlı işlem raporu değildir.
