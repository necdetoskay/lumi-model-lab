# Fenerdeki Hırsız — onay ve üretim hazırlığı

## Güncel durum

İnsan plan onayı alındı. Kaynak: `546b88821ea961153840a09312e5e8d68a52ef01`
commit'indeki `lighthouse-context-and-spine-draft.md`. Kaynak dosya tarihsel taslak
olarak değiştirilmedi; güncel onay `evidence/lighthouse-editorial/plan-approval.json`
dosyasında kaynak SHA-256'sına bağlı. Onay mesajı: “Evet onaylıyorum”.

Deney türü: insanın onayladığı editoryal plan üzerinden Writer/Quality deneyi.
SPINE_ARCHITECT başarısı veya tam otomatik uçtan uca üretim başarısı ölçülmüyor.
Ücretli yetki yok; önceki köprü deneyi yetkisi kullanılamaz.

## Hazırlanan girdi

`python -m src.lighthouse_editorial_handoff` kaynak hash'ini ve onay kapsamını
kontrol eder; bağlamı, mekânı, SC01–SC06 olaylarını ve korunacak sonuçları kaynak
metinden doğrudan aktarır. Son sahnenin kapanış paragrafı bitiş durumu olarak
korunur. Yeni olay eklenmez. Çıktı:
`evidence/lighthouse-editorial/writer-input.json`.

Bu, mevcut v20 Writer contract'ı olduğunu iddia eden bir dosya değildir.
Durumu `PREPARED_NOT_RUNTIME_QUALIFIED`; mevcut çalıştırıcıya doğrudan verilemez.
Kaynak belgedeki eski “onay bekleniyor” idari satırları model girdisine taşınmaz.

Yerel doğrulama: `python -m pytest -q tests/test_lighthouse_editorial_handoff.py`
→ 5 PASS. Kontroller değişen kaynak, ret kararı, yanlış kapsam ve ücretli yetkiye
dönüştürme girişimini kapsar. Model çağrısı yapılmadı; hikâye kalitesi ölçülmedi.

## Üretim öncesi kalan işler

1. Mevcut Aion Writer adapter'ına bu editoryal girdiyi bağla; eski Arda–Nisa,
   köprü onayı veya önceki hikâye verisini taşımadığını ücretsiz doğrula.
2. Writer çıktısındaki gerçek sahne sınırlarını kaydet. SC01–SC06 plan kimlikleri
   metin konumu değildir. v21'deki eski S159–S177 seçimi yeniden kullanılamaz.
3. Sonnet denetim ve en fazla bir sahne tamiri için yeni kaynağa bağlı kapsamı
   doğrula. Birden çok sahne gerektiren hatada otomatik ikinci tamir başlatma.
4. Kesin model kimliklerini, güncel fiyatları, girdi/çıktı limitlerini ve toplam
   deney bütçesini birlikte doğrula; ardından ayrı ücretli onay iste.

Beklenen azami model çağrısı: 1 Writer + 1 ilk denetim + gerekirse 1 tamir ve
1 hedefli son denetim = 4. Temiz taslakta 2. Çeviri bu hesabın dışında ve ayrıca
kapsamlandırılmalı. Önceki $0.20 köprü bütçesi bu yeni üretime aktarılmadı.
Bu kayıt fiyat teklifi, paid preflight PASS veya üretim yetkisi değildir.
