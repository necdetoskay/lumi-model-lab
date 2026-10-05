# Fenerdeki Hırsız — onaylı girdi hazırlığı

Durum: OFFLINE_INPUT_PREPARED_NOT_RUNTIME_QUALIFIED. Ücretli çağrı: 0.

Kullanıcının ayrıntılı plan için verdiği “Evet onaylıyorum” yanıtı,
546b88821ea961153840a09312e5e8d68a52ef01 commit'indeki planın SHA-256 değerine
evidence/lighthouse-editorial-preparation/approval.json içinde bağlandı.
Kaynak taslak değiştirilmedi; tarihsel “onay bekliyor” ifadesinin güncel durumu
bu ayrı onay kaydıdır. Plan onayı ücretli çağrı yetkisi değildir.

## Hazırlanan girdiler

- İngilizce Writer: aion-labs/aion-3.5-mini; hedef 1.400–1.800 kelime.
- Onaylı bağlam ve olay zinciri kaynak metinden aynen alınır; model girdisinde
  bir kez bulunur. Onay geçmişi, köprü metni ve eski tamirler gönderilmez.
- Prompt, belirtilmemiş duyusal ayrıntı ve diyalog için yaratıcı alan bırakır;
  yeni güç, ekipman, yol veya farklı son ekleme yetkisi vermez.
- SC01–SC06 işaretleri gerçek Writer çıktısında sınır üretmek içindir.
  bind_scenes ham metnin hash'ini ve Unicode karakter aralıklarını saklar.
  Okur metninden işaretlerin kaldırılması sonraki çıktı adaptörünün işidir.
- Deney türü insan onaylı editoryal plan → Writer/Quality'dir. Otomatik Spine
  üretiminin kalitesi, başarısı veya maliyeti ölçülmüş sayılmaz.

## Ücretsiz doğrulama

`python -m src.lighthouse_editorial_preparation`

`python -m pytest -q tests/test_lighthouse_editorial_preparation.py tests/test_spineforge_v21_*.py`

Yerel sonuç: 81 PASS (73 mevcut v21 + 8 hazırlık testi). Model çağrısı yok.
İstek JSON'u: 9.344 karakter; bu ölçüm token sayısı veya maliyet değildir.
Girdi hash değişimi, eksik/tekrar/yanlış sıradaki sınırlar ve boş sahne durur.
Henüz GitHub CI veya gerçek model başarısı iddiası yoktur.

## Bütçe taslağı — henüz onaya hazır çalıştırma profili değil

5 Ekim 2026 OpenRouter sayfalarındaki milyon token fiyatları:

| Model | Girdi USD | Çıktı USD |
|---|---:|---:|
| Aion 3.5 Mini | 0.70 | 1.40 |
| Claude Sonnet 5.5 | 2.00 | 10.00 |

Kaynaklar: https://openrouter.ai/aion-labs/aion-3.5-mini ve
https://openrouter.ai/anthropic/claude-sonnet-5.5

Writer'ın 7.000 completion token limiti tek başına $0.0098 çıktı maliyeti
hesabına karşılık gelir. Girdi, reasoning'in sağlayıcı kullanım kaydındaki
muhasebesi ve başarısız çağrılar ayrıca kontrol edilmelidir. Bu sınır 7.000
token hikâye garantisi değildir; reasoning de completion bütçesini tüketebilir.

Planlama rezervi önerisi: Writer $0.020 + ilk denetim $0.080 + en fazla bir
tamir $0.070 + son denetim $0.050 = $0.220. Çeviri dahil değildir. Bu bir
harcama yetkisi veya kesin sağlayıcı kilidi değildir. Kesin çalıştırma
teklifinden önce her aşamanın tam girdisi ve çağrı öncesi kontrolü doğrulanmalı.

## Gerçek çalıştırmadan önce kalan bağlantılar

1. Eski v20 Writer doğrulayıcısı 1.600–2.500 kelimeye sabitlenmiş; prompt'u da
   Arda/Nisa/köprüye özgü. Yeni girdiyi eski schema altında WRITER_READY diye
   etiketlemiyoruz. Ayrı editoryal adaptör, mevcut transport'u kullanarak yeni
   girdi ve uzunluk yetkisini doğrulamalı; eski frozen runtime değişmemeli.
2. Gerçek sahne aralıkları v21 sentence span'lerine dönüştürülmeli. Tek sahne
   dışına yayılan blocking bulgular tek tamire zorlanmamalı; STOP olmalı.
3. Sahneye ait giriş/çıkış durumları ve sonraki sahnenin gereksinimleri onaylı
   metinden handoff'a bağlanmalı. Henüz kalite runtime'ına entegre edilmedi.
4. Sahte sağlayıcıyla Writer → temiz denetim ve Writer → tek tamir → son
   denetim uçtan uca doğrulanmalı. Eksik maliyet veya bozuk yanıt durmalı;
   hiçbir başarısızlık otomatik ikinci üretim başlatmamalı.
5. Bu bağlantılar tamamlandıktan sonra tek denemenin kapsamı ve bütçesi açık
   ücretli onaya sunulmalı. Eski köprü deneyinin tüketilmiş yetkisi kullanılamaz.

Bu hazırlık yeni bir üretim hattı veya model karşılaştırması değildir;
mevcut kontrollü akışa yeni onaylı girdinin güvenilir şekilde hazırlanmasıdır.
