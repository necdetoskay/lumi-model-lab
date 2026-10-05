# Lighthouse: kaynak denetimi ve karar adımı — 5 Ekim 2026

**Son durum:** Denetim kapsamı genişletildi, fakat otomatik anlamsal kabul henüz doğrulanmadı. Kanıt ile karar etiketini ayıran yeni deneme hazır ve çalıştırıcı bekliyor. Hikâye bu tur yeniden yazdırılmadı; henüz içerik düzeltmesi yapılmadı.

Bu çalışma yalnızca onaylı “Fenerdeki Hırsız” planı ve onun kayıtlı Aion çıktısı üzerinde yürütülüyor. Planın özgün Türkçe ifadeleri korunuyor; minimum 1400 kelime, üst sınır yok. Üretim LUMI verisine yazılmıyor.

## Bulunan temel sorun

Model bir hatayı gerekçesinde doğru tarif ettiği halde sonuç alanına `SATISFIED` yazabiliyor. Kayıtlı örnek: Duru’nun “yarım kat yukarıda, bir basamak yukarıda değil” olduğunu belirtiyor, fakat ilgili plan maddesini uygun işaretliyor. Final ihlalini bildirirken düzeltme cümlesi listesini boş bırakması da ayrı bir karar biçimi hatası.

Bu yüzden yalnızca daha uzun bir istem veya daha çok kontrol eklemek yeterli görünmedi. Yeni adım, önceki denetimin etiketlerini kaldırıp kaynak alıntıları ve gerekçelerini aday kanıt olarak kullanıyor. Son kararı mevcut hikâye ve onaylı plana karşı yeniden veriyor. Gerçek kusurlar dolu ve doğrulanabilir bir düzeltme kapsamı taşımak zorunda; yorum gerektiren üslup tavsiyesi tek başına düzeltme başlatmıyor.

## Bu turdaki model denemeleri

| Deneme | Yeni çağrı | Maliyet | Gözlenen sonuç |
|---|---:|---:|---|
| Tam kaynak, 16 kontrol | 2 | $0,130758 | Temiz kontrol kabul; hatalı metinde kordon yakalandı, Duru ve final kaçırıldı. Düzeltme başlamadı. |
| Kaynağı noktalama ile 74 parçaya ayırma | 1 | $0,169832 | Temiz metin olumlu; tek bir alıntı komşu cümleye bağlandığı için doğrulama durdu. |
| Kayıtlı temiz denetimi otomatik referans düzeltmesiyle yeniden kullanma | 1 | $0,174174 | Temiz kontrol sıfır yeni çağrıyla geçti. Hatalı metinde final için kapsam boş; Duru gerekçesi ile uygun etiketi çelişkili; bir üslup maddesi belirsiz. |
| Ayrı karar adımı | 0, henüz | Henüz ücret yok | Kaynak bağlama, boş kapsam, belirsiz karar, bütçe ve sınırlı düzeltme kontrolleri hazır; canlı çalışma kuyrukta. |

Alıntı düzeltmesi yalnızca aynı paragrafta, komşu cümlede, tek ve birebir kaynak eşleşmesi bulunan olumlu kontrol için yapılıyor. Kararı veya düzeltme kapsamını değiştirmiyor. Hatalı / belirsiz bulgular otomatik taşınmıyor.

74 parçalı sözleşme kaynaktaki karakterleri ve noktalama aralıklarını koruyor. Genel derleyici belirli karakter isimlerine, altı sahneye veya bu hikâyenin finaline bağlı değil. Üç bilinen kusuru arayan başarı ölçütü bu tek hikâyenin ayrı test değerlendiricisinde; modele beklenen kontrol sonuçları gönderilmiyor.

## Hazırdaki akış

