# Offline doğrulama — 2026-10-14

**LAB ONLY.** Bu rapor mühendislik testidir; hikâye kalitesi, bölüm doğruluğu,
insan okur beğenisi veya production yeterliliği raporu değildir.

| Kontrol | Sonuç |
|---|---|
| Windows, Python 3.14.7; `python -m unittest tests.test_narrative_mechanics -v` | **54 test PASS**, 0 atlanan; 26.726 saniye |
| `python -m experiments.narrative_mechanics verify` | PASS; 314 bölüm, 18 kart |
| Mevcut `validate_atlantis.py` | PASS; 100/100, 250–287 kelime, 0 issue |
| `compileall` | PASS |
| `git diff --check` | PASS |
| Kaynak dosyaları / mevcut üretim kodu | Değişiklik yok |
| Provider çağrısı / ücretli AI / state commit | 0 / 0 / 0 |

İlk test çalıştırmasında Windows sandbox'ın TEMP dizini izinleri nedeniyle
9 ortam hatası oluştu. İzinli workspace altındaki geçici dizin `TMP`/`TEMP`
olarak ayarlandı; test koşulları gevşetilmeden 54 testin tamamı geçti.

## Kapsam

- Tüm 314 yayın parçasının sabit commit'e bağlı kapsaması; ancillary dosyalar
  dahil manifest tekrar üretimi; değiştirilmiş hash/metadata reddi.
- Ek, eksik, değiştirilmiş veya CRLF'ye çevrilmiş kaynak; symlink ve traversal;
  immutable çakışma ve artifact adı üzerinden dışarı yazma reddi.
- Release'in, bütün data dosyalarının ve şemaların byte bütünlüğü.
- Kaynak kimliği ve fingerprint bağlantısı, tam UTF-8 span sınırı, aralık/hash
  uyuşmazlığı, UNKNOWN ve pozitif skor tutarsızlığı, sahte insan onayı reddi.
- Bir geçerli span'in semantik iddiayı kanıtlamadığına ilişkin açık karşı-test.
- Katı türler, ek alanlar, bilinmeyen enum, duplicate JSON key, NaN/Infinity,
  eksik bağlam fingerprint'i ve tanınmayan recent-ID reddi.
- Yaş sınırları, çağıranın gevşetemediği genç yaş filtresi, risk/canon feature/
  aday-state/reveal kapıları, withheld kart ve geçmiş tekrar dışlaması.
- Çeşitlilik alt/üst kotaları, çözüm yoksa ABSTAIN, greedy seçimin zorlanabileceği
  durumda tam aramanın uygun küme bulması, seed ve sıra bağımsız tekrar.
- Writer allowlist projeksiyonu; istek metni ve audit verisinin sızmaması; tüm
  şablonlarda kaynak özel adı/URL ve sekiz kelimelik arşiv parçası olmaması.
- Gerçek CLI'nin farklı `PYTHONHASHSEED` değerleriyle aynı byte çıktısı,
  audit dosyasının ayrı tutulması, kaynak içermeyen hata çıktısı.
- Ağ bağlantısı engelliyken seçim; provider/production importu veya çağrı noktası
  olmaması; CI'nin model secret'ı, ücretli trigger'ı ve yazma yetkisi taşımaması.

## Tekrar üretilebilir örnek

Sentetik yaş 10 bağlamı `examples/request.v1.json` ile seçilen kartlar:
**NM-004, NM-009, NM-011**. Ayrı `writer-preview.v1.json` ve
`selection-audit.v1.json` dosyaları testte yeniden üretilen sonuçla eşleştirilir.
Bağlam fingerprint'i sentetiktir; gerçek kullanıcı/canon verisi içermez.

## CI

`.github/workflows/narrative-mechanics-offline.yml` sadece bu araştırma branch'inin
ilgili değişikliklerini ve archive tabanına açılan PR'ı doğrular. Self-hosted
runner, Python 3.11, read-only repository token, tam Git geçmişi, sıfır pip/model
bağımlılığı kullanır. Eski ücretli workflow'lar veya tetik dosyaları değiştirilmedi.
CI'nin gerçekleşen sonucu GitHub check'inden okunmalıdır; bu yerel rapor tek başına
CI geçti iddiası taşımaz.

## Açık sınırlılıklar

18 kartın semantic/human review'u bekliyor. 18 kayıttaki kanıt aralıkları geniş
özet bağlamıdır; dar cümle anotasyonu ve bağımsız kaynak kontrolü yapılmadı.
NM-007 bu nedenle seçim dışıdır. 4–6 yaş için kart bulunmaması bilinçli ABSTAIN
sonucudur. Seriler arası denge aynı franchise içinde kalır. Tam kanon semantiği,
uzun dönem anlatı çeşitliliği, gerçek writer etkisi ve Story Harness bağlantısı
bu testlerin dışında ve henüz uygulanmamıştır.
