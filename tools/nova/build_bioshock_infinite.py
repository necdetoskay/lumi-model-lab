#!/usr/bin/env python3
"""Deterministic v0.12 research build: BioShock Infinite 2013 base game only."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'data/nova/v0.12'
SRC=BASE/'source_records/bioshock_infinite_2013.json'
DOCS=ROOT/'docs/research/bioshock-infinite'
TABLES=('works','sources','story_events','world_variants','identity_variants',
 'knowledge_states','player_choice_scopes','narrative_links','mechanics',
 'prior_bioshock_links','editorial_boundaries','mechanic_evidence','prior_mechanic_links')
def doc(path,text):
 f=DOCS/path
 f.parent.mkdir(parents=True,exist_ok=True)
 f.write_text(text.rstrip()+'\n',encoding='utf8')
def build():
 c=json.loads(SRC.read_text(encoding='utf8'))
 ev={e['event_id']:e for e in c['story_events']}
 evidence=[];prior=[]
 for m in c['mechanics']:
  for eid in m['event_anchors']:
   e=ev[eid]
   evidence.append({'evidence_id':m['mechanic_id']+':'+eid,'mechanic_id':m['mechanic_id'],
     'event_id':eid,'work_id':'BI-2013','source_ids':e['source_ids'],
     'event_kind':e['event_kind'],'world_scope':e['world_scope'],
     'evidence_strength':e['evidence_strength'],'quality_effect':'not_evaluated','lumi_canon':False})
  for previous in m['related_prior_mechanic_ids']:
   prior.append({'mechanic_id':m['mechanic_id'],'prior_mechanic_id':previous,
       'relation':'conceptually_related_not_equivalent','quality_effect':'not_evaluated'})
 rows={k:c[k] for k in TABLES if k in c}
 rows['mechanic_evidence']=evidence;rows['prior_mechanic_links']=prior
 for name in TABLES:
  (BASE/(name+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n' for x in rows[name]),encoding='utf8')
 for name in ('quality_evaluations','lumi_usage_history'):
  (BASE/(name+'.jsonl')).write_text('',encoding='utf8')
 intro='# NOVA v0.12 — BioShock Infinite (2013) kaynak paketi\n\n'
 intro+='Sadece orijinal ana oyun; **Burial at Sea ve Clash in the Clouds hariç**. '
 intro+='Bağımsız tam oyun görüntüsü denetimi yapılmadı; yazılı rehber, resmî ürün bilgileri ve 2013 yaratıcısının röportajı.\n\n'
 for k in TABLES:intro+='- '+k+': **'+str(len(rows[k]))+'**\n'
 intro+='\n## Belgeler\n\n'
 for n,label in [
  ('EVENTS.md','33 olay ve dünyaları'),('MECHANICS.md','20 mekanik hipotezi'),
  ('WORLD_TIMELINES.md','A/B/C dünyaları ve geçişleri'),
  ('IDENTITY_AND_KNOWLEDGE.md','Booker–Comstock / Anna–Elizabeth / Luteceler'),
  ('PLAYER_CHOICES.md','Oyuncu seçimleri ile zorunlu son'),
  ('SOURCES.md','17 kaynak ve güven düzeyi'),
  ('CONTINUITY.md','Süreklilik, DLC ve telif sınırları'),
  ('VALIDATION_REPORT.md','Gerçek doğrulama kanıtı'),
  ('NEXT_SOURCE_PLAN.md','Sıradaki kaynak planı')]:
  intro+='- ['+label+']('+n+')\n'
 intro+='\nKalite ölçülmedi; ücretli model veya hikâye üretimi yok; LUMI production/Harness değişmedi.\n'
 doc('README.md',intro)
 s='# BioShock Infinite — 33 ilk kaynaklı olay kaydı\n\n'
 for e in c['story_events']:
  s+='## '+e['event_id']+' — '+e['label_tr']+'\n\n'+e['observation_tr']+'\n\n'
  s+='**Dünya:** '+e['world_scope']+'; **tür:** '+e['event_kind']+'; **zaman:** '+e['narrative_time']+'\n\n'
  s+='**Kaynak:** '+', '.join(e['source_ids'])+'; **yorum:** '+str(e['claim_inference'])+'\n\n'
 doc('EVENTS.md',s)
 s='# BioShock Infinite — 20 özgün soyutlama adayı\n\n'
 s+='Hipotezler başka bir hikâyenin kalitesini ölçülmüş biçimde artırmış değildir.\n\n'
 for m in c['mechanics']:
  s+='## '+m['mechanic_id']+' — '+m['label_tr']+'\n\n'
  s+='**Gözlem:** '+m['observed_tr']+'\n\n**Genelleme:** '+m['abstraction_tr']
  s+='\n\n**Sınır:** '+m['guardrail_tr']+'\n\n'
  s+='**Kaynaklı olaylar:** '+', '.join(m['event_anchors'])+'; **önceki kavramlar:** '+', '.join(m['related_prior_mechanic_ids'])+'\n\n'
 doc('MECHANICS.md',s)
 s='# Ayrı dünya kayıtları ve geçişler\n\n'
 s+='Tek bir evren kronolojisi veya tek fiziksel Booker yoktur. Bir kişinin başka dünyada ölmesi, yaşayan varyantının ölümünü değiştirmez.\n\n'
 for w in c['world_variants']:
  s+='- **'+w['world_id']+' — '+w['scope']+'**: '+w['identity_description']+'; olay aralığı '+w['first_event']+'…'+w['last_event']+'\n'
 s+='\n## 19 yorumlanmış veya gözlenen olay bağı\n\n'
 for e in c['narrative_links']:
  s+='- '+e['from_event_id']+' → '+e['to_event_id']+': '+e['relation']+'; '+e['link_type']+'; yorum='+str(e['interpretive_link'])+'\n'
 doc('WORLD_TIMELINES.md',s)
 s='# Kimlik sürümleri ve bilgi erişimi\n\n'
 for i in c['identity_variants']:
  s+='- **'+i['identity_id']+'** '+i['display_name']+'; dünya '+i['scope']+'; kural '+i['identity_rule']+'; olaylar '+', '.join(i['event_refs'])+'\n'
 s+='\n## Karakterin inancı ile dünyanın kaydı\n\n'
 for x in c['knowledge_states']:
  s+='- '+x['knowledge_id']+' '+x['subject']+': ilk iddia='+x['initial_claim']+'; sınır='+x['actual_or_limited_truth']+'; olay '+x['setup_event_id']+' → '+x['revealed_event_id']+'\n'
 doc('IDENTITY_AND_KNOWLEDGE.md',s)
 s='# Oyuncu eylemi ≠ zorunlu sahne veya dünya tarihi\n\n'
 for x in c['player_choice_scopes']:
  s+='- '+x['choice_id']+': '+x['kind']+'; etki='+x['world_state_effect']+'; tür='+x['branch_type']+'; olay='+', '.join(x['event_ids'])+'\n'
 s+='\nKozmetik kolye ve çekiliş seçimleri ana finalin ayrı otomatik dalları değildir. Vaftiz ayrımı, 1912 sahnesinde oyuncuya verilen alternatif kullanıcı kararı değildir.\n'
 doc('PLAYER_CHOICES.md',s)
 s='# Kaynak sicili\n\n'
 s+='Dönemsel 2013 oynanış rehberleri ve retrospektif yaratıcı röportajı farklı türden kanıttır; ana oyunun tüm sahnelerini bağımsız tekrar oynama yapılmadı.\n\n'
 for x in c['sources']:
  s+='- **'+x['source_id']+'** ['+x['kind']+']('+x['url']+') — '+x['evidence_tier']+'; '+x['coverage']+'\n'
 doc('SOURCES.md',s)
 s='# Araştırma süreklilik/telif/kesinlik korumaları\n\n'
 for i,x in enumerate(c['continuity_firewall'],1):s+=str(i)+'. '+x+'\n'
 s+='\n## Editoryal belirsizlikler\n\n'
 for x in c['editorial_boundaries']:
  s+='- '+x['boundary_id']+': '+x['rule_tr']+'\n'
 doc('CONTINUITY.md',s)
 manifest={'schema_version':c['schema_version'],'research_cutoff_date':c['research_cutoff_date'],
   'source_file':str(SRC.relative_to(ROOT)),
   'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
   'counts':{k:len(rows[k]) for k in TABLES},
   'full_original_gameplay_independently_audited':False,
   'quality_effect':'not_evaluated','story_quality_trials':0,'new_paid_model_calls':0,
   'lumi_production_modified':False}
 (BASE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return manifest
if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
