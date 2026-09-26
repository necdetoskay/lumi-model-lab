from experiments.prototypes import story_spine_refined_recipe_20260926 as base


ORIGINAL_CALL = base.call_openrouter


def seeded_call_openrouter(*args, **kwargs):
    kwargs["seed"] = 2026092601
    return ORIGINAL_CALL(*args, **kwargs)


if __name__ == "__main__":
    base.WRITER_MODEL = "mistralai/ministral-8b-2512"
    base.call_openrouter = seeded_call_openrouter
    base.WRITER_SYSTEM = base.WRITER_SYSTEM.replace(
        "UZUNLUK:\n- Hedef: 475-525 kelime.\n- Hard aralık: 375-625 kelime.\n- 375 kelimenin altında bitirme.",
        "ÜRETİM HACMİ:\n- Yaklaşık 700 kelimelik anlatı hacmi hedefle.\n- Bu sayı yayın kabul hedefi değildir; amaç modelin kısa kesme eğilimini kalibre etmektir.\n- Yeni olay, yeni canon, açıklama dolgusu veya mekanik tekrar ekleme.\n- Omurgadaki develop ve anchor beat'leri yeterince yaşat.\n- Nihai yayın kabul aralığı yine 375-625 kelimedir; 375 kelimenin altında bitirme."
    )
    base.main()
