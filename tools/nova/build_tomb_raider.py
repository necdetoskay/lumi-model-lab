#!/usr/bin/env python3
"""Deterministic, offline, NOVA v0.5 Survivor research compiler."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.5'
SRC=BASE/'source_records/tomb_raider_survivor.json'
DOCS=ROOT/'docs/research/tomb-raider-survivor'
TABLES=('works','sources','story_events','character_states','cross_work_links',
        'supplementary_releases','mechanics','mechanic_evidence','prior_links')
def write(name,rows):
    p=BASE/(name+'.jsonl')
    p.write_text(''.join(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n' for row in rows),encoding='utf8')
def doc(name,s):
    p=DOCS/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(s.rstrip()+'\n',encoding='utf8')
def build():
    c=json.loads(SRC.read_text(encoding='utf8'))
    ev={e['event_id']:e for e in c['story_events']}
    evidence=[]
    prior=[]
    for m in c['mechanics']:
        for aid in m['evidence_anchors']:
            e=ev[aid]
            evidence.append({'evidence_id':m['mechanic_id']+':'+aid,'mechanic_id':m['mechanic_id'],
                'event_id':aid,'work_id':e['work_id'],'source_ids':e['source_ids'],
                'observed_event_tr':e['observed_event_tr'],'mechanism_inference':True,
                'quality_effect':'not_evaluated','lumi_canon':False})
        for version,field in (('0.3','related_pop_ids'),('0.4','related_prt_ids')):
            for old_id in m[field]:
                prior.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':old_id,
                    'prior_version':version,'relation':'related_concept_not_equivalent',
                    'quality_effect':'not_evaluated'})
    tables={n:c[n] for n in TABLES if n in c}
    tables['mechanic_evidence']=evidence
    tables['prior_links']=prior
    for name,rows in tables.items():write(name,rows)
    write('quality_evaluations',[])
    write('lumi_usage_history',[])
    rootdoc='# NOVA v0.5 — Tomb Raider Survivor araştırma kataloğu\n\n'
    rootdoc+='İlk kaynaklı araştırma parafrazlarıdır; oyun dosyası veya uzman editoryal denetimi değildir.\n\n'
    rootdoc+='## Sayımlar\n\n'
    for name in TABLES:rootdoc+='- '+name+': '+str(len(tables[name]))+'\n'
    rootdoc+='\n## Kayıtlar\n\n'
    for w in c['works']:rootdoc+='- ['+w['title']+'](works/'+w['work_id'].lower()+'.md)\n'
    for name,title in [('MECHANICS.md','Mekanikler'),('CHARACTER_ARC.md','Karakter durumları'),
        ('CROSS_GAME.md','Oyunlar arası bağlar'),('SOURCES.md','Kaynaklar'),
        ('CONTINUITY_FIREWALL.md','Süreklilik sınırları'),
        ('VALIDATION_REPORT.md','Doğrulama kanıtı'),('NEXT_SOURCE_PLAN.md','Sonraki eserler')]:
        rootdoc+='- ['+title+']('+name+')\n'
    rootdoc+='\nGerçek hikâye testleri, ücretli model çağrıları ve LUMI üretim entegrasyonu yok; kalite etkisi değerlendirilmedi.\n'
    doc('README.md',rootdoc)
    for w in c['works']:
        s='# '+w['title']+' — kaynaklı olay haritası\n\n'
        s+='Ayrı eser, Survivor ortak sürekliliği. Olaylar oyun metninin kopyası değildir.\n\n'
        for e in c['story_events']:
            if e['work_id']!=w['work_id']:continue
            s+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
            s+=e['observed_event_tr']+'\n\n'
            s+='**Durum:** '+e['character_state_delta_tr']+'\n\n'
            s+='**Kaynak:** '+', '.join(e['source_ids'])+'\n\n'
        doc('works/'+w['work_id'].lower()+'.md',s)
    s='# NOVA Survivor — 18 anlatı mekaniği adayı\n\n'
    s+='Soyutlama hikâye kalitesi kanıtı değildir; özgün sahneler kopyalanmaz.\n\n'
    for m in c['mechanics']:
        s+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        s+='**Gözlem:** '+m['observed_tr']+'\n\n'
        s+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        s+='**Koruma kuralı:** '+m['guardrail_tr']+'\n\n'
        s+='**Kanıt:** '+', '.join(m['evidence_anchors'])+'\n\n'
        s+='**Önceki benzer adaylar:** '+', '.join(m['related_pop_ids']+m['related_prt_ids'])+'\n\n'
    doc('MECHANICS.md',s)
    s='# Lara karakter durumunun 9 gözlem aşaması\n\n'
    for row in c['character_states']:
        s+='## '+row['state_id']+' — '+row['state_label']+'\n\n'
        s+=row['work_id']+' / '+row['anchor_event_id']+': '+row['observation_tr']+'\n\n'
    doc('CHARACTER_ARC.md',s)
    s='# Survivor oyunları arası gözlem ve benzerlik bağları\n\n'
    s+='Yalnız franchise_continuity kaynak anlatıda süreklilik, interpretive_comparison çıkarımdır.\n\n'
    for x in c['cross_work_links']:
        s+='- '+x['from_event_id']+' → '+x['to_event_id']+': '+x['relation']+'; '+x['edge_kind']+'; inference='+str(x['inference'])+'\n'
    s+='\n## Ayrı ana eser sayılmayan yayınlar\n\n'
    for x in c['supplementary_releases']:s+='- '+x['release_id']+': '+x['note_tr']+'\n'
    doc('CROSS_GAME.md',s)
    s='# Resmî Tomb Raider yayıncı retrospektifleri\n\n'
    s+='Bu kaynaklar doğrudan oyun dosyası oynanış doğrulaması değildir.\n\n'
    for x in c['sources']:s+='- **'+x['source_id']+'**: ['+x['source_type']+']('+x['url']+') — '+x['coverage']+'\n'
    doc('SOURCES.md',s)
    s='# Süreklilik ve telif bariyeri\n\n'
    for i,x in enumerate(c['continuity_firewall'],1):s+=str(i)+'. '+x+'\n'
    doc('CONTINUITY_FIREWALL.md',s)
    manifest={'schema_version':c['schema_version'],'research_cutoff_date':c['research_cutoff_date'],
        'source_file':str(SRC.relative_to(ROOT)),
        'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
        'counts':{n:len(tables[n]) for n in TABLES},
        'quality_effect':'not_evaluated','story_quality_trials':0,'new_paid_model_calls':0,
        'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return manifest
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
