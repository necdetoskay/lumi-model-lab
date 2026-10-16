# NOVA v0.13 — BioShock Burial at Sea: doğrulama raporu

**Tarih:** 2026-10-16
**Branch:** research/nova-burial-at-sea-v0.13
**Başlangıç commit:** b27691b3d790be4d51354dd640f61cc781027742

## Gerçek araştırma kapsamı

- İki ayrı DLC: Episode One (12 Kasım 2013) ve Episode Two (25 Mart 2014).
- 14 kaynak; 28 olay (13 + 15); 10 öznel bilgi-dünya durumu kaydı.
- 16 yeni mekanik hipotezi, 43 kaynaklı olay bağı, önceki mekaniklerle 32 kavramsal bağ.
- 15 anlatı olay bağlantısı, önceki BioShock 2007/Infinite 2013 olaylarıyla 8 karşılaştırma ve 16 editoryal sınır.
- Kanonik kaynak: data/nova/v0.13/source_records/burial_at_sea.json
- Kaynak SHA-256: 2178285e4f4c13239760c50d183d1474b12877cc9ec8dd48509225a2dc403677

## CI runner üzerinde gözlenen testler

| Komut | Gerçek sonuç | Exit |
|---|---|---:|
| build_burial_at_sea.py | 0.13.0-source-first-pass; deterministik JSONL ve manifest | 0 |
| validate_burial_at_sea.py | PASS, errors=[] | 0 |
| test_burial_at_sea.py -q | Ran 40 tests ... OK | 0 |
| sqlite_burial_at_sea.py | PASS, foreign_key_violations=0, evidence_sources=79 | 0 |
| v0.1 validate.py ve smoke_test.py | PASS, 13 sentetik lexical smoke | 0 |
| v0.2 cross-media validate + test | PASS, 25/25 | 0 |
| v0.3 Prince of Persia validate + test | PASS, 39/39 | 0 |
| v0.4 Prototype validate + test | PASS, 22/22 | 0 |
| v0.5 Tomb Raider Survivor validate + test | PASS, 26/26 | 0 |
| v0.6 Tomb Raider Classic validate + test | PASS, 26/26 | 0 |
| v0.7 Tomb Raider LAU validate + test | PASS, 30/30 | 0 |
| v0.8 Prototype 2 validate + test | PASS, 30/30 | 0 |
| v0.9 Prototype comics validate + test | PASS, 32/32 | 0 |
| v0.10 BioShock validate + test | PASS, 32/32 | 0 |
| v0.11 BioShock 2 validate + test | PASS, 40/40 | 0 |
| v0.12 BioShock Infinite validate + test | PASS, 40/40 | 0 |
| python3 -m py_compile four v0.13 Python tools | PASS | 0 |

## Kanıt ve kalite sınırlamaları

- PASS yalnız kaynak referansları, sözleşme, önceki sürümler ve SQL bütünlüğünü doğrular; oyun sahneleri bağımsız baştan sona oynanmadı.
- 2K/Steam resmî kaynakları sürüm tarihleri, oynanabilir karakter ve gizlilik oynanışını doğrular; son oyun sahneleri ağırlıkla GameFAQs rehberleri ve topluluk özetlerine dayanır.
- Episode One'daki Rapture Comstock sürümü 2013 ana oyununun Booker bedeniyle aynı değildir. Anna'nın farklı iki tarih sonucu birleştirilmez.
- Episode Two Elizabeth'in ölümlü dönme hali ve zihinsel Booker görüntüsü birinci bölümdeki fiziksel durumla otomatik eşitlenmez.
- Suchong'tan Atlas'a bilgiyi teslim etmek BioShock 2007'deki Jack'in sonraki eylemini aynı anda gerçekleşmiş hale getirmez.
- İleride Jack'in hangi kurtarma dalını seçtiği Elizabeth'in finaldeki umudundan kesin tek kanon olarak türetilmez.
- Bölüm sonundaki toplum özeti community_only etiketli düşük güven verisi olarak tutulur. Birincil özgün tam oynanış doğrulaması yapılmadı.
- No paid calls, no story quality A/B, no story generation, no LUMI production or Story Harness change. quality_effect=not_evaluated.
- SQLite dosyası .nova-cache altında geçicidir; git commit dışındadır.
