#!/usr/bin/env python3
"""Deterministic offline NOVA v0.10 original BioShock research builder."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.10'
SRC=BASE/'source_records/bioshock_2007.json'
DOCS=ROOT/'docs/research/bioshock'
TABLES=('works','sources','story_events','mechanics','knowledge_states','narrative_links',
        'ending_variants','prior_mechanic_references','editorial_boundaries','mechanic_evidence')
def dump(name,rows):
    (BASE/(name+'.jsonl')).write_text(
        ''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf8')
def doc(name,contents):
    file=DOCS/name
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(contents.rstrip()+'\n',encoding='utf8')
def build():
    c=json.loads(SRC.read_text(encoding='utf8'))
    ev={e['event_id']:e for e in c['story_events']}
    evidence=[]
    for m in c['mechanics']:
        for id in m['event_anchors']:
            e=ev[id]
            evidence.append({'evidence_id':m['mechanic_id']+':'+id,'mechanic_id':m['mechanic_id'],
                 'event_id':id,'work_id':'BS2007','event_kind':e['event_kind'],
                 'source_ids':e['source_ids'],'confidence':e['evidence_strength'],
                 'quality_effect':'not_evaluated','lumi_canon':False})
    data={name:c[name] for name in TABLES if name in c}
    data['mechanic_evidence']=evidence
    for k in TABLES:dump(k,data[k])
    dump('quality_evaluations',[])
    dump('lumi_usage_history',[])
    intro='# NOVA v0.10 — BioShock (2007)\n\n'
    intro+='İlk kaynaklı araştırma geçişi. **Yalnız 2007 özgün ana oyun**, 2016 Remastered/ekler ve BioShock 2/Infinite hariç. '
    intro+='Doğrudan tüm özgün oyun sahnelerinin bağımsız tekrarlı görüntü kaydı yapılmadı.\n\n'
    intro+='## Kayıtlar\n\n'
    for name in TABLES:intro+='- '+name+': **'+str(len(data[name]))+'**\n'
    intro+='\n## Belgeler\n\n'
    for name,label in [('EVENTS.md','23 kaynaklı olay'),('MECHANICS.md','16 soyut mekanik'),
      ('KNOWLEDGE.md','Beş karakter inancı ile gerçeklik ayrımı'),
      ('CHOICE_AND_ENDINGS.md','Little Sister kararları ve ayrı sonlar'),
      ('WORLD_STATE.md','Fiziksel önkoşullar ve nedensellik'),
      ('SOURCES.md','Kaynak sicili'),('FIREWALL.md','Süreklilik, seçim ve telif sınırları'),
      ('VALIDATION_REPORT.md','CI doğrulama kanıtı'),('NEXT_SOURCE_PLAN.md','Sonraki kaynak planı')]:
        intro+='- ['+label+']('+name+')\n'
    intro+='\nNOVA için veri araştırmasıdır. Gerçek hikâye kalitesi A/B testi veya LUMI üretim kullanımı yok.\n'
    doc('README.md',intro)
    t='# BioShock (2007) — olay kayıtları\n\n'
    for e in c['story_events']:
        t+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'+e['observed_event_tr']+'\n\n'
        t+='**Kaynaklar:** '+', '.join(e['source_ids'])+'; **tür:** '+e['event_kind']+'; **yer:** '+e['location_zone']+'\n\n'
        t+='**Bilgi/dünya durumu:** '+e['world_knowledge_delta']+'\n\n'
    doc('EVENTS.md',t)
    t='# BioShock — 16 araştırma mekaniği\n\n'
    t+='Bunlar gözleme dayalı hipotezlerdir; özgün oyun olayları veya yeni hikâyede kanıtlanmış etki olarak yorumlanamaz.\n\n'
    for m in c['mechanics']:
        t+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        t+='**Gözlem:** '+m['observed_tr']+'\n\n'
        t+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        t+='**Koruma kuralı:** '+m['guardrail_tr']+'\n\n'
        t+='**Olaylar:** '+', '.join(m['event_anchors'])+'; **önceki kavramlar:** '+', '.join(m['prior_mechanic_ids'])+'\n\n'
    doc('MECHANICS.md',t)
    t='# Jack / Atlas / Fontaine: karakter bilgisi ile nesnel gerçek\n\n'
    for r in c['knowledge_states']:
        t+='## '+r['state_id']+' — '+r['subject']+'\n\n'
        t+='**İlk iddia:** '+r['claim']+'\n\n**Dünya durumu / kayıtlı yorum:** '+r['world_truth']+'\n\n'
        t+='**Olaylar:** '+r['setup_event_id']+' → '+r['reveal_event_id']+'; '+r['knowledge_status']+'\n\n'
    doc('KNOWLEDGE.md',t)
    t='# Little Sister: gerçek kararlar ile sabit sahneleri ayırmak\n\n'
    t+='Karar birimi BS-E05 tekrarlanabilir player_branch; Ryan karşılaşması BS-E15 mandatory_story. '
    t+='Epiloglar birbirini dışlar. Bir Little Sister hasadı için tam eşik, rehberler çeliştiği için doğrulanmamış kabul edilir.\n\n'
    for o in c['ending_variants']:
        t+='- **'+o['variant_id']+'**: '+o['name']+'; olay '+o['event_id']+'; koşul: '+o['when_tr']
        t+='; doğrulanan kesin eşik: '+str(o['specific_numeric_threshold'])+'; doğrulandı mı: '+str(o['threshold_verified'])+'\n'
    doc('CHOICE_AND_ENDINGS.md',t)
    t='# Rapture: çevresel durum ve neden-sonuç bağlantıları\n\n'
    t+='Dünyanın bitki/oksijen koşulu, fiziksel Plasmid gücü, eşya birleşimi ve kılık değiştirme önkoşulları yalnız sahne gerektirdiği için değişmez.\n\n'
    for x in c['narrative_links']:
        t+='- '+x['from_event_id']+' → '+x['to_event_id']+' '+x['relation']+'; tür='+x['relation_kind']+'; yorum='+str(x['inference'])+'\n'
    doc('WORLD_STATE.md',t)
    t='# Kaynak sicili\n\n'
    t+='Ürün sayfası çıkış yılını, 2007 yapımcı röportajları tasarım niyetini, GameSpot/GameFAQs walkthrough oynanış iddiasını destekler. Kaynak türlerini eşitlemeyin.\n\n'
    for r in c['sources']:
        t+='- **'+r['source_id']+'** — ['+r['kind']+']('+r['url']+'); kanıt türü='+r['evidence_tier']+'\n'
    doc('SOURCES.md',t)
    t='# Süreklilik, agency, telif ve kanıt bariyeri\n\n'
    for i,x in enumerate(c['continuity_firewall'],1):t+=str(i)+'. '+x+'\n'
    t+='\n## Kanıtı ayrıca doğrulanacak iddialar\n\n'
    for row in c['editorial_boundaries']:
        t+='- '+row['id']+': '+row['claim_tr']+' — '+row['status']+'\n'
    doc('FIREWALL.md',t)
    meta={'schema_version':c['schema_version'],
          'source_file':str(SRC.relative_to(ROOT)),
          'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
          'research_cutoff_date':c['research_cutoff_date'],
          'counts':{k:len(data[k]) for k in TABLES},
          'original_gameplay_captured_and_audited':False,
          'quality_effect':'not_evaluated','story_quality_trials':0,
          'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return meta
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
