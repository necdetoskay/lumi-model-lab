#!/usr/bin/env python3
"""NOVA v0.9 offline three arcs / six parts / bibliographic provenance compiler."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.9'
SRC=BASE/'source_records/prototype_comic_bridge.json'
DOCS=ROOT/'docs/research/prototype-comics'
TABLES=('works','sources','issues','story_observations','unverified_candidate_claims',
        'prior_game_links','mechanics','mechanic_evidence','mechanic_prior_links')
def emit(name,records):
    (BASE/(name+'.jsonl')).write_text(
        ''.join(json.dumps(v,ensure_ascii=False,sort_keys=True)+'\n' for v in records),
        encoding='utf8')
def document(name,body):
    file=DOCS/name
    file.parent.mkdir(parents=True,exist_ok=True)
    file.write_text(body.rstrip()+'\n',encoding='utf8')
def build():
    c=json.loads(SRC.read_text(encoding='utf8'))
    observations={e['event_id']:e for e in c['story_observations']}
    evidence=[]
    links=[]
    for m in c['mechanics']:
        for aid in m['evidence_anchors']:
            e=observations[aid]
            evidence.append({'evidence_id':m['mechanic_id']+':'+aid,
                'mechanic_id':m['mechanic_id'],'observation_id':aid,
                'work_id':e['work_id'],'issue_id':
                  next(i['issue_id'] for i in c['issues'] if i['arc_id']==e['work_id'] and
                       i['part_number']==e['part_number']),
                'source_ids':e['source_ids'],'evidence_tier':e['evidence_tier'],
                'evidence_scope':'solicitation_paraphrase_not_panel_audit',
                'quality_effect':'not_evaluated','lumi_canon':False})
        for prev in m['related_prior_mechanic_ids']:
            links.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':prev,
              'relation':'related_concept_not_equivalent','quality_effect':'not_evaluated'})
    data={k:c[k] for k in TABLES if k in c}
    data['mechanic_evidence']=evidence
    data['mechanic_prior_links']=links
    for name in TABLES:emit(name,data[name])
    emit('quality_evaluations',[])
    emit('lumi_usage_history',[])
    intro='# NOVA v0.9 — Prototype 2 Dark Horse çizgi roman köprüsü\n\n'
    intro+='**Ayrım:** 3 ana hikâye → 6 dijital bölüm → 2012 tek toplama baskı (80 sayfa). '
    intro+='Tam çizgi roman sayfaları okunup bağımsız denetlenmedi. Olaylar yeniden yayımlanmış promosyon özetine dayanan, düşük güvenli ilk geçiştir.\n\n'
    intro+='## Sayımlar\n\n'
    for name in TABLES:intro+='- '+name+': **'+str(len(data[name]))+'**\n'
    intro+='\n## Araştırma belgeleri\n\n'
    for filename,title in [('WORKS_AND_ISSUES.md','Üç hikâye / altı bölüm / toplu basım'),
          ('OBSERVATIONS.md','On iki promo gözlemi'),
          ('MECHANICS.md','On iki hipotez niteliğinde mekanik'),
          ('PENDING_CLAIMS.md','Dört doğrulanmamış ayrıntı'),
          ('CROSS_GAME.md','İki oyunla süreklilik ve tema bağları'),
          ('SOURCES.md','Dokuz kaynak / erişim kısıtları'),
          ('FIREWALL.md','Kaynak, kanon ve telif sınırları'),
          ('VALIDATION_REPORT.md','Gerçek test kanıtları'),
          ('NEXT_SOURCE_PLAN.md','İleriki araştırma seçenekleri')]:
        intro+='- ['+title+']('+filename+')\n'
    intro+='\nYeni hikâye üretimi/kalite denemesi yoktur. LUMI kanonuna veya uygulamaya eklenmedi.\n'
    document('README.md',intro)
    z='# Prototype Comic: eserin sürüm ve medya modeli\n\n'
    for w in c['works']:
        z+='## '+w['work_id']+' — '+w['title']+'\n\n'
        z+='**Çizer:** '+w['illustrator']+'; **odak:** '+w['main_story_focus']+'\n\n'
        for x in c['issues']:
            if x['arc_id']==w['work_id']:
                z+='- '+x['issue_id']+' — Dijital bölüm '+str(x['digital_edition_issue_number'])+', hikâye kısmı '+str(x['part_number'])+'; gün: doğrulanmadı\n'
        z+='\n'
    z+='**Toplu basım:** '+c['collection']['title']+', 2012, ISBN '+c['collection']['isbn13']+', '+str(c['collection']['page_count'])+' sayfa. '
    z+='Altı dijital bölümü içerir; yedinci bağımsız hikâye değildir.\n'
    document('WORKS_AND_ISSUES.md',z)
    z='# Tanıtım metniyle sınırlı gözlemler\n\n'
    z+='Bu olaylar özgün çizgi roman sayfasından bağımsız doğrulanmış olaylar olarak kaydedilmez; kaynakların geçerli kapsamını aşma.\n\n'
    for e in c['story_observations']:
        z+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'
        z+=e['observed_public_summary_tr']+'\n\n'
        z+='**Yapıt:** '+e['work_id']+'; **bölüm:** '+str(e['part_number'])+'; **kaynaklar:** '+', '.join(e['source_ids'])+'\n\n'
        z+='**Sınır:** '+e['knowledge_scope']+'\n\n'
    document('OBSERVATIONS.md',z)
    z='# NOVA v0.9 — On iki anlatı mekanik adayı\n\n'
    for m in c['mechanics']:
        z+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
        z+='**Tanıtım gözlemi:** '+m['observed_tr']+'\n\n'
        z+='**Araştırma soyutlaması:** '+m['abstraction_tr']+'\n\n'
        z+='**Koruma kuralı:** '+m['guardrail_tr']+'\n\n'
        z+='**Olay dayanakları:** '+', '.join(m['evidence_anchors'])+'; **önceki mekanikler:** '+', '.join(m['related_prior_mechanic_ids'])+'\n\n'
    document('MECHANICS.md',z)
    z='# Panel kontrolü bekleyen ayrıntılar\n\n'
    z+='Aşağıdakiler yalnız ikincil/fan anlatılarında yer alıyor, NE kanonik olay NE mekanik kanıtıdır.\n\n'
    for x in c['unverified_candidate_claims']:
        z+='- '+x['candidate_id']+': '+x['claim_tr']+' Kaynak: '+', '.join(x['source_ids'])+'.\n'
    document('PENDING_CLAIMS.md',z)
    z='# 2009 / çizgi roman / 2012 oyun karşılaştırma bağı\n\n'
    for x in c['prior_game_links']:
        z+='- '+x['link_id']+': '+x['prior_event_id']+' ↔ '+x['target_work_id']+' — '+x['relation']+'; '+x['kind']+'; yorum='+str(x['inference'])+'\n'
    document('CROSS_GAME.md',z)
    z='# Kaynak sicili ve erişim sınırları\n\n'
    z+='Ocak 2012 yayıncı açıklaması üç odak konusunu; bibliyografi altı bölümü ve 80 sayfalık derlemeyi; '
    z+='Steam topluluk rehberi özgün yayıncıdan şu anda bağımsız doğrulanmayan bölüm tanıtımlarını sağlıyor.\n\n'
    for s in c['sources']:
        z+='- **'+s['source_id']+'** ['+s['source_kind']+']('+s['url']+'), güven='+s['evidence_tier']+', kapsam='+s['coverage']+'\n'
    document('SOURCES.md',z)
    document('FIREWALL.md','# Süreklilik ve epistemik sınırlar\n\n'+'\n'.join(
        str(i)+'. '+x for i,x in enumerate(c['firewall'],1)))
    m={'schema_version':c['schema_version'],'research_cutoff_date':c['research_cutoff_date'],
        'source_file':str(SRC.relative_to(ROOT)),
        'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
        'counts':{k:len(data[k]) for k in TABLES},'primary_comic_panels_examined':0,
        'quality_effect':'not_evaluated','story_quality_trials':0,
        'new_paid_model_calls':0,'lumi_production_modified':False}
    (BASE/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return m
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
