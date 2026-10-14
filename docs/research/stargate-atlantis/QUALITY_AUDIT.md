# Stargate Atlantis — Arşiv Doğrulama Kaydı

**Tarih:** 14 Ekim 2026  
**Branch:** `research/stargate-atlantis-episode-archive`  
**Yazılı arşiv snapshot'u:** `528945737d0822f6e0bac085e238dec2c828049f`

## Kapsam ve sayımlar

- Sezon: **5**, her sezonda **20**, toplam **100/100 bölüm**.
- Kayıt durumu: **100 complete**, **0 pending**, **0 draft**.
- Her özetin özgün Türkçe kelime sayısı: **250–287**.
- Toplam özet sözcüğü: **26.744**; bölüm başına ortalama **267,44**.
- Tüm kayıtlarda `source_verified: true`, `spoilers: true` ve bölüm bazlı GateWorld + StargateWiki bağlantısı.
- Bağlantı testi (bağlı CI hostunda, HTTP GET `?action=raw`): **100/100 StargateWiki bölüm rehberi 200**, içerik her biri en az 300 bayt.
- GateWorld bölümleri de dosya bazında kaynak olarak listelenir; GateWorld URL'leri için toplu HTTP 200 denetimi yapılmış sayılmamalıdır.

## Tekrarlanabilir kontrol

```sh
python3 docs/research/stargate-atlantis/validate_atlantis.py
```

Denenen ortam: bağlantılı CI hostunda, GitHub branch'inin `--depth 1 --sparse` geçici klonu. Production, main ve SG-1 arşivi değiştirilmedi. Script yalnız Python standart kütüphanesini kullanır.

Denetlenenler: tam 100 dosya, eksiksiz S01E01…S05E20 kümesi, klasör/metadata eşleşmeleri, `complete` durumu, 250–400 kelime aralığı, sayı metadatası, spoiler ve kaynak alanları, bölüm indeksinin kapsamı, README ilerleme sayısı.

**Sınır:** Bu yapısal kontrol otomatik olgu-doğruluk sınaması değildir. Bağlı bölüm rehberlerinin erişilebilir olması, her cümlenin olay örgüsüne sadakatini tek başına ispatlamaz; gerekirse bölüm transkriptleriyle ayrıca editoryal denetim yapılmalıdır.

## Yayın kararı

Araştırma branch'inde tutulur. **Main merge: yok. Production deploy: yok. Model çağrı maliyeti: yok.**
