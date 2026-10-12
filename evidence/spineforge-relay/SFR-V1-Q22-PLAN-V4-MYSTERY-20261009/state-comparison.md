# Başlangıç ve bitiş state’i

Değişmez başlangıç kaydı korundu. Kabul edilen altı sahne çalışma state’ini revision 0 → 6 ilerletti; next_spine_beat null.

| Alan | Başlangıç | Bitiş |
| --- | --- | --- |
| Nisa duygusu / amacı | worried / find_the_bookmark | relieved / lead_reading_activity |
| Eren duygusu | curious | thoughtful |
| Cem duygusu | calm | relieved_but_still_tender |
| Nisa/Eren’in Cem’e güveni | uncertain | good |
| Ayraç bulundu / sahibine döndü | false / false | true / true |
| Atlasın içindeki ayraç | var | yok |
| Açık sorun / açık yükümlülük | 3 / 3 | 0 / 0 |
| Etkinliğe kalan dakika | 30 | 0 |

Yazılı kanıtlar karakter bilgisine sonradan eklendi; konumlar ve kanon korundu. Ayrıntılar state-comparison.json içinde.

**Okuma bulgusu:** son metinde ayraç hazırlık defterine yerleştiriliyor, fakat `/objects/red_bookmark/state/container` null. Teknik replay PASS, bildirilmiş delta’ların tutarlılığını doğrular; metindeki bütün fiziksel değişikliklerin state’e işlendiğini kanıtlamaz. Sonuç ACCEPT korunuyor; ayrı editoryal inceleme FINDINGS_PRESENT. Metin veya state sonradan tamir edilmedi.
