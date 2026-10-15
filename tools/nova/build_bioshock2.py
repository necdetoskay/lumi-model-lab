#!/usr/bin/env python3
"""NOVA v0.11 offline BioShock 2 and separate Minerva's Den source builder."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.11'
SRC=BASE/'source_records/bioshock2_minerva_2010.json'
DOCS=ROOT/'docs/research/bioshock2-minerva'
TABLES=('works','sources','story_events','choice_axes','ending_outcomes','knowledge_states',
        'narrative_links','object_states','mechanics','prior_bioshock_links',
        'editorial_boundaries','mechanic_evidence','mechanic_prior_links')
def emit(key,rows):
    (BASE/(key+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows),encoding='utf8')
def doc(name,contents):
    file=DOCS/name
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(contents.rstrip()+'\n',encoding='utf8')
def build():
    data=json.loads(SRC.read_text(encoding='utf8'))
    events={x['event_id']:x for x in data['story_events']}
    evidence=[]
    older=[]
    for m in data['mechanics']:
        for ev_id in m['event_anchors']:
            e=events[ev_id]
            evidence.append({'evidence_id':m['mechanic_id']+':'+ev_id,
                'mechanic_id':m['mechanic_id'],'event_id':ev_id,
                'work_id':e['work_id'],'source_ids':e['source_ids'],
                'evidence_strength':e['evidence_strength'],
                'quality_effect':'not_evaluated','lumi_canon':False})
        for old_id in m['prior_mechanic_ids']:
            older.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':old_id,
                'relation':'related_concept_not_equivalent','quality_effect':'not_evaluated'})
    tables={k:data[k] for k in TABLES if k in data}
    tables['mechanic_evidence']=evidence
    tables['mechanic_prior_links']=older
    for key in TABLES:emit(key,tables[key])
    emit('quality_evaluations',[])
    emit('lumi_usage_history',[])
    index='# NOVA v0.11 — BioShock 2 (2010) ve Minerva’s Den\n\n'
    index+='**Bir ana oyun + bir bağımsız anlatı DLC**, hikâyeleri ve envanterleri ayrı. Yalnız kaynaklı ilk araştırma, LUMI entegrasyonu yok.\n\n'
    index+='## Veri sayıları\n\n'
    for k in TABLES:index+='- '+k+': **'+str(len(tables[k]))+'**\n'
    index+='\n## Yapıtlar ve belgeler\n\n'
    for w in data['works']:index+='- ['+w['title']+'](works/'+w['work_id'].lower()+'.md)\n'
    for file,label in [('MECHANICS.md','18 yeni kavramsal mekanik'),
      ('CHOICES_AND_OUTCOMES.md','Dört bağımsız seçim ekseni ve üç final sınıfı'),
      ('KNOWLEDGE_AND_IDENTITY.md','Sekiz öznel bilgi ve gerçek durum ayrımı'),
      ('OBJECT_STATE.md','Altı kalıcı nesne/durum kaydı'),
      ('CHRONOLOGY.md','1958/1968 ve ayrı DLC zaman sınırı'),
      ('SOURCES.md','19 kaynak'),('CONTINUITY_FIREWALL.md','18 araştırma ve kanon sınırı'),
      ('VALIDATION_REPORT.md','Gerçek doğrulama raporu'),
      ('NEXT_SOURCE_PLAN.md','Yeni sürüm araştırma planı')]:
        index+='- ['+label+']('+file+')\n'
    index+='\nKalite etkisi değerlendirilmedi, özgün 2010 oyun bağımsız tam oynanışla denetlenmedi.\n'
    doc('README.md',index)
    for w in data['works']:
        s='# '+w['title']+' — v0.11 kaynaklı olaylar\n\n'
        s+='Sadece oyun veya DLC kapsamındaki olaylar; yeniden yayımlanan rehberler özgün 2010 sürümünün doğrudan kayıtları değildir.\n\n'
        for e in data['story_events']:
            if e['work_id']!=w['work_id']:continue
            s+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
            s+=e['observation_tr']+'\n\n'
            s+='**Kaynak:** '+', '.join(e['source_ids'])+'; **tip:** '+e['event_kind']
            s+='; **zaman:** '+e['narrative_time_type']+'; **güven:** '+e['evidence_strength']+'\n\n'
        doc('works/'+w['work_id'].lower()+'.md',s)
    s='# BioShock 2 + Minerva’s Den — 18 mekanik adayı\n\n'
    s+='Telif koruması: soyut kavramlar aktarılabilir; özgün oyun isimlerini/olaylarını/sahnelerini yeni hikâyeye kopyalamayın.\n\n'
    for m in data['mechanics']:
        s+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        s+='**Gözlem:** '+m['observed_tr']+'\n\n'
        s+='**Soyutlama:** '+m['abstraction_tr']+'\n\n'
        s+='**Kısıt:** '+m['guardrail_tr']+'\n\n'
        s+='**Olaylar:** '+', '.join(m['event_anchors'])+'; **önceki mekanikler:** '+', '.join(m['prior_mechanic_ids'])+'\n\n'
    doc('MECHANICS.md',s)
    s='# Birbirinden ayrı seçim ve final sonuçları\n\n'
    s+='Delta eylemleri Eleanor’a örnek olur ancak Eleanor bağımsız öznedir. Little Sister kararı, yetişkin karakterleri sağ bırakma ve farklı final parçaları tek puanla birleştirilmez.\n\n'
    for x in data['choice_axes']:
        s+='- '+x['axis_id']+': '+x['subject_type']+' — '+', '.join(x['options'])+'; etki '+', '.join(x['later_impacts'])+'\n'
    s+='\n## Birbirini dışlayan ana epilog kategorileri\n\n'
    for x in data['ending_outcomes']:
        s+='- '+x['outcome_id']+': '+x['outcome_type']+'; '+x['conditions_tr']+'\n'
    s+='\nOyun finalindeki daha küçük kombinasyonlar bu ilk araştırmada doğrudan oynanıp sayılmadı.\n'
    doc('CHOICES_AND_OUTCOMES.md',s)
    s='# Kim ne biliyor? Porter / Sigma / Thinker / Delta / Eleanor\n\n'
    for x in data['knowledge_states']:
        s+='## '+x['knowledge_id']+' — '+x['subject']+'\n\n'
        s+='**Ön kabul:** '+x['initial_claim_tr']+'\n\n'
        s+='**Dünya gerçekliği:** '+x['actual_world_rule']+'\n\n'
        s+='**Olay zamanı:** '+x['setup_event']+' → '+x['correction_event']+'\n\n'
    doc('KNOWLEDGE_AND_IDENTITY.md',s)
    s='# Kalıcı nesne, kişi ve kimlik durumları\n\n'
    for x in data['object_states']:
        s+='- '+x['object_id']+' — '+x['title']+'; eser '+x['work_id']+'; '+x['state_rule']
        s+='; kanıt olayları '+', '.join(x['event_refs'])+'\n'
    doc('OBJECT_STATE.md',s)
    s='# Ayrı zaman / fiziksel / yorum bağlantıları\n\n'
    s+='**Kronoloji:** BioShock 2 oyun prologu 1958; birinci BioShock 1960; Delta ana hikâyesi 1968. '
    s+='Minerva’s Den aynı genel Rapture sonrası dönemde geçen ayrı hikâye; ana oyuna göre kesin gün/saat ve aynı oyun oturumu kronolojisi doğrulanmadı.\n\n'
    for x in data['narrative_links']:
        s+='- '+x['from_event_id']+' → '+x['to_event_id']+': '+x['relation']+'; '+x['kind']+'; çıkarım='+str(x['inference'])+'\n'
    s+='\n## Önceki BioShock 2007 kavram/olay bağlantıları\n\n'
    for x in data['prior_bioshock_links']:
        s+='- '+x['from_prior_event_id']+' → '+x['to_new_event_id']+'; '+x['relation']+'\n'
    doc('CHRONOLOGY.md',s)
    s='# Kaynak sicili / güven türü\n\n'
    s+='2K ve Xbox resmi açıklamaları eser/öykü kapsamı; Prima lisanslı rehberi seçime bağlı sonlar; GameFAQs rehberi olay ayrıntıları ve yerel mekanikler içindir. '
    s+='Wikipedia olay örgüsü yalnız düşük güvenli tersine yorumlar için kullanıldı.\n\n'
    for x in data['sources']:
        s+='- **'+x['source_id']+'** — ['+x['source_kind']+']('+x['url']+'); düzey '+x['evidence_tier']+'; '+x['coverage']+'\n'
    doc('SOURCES.md',s)
    s='# Sürüm, kurmaca ve fiziksel süreklilik sınırları\n\n'
    for i,x in enumerate(data['continuity_firewall'],1):s+=str(i)+'. '+x+'\n'
    s+='\n## Editoryal belirsizlikler\n\n'
    for x in data['editorial_boundaries']:
        s+='- '+x['boundary_id']+' — '+x['type']+': '+x['rule_tr']+'\n'
    doc('CONTINUITY_FIREWALL.md',s)
    m={'schema_version':data['schema_version'],'research_cutoff_date':data['research_cutoff_date'],
       'source_file':str(SRC.relative_to(ROOT)),
       'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
       'counts':{k:len(tables[k]) for k in TABLES},
       'quality_effect':'not_evaluated','original_gameplay_replayed_and_audited':False,
       'story_quality_trials':0,'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return m
if __name__=='__main__':
    print(json.dumps(build(),ensure_ascii=False,indent=2))
