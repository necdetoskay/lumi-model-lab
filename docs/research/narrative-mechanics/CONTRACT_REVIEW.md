# Sözleşme incelemesi ve yetki sınırı

Araştırma branch'i `9ae2874cabe582f9e626fc77f36cd208ad234600` tabanındadır.
Bu taban güncel deneysel SpineForge/Q25 belgelerini içermez. Onları branch'e
birleştirmeden, `experiment/q25-narrative-memory-intent` başı
`2eb3d825b5baf8f0f16ccb23805f619d433c7236` üzerinden salt okunur inceledik.
`main` başı `f582f3e8471882df9e012059a44cea7f92afa1c8` de karşılaştırıldı;
deneysel branch belgeleri main/production otoritesi sayılmadı.
Dosya bazlı SHA-256'lar `data/provenance.v1.json` içinde kayıtlıdır.

| İncelenen belge/sözleşme | Alınan sınır | Kütüphanede karşılığı |
|---|---|---|
| STORY_PRODUCTION_QUALIFICATION_ARCHITECTURE_V1 | Kanon/state doğruluğu, kalite ve immutable evidence farklı otoritelerdir | Seçim mühendislik PASS'i anlatı kabulü değildir |
| STORY_PRODUCTION_V5_WHOLE_DRAFT_PROTOTYPE | State sonucu uygulama sahipliğindeki commit'ten ayrıdır | Sadece öneri; commit fonksiyonu yok |
| age7_8_canon_constraints örneği | İzinli/güvenli alan, farklı katkılar, keyfî yeni dünya gerçeği yok | Açık feature/effect izinleri ve yaş kapısı |
| SPINEFORGE_V1 | Yaratıcı çekirdek, yapı, kalite kapısı ve insan onayı ayrı sorumluluktur | Kart bir Spine Product veya writer onayı değildir |
| SPINE_CONTEXT_PACK_V1 | Aynı immutable context ve reveal-safe projeksiyon; eski feedback kullanılamaz | İstek fingerprint'i/audit bağı; gizli Saga cevabı alınmaz |
| episode_spine_v3_contract.py | Nedensel beat bağı, kanıtlı reversal, iki gerçek seçenek, uncommitted outcome | Sekiz eksenli rubrik; şablonlar beat veya outcome üretmez |
| spineforge_v21_bounded_quality.py | Kanon, epistemik sıra, closure, yaş vb. bulgular ayrı ailelerdir | Mekanik seçimi kalite denetimini geçersiz kılamaz |
| Q25_NARRATIVE_INTENT_MEMORY_BANK_V1 | Memory/editorial adaylar state yetkisi değildir; kötü citation hikâyeyi otomatik reddetmez | Byte bütünlüğü ve semantik destek ayrı; human_review=PENDING |
| q25_state_admission.py | UNKNOWN/NONE ayrımı; STATE_MODEL_GAP persistence'ı durdurur | Kalıcı sonuç bilinmiyorsa UNKNOWN; writer'a state mutation şeması verilmez |
| STORY_QUALITY_LEARNING_LOOP_SQRL | Gözlemler aktif writer profilini doğrudan değiştiremez | Kütüphane hiçbir profile veya prompta yazmaz |

Bu eşleme bir adapter değildir. Sözleşmeler import edilmedi, eski branch'e
taşınmadı ve runtime davranışları değiştirilmedi. `nml.*.v1` şemaları ayrı LAB
isim uzayındadır. Seçici genel dünyayı/kanonu anlamsal olarak değerlendiremez;
yalnız açıkça beyan edilen sonlu izin kümelerini denetler. Yeni bir dünya kuralı,
nesne, yer, güç veya karakter yaratma yetkisi üretmez.

## Provenance zinciri

```text
sabit Git commit + Git blob byte'ları
  -> archive manifest (322 dosya, 314 yayın parçası)
  -> source_id + archive fingerprint + byte span SHA
  -> sınırlılıkları açık sekiz eksenli aday
  -> elle önerilmiş kart + ayrı soyut sözlük
  -> kodda sabit release SHA + dosya/schema SHA'ları
  -> doğrulanmış istek + bağlam fingerprint'i
  -> audit (araştırmacı) / sanitized preview (writer için yalnız aday)
```

Release dosyasının hash'i dosyanın byte'larına (son LF dahil), semantik request
ve archive fingerprint'leri canonical JSON'a (son LF hariç) aittir. Canonical JSON:
UTF-8, anahtarlar sıralı, boşluksuz ayırıcılar, Unicode korunur, NaN/Infinity yok.
Saat, yerel mutlak yol, sıralanmamış dosya gezintisi veya Python `hash()` sonucu
kimliğe katılmaz. Manifest çalışma ağacından değil Git blob'larından üretilir;
çalışma ağacı ayrıca bu tam byte'lara eşit olmalıdır. `.gitattributes` LF sağlar.

İçerik adresli dosya oluşturma exclusive'dir. Aynı içerik aynı adla tekrar
kullanılır; başka içerik yeni ad alır. Mevcut dosya sessizce değiştirilmez.
Bu OS düzeyinde WORM depolama değildir: elle değiştirme mümkündür ama doğrulama
bunu yakalar. Değişen arşiv için yeni protokol/release ve kod incelemesi gerekir.
Bir release yayımlandıktan sonra ona bağlı `*.v1.json` dosyaları değiştirilmez;
yeni sürüm yeni artifact yolları ve yeni release pin'i kullanmalıdır.

Arşivdeki kaynak URL'leri var olan özetlerin provenance'ıdır; bu çalışmada ağdan
yeniden okunmadı. Arşiv metninin doğruluğu, yazar hakları veya kullanım lisansı
hakkında yeni bir doğrulama iddiası yoktur. Ham arşiv eğitim setine veya writer
bağlamına dönüştürülmez. Ücretli AI kullanım sayısı bu modül için sıfırdır;
asistanın mevcut sohbet çalışması için ayrıca sağlayıcı faturalama ölçümü yapılmaz.
