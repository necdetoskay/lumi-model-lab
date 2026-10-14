# NOVA v0.1 — Stargate Universe Veri Kabul Raporu

2026-10-14 · research/nova-sgu-v0.1

| Kabul kontrolü | Sonuç |
|---|---:|
| Dizi sezonları | 2 |
| Bölüm kaynakları | 40/40 · HTTP 200 alındı |
| Bölüm bazlı NOVA analizi | 40/40 |
| Soyut mekanik sınıfı | 21 |
| Birden fazla bölümle desteklenen mekanik | 18 |
| Yalnız tek bölüm kanıtı olan mekanik | 3 |
| Episode→mechanic kanıtı | 80/80 |
| JSONL yapısal/kaynak/foreign key kanıtı | PASS |
| SQLite works/episodes/analyses/mechanics/evidence kayıtları | 1/40/40/21/80 · PASS |
| Sentetik açıklanabilir eşleştirme kontrolleri | 13/13 PASS |
| Bağımsız hikâye kalitesi deneyleri | **0/12** |
| LUMI usage_history kaydı | 0 |
| Ücretli model çağrısı | 0 / $0 |
| Main ve production değişimi | Yok |

## Kesin kabul

Yapısal ve kaynak eşleştirme testi PASS. Her bölüm bir kaynağa ve iki somut mekanizma yorumuna bağlanıyor, kanon izolasyonu korunuyor.

## Kapsam dışı

Bu test, her olayın ikinci bağımsız araştırmacı tarafından satır satır doğrulandığını, mekaniklerin yeni hikâyeye uyumunu veya kaliteyi iyileştirdiğini **kanıtlamıyor**. Kaynak HTTP 200 durumu araştırma anına aittir. Kaynaklardan uzun pasajlar depolanmamıştır.

## Tekrar çalıştırma

~~~bash
python3 tools/nova/validate.py
python3 tools/nova/smoke_test.py
python3 tools/nova/build_sqlite.py
~~~
