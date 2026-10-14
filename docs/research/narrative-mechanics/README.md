# Stargate-inspired Narrative Mechanics Library v1

**LAB ONLY · bağımsız araştırma sistemi · 0 provider çağrısı / 0 ücretli AI**

Amaç bir bölümün olaylarını başka adlarla yeniden yazmak değil, anlatının nasıl
çalıştığına dair sınanabilir öneriler üretmektir. Örneğin başarısız bir girişimin
bir varsayımı çürütmesi, yardımla sahipliğin ayrılması veya yerel çözümün daha
büyük soruyu açık bırakması farklı dünyalarda yeni olaylar tasarlamaya yarayabilir.
Bu yarar henüz insan değerlendirmesiyle gösterilmiş değildir.

Bu sürüm gerçek LUMI pipeline, Story Harness, SpineForge, writer, veritabanı veya
production koduna bağlanmaz. Yeni kod yalnız `experiments/narrative_mechanics/`
altındadır; `src/`, mevcut promptlar ve mevcut kanon belgeleri değişmez.

## Teslim ve sınırlar

- 314 bölüm: SG-1 214, Atlantis 100. Arşivin yardımcı belgeleri dahil **322 dosya**.
- Kaynak commit: `9ae2874cabe582f9e626fc77f36cd208ad234600`.
- Her dosya için Git blob kimliği, tam byte sayısı ve SHA-256; her yayın parçası
  için seri + sezon + bölüm kimliği. Çift bölümler birleştirilmez.
- 18 elle hazırlanmış soyut kart ve 18 örnek çıkarım kaydı; bunlar bu çalışma
  sırasında asistanın okuma ve yorumlamasıyla oluşturulmuştur. **İnsan yazarlığı
  veya insan onayı iddia edilmez.** 17 kart seçilebilir, NM-007 beklemededir.
- Sekiz eksen: olay, kural, merak, çatışma, karar, bedel, reveal, kalıcı-state.
- Kapalı şemalar, UTF-8 byte aralıkları, kaynak ve release bütünlüğü, sınırlı tam
  aramalı deterministik seçici, ayrı audit ve writer görünümleri.
- Doğrulananlar mühendislik sınırlarıdır. Gerçek bölüm doğruluğu, anlatı kalitesi,
  pedagojik uygunluk ve bir LUMI kanonuna semantik uyumluluk sertifikalanmaz.

## Kullanım

Repo kökünde Python 3.11+ ve Git yeterlidir; pip kurulumu ve ağ gerekmez.
Checkout, sabit arşiv commit'inin Git nesnelerini içermelidir. Sığ indirmede
bu commit yoksa doğrulama kapanır; otomatik ağ erişimi yapılmaz.

```bash
python -m experiments.narrative_mechanics verify
python -m unittest tests.test_narrative_mechanics -v
python -m experiments.narrative_mechanics freeze-archive --directory runs/tmp/nml-manifests
python -m experiments.narrative_mechanics select --request experiments/narrative_mechanics/examples/request.v1.json --audit-dir runs/tmp/nml-audit
```

`select` stdout'a yalnız `nml.writer-preview.v1` verir. Audit açıkça belirtilen
dizinde içerik adresli ayrı dosyaya yazılır; writer'a audit dosyası verilmez.
Bu komut herhangi bir writer çalıştırmaz. `ABSTAIN` geçerli bir sonuçtur ve sıfır
kart içerir. Geçersiz girdi veya bütünlük bozulması kod 2 ile, kaynak içermeyen
genel hata verir. Eksik kanon alanları varsayılanla tamamlanmaz.

Windows sandbox TEMP dizinine yazmayı engellerse, repo dışında izinli bir geçici
dizin oluşturup o komutta `TMP` ve `TEMP` değişkenlerini o dizine ayarlayın.
Testler kaynak arşivi değiştirmez; değişiklik saldırıları geçici kopyalarda denenir.

## Dosya haritası

| Alan | İçerik | Writer erişimi |
|---|---|---|
| `docs/research/stargate-*` | Eski ham ikincil özetler | Hayır |
| `experiments/narrative_mechanics/releases/` | İçerik adresli archive/release manifestleri | Hayır |
| `data/extractions.v1.json` | Kaynak bağlı editoryal adaylar ve byte kanıtı | Hayır |
| `data/cards.v1.json` | Uygunluk, risk, soy bağı, durum ve provenance | Hayır |
| `data/writer-templates.v1.json` | İncelenebilir, sabit soyut ifade sözlüğü | Yalnız seçilmiş şablonlar |
| `data/provenance.v1.json` | İncelenen sözleşmelerin commit ve hash'leri | Hayır |
| `schemas/` | Kapalı JSON Schema sözleşmeleri | Hayır |
| `examples/` | Sentetik bağlam isteği ve tekrar üretilebilir sonuç | Ayrı writer örneği |

Şemalar Draft 2020-12 uyumludur. Runtime yalnız kullandığımız küçük ve açık
keyword kümesini standart kütüphaneyle doğrular; genel JSON Schema motoru değildir.
Ek alanlar, tür dönüşümleri, yinelenen anahtarlar ve bilinmeyen enum değerleri
reddedilir. Kartlar ve şemalar da release hash'ine bağlıdır.

## Seçim politikası

1. Kodda sabit release SHA'sı, her artifact/schema hash'i ve sabit Git arşivi
   doğrulanır. Çalışma ağacında değişmiş, eksik veya ek arşiv dosyası reddedilir.
2. İstek gerçek yaş (4–120), bağlam fingerprint'i ve açık izin listelerini taşır.
   Örnek bağlam sentetiktir; üretim kanonu değildir.
