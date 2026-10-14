#!/usr/bin/env python3
"""12 synthetic lexical routing checks, not the required 12 real story-quality trials."""
import json
import sys
from validate import validate
from match import rank

CASES = [
    ("Gemide oksijen azalıyor, herkes için son tarih var", "M01"),
    ("Askeri lider ile uzman yetki konusunda karşı karşıya", "M02"),
    ("Bir kişi hayatını fedakarlık uğruna kayıp olarak kabul eder", "M03"),
    ("Uzak görevde ayrılan ekip kurtarma için bekler", "M05"),
    ("Eve dönüş isteği, anne ve aile özlemi doğurur", "M06"),
    ("İzleyici aygıt ve takip sinyali uzaylı saldırısını getirir", "M07"),
    ("İşgalciler rehineler alıp darbe ile komutayı değiştiriyor", "M08"),
    ("Tehlikeli teknoloji arayüz cihazıyla umut doğurur", "M09"),
    ("Torun ve nesil mirası geçmişin etkisini gösteriyor", "M10"),
    ("Eski düşman ile ittifak, ortak tehdit nedeniyle oluşur", "M13"),
    ("Zaman döngüsü, alternatif zaman yolculuğu gösterir", "M16"),
    ("Dron abluka stratejisi karşısında taktik üretir", "M18"),
]

def check():
    failures = []
    for prompt, expected in CASES:
        matches = rank(prompt, limit=3)
        if expected not in [m["mechanic_id"] for m in matches]:
            failures.append({"prompt": prompt, "expected": expected,
                             "received": [m["mechanic_id"] for m in matches]})
    no_match = rank("Ayçiçeği tarlasındaki futbol skorları", limit=3)
    if no_match:
        failures.append({"no_match_failed": no_match})
    return {
        "status": "PASS" if not failures else "FAIL",
        "type": "SYNTHETIC_LEXICAL_SMOKE",
        "cases": len(CASES) + 1,
        "story_quality_trials": 0,
        "failures": failures,
    }

if __name__ == "__main__":
    a, b = validate(), check()
    result = {"structural": a, "lexical_smoke": b}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if a["status"] == b["status"] == "PASS" else 1)
