# NOVA v0.2 — Bağımsız 12 senaryolu A/B kohortu (uygulama öncesi)

**Gerçek durum:** 12 senaryo fixture'ı hazır; **0/12 gerçek A/B hikâye çifti** üretildi. Yeni ücretli model çağrısı **0**. Bu dosya sonraki çalıştırma için kabul sözleşmesidir, deney sonucu değildir.

## Kohort dağılımı

| Yaş | Senaryo | Hedef kelime / hikâye | Amaç |
|---|---:|---:|---|
| 4 | NOVA-AB-01…03 | 520 | Güvenli keşif, NPC hafızası, mantıklı ipucu |
| 10 | NOVA-AB-04…06 | 760 | Dallanan sonuç, keşif ve diyalogla kanıt |
| 25 | NOVA-AB-07…09 | 1000 | Gecikmiş sonuç, State/knowledge ayrımı, güven |
| 40 | NOVA-AB-10…12 | 1150 | Zaman kurgusu, delil, karakterin iç çatışması |

Kaynak: [Makinece doğrulanabilir 12 senaryo](../../data/nova/v0.2/EVAL_COHORT_12.json).

## Deney sözleşmesi

A/B çifti için State, karakter bilgisi, gerçek dünya bilgisi, tema, yaş, kelime hedefi, model, model ayarları ve çıktı kalite kuralları **sabit** kalır.

- **A (baz hat):** Bütün kaynak State verilir; NOVA mekanikleri eklenmez.
- **B (NOVA):** Bütün diğer koşullar aynıdır; uygun görülen 1–2 soyut mekanik ID'si, koruma kuralıyla birlikte eklenir. Kaynak eserin karakteri, mekânı, özgün teknolojisi, sahnesi veya repliği kopyalanamaz.
- Her senaryoda bağımsız **A ve B için iki ayrı hikâye** gerekir: toplam 24 ayrı üretim. Aynı story prompt/State hash'i saklanır; yalnız B'ye NOVA etkisi eklenir.
- Değerlendirici A/B etiketini bilmeden fiziki nedensellik, temporal/mekânsal süreklilik, epistemik tutarlılık, karakter failiyeti, yaş uygunluğu, özgünlük, anlatım ritmi ve kapanışı değerlendirir.
- Başarı eşiği, model seti, üretim bütçesi, ücretli anahtar güvenlik kuralları ve çıktı ledger'ı **ilk çalıştırmadan önce dondurulur**. Çalıştırma başladıktan sonra sonuçlar bitene dek modele, koda, prompta, mekaniklere, kalite kuralına veya senaryoya sessizce müdahale edilmez. Yalnız güvenlik veya bütçe ihlalinde fail-closed STOP.
- Her bir deneme için input/output hash, token, maliyet, süre, model id, otomatik hata/ret, denetçi skoru ve gerekçe tutulur.
- Kullanıcı açıkça ücretli çalıştırma yetkisi verene ve bütçe onaylanana kadar **hiçbir ücretli çağrı yapılmaz**. Bu kohort, mevcut ücretli Story Harness B01–B10 çalışmasından bağımsızdır.

## Tekrar komutları

~~~bash
python3 tools/nova/validate_cross_media.py
python3 tools/nova/test_cross_media.py
python3 tools/nova/validate_eval_cohort.py
~~~

**Kabul:** Fixture PASS yalnızca test setinin bütünlüğü ve kaynak bağlantısı korunmuş demektir. NOVA'nın hikâyeyi geliştirdiği sonucuna varılmaz.
