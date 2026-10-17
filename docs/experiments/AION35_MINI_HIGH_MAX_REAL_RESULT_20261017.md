# Aion 3.5 Mini — Deniz: gerçek HIGH / MAX akıl yürütme karşılaştırması

**17 Ekim 2026 | Gerçek ücretli deney | GitHub [run #39006601046](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39006601046) — SUCCESS | Provider makbuz artefaktı ID `12090764790`**

## Araştırma sorusu

**Daha fazla düşünme (`max`) Aion 3.5 Mini'de, aynı sekiz olaylı ve 4 yaşa yönelik Deniz/balkon hikâyesini `high` ayarına göre anlamlı biçimde iyileştiriyor mu?**

İki çağrıda aynı model (`aion-labs/aion-3.5-mini`), aynı 8 maddelik dondurulmuş Spine, aynı sistem/user prompt, aynı `temperature=0.72`, aynı English story hedefi kullanıldı. **Tek fark `reasoning.effort`: HIGH / MAX.** `reasoning.exclude=true`. **Hiçbir model output-token veya reasoning-token tavanı gönderilmedi.** Hiçbir editör veya ikinci ücretli semantic judge çağrısı yapılmadı.

### Gerçek model yanıtı sonuçları

| Ölçüm | HIGH | MAX | MAX - HIGH |
|---|---:|---:|---:|
| Girdi tokenı | 661 | 661 | 0 |
| Üretilen orijinal kelime | 503 | 514 | +11 |
| Toplam çıktı tokenı (düşünme dahil) | 9.405 | 12.378 | +2.973 |
| **Reasoning tokenı** | **8.288** | **9.787** | **+1.499** |
| Gerçek gecikme (saniye) | 128,539 | 225,453 | +96,914 |
| Sağlayıcıda gözlemlenen USD ücret | 0,0136297 | 0,0177919 | +0,0041622 |
| `finish_reason` | `stop` | `stop` | İkisi de tam |
| Gerçek model | `aion-labs/aion-3.5-mini` | `aion-labs/aion-3.5-mini` | İkisi de doğru |
| Hikâyeye manuel tamir | 0 | 0 | 0 |

**Toplam gözlemlenen sağlayıcı maliyeti: 0,0314216 USD.** MAX, HIGH'a göre yaklaşık **%30,5 daha pahalı ve %75,4 daha yavaş**. MAX'ın düşünme tokenı yaklaşık **%18,1 fazla**, hikâyesi ise yalnızca **11 kelime uzun**. Bunlar tek örnekten ölçülen rakamlardır, model genel performansı değildir.

- HIGH provider generation ID: `gen-1792215125-tzTW0s5B9xDqgaSkl02k`, orijinal SHA-256: `ed9bdc2db3a888ecbc0cae350e29c65cfb6360077b4ea843a8ad113c3bfa91c4`.
- MAX provider generation ID: `gen-1792215254-2BslNN6pJ3e0M64zvfqt`, orijinal SHA-256: `9395072d78616ff689ba4304c9951d680cc8425283fbe51582c502293ca5cefe`.
- Gerçek bağlı story, summary, usage, input SHA'ları ve provider envelopes: `aion35-mini-deniz-highmax-one-use-39006601046` artifact (ID `12090764790`); `comparison.json` `PAIRED_RECEIPTS_VERIFIED_QUALITY_UNDETERMINED`.

### Metinsel değerlendirme — bağlayıcı semantik kabul değildir

- **İkisi de Spine'ın ana sekiz olay sırasını koruyor**: sessiz tekil tik, saksı/taş/railing arayışı, rüzgârın sesi belirginleştirmesi, halkaların teması, rüzgâr yokken susma, Deniz'in eliyle hava üretmesi, iki-tik-duraklama ve rüzgâr cevabı. Deniz halkaları elle çekmiyor.
- **HIGH**, daha somut ve sakin çocuk dili kullanıyor: “one small, short tick”, yerdeki taşlar, rüzgârın saçını uçurması ve oyun ritmi. Son cümlede ritim bir kez daha tekrarlanarak kapanış kısmen yeniden açılıyor.
- **MAX**, benzetmeyi ve tekrarları artırıyor: “ears, wide as doors”, “quiet as a nap”, “a pause as big as the sky”, “Maybe the wind was thinking”. Bu örnekte dramatik anlamda yeni nedensel başarı veya daha net olay örgüsü sağlamıyor; bazı imgeler 4 yaş için gereksiz soyut hissedilebilir.
- **İkisinde de denetlenecek semantik ayrıntı**: finalde anlatılan tek temas ile iki ardışık tik arasındaki temas sayısı açık değil; rüzgâr halkaları art arda çarptırmış olabilir, ancak metin bunu kanıtlamıyor. Tekrar üretilecek bir fiziksel gerçek olarak kabul edilmemeli.
- İki hikâye de ham anlatımda görünen uzun çizgi karakterini `â\x80\x94` olarak taşıyor. **Bu modelin hikâye başarısızlığından önce, OpenRouter SSE akışımızdaki karakter kodlaması kusuru**: `decode_unicode=True` response charset varsayımı UTF-8 JSON'u Latin-1 gibi çözmüş olabilir. Eski gerçek paid receipts **değiştirilmedi**. Sonraki denemeler için ham SSE bytes üzerinde açık `utf-8` decode düzeltmesi ve yeni Unicode testi ayrı commit'te yapıldı. Bu düzeltme **yeni ücretli çağrı yapmadı**.

### Ara karar

**Yalnızca bu tek eşlenik denemede:** HIGH belirgin biçimde daha ucuz ve hızlı; MAX'ın ek düşünmesinin hikâyeyi açık şekilde daha iyi yaptığı görülmüyor. 4 yaş için sade anlatım hedefinde **HIGH şimdilik maliyet/latency açısından tercih edilebilir**. Bu **üretim model/effort terfisi değildir** ve Aion'un yaratıcı kapasitesine dair kesin hüküm değil. En az birkaç bağımsız genre/age/spine örneğinde kör insan/editör veya model bağımsız hakem değerlendirilmeli; fiziksel nedensellik SERA'nın ayrı gates'inden geçmeli. Kullanıcının **insan tarafından hikâye tamiri yok** kuralı bu değerlendirmelerde de devam edecek.

## Kontrol izi

- İlk ücretli job `#39006502083`: runner ismi uyuşmadığı için **provider POST öncesinde** hata, 0 billed.
- Düzeltme: `RUNNER_NAME=q25-offline-isolated`, `git fetch-depth=2`, grant-only kullanıcı onaylı tek-use commit `0e6dfc769414295beeefb61c0d1b8c006123e123`.
- Gerçek ücretli job [`#39006601046`](https://github.com/necdetoskay/lumi-model-lab/actions/runs/39006601046): **SUCCESS**, tam iki provider response, iki benzersiz generation ID, tek-use claim, 0 manuel metin tamiri, 0 G2/SQLite/production world write, 0 ekstra ücretli judge çağrısı.
- Offline test suite önce 16/16 PASS; SSE Unicode düzeltmesi sonrası ek test ile suite 17/17 olmalı ve CI sonucu ayrıca kaydedilmeli.
- `main` değiştirilmedi. Ücretli grant **kullanılmıştır; otomatik tekrar/ek ücretli Aion testi yapma yetkisi yoktur.**
