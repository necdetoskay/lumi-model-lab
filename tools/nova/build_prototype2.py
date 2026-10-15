#!/usr/bin/env python3
"""NOVA v0.8 Prototype 2 research-only, deterministic offline artifact compiler."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.8'
SRC=BASE/'source_records/prototype2_2012.json'
DOCS=ROOT/'docs/research/prototype2'
TABLES=('works','sources','story_events','belief_states','cross_game_links','mechanics',
        'editorial_boundaries','mechanic_evidence','prior_links')
def dump(name,records):
    (BASE/(name+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in records),encoding='utf8')
def doc(name,body):
    path=DOCS/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(body.rstrip()+'\n',encoding='utf8')
def build():
    c=json.loads(SRC.read_text(encoding='utf8'))
    event={e['event_id']:e for e in c['story_events']}
    evidence=[];older=[]
    for m in c['mechanics']:
        for eid in m['event_anchors']:
            e=event[eid]
            evidence.append({'evidence_id':m['mechanic_id']+':'+eid,
               'mechanic_id':m['mechanic_id'],'event_id':eid,
               'work_id':'PROTOTYPE2-2012','source_ids':e['source_ids'],
               'confidence':e['confidence'],'quality_effect':'not_evaluated',
               'lumi_canon':False})
        for version,field in [('0.4','related_prototype_ids'),('other','related_other_ids')]:
            for mid in m[field]:
                older.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':mid,
                  'source_version':version,'relation':'related_concept_not_equivalent',
                  'quality_effect':'not_evaluated'})
    data={k:c[k] for k in TABLES if k in c}
    data['mechanic_evidence']=evidence
    data['prior_links']=older
    for k in TABLES:dump(k,data[k])
    dump('quality_evaluations',[])
    dump('lumi_usage_history',[])
    intro='# NOVA v0.8 — Prototype 2 (2012)\n\n'
    intro+='**Sadece kaynak verisi, kavramsal anlatı incelemesi ve çevrimdışı bütünlük testleri.** Hikâye üretimi, ücretli API, LUMI entegrasyonu ve A/B testi yok.\n\n'
    intro+='## Kaydedilen tablolar\n\n'
    for k in TABLES:intro+='- '+k+': **'+str(len(data[k]))+'**\n'
    intro+='\n## Belgeler\n\n'
    files=[('EVENTS.md','20 olay'),
           ('MECHANICS.md','14 mekanik çıkarımı'),
           ('BELIEF_VS_TRUTH.md','7 bilgi-dünya durum ayrımı'),
           ('CROSS_GAME.md','8 önceki oyuna bağlantı'),
           ('SOURCES.md','11 kaynak ve güven seviyeleri'),
           ('CONTINUITY.md','Süreklilik ve kalite sınırları'),
           ('VALIDATION_REPORT.md','Doğrulama raporu'),
           ('NEXT_SOURCE_PLAN.md','Sonraki araştırma kaynakları')]
    for name,label in files:intro+='- ['+label+']('+name+')\n'
    intro+='\nKaynak URL bulunması veya şemanın PASS olması, her final olayının özgün oyun kaydıyla bağımsız denetlendiği anlamına gelmez.\n'
    doc('README.md',intro)
    efile='# Prototype 2 — kaynaklı olay kayıtları\n\n'
    for e in c['story_events']:
        efile+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
        efile+=e['observed_event_tr']+'\n\n'
        efile+='**Kanıt:** '+', '.join(e['source_ids'])+'; **güven:** '+e['confidence']+'; **bölge:** '+e['zone']+'.\n\n'
        if e['belief_truth_delta']!='none_registered':
            efile+='**Bilgi/dünya ayrımı:** '+e['belief_truth_delta']+'\n\n'
    doc('EVENTS.md',efile)
    mm='# Prototype 2 — 14 soyut anlatı mekaniği\n\n'
    mm+='Bunlar kaynak gözlemlerinden türetilmiş yorumlardır, kalitenin arttığını ispatlamaz.\n\n'
    for m in c['mechanics']:
        mm+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        mm+='**Gözlem:** '+m['observed_tr']+'\n\n'
        mm+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        mm+='**Koruma:** '+m['guardrail_tr']+'\n\n'
        mm+='**Kanıt olayları:** '+', '.join(m['event_anchors'])+'\n\n'
        mm+='**Önceki aday bağlantıları:** '+', '.join(m['related_prototype_ids']+m['related_other_ids'])+'\n\n'
    doc('MECHANICS.md',mm)
    bs='# Heller bildikleri ve dünyanın gerçek durumu\n\n'
    bs+='Karakterin inancı, olayın öznel yorumu ve gözlenebilir gerçek dünya durumu ayrı tutulur.\n\n'
    for st in c['belief_states']:
        bs+='## '+st['state_id']+' — '+st['subject']+'\n\n'
        bs+='Kurulum: '+st['setup_event_id']+'; güncelleme: '+st['reveal_event_id']+'. '+st['knowledge_boundary_tr']+'\n\n'
        bs+='**Dünya kuralı:** '+st['world_state_rule']+'\n\n'
    doc('BELIEF_VS_TRUTH.md',bs)
    cg='# Prototype 2009 → Prototype 2 devam bağları\n\n'
    cg+='narrative_continuation / shared_actor_continuity olaya ilişkin bağlantıdır; karşılaştırmalar inferential olarak ayrı tutulur.\n\n'
    for x in c['cross_game_links']:
        cg+='- '+x['from_prior_event_id']+' → '+x['to_event_id']+' — '+x['relation']+'; '+x['edge_type']+'; inference='+str(x['inference'])+'\n'
    doc('CROSS_GAME.md',cg)
    rs='# Kaynak sicili\n\n'
    rs+='Kaynak çeşitleri farklı güven sınıfı taşır; oyuncu rehberi ve ansiklopedi, bağımsız oyun içi denetim değildir.\n\n'
    for x in c['sources']:
        rs+='- '+x['source_id']+': ['+x['source_kind']+']('+x['url']+') — '+x['evidence_tier']+'\n'
    doc('SOURCES.md',rs)
    co='# Continuity, bellek, etik ve telif bariyerleri\n\n'
    for i,r in enumerate(c['continuity_firewall'],1):co+=str(i)+'. '+r+'\n'
    co+='\n## Editoryal sınırlar\n\n'
    for x in c['editorial_boundaries']:
        co+='- '+x['id']+' — '+x['name']+': '+x['rule']+'\n'
    doc('CONTINUITY.md',co)
    manifest={'schema_version':c['schema_version'],
       'source_file':str(SRC.relative_to(ROOT)),
       'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
       'research_cutoff_date':c['research_cutoff_date'],
       'counts':{k:len(data[k]) for k in TABLES},
       'quality_effect':'not_evaluated','story_quality_trials':0,
       'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return manifest
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
