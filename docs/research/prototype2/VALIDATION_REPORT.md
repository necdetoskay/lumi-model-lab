# NOVA v0.8 — Prototype 2 (2012): CI test kanıtı

**Tarih:** 2026-10-15
**Repository:** necdetoskay/lumi-model-lab
**Branch:** research/nova-prototype2-v0.8
**Başlangıç commit:** e2e45836acbc2918f791ab2844403eb717510f1b

## Araştırma kayıtları

- 1 oyun; 11 kaynak (Activision resmi basın bülteni, yapımcı röportajı, çağdaş GameSpot inceleme/rehber ve oyuncu kaynakları, ansiklopedi).
- 20 gözlemlenen/derlenen olay; 7 karakter bilgisi ve nesnel dünya olgusu ayrımı.
- 8 önceki Prototype (2009) olayıyla bağlantı; 14 anlatı mekanik adayı, 42 kanıt bağı, önceki araştırma sürümlerine 38 mekanik bağlantısı.
- 6 editoryal sınır; son oyun sahnelerinin 4'ü bilerek tertiary_and_community_nonindependent güven sınıfında.
- Kanonik kaynak: data/nova/v0.8/source_records/prototype2_2012.json
- SHA-256: cafbd9e49421a99e6ad1400042fcfadc22d07aed597b2ab9767988cf53b88adc

## Bağlı ci-runner'da gözlenen komutlar

| Komut | Gözlenen çıktı | Çıkış |
|---|---|---:|
| python3 tools/nova/build_prototype2.py | 0.8.0-research-first-pass; sayımlar 1/11/20/7/8/14/6/42/38 | 0 |
| python3 tools/nova/validate_prototype2.py | status PASS; errors=[] | 0 |
| python3 tools/nova/test_prototype2.py -q | Ran 30 tests ... OK | 0 |
| python3 tools/nova/sqlite_prototype2.py | status PASS; foreign_key_violations=0; evidence_sources=84 | 0 |

## Bulguların kanıt düzeyi

- PASS, yapısal tutarlılık, kaynak kimliği, ilk/ikinci oyun bağlantısı, Maya’nın gerçek durumu ile Heller’ın inancı, aktör kimliği, veri kalite sınırları ve SQL foreign key denetimidir.
- Oyun finali ve koalisyon dönüşümleri çoğunlukla GameFAQs oyuncu rehberleri + Wikipedia özetine dayanır; özgün oyun dosyasından sahne sahne bağımsız ikinci editoryal denetim yapılmadı.
- Yapımcının Alex'i karşıt kahraman yapma kararına ilişkin röportajı, oyun evrenindeki tüm biyolojik/psikolojik nedenleri açıklayan kesin kanıt değildir.
- İki oyun arasında yayımlanan üç çizgi roman ayrı bir anlatı ortamıdır ve bu pakete olay olarak dahil edilmedi; sonraki v0.9 araştırmasında ayrıca değerlendirilmesi önerilir.
- DLC, basım/port sürümü, çizgi roman ve oyun içi olaylar aynı eser kanonunda çift sayılmadı.
- Bu çalışma gerçek hikâye üretimi, gerçek hikâye kalitesi A/B testi veya ücretli model API çağrısı içermiyor. LUMI production / Story Harness entegrasyonu yapılmadı; quality_effect=not_evaluated.
- Geçici SQLite dosyası .nova-cache altındadır, Git'e eklenmez.
