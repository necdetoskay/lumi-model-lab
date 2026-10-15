#!/usr/bin/env python3
"""Deterministic offline NOVA v0.6 classic Core Design corpus builder.

Research only; no paid models, network calls, LUMI runtime, or story generation.
"""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.6'
SRC=BASE/'source_records/tomb_raider_classic.json'
DOCS=ROOT/'docs/research/tomb-raider-classic'
TABLES=('works','sources','story_events','narrative_links','supplementary_releases',
        'editorial_boundaries','mechanics','mechanic_evidence','prior_links')
def write_jsonl(key,rows):
    f=BASE/(key+'.jsonl')
    f.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in rows),encoding='utf8')
def document(name,txt):
    file=DOCS/name
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(txt.rstrip()+'\n',encoding='utf8')
def build():
    canon=json.loads(SRC.read_text(encoding='utf8'))
    ev={e['event_id']:e for e in canon['story_events']}
    evid=[]
    older=[]
    for m in canon['mechanics']:
        for anchor in m['evidence_anchors']:
            a=ev[anchor]
            evid.append({'evidence_id':m['mechanic_id']+':'+anchor,
                'mechanic_id':m['mechanic_id'],'event_id':anchor,
                'work_id':a['work_id'],'source_ids':a['source_ids'],
                'claim_kind':a['claim_kind'],'narrated_time_type':a['narrated_time_type'],
                'quality_effect':'not_evaluated','lumi_canon':False})
        for field,version in [('related_survivor_mechanics','0.5'),('related_older_mechanics','prior')]:
            for old_id in m[field]:
                older.append({'mechanic_id':m['mechanic_id'],'older_mechanic_id':old_id,
                  'prior_version':version,'relation':'related_concept_not_equivalent',
                  'quality_effect':'not_evaluated'})
    d={key:canon[key] for key in TABLES if key in canon}
    d['mechanic_evidence']=evid
    d['prior_links']=older
    for key in TABLES:write_jsonl(key,d[key])
    write_jsonl('quality_evaluations',[])
    write_jsonl('lumi_usage_history',[])
    overview='# NOVA v0.6 — Tomb Raider Classic dönemi (1996–2003)\n\n'
    overview+='**Kapsam:** Core Design tarafından geliştirilmiş altı ana oyun. İlk resmî kaynaklı araştırma geçişi; doğrudan oyun dosyası/oynanış denetimi değildir.\n\n'
    overview+='## Kayıt sayıları\n\n'
    for key in TABLES:overview+='- '+key+': **'+str(len(d[key]))+'**\n'
    overview+='\n## Eser bazlı kayıtlar\n\n'
    for w in canon['works']:
        overview+='- ['+w['title']+'](works/'+w['work_id'].lower()+'.md)\n'
    overview+='\n## Araştırma belgeleri\n\n'
    for filename,label in [('MECHANICS.md','19 mekanik çıkarımı'),
                           ('CHRONOLOGY.md','Geçmiş anılar ve olay zamanı'),
                           ('SOURCE_REGISTER.md','21 kaynak'),
                           ('CONTINUITY.md','Süreklilik bariyerleri'),
                           ('VALIDATION_REPORT.md','Gerçek test kanıtları'),
                           ('NEXT_SOURCE_PLAN.md','Legend/Anniversary/Underworld planı')]:
        overview+='- ['+label+']('+filename+')\n'
    overview+='\nHikâye oluşturulmadı. LUMI kanonu değişmedi. Kalite artışı test edilmedi.\n'
    document('README.md',overview)
    for w in canon['works']:
        txt='# '+w['title']+' — NOVA klasik dönem kaynak olayları\n\n'
        txt+='Araştırma parafrazları ve kaynak ID’leri; yayın sırası, geçmiş olay zamanı ve sunum sırası aynı kabul edilmez.\n\n'
        for e in canon['story_events']:
            if e['work_id']!=w['work_id']:continue
            txt+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
            txt+=e['observed_event_tr']+'\n\n'
            txt+='**Kaynak:** '+', '.join(e['source_ids'])+'; **kanıt tipi:** '+e['claim_kind']+'; '
            txt+='**zaman türü:** '+e['narrated_time_type']+'; **güven:** '+e['evidence_strength']+'.\n\n'
        document('works/'+w['work_id'].lower()+'.md',txt)
    txt='# Tomb Raider Classic — 19 soyut mekanik adayı\n\n'
    txt+='Yalnız araştırma çıkarımıdır; hikâyeleri iyileştirdiği kanıtlanmış bir kural listesi değildir.\n\n'
    for m in canon['mechanics']:
        txt+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        txt+='**Gözlem:** '+m['observed_tr']+'\n\n'
        txt+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        txt+='**Koruma kuralı:** '+m['guardrail_tr']+'\n\n'
        txt+='**Olay kanıtı:** '+', '.join(m['evidence_anchors'])+'\n\n'
        txt+='**Diğer eser benzerleri:** '+', '.join(m['related_survivor_mechanics']+m['related_older_mechanics'])+'\n\n'
    document('MECHANICS.md',txt)
    txt='# Anma çerçevesi, iç tarih ve yayın sırası ayrımı\n\n'
    txt+='NOVA v0.6 olayları main_story_relative / legendary_past / historical_past / flashback_young_lara / memorial_present / recalled_past / recalled_childhood / memorial_frame / multi_time_lore / development_history türlerini taşır.\n\n'
    txt+='## Zaman/yorum bağlantıları\n\n'
    for x in canon['narrative_links']:
        txt+='- '+x['from_event_id']+' → '+x['to_event_id']+': '+x['relation']+'; '+x['edge_kind']+'; çıkarım='+str(x['inference'])+'\n'
    txt+='\nBu bağlar tek bir doğrusal tarihsel nedensellik grafiği değildir; geçmişe dönük anlatım bağlantıları ile tematik paraleller ayrı tutulur.\n'
    document('CHRONOLOGY.md',txt)
    txt='# Resmî Tomb Raider kaynakları\n\n'
    txt+='Bu linkler editoryal/tasarımcı kaynaklarıdır; URL gözlemi her sahnenin orijinal oynanışla bağımsız doğrulaması değildir.\n\n'
    for s in canon['sources']:
        txt+='- **'+s['source_id']+'** ['+s['source_type']+']('+s['url']+') — '+s['verification']+'\n'
    document('SOURCE_REGISTER.md',txt)
    txt='# Yayınlanan kanon / süreklilik / fikir ayrımı\n\n'
    for k,rule in enumerate(canon['continuity_firewall'],1):
        txt+=str(k)+'. '+rule+'\n'
    txt+='\n## Kaynak şüphe/plan kayıtları\n\n'
    for issue in canon['editorial_boundaries']:
        txt+='- '+issue['issue_id']+' — '+issue['title_tr']+': '+issue['note_tr']+'\n'
    txt+='\n## Ayrı ana eser olmayan yayınlar\n\n'
    for r in canon['supplementary_releases']:
        txt+='- '+r['release_id']+': '+r['release_type']+'\n'
    document('CONTINUITY.md',txt)
    manifest={'schema_version':canon['schema_version'],
              'research_cutoff_date':canon['research_cutoff_date'],
              'source_file':str(SRC.relative_to(ROOT)),
              'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
              'counts':{k:len(d[k]) for k in TABLES},
              'quality_effect':'not_evaluated','story_quality_trials':0,
              'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return manifest
if __name__=='__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
