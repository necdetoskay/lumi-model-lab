# SERA v0.44 — SceneTrace kaynak kanıtı ve fiziksel geçiş karar kartları

**Durum: SHADOW ONLY.** [SceneTrace backlog #307](https://github.com/necdetoskay/lumi-model-lab/issues/307) / [Epic #306](https://github.com/necdetoskay/lumi-model-lab/issues/306). Mevcut v0.43 hattının üzerine, gerçek iki OpenRouter testinden **yeni ödeme veya model isteği yapmadan** kaynak-kanıt zorunluluğu açıklayan dar kapsamlı bir denetim eklendi. Project_LUMI / SQLite mutasyonu, branch merge veya üretim rollout yok.

## Ne yapar?

`scene_trace_evidence_challenge_v044.py` geçmişte ücretli çalışmış **gerçek** Gemini 3.7 Flash ve Claude Haiku 4.5 yanıtlarını, SERA v0.43'ün SHA-256 sabitli kaynak, exact quote/span ve model-yanıt bağlama sistemi üzerinden yeniden doğrular. Kaynak 243 kelimelik Mara S1, 28 cümle. Daha önce aynı iki batch'te **8/28** cümle incelendi; kalan 20 gerçek model tarafından değerlendirilmedi. Altı event-signature anlaşmazlığı değişmedi.

Daha önce tespit edilmiş iki gerçek aday için `EvidenceChallenge` çıkarır:

1. Haiku, `s004`: Cümle saat **zaten açık** derken `CHANGE_STATE` önerdi. Kartta `BLOCK_STATIC_PREDICATE_AS_TRANSITION`; eksik `EXPLICIT_OPENING_ACTION` ve `PREVIOUS_CLOSED_STATE_AND_CHANGED_STATE`; önerilen otomatik sonraki iş `TARGETED_INDEPENDENT_STATE_TRANSITION_REEXTRACTION`.
2. Gemini, `s022`: Vane kalemin hareketini **izliyor**; `MOVE` adayı kalemi kimin hareket ettirdiğini kanıtlamıyor. Kartta `BLOCK_UNATTRIBUTED_CAUSAL_AGENT`; eksik `ACTOR_WHO_CAUSED_PENCIL_MOTION` ve `BEFORE_AFTER_OBJECT_LOCATION_AND_TIMING`; önerilen otomatik sonraki iş `TARGETED_INDEPENDENT_CAUSAL_AGENT_REEXTRACTION`.

**Her kart** kaynak cümlesi, exact span, gerçek model ID, olay türü, fail/eksik fiziksel kanıt türü, machine-next-action, belirsiz saat, `world_state_transition_authorized=false`, `repair_was_executed=false` alanlarını taşır. Çevrimdışı karar çıktısı `status=REAL_SOURCE_EVIDENCE_CHALLENGED_SHADOW_ONLY`.

İki önemli doğruluk sınırı:

- Bu kurallar yalnızca **iki somut kaynak sözcük örüntüsü** için tanısaldır, genel İngilizce/anlamsal yargıç değil. Bir kuralın eşleşmemesi otomatik **PASS** değildir (`NO_POLICY_BLOCK_SEMANTIC_UNVERIFIED`). Modellerin diğer yanlış eylemlerini yakaladığımızı iddia etmiyoruz.
- Bu iki aday mevcut SERA'da zaten **HOLD** idi. `mutation_proposals_blocked_in_shadow=2` ifadesi **üretimde iki hatalı yazım engellendi** demek değildir; `mutation_proposals_previously_committed=0` ve `new_real_model_errors_proven=0`. v0.44'ün yeni faydası *hangi kanıt eksik, sonra sistem neyi yeniden çıkarsın* bilgisidir.

## Gerçek vaka ve bağımsız protokol karşılaştırma testi

`fixtures/scene_trace_policy_contrasts_v044.json` sekiz test maddesini **politikadan ayrı** sabit tutar: açık saat betimlemesi / gerçekten saati açma, kalem hareketini izleme / kalemi hareket ettirme, yalnızca gözlem olayı ve kural kapsamı dışında kalan cümleler. Bu sekiz test, **yalnız dar tespit politikasının davranışı** için beklenen kararlardır; tüm hikâye gold etiketleri değildir.

`tests/test_scene_trace_evidence_challenge_v044.py`: 8 test; gerçek kaynak/span sahteciliği, modelde bulunmayan olayın risk kaydına enjeksiyonu, kanonik yetki sahteciliği, değiştirilmiş kaynak SHA, yinelenmiş risk kartı ve karantinadan güvenli olaya kaçış reddediliyor. Hiçbir durumda gerçek çıkarım semantik doğruluk veya G2 yetkisi kazanmaz.

## Kanıt

[Self-hosted CI 38946880572](https://github.com/necdetoskay/lumi-model-lab/actions/runs/38946880572) **SUCCESS**; **696/696 Python testi**, gerçek dondurulmuş ücretli provider artefaktlarına karşı 2 source-bound risk kartı, 8/8 sabit regresyon maddesi PASS. Artefakt: `sera-v044-real-mara-risk-cards-38946880572` (ID `12067600873`). Yeni LLM çağrısı ve maliyeti **0**; üretim ve simülasyon DB yazısı **0**.

## Sonraki AEGIS kapısı

Her olay için tek tek doğrulama, otomatik hedefli yeniden çıkarım, yeniden kontrol ve düşük maliyetli farklı model fallback'i **gerçek hikâye üretim hattına bağlanmış değil**. Bu sürüm yalnızca *hangi aşamanın eksik olduğunu* belirler, sahne otomatik onarımının gerçekleştiğini iddia etmez. Ücretli otomatik denemelerden önce provider receipt/idempotent recovery gerekir. Hatalar çözülemiyorsa kalıcı `FAILED_SAFE_FINAL`, asla insan zorunluluğu veya yanlış dünya commit'i. Sahnenin tümünde recall/precision ve A/B zaman/beat yazım üstünlüğü henüz ölçülmedi. **SceneTrace çekirdek entegrasyonu: HOLD / SHADOW ONLY.**
