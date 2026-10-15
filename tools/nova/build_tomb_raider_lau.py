#!/usr/bin/env python3
"""NOVA v0.7 LAU research: offline deterministic data and documentation build."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.7'
SRC=BASE/'source_records/tomb_raider_lau.json'
DOCS=ROOT/'docs/research/tomb-raider-lau'
TABLES=('works','sources','story_events','narrative_chronology','narrative_links',
        'artifacts','remake_analogues','editorial_boundaries','mechanics',
        'mechanic_evidence','prior_links')
def jsonl(name,rows):
    p=BASE/(name+'.jsonl')
    p.write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf8')
def doc(name,txt):
    p=DOCS/name
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(txt.rstrip()+'\n',encoding='utf8')
def build():
    c=json.loads(SRC.read_text(encoding='utf8'))
    events={x['event_id']:x for x in c['story_events']}
    derived={k:c[k] for k in TABLES if k in c}
    evidence=[]
    older=[]
    for m in c['mechanics']:
        for aid in m['event_anchors']:
            e=events[aid]
            evidence.append({'evidence_id':m['mechanic_id']+':'+aid,
                'mechanic_id':m['mechanic_id'],'event_id':aid,
                'work_id':e['work_id'],'source_ids':e['source_ids'],
                'event_type':e['event_type'],'quality_effect':'not_evaluated',
                'lumi_canon':False})
        for old in m['prior_mechanic_ids']:
            older.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':old,
              'relation':'conceptually_related_not_equivalent',
              'quality_effect':'not_evaluated'})
    derived['mechanic_evidence']=evidence
    derived['prior_links']=older
    for name in TABLES:jsonl(name,derived[name])
    jsonl('quality_evaluations',[])
    jsonl('lumi_usage_history',[])
    overview='# NOVA v0.7 — Legend / Anniversary / Underworld kaynak kütüphanesi\n\n'
    overview+='Sadece ilk kaynak araştırması: ücretli model, hikâye üretimi, A/B testleri veya LUMI entegrasyonu yok.\n\n'
    overview+='## Kaydedilen veri\n\n'
    for name in TABLES:overview+='- '+name+': '+str(len(derived[name]))+'\n'
    overview+='\n## Her oyunun olayları\n\n'
    for w in c['works']:overview+='- ['+w['title']+'](works/'+w['work_id'].lower()+'.md)\n'
    overview+='\n## İnceleme belgeleri\n\n'
    for filename,title in [
       ('MECHANICS.md','18 anlatı mekaniği'),
       ('CHRONOLOGY.md','Yayın ve hikâye kronolojisi'),
       ('ARTIFACTS.md','7 eşyanın edinim koşulları'),
       ('REMAKE_FIREWALL.md','Klasik 1996 ile Anniversary karşılaştırması'),
       ('SOURCES.md','17 resmî kaynak'),
       ('CONTINUITY.md','Yayınlanan içerik / DLC / kopya kimliği sınırları'),
       ('VALIDATION_REPORT.md','Gözlenen test sonuçları'),
       ('NEXT_SOURCE_PLAN.md','Sonraki kaynak önerileri')
    ]:overview+='- ['+title+']('+filename+')\n'
    overview+='\n**Kalite etkisi:** not_evaluated. Bu, oyun dünyası veya LUMI kanonu değildir.\n'
    doc('README.md',overview)
    for w in c['works']:
        s='# '+w['title']+' — ilk kaynaklı olay kayıtları\n\n'
        s+='Yayıncı retrospektiflerine dayanan Türkçe parafraz; doğrudan oyun içi görüntü denetimi değil.\n\n'
        for e in c['story_events']:
            if e['work_id']!=w['work_id']:continue
            s+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
            s+=e['observation_tr']+'\n\n'
            s+='**Kaynak:** '+', '.join(e['source_ids'])+'; **olay sınıfı:** '+e['event_type']+'\n\n'
        doc('works/'+w['work_id'].lower()+'.md',s)
    s='# NOVA v0.7 — 18 mekanik adayı\n\n'
    s+='Mekanik soyutlamaları yorumdur, hikâye kalitesi etkisi ölçülmüş değildir.\n\n'
    for m in c['mechanics']:
        s+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        s+='**Gözlem:** '+m['observed_tr']+'\n\n'
        s+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        s+='**Koruma kuralı:** '+m['guardrail_tr']+'\n\n'
        s+='**Kanıt olayları:** '+', '.join(m['event_anchors'])+'\n\n'
        s+='**Önceki kavramlar:** '+', '.join(m['prior_mechanic_ids'])+'\n\n'
    doc('MECHANICS.md',s)
    s='# Hikâye zamanı, yayın yılı ve sunum sırası\n\n'
    s+='Ana hikâyelerin sırası Anniversary → Legend → Underworld, yayın sırası Legend → Anniversary → Underworld.\n\n'
    s+='Legend çocukluk/Paraíso geçmiş olayları ana hikâye öncesinde bulunduğu için oyunun bütün olayları tek ana sıralamayla otomatik sıralanmaz.\n\n'
    for r in c['narrative_chronology']:
        s+='- '+r['work_id']+': story_rank='+str(r['story_rank'])+', release_rank='+str(r['release_rank'])+'\n'
    s+='\n## Kaydedilen 16 bağlantı\n\n'
    for l in c['narrative_links']:
        s+='- '+l['from_event_id']+' → '+l['to_event_id']+': '+l['relation']+'; '+l['link_type']+'; çıkarım='+str(l['inference'])+'\n'
    doc('CHRONOLOGY.md',s)
    s='# Eşyalar ve erişim koşulları\n\n'
    for a in c['artifacts']:
        s+='- **'+a['artifact_id']+' — '+a['name']+'**: '+a['state_note']+'; '
        s+='kanıt='+', '.join(a['event_refs'])+'\n'
    s+='\n**Mjölnir önkoşulları:** iki ayrı eldiven + kemer; kaynak: UND-GAUNTLETS.\n'
    doc('ARTIFACTS.md',s)
    s='# Anniversary yeniden anlatımı ile Core Design 1996 arasındaki sınır\n\n'
    s+='Bunlar benzerlik bağlantılarıdır, aynı kanon olayı veya zaman çizgisi değildir.\n\n'
    for r in c['remake_analogues']:
        s+='- '+r['lau_event_id']+' ↔ '+r['classic_event_id']+': '+r['resemblance']+'; '+r['link_type']+'\n'
    doc('REMAKE_FIREWALL.md',s)
    s='# İlk-pass kaynak sicili\n\n'
    s+='Tüm URL’ler bu oturumda web aramasında bulunan resmî kaynaklardır. Her hikâye iddiası video/kod ile bağımsız doğrulanmadı.\n\n'
    for r in c['sources']:
        s+='- **'+r['source_id']+'** — ['+r['source_type']+']('+r['url']+'); '+r['verification']+'\n'
    doc('SOURCES.md',s)
    s='# Süreklilik, telif ve içerik geçerlilik sınırları\n\n'
    for i,x in enumerate(c['continuity_firewall'],1):
        s+=str(i)+'. '+x+'\n'
    s+='\n## Geliştirme/DLC ayrımı\n\n'
    for x in c['editorial_boundaries']:
        s+='- '+x['id']+': '+x['note']+'; kaynak='+', '.join(x['sources'])+'\n'
    doc('CONTINUITY.md',s)
    manifest={
      'schema_version':c['schema_version'],'research_cutoff_date':c['research_cutoff_date'],
      'source_file':str(SRC.relative_to(ROOT)),
      'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
      'counts':{k:len(derived[k]) for k in TABLES},
      'quality_effect':'not_evaluated','story_quality_trials':0,
      'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return manifest
if __name__=='__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