3. Yaş aralığı, kart durumu, aile, yasak riskler, gereken özellikler, izinli aday
   etkiler, reveal tavanı ve yakın geçmiş tekrarları ayrı sert engellerdir.
4. 10 yaş altında `loss`, `ethical_conflict`, `identity_uncertainty` kartları
   çağıran izin verse bile engellenir. Bu ilk katalog 4–6 yaş için kart sunmaz.
5. Uygun kartların `count` elemanlı kümeleri tam aranır (en çok 20 kart, seçim 1–5).
   Aile ve kaynak-serisi alt sınırları/üst kotaları korunur. En çeşitli kümeler
   tercih edilir; eşitlik SHA-256(seed + sıralı kart kimlikleri) ile çözülür.
6. Çözüm yoksa boş sonuç döner. Risk, kanon veya çeşitlilik kuralı gevşetilmez.
7. Audit request hash'ini ve bağlam fingerprint'ini taşır. Yeni bağlam yeni audit
   üretir. Gelecekteki tüketici eski seçimi yeni state'e taşıyamaz; bu sürümde
   bir onay/yeniden kullanım veya state commit API'si yoktur.

`authorized_features` gerçekleri uydurmak için izin değildir. Bir insanın
sentetik LAB bağlamında beyan ettiği sınırlı özellik kümesidir; runtime tam bir
kanon metnini anlamaz. `allowed_effects` yalnız aday bilgi/ilişki/kaynak/yükümlülük
önerilerine izin verir; kalıcı duruma yazma yetkisi vermez. `reveal_level` 0 açıklama
yok, 1 yerel çıkarım, 2 ileri soru demektir; gizli cevap veya Saga bilgisi taşınmaz.

Kaynak-serisi çeşitliliği sadece SG-1 / Atlantis dağılımıdır. İki seri aynı
franchise'dır; bunun geniş kültürel, türsel veya eserler arası çeşitlilik olduğu
iddia edilmez. İlk sürümde 6 anlatı ailesi ve recent-ID dışlaması vardır;
semantik benzerlik veya uzun dönem novelty ölçümü gelecekte sınanmalıdır.

## Sanitized output güven sınırı

Writer projection, kaynak metni silmeye çalışan bir blacklist değildir.
Yalnız hash ile sabitlenmiş soyut sözlükten seçilmiş kartlar derin kopyayla çıkar.
İstekten serbest metin, kaynak adı, bölüm kimliği, URL, alıntı, span, hash veya
audit gerekçesi projection'a eklenmez. Kaynak metindeki talimatlar çalıştırılmaz.
Değiştirilmiş kart/sözlük/schema release doğrulamasından geçemez.

Testler bütün şablonlarda eser/karakter adları ve link olmadığını, arşivden sekiz
kelimelik parçalar kopyalanmadığını, zararlı seed metninin yansımadığını kontrol eder.
Bu taramalar özgünlüğün hukuki veya semantik kanıtı değildir. Soyut kartların
olay dizisini, ayırt edici dünyayı, teknoloji kurallarını veya karakter rollerini
kopyalamadığı ayrıca insan incelemesi ister.

Tehdit modeli: arşiv/aday/istek verisi güvenilmez, kod ve incelenmiş release pin'i
güvenilir; çağrı sırasında diske eşzamanlı yetkisiz yazma yoktur. Bu bir işletim
sistemi sandbox'ı değildir. Writer'a repo veya audit klasörünü ayrıca açmak bu
sınırı ihlal eder. Gelecek entegrasyonda sadece writer JSON'u ayrı bağlam olarak
aktarılmalıdır; bu sürüm böyle bir entegrasyon içermez.

## Olgunlaşma kapıları

| Aşama | Ölçülebilir çıkış koşulu | Şimdiki durum |
|---|---|---|
| M0 Arşiv bütünlüğü | 314 kimlik, 322 dosya, tekrar üretilebilir hash | Uygulandı |
| M1 Yorum prototipi | 15–20 soyut kart, karşıörnek, açık belirsizlik | 18 öneri, insan incelemesi bekliyor |
| M2 İnsan kaynak incelemesi | İki bağımsız okuyucu; iddia–kanıt uyumu ve görüş ayrılığı kaydı | Yapılmadı |
| M3 Offline kullanım deneyi | Kaynaksız kart / kartsız kontrol ile kör, özgün manuel taslaklar | Yapılmadı |
| M4 Kalite ve güvenlik | İlgi, karar-bedel, nedensellik, yaş, özgünlük; kanon/reveal ihlali yok | Yapılmadı |
| M5 Ayrı entegrasyon kararı | Sürüm dondurma, izin sözleşmesi, ayrı kapsam ve onay | Kapsam dışı |

M2'de her eksen 0–3 rubrikle ayrı puanlanır; kaynak doğruluğu tartışmalıysa kart
WITHHELD kalır. M3'te farklı yaşlar/aileler, başarısız/boş seçimler ve yakın mekanik
tekrarları da örneklenir. İki okuyucu uyuşmazlığında üçüncü görüş veya açık
adjudication kaydı gerekir. Sentetik PASS insan golden label'ı olmaz.
Ücretli generation deneyi veya production önerisi bu belgede yetkilendirilmez.

## Ayrıntılar

- [Çıkarım rubriği](RUBRIC.md)
- [18 kartın okunabilir kataloğu](CARDS.md)
- [Mevcut sözleşmelerle ilişki ve provenance](CONTRACT_REVIEW.md)
- [Doğrulama raporu](VALIDATION.md)