1. Yeni çalıştırıcı önce tam olarak önceki kuyruk işini iptal eder ve model adımının başlamadığını doğrular. Önceki iş başlamışsa yeni model çağrısını reddeder.
2. Aynı istem ve karar şemasıyla kayıtlı temiz metni ve hatalı metni sınar.
3. Temiz kontrol yanlış kusur üretmez ve hatalı kontrol kordon, Duru konumu ve gerçek finali ayrı ayrı yakalarsa düzeltmeye geçer.
4. En fazla iki düzeltme turu, toplam en fazla altı çağrı. Her düzeltme yalnızca denetimin izin verdiği kaynak cümlelerde uygulanır; dışarıdaki metnin aynen korunduğu kanıtlanır.
5. Her aday bütün hikâye ve onaylı kaynaklar üzerinden yeniden denetlenir. Belirsiz maddi sorun, kapsam dışı değişiklik, bütçe veya biçim sorunu kabul oluşturmaz.

Yeni karar girdisinde tekrar edilen ana plan alıntıları çıkarıldı; ana bağlam aynı onaylı planın kaynak alanlarında duruyor. Bu sadeleştirme kanıtı veya plan maddesini kaldırmıyor.

## Bekleyen çalıştırma ve dış engel

- Ayrı çalıştırıcı: https://github.com/necdetoskay/lumi-model-lab/actions/runs/37371216752
- Önceki kuyruk işi: https://github.com/necdetoskay/lumi-model-lab/actions/runs/37370235996
- Yayımlanan kod ve dondurulmuş yetki: `a45a500ce1d4710f898493963a27c498529dacc3`.

GitHub’ın resmi durum kaydı Actions için `degraded_performance` bildiriyor. 5 Ekim 19:50 UTC güncellemesi GitHub-hosted çalıştırıcı atamalarındaki gecikmenin sürdüğünü belirtiyor: https://www.githubstatus.com/api/v2/summary.json . Ortak yerel havuz da başka kuyruk işleriyle dolu. Bu kayıtta iki deneme henüz başlamadı; yeni karar adımının sonucu bekleniyor. İptal kontrolü çalışmadan önceki işin iptal edildiği iddia edilmiyor.

## Bütçe ve doğrulama

Bu turdaki dört bilinen model çağrısı **$0,474764**. Bu tek hikâye için bilinen model toplamı **$2,42645486**; geçmişte cevabı kaybolan bir deneme için **$0,04** ayrıldı. Ayrı çalıştırıcı için ek **$0,10** ihtiyat payıyla bütçe hesabı **$2,56645486**. Onaylı toplam sınır **$3**. Bu değerlerin tümü gerçekleşmiş fatura toplamı değil; bilinmeyen eski çağrı ve çalıştırıcı faturası tam uzlaştırılmış değil.

Standart Linux GitHub çalıştırıcısı için resmi belgede $0,006/dakika yazıyor; 15 dakika iş sınırı ve yuvarlama için $0,10 ayrıldı. Hesabın ücretsiz dakika kotası bilinmediğinden gerçek çalışma ücretinin sıfır olduğu varsayılmıyor: https://docs.github.com/en/billing/concepts/product-billing/github-actions . Yeni çağrıdan önce model maliyeti, bilinmeyen çağrı payı, çalıştırıcı payı ve sıradaki çağrı rezervi birlikte kontrol ediliyor.

Yerelde 264 geniş kapsamlı test (30,77 saniye) ve sonradan eklenen altı ayrı çalıştırıcı / iptal testi geçti. Tam kaynak 16 kontrol CI: 238 test; 74 kontrol CI: 244 test; referansla devam CI: 249 test geçti. Bu testler kodun ve kanıt bağlamanın doğrulaması; model kalitesinin başarılı olduğunun kanıtı değiller.

Bir sonraki iş yeni Writer çalıştırmak değil, mevcut çalıştırmanın kayıtlarını almak; iki kontrolün sonucu, düzeltme dışındaki metin koruma kanıtları ve varsa kabul edilen adayın içeriğini incelemek. Mevcut $3 onayı içinde yeniden izin istemek gerekmiyor.
