#!/usr/bin/env python3
"""NOVA v0.13 research corpus: 2013/2014 Burial at Sea episodes, separate works."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.13'
SRC=BASE/'source_records/burial_at_sea.json'
DOC=ROOT/'docs/research/burial-at-sea'
TABLES=('works','sources','story_events','knowledge_states','mechanics',
        'narrative_links','cross_game_links','editorial_boundaries',
        'mechanic_evidence','prior_mechanic_links')
def write_doc(name,txt):
 f=DOC/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(txt.rstrip()+'\n',encoding='utf8')
def build():
 c=json.loads(SRC.read_text(encoding='utf8'))
 events={e['event_id']:e for e in c['story_events']}
 evidence=[];prior=[]
 for m in c['mechanics']:
  for id in m['event_anchors']:
   e=events[id]
   evidence.append({'evidence_id':m['mechanic_id']+':'+id,'mechanic_id':m['mechanic_id'],
    'event_id':id,'work_id':e['work_id'],'source_ids':e['source_ids'],'evidence_tier':e['evidence_tier'],
    'quality_effect':'not_evaluated','lumi_canon':False})
  for old in m['prior_mechanic_ids']:
   prior.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':old,
    'relation':'conceptual_comparison_not_equivalence','quality_effect':'not_evaluated'})
 t={k:c[k] for k in TABLES if k in c}
 t['mechanic_evidence']=evidence;t['prior_mechanic_links']=prior
 for key in TABLES:
  (BASE/(key+'.jsonl')).write_text(''.join(json.dumps(x,sort_keys=True,ensure_ascii=False)+'\n' for x in t[key]),encoding='utf8')
 for key in ('quality_evaluations','lumi_usage_history'):
  (BASE/(key+'.jsonl')).write_text('',encoding='utf8')
 index='# NOVA v0.13 — Burial at Sea Episode One / Episode Two\n\n'
 index+='Orijinal iki DLC ayrı eser; 2013/2014. İlk kaynaklı araştırma; tam oyun görüntüsü bağımsız denetlenmedi.\n\n'
 for k in TABLES:index+='- '+k+': **'+str(len(t[k]))+'**\n'
 index+='\n## Okuma\n\n'
 for filename,title in [('WORKS.md','İki DLC ve kronoloji'),('EVENTS.md','28 olay'),
  ('MECHANICS.md','16 mekanik çıkarımı'),('KNOWLEDGE.md','Kimlik ve bilgi ayrımı'),
  ('CROSS_GAME.md','Önceki oyunlarla sınırlı bağlantılar'),
  ('SOURCES.md','14 kaynak'),('CONTINUITY.md','16 koruma sınırı'),
  ('VALIDATION_REPORT.md','Çevrimdışı test kanıtı'),('NEXT_SOURCE_PLAN.md','Sonraki araştırma')]:
  index+='- ['+title+']('+filename+')\n'
 write_doc('README.md',index)
 s='# İki ayrı DLC\n\n'
 for w in c['works']:
  s+='## '+w['work_id']+' — '+w['title']+'\n\n'
  s+='Çıkış: '+w['release_date']+'; oynanan karakter: '+w['playable_character']+'; kayıtlı tür: '+w['format']+'\n\n'
 write_doc('WORKS.md',s)
 s='# Kaynaklı olaylar\n\n'
 for e in c['story_events']:
  s+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'+e['observation_tr']+'\n\n'
  s+='**Eser/dünya:** '+e['work_id']+'/'+e['world_scope']+'; **kanıt:** '+e['evidence_tier']+'; **kaynaklar:** '+', '.join(e['source_ids'])+'\n\n'
 write_doc('EVENTS.md',s)
 s='# NOVA v0.13 — 16 soyut mekanik adayı\n\n'
 s+='Kalite artışının kanıtı değildir; ticari oyunun sahne/diyalog/benzersiz ifadesi kopyalanamaz.\n\n'
 for m in c['mechanics']:
  s+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
  s+='**Çıkarım:** '+m['abstraction_tr']+'\n\n**Koruma:** '+m['guardrail_tr']+'\n\n'
  s+='**Olaylar:** '+', '.join(m['event_anchors'])+'; **önceki kavramlar:** '+', '.join(m['prior_mechanic_ids'])+'\n\n'
 write_doc('MECHANICS.md',s)
 s='# Kimlik, bilgi ve fiziksel durum ayrımları\n\n'
 for x in c['knowledge_states']:
  s+='- '+x['state_id']+' ('+x['work_id']+'): '+x['initial_claim']+' ⇒ '+x['actual_rule']+'; '+x['setup_event_id']+' → '+x['reveal_event_id']+'\n'
 write_doc('KNOWLEDGE.md',s)
 s='# Bölümler ve eski BioShock oyunları arasındaki temkinli bağlantılar\n\n'
 for e in c['narrative_links']:
  s+='- '+e['from_event_id']+' → '+e['to_event_id']+': '+e['relation']+'; '+e['kind']+'; yorum='+str(e['inference'])+'\n'
 s+='\n## Önceki oyun olaylarıyla karşılaştırma\n\n'
 for e in c['cross_game_links']:
  s+='- '+e['from_event_id']+' → '+e['prior_event_id']+': '+e['relation']+'; '+e['evidence_link_type']+'\n'
 write_doc('CROSS_GAME.md',s)
 s='# Kaynak sicili\n\n'
 for e in c['sources']:
  s+='- '+e['source_id']+' ['+e['source_kind']+']('+e['url']+'); '+e['evidence_tier']+' — '+e['supports']+'\n'
 write_doc('SOURCES.md',s)
 s='# Editoryal süreklilik ve telif korumaları\n\n'
 for e in c['editorial_boundaries']:s+='- '+e['id']+': '+e['rule']+'\n'
 write_doc('CONTINUITY.md',s)
 manifest={'schema_version':c['schema_version'],'research_date':c['research_date'],
  'source_file':str(SRC.relative_to(ROOT)),
  'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
  'counts':{k:len(t[k]) for k in TABLES},
  'firsthand_original_gameplay_audited':False,'quality_effect':'not_evaluated',
  'paid_model_calls':0,'story_quality_trials':0,'lumi_production_modified':False}
 (BASE/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 return manifest
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
