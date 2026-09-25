# LUMI V5 Hikâye Okuma Paketi — 25 Eylül 2026

Bu paket iki ayrı kanıt grubunu içerir.

## A. Önceden doğrulanmış gerçek V5 baseline

Bunlar geçmiş production-like V5 qualification koşusu 36027213240 içindeki orijinal result.story.txt çıktılarıdır. Yeniden üretilmemiştir.

| Hikâye | Yaş | Kelime | Hedef | Judge | Min | JEV | commit_ready |
|---|---:|---:|---:|---:|---:|---|---|
| Ece — friendship/social | 7 | 972 | 900 | 4.875 | 4 | PASS | true |
| Arda — puzzle/problem solving | 13 | 2051 | 2300 | 4.875 | 4 | PASS | true |
| Ada — world-lore | adult | 3816 | 3600 | 4.875 | 4 | PASS | true |

Dosyalar old-baseline/ klasöründedir. Orijinal İngilizce metin ve qualification JSON birlikte tutulur.

## B. Yeni istenen V5 production-ready cohort

İstenen yaşlar: 4, 10, 25, 40, 40.

Her hikâye şu zincirden geçti:

English V5 generation -> deterministic gates -> whole-story JEV -> Haiku semantic judge -> typed StoryOutcome -> commit_ready -> Turkish finalization -> bilingual fidelity gate

| Case | Yaş | Tür | Kelime | Hedef | Judge | Min | JEV | commit_ready | TR fidelity |
|---|---:|---|---:|---:|---:|---:|---|---|---|
| age-04-nature | 4 | nature/environment | 544 | 500 | 4.875 | 4 | PASS | true | 5.0 / min 5 |
| age-10-mystery | 10 | exploration/mystery | 3101 | 2800 | 4.875 | 4 | PASS | true | 5.0 / min 5 |
| age-25-science | 25 | scientific curiosity | 3962 | 4200 | 4.875 | 4 | PASS (no_contradictions=0.90) | true | 5.0 / min 5 |
| age-40-world-lore | 40 | world-lore discovery | 4382 | 4200 | 4.875 | 4 | PASS | true | 5.0 / min 5 |
| age-40-emotional | 40 | emotional development | 4319 | 4200 | 4.875 | 4 | PASS | true | 5.0 / min 5 |

Yeni hikâyelerin her biri new-cohort/ klasöründe:
- _EN.txt — accepted İngilizce kaynak hikâye
- _TR.txt — Türkçe final hikâye
- _qualification.json — judge/JEV/commit-ready/translation evidence özeti

25 yaş science ilk koşuda JEV no_contradictions=0.79 nedeniyle reddedildi. Nicel gözlem -> nedensel sonuç dilini sıkılaştıran genel constraint eklendi ve yalnız bu case targeted rerun edildi. Final koşu 36140101053 içinde JEV no_contradictions=0.90, commit_ready=true, Türkçe fidelity 5.0 oldu.

## Önemli not

Buradaki commit_ready=true, V5 qualification protokolünün validated StoryOutcome sonucudur. V5 prototipi gerçek LUMI veritabanına yazmaz (database_written=false); gerçek atomik/idempotent commit uygulama katmanının sorumluluğudur.

## Evidence kaynakları

- Eski baseline: run 36027213240, evidence branch evidence/story-v5-production-cohort-36027213240
- Yeni 4 başarılı case: run 36137318722, evidence branch evidence/story-v5-whole-draft-36137318722
- 25 yaş targeted final: run 36140101053, evidence branch evidence/story-v5-whole-draft-36140101053
