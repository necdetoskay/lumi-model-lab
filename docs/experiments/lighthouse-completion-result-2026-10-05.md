# Fenerdeki Hırsız — tek üretim sonucu, 5 Ekim 2026

İlk İngilizce çıktı kabul edildi: **2731 kelime**, **$1.4208331** gerçek toplam model maliyeti. Kullanıcının tek üretim için verdiği $3 onayının içinde kaldı. Üst kelime sınırı yok; minimum 1.400 kelime. İlk metni Aion 3.5 Mini, denetim ve sınırlı onarımları Claude Sonnet 5.5 oluşturdu. Hikâyenin cümlelerini Codex elle yeniden yazmadı; Codex plan sapmalarını bulgu olarak ekledi, değişiklik metinlerini model üretti.

[Son hikâye](../../evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-04-20261005/accepted-story.txt), [maliyet ve çağrı dökümü](../../evidence/lighthouse-editorial/completion-summary.json), [bağımsız editoryal kontrol](../../evidence/lighthouse-editorial/independent-review-04.json).

## Son metindeki davranış

Kapı doğrudan kuru üst odaya açılıyor; dönüş aynı kapı ve kıyı patikasından. Anne bel yüksekliğinde, geniş göğsüyle dar dönüşe gerçekten takılıyor. Pusula sabit ızgaradan denize sürükleniyor ve geri gelmiyor. Kordonun bilekte kalması ve cebe aktarılması gösteriliyor. Ekin yavruyu kuru basamakta ceketiyle alıyor; Duru aynı merdivende destek oluyor. Yeni kurtarma ekipmanı, yetişkin kurtarıcı veya telafi armağanı yok. Son görüntü, Ekin'in cebindeki boş kordonu parmaklarıyla çevirirken Duru'ya yetişmesi. Kalan iki küçük editoryal not: önceden kurulmamış çitlerden söz edilmesi ve itirafın biraz fazla açıklayıcı olması. Bunlar olay örgüsünü veya kurtarma mekaniğini değiştirmiyor.

## Gerçek maliyet

| Aşama | Çağrı | Gerçek ücret | Model süresi |
|---|---:|---:|---:|
| 1 | 1 | $0.0075551 | 52.652 s |
| 2 | 1 | $0.0264680 | 4.590 s |
| 3 | 1 | $0.0278240 | 5.737 s |
| 4 | 3 | $0.1152760 | 27.443 s |
| 5 | 6 | $0.2180480 | 44.869 s |
| 6 | 30 | $1.0256620 | 176.088 s |
| Toplam | 42 | $1.4208331 | 311.379 s |

Aşamalar sırasıyla ilk Writer, ilk denetim, ilk patch denemesi, substring desteğiyle devam, kayıtlı denetimden devam ve bağımsız plan bulgularının onarımıdır. Son aşama **15 patch + 15 tam denetim** çağrısı yaptı. Toplam **1 Writer, 20 patch ve 21 denetim** çağrısı var. Başarısız sözleşme/uygulama denemelerinin ücretleri de dahildir; tamamlanmış çağrılar yeniden ücretlendirilmeden kayıtlarından kullanıldı. Süreler sağlayıcı/model çağrı süreleridir; geliştirme, kuyruk ve çalıştırıcı kurulum süresini kapsamaz. Kod yürütme/CI ücretleri bu model maliyeti dökümünde yer almaz. Sonuç, bu geliştirme denemesinin maliyetidir; sonraki üretimin beklenen birim maliyeti değildir.

## Hattın güvenilirliği

**Bir kabul edilebilir hikâye elde edildi; tam otonom ve güvenilir üretim hattı henüz kanıtlanmadı.** Önceki denetim ek kule merdivenini ve değişmiş son görüntüyü kabul etmişti. Codex bağımsız editoryal kontrolde bu iki plan sapmasını saptayıp kapsamı sınırlı model onarımına verdi. Sonraki turda denetleyici, gerekçesinde “hata değil / onarım gerekmiyor” dediği kayıtları moderate + SCENE_REPAIR olarak döndürdü; mevcut karar mekanizması bunları engelleyici sayıp gereksiz turlara girdi. Ham kayıtlar değiştirilmeden saklandı. Sorun bütçe artırılarak çözülmüş sayılmıyor.

Sonraki teknik iyileştirme, denetim sözleşmesinde doğrulama notlarını/advisory notları gerçek engelleyici kusurlardan ayırmak ve şiddet–gerekçe çelişkilerinde hikâyeyi yeniden değiştirmeden önce kararını doğrulamaktır. Sıkı kaynak/plan kontrolü korunmalı. Bu tek örnek başarı oranını veya seri üretim güvenilirliğini ölçmez.

## Doğrulama ve kanıt

84 ilgili test yerelde ve ücretli çalışmanın ön kontrolünde geçti. Son çalışma: [GitHub Actions 37294186194](https://github.com/necdetoskay/lumi-model-lab/actions/runs/37294186194), kaynak commit `fb0af3957475c9f48fa8035a6cde1ee76c08682f`. Her patch için izinli aralık dışında metnin aynen korunduğu kanıtı, ham model yanıtı, kullanım/ücret, adaylar ve son bulgular saklandı. Son metin SHA-256: `ea351d29b7298e13ee53fcb059ac27155968cc1a7031544e48eddc092bfca1ec`. GitHub artifact ZIP SHA-256: `fe98956eda7337f2f3bdcad81fb21bb360f8d91ec68fdbada38fa56f2c48d010`; indirmede doğrulandı. Deney dosyaları dışına üretim/canon yazımı ve çeviri yapılmadı. Kullanıcıdan yeni ara onay alınmadı; aynı tek hikâye ve toplam bütçe onayı kullanıldı.
