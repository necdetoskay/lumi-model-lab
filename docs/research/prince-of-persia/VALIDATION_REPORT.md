# NOVA v0.3 — Prince of Persia çevrimdışı doğrulama kanıtı

**Tarih:** 2026-10-15
**Repository:** necdetoskay/lumi-model-lab
**Branch:** research/nova-prince-of-persia-v0.3
**Başlangıç HEAD:** 399c00169d61c83b8862ac19dc811a9a7d871dcf

## Kanonik kapsam

19 ayrı analiz eseri; 8 ek yayın/uyarlama (bir iptal edilmiş remake); 29 kaynak; 84 genel olay; 29 Warrior Within zaman olayı; 7 zamansal mekân; 34 zamansal bağlantı; 2 alternatif final; 22 yeni mekanik adayı; 72 mekanik kanıtı; önceki sürümle 27 karşılaştırma bağlantısı.

## Çalıştırılan komutlar ve gerçek sonuçları

Komutlar repository kökünden çalıştırılır.

| Komut | Gözlenen çıktı | Çıkış kodu |
|---|---|---:|
| python3 tools/nova/build_prince_of_persia.py | manifest schema_version=0.3.0, temporal_edges=34 | 0 |
| python3 tools/nova/validate_prince_of_persia.py | status=PASS, errors=[] | 0 |
| python3 tools/nova/test_prince_of_persia.py -q | Ran 39 tests ... OK | 0 |
| python3 tools/nova/sqlite_prince_of_persia.py | status=PASS; foreign_key_violations=0; anchors=113; time_edges=34 | 0 |
| python3 tools/nova/validate.py | status=PASS; episodes=40; mechanics=21 | 0 |
| python3 tools/nova/smoke_test.py | structural PASS, lexical PASS, synthetic cases=13; story quality trials=0 | 0 |
| python3 tools/nova/validate_cross_media.py | status=PASS; works=5; mechanics=35 | 0 |
| python3 tools/nova/test_cross_media.py -q | Ran 25 tests ... OK | 0 |
| python3 tools/nova/validate_eval_cohort.py | status=PASS; only offline existing preflight fixtures; actual A/B story trials=0 | 0 |

## Nedensellik eksikliği ve düzeltme

Water Sword edinimi W24, kanonik karşılaşma W26 ile bağlıydı; Kaileena'nın bugüne taşınması W23 ise W26 olayına açıkça bağlı değildi. W23 → W26 (kaileena_transferred_to_present) bağı ve kanonik final kanıt listesinde W23 eklendi. Bağlantı sayısı 33'ten 34'e çıktı.

Yeni grafik denetiminde ilk/revize geçmiş karşılaşmaları aynı time slot ve epoch üzerinden eşlenir. Geriye dönük bakış bağlantıları ile spekülatif bootstrap kenarı ilerleme ağından ayrılır; ileri ağda çevrim bulunmadığı sınanır. W23 ile W24 önkoşullarının ikisi de W26'ya bağlanır, W26 → W27 → W28 kanonik devamdır. W25 standart bitişinden W28/W29 kanonik devamına geçiş yasaktır.

Olumsuz örnek testlerinde birleşen W23 bağı silinir, nedensel çevrim eklenir, karşılaşmanın slotu bozulur ve standart finalden kanonik devam bağlantısı eklenir. Her biri ayrı denetimde hata oluşturmalıdır.

## Kanıtın sınırları

Manifest üç kanonik JSON dosyasının SHA-256 hashlerini içerir. Derleyici kaynak JSON'dan JSONL ve araştırma Markdown sayfaları üretir. Kaynak URL'leri bu turda yeniden HTTP ile doğrulanmadı; kaynak olaylar ikinci bağımsız editoryal denetimden veya oyun dosyası yakalamasından geçmedi. Spekülatif nedensellik kaydı inference=true ile korunuyor.

Yalnız veri derleme, yapısal doğrulama ve SQLite indisleme yapıldı. Hikâye üretimi, gerçek A/B testleri, ücretli model çağrıları, LUMI production veya Story Harness entegrasyonu yapılmadı. Kalite etkisi not_evaluated. Yerel geçici SQLite .nova-cache altındadır ve commit kapsamına alınmaz.
