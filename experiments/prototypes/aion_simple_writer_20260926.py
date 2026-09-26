from __future__ import annotations
import json, os, time
from pathlib import Path
from dotenv import load_dotenv
from src.generate import call_openrouter, count_words, parse_cost, parse_usage

MODEL="aion-labs/aion-3.0"

SYSTEM=r"""
Sen profesyonel bir Türk çocuk kitabı yazarısın.
Tam 4 yaşındaki bir çocuğa bir yetişkin tarafından sesli okunacak doğal, sıcak ve eğlenceli bir Türkçe hikâye yaz.

Hedef yaklaşık 500 kelime. 375-625 kelime aralığında kal.
Türkçe doğrudan Türkçe yazılmış gibi duyulsun.

Karakter:
- Deniz 4 yaşında.
- Deniz'in en sevdiği küçük mavi oyuncak arabası kaybolmuş.
- Deniz annesiyle evde arıyor.
- Aramayı asıl Deniz'in somut gözlemleri, küçük denemeleri ve çocukça fikirleri ilerletsin.
- Anne cevabı bilen öğretmen/dedektif gibi davranmasın; Deniz'in oyununa ve aramasına doğal biçimde eşlik etsin.
- Araba mantıklı, fiziksel olarak mümkün bir yerde bulunsun.
- Hikâye ders, mesaj veya açıklayıcı özetle bitmesin; Deniz'e özgü somut bir hareket ya da kısa replikle bitsin.

Üslup:
- kısa ve sesli okumaya uygun cümleler,
- doğal çocuk diyaloğu,
- küçük mizah ve sürpriz,
- yetişkin gibi soyut muhakeme yok,
- anlatıcı karakterlerin zihnini gereksiz yere açıklamasın,
- yapay/çeviri kokan Türkçe kullanma.

Sadece bitmiş hikâyeyi yaz. İlk satır başlık olsun.
""".strip()

def main():
    load_dotenv()
    key=os.environ["OPENROUTER_API_KEY"]
    started=time.perf_counter()
    story,body,payload=call_openrouter(
        api_key=key,
        model=MODEL,
        system_prompt=SYSTEM,
        user_prompt="Hikâyeyi şimdi yaz.",
        temperature=0.72,
        max_tokens=None,
        seed=None,
        request_class="teacher_story",
        structured_output=False,
    )
    words=count_words(story)
    result={
      "experiment":"aion-simple-writer",
      "model":MODEL,
      "prompt_style":"minimal_positive_constraints",
      "judge_used":False,
      "local_edit_used":False,
      "provider_token_cap":None,
      "word_count":words,
      "hard_length_pass":375 <= words <= 625,
      "story":story,
      "cost":parse_cost(body).model_dump(mode="json"),
      "usage":parse_usage(body).model_dump(mode="json"),
      "elapsed_seconds":round(time.perf_counter()-started,3),
      "request_payload":payload,
    }
    out=Path("runs/aion-simple-writer")
    out.mkdir(parents=True,exist_ok=True)
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"story.txt").write_text(story+"\n",encoding="utf-8")
    print(json.dumps({k:result[k] for k in ["model","word_count","hard_length_pass","cost","elapsed_seconds"]},ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
