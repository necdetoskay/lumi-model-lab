#!/usr/bin/env python3
"""NOVA v0.12 disposable SQLite graph index; foreign-key audit, no production DB."""
import json,sqlite3,sys
from pathlib import Path
from validate_bioshock_infinite import ROOT,BASE,rows,validate
def build(path=ROOT/'.nova-cache/nova-bioshock-infinite-v012.sqlite'):
 check=validate()
 if check['status']!='PASS':raise ValueError('invalid source corpus '+str(check.get('errors')))
 dst=Path(path);dst.parent.mkdir(parents=True,exist_ok=True)
 tmp=dst.with_suffix('.building.sqlite')
 if tmp.exists():tmp.unlink()
 conn=sqlite3.connect(tmp);conn.execute('PRAGMA foreign_keys=ON')
 conn.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE worlds(id TEXT PRIMARY KEY,first_event TEXT NOT NULL REFERENCES events(id),last_event TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE identities(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE identity_evidence(identity_id TEXT NOT NULL REFERENCES identities(id),event_id TEXT NOT NULL REFERENCES events(id),PRIMARY KEY(identity_id,event_id));
CREATE TABLE knowledge(id TEXT PRIMARY KEY,setup_id TEXT NOT NULL REFERENCES events(id),reveal_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE choices(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE choice_evidence(choice_id TEXT NOT NULL REFERENCES choices(id),event_id TEXT NOT NULL REFERENCES events(id),PRIMARY KEY(choice_id,event_id));
CREATE TABLE event_links(id INTEGER PRIMARY KEY,from_id TEXT NOT NULL REFERENCES events(id),to_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE previous_events(id TEXT PRIMARY KEY);
CREATE TABLE prior_bioshock_links(id INTEGER PRIMARY KEY,new_id TEXT NOT NULL REFERENCES events(id),previous_id TEXT NOT NULL REFERENCES previous_events(id),body TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE mechanic_evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES mechanic_evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE mechanic_prior_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),previous_id TEXT NOT NULL REFERENCES previous_mechanics(id),body TEXT NOT NULL);
CREATE TABLE boundaries(id TEXT PRIMARY KEY,body TEXT NOT NULL);
""")
 ser=lambda v:json.dumps(v,sort_keys=True,ensure_ascii=False)
 for v in rows('works'):conn.execute('INSERT INTO works VALUES (?,?)',(v['work_id'],ser(v)))
 for v in rows('sources'):conn.execute('INSERT INTO sources VALUES (?,?)',(v['source_id'],ser(v)))
 for v in rows('story_events'):conn.execute('INSERT INTO events VALUES (?,?,?)',(v['event_id'],'BI-2013',ser(v)))
 for v in rows('world_variants'):
  conn.execute('INSERT INTO worlds VALUES (?,?,?,?)',(v['world_id'],v['first_event'],v['last_event'],ser(v)))
 for v in rows('identity_variants'):
  conn.execute('INSERT INTO identities VALUES (?,?)',(v['identity_id'],ser(v)))
  for eid in v['event_refs']:conn.execute('INSERT INTO identity_evidence VALUES (?,?)',(v['identity_id'],eid))
 for v in rows('knowledge_states'):
  conn.execute('INSERT INTO knowledge VALUES (?,?,?,?)',(v['knowledge_id'],v['setup_event_id'],v['revealed_event_id'],ser(v)))
 for v in rows('player_choice_scopes'):
  conn.execute('INSERT INTO choices VALUES (?,?)',(v['choice_id'],ser(v)))
  for eid in v['event_ids']:conn.execute('INSERT INTO choice_evidence VALUES (?,?)',(v['choice_id'],eid))
 for v in rows('narrative_links'):
  conn.execute('INSERT INTO event_links(from_id,to_id,body) VALUES (?,?,?)',(v['from_event_id'],v['to_event_id'],ser(v)))
 for path in (
  'data/nova/v0.10/source_records/bioshock_2007.json',
  'data/nova/v0.11/source_records/bioshock2_minerva_2010.json'):
  for v in json.loads((ROOT/path).read_text(encoding='utf8'))['story_events']:
   conn.execute('INSERT INTO previous_events VALUES (?)',(v['event_id'],))
 for v in rows('prior_bioshock_links'):
  conn.execute('INSERT INTO prior_bioshock_links(new_id,previous_id,body) VALUES (?,?,?)',(v['from_new_event_id'],v['to_prior_event_id'],ser(v)))
 for path in (
  'v0.3/source_records/prince_mechanics.json',
  'v0.4/source_records/prototype_2009.json',
  'v0.5/source_records/tomb_raider_survivor.json',
  'v0.6/source_records/tomb_raider_classic.json',
  'v0.7/source_records/tomb_raider_lau.json',
  'v0.8/source_records/prototype2_2012.json',
  'v0.9/source_records/prototype_comic_bridge.json',
  'v0.10/source_records/bioshock_2007.json',
  'v0.11/source_records/bioshock2_minerva_2010.json'):
  for v in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['mechanics']:
   conn.execute('INSERT INTO previous_mechanics VALUES (?)',(v['mechanic_id'],))
 for v in rows('mechanics'):
  conn.execute('INSERT INTO mechanics VALUES (?,?)',(v['mechanic_id'],ser(v)))
 for v in rows('mechanic_evidence'):
  conn.execute('INSERT INTO mechanic_evidence VALUES (?,?,?,?)',(v['evidence_id'],v['mechanic_id'],v['event_id'],ser(v)))
  for sid in v['source_ids']:conn.execute('INSERT INTO evidence_sources VALUES (?,?)',(v['evidence_id'],sid))
 for v in rows('prior_mechanic_links'):
  conn.execute('INSERT INTO mechanic_prior_links(mechanic_id,previous_id,body) VALUES (?,?,?)',
    (v['mechanic_id'],v['prior_mechanic_id'],ser(v)))
 for v in rows('editorial_boundaries'):
  conn.execute('INSERT INTO boundaries VALUES (?,?)',(v['boundary_id'],ser(v)))
 violations=conn.execute('PRAGMA foreign_key_check').fetchall()
 if violations:raise ValueError('FK failures: '+repr(violations))
 expected={'works':1,'sources':17,'events':33,'worlds':7,'identities':10,
  'knowledge':9,'choices':6,'event_links':19,'previous_events':53,
  'prior_bioshock_links':8,'mechanics':20,'mechanic_evidence':60,
  'previous_mechanics':149,'mechanic_prior_links':41,'boundaries':10}
 counts={}
 for table,n in expected.items():
  counts[table]=conn.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
  if counts[table]!=n:raise ValueError(f'{table} count {counts[table]} expected {n}')
 counts['identity_evidence']=conn.execute('SELECT COUNT(*) FROM identity_evidence').fetchone()[0]
 counts['choice_evidence']=conn.execute('SELECT COUNT(*) FROM choice_evidence').fetchone()[0]
 counts['evidence_sources']=conn.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
 conn.commit();conn.close();tmp.replace(dst)
 return {'status':'PASS','file':str(dst),'counts':counts,'foreign_key_violations':0,
   'story_quality_trials':0,'paid_model_calls':0,'lumi_production_modified':False}
if __name__=='__main__':
 try:result=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-bioshock-infinite-v012.sqlite')
 except Exception as ex:result={'status':'FAIL','fatal':repr(ex)}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 sys.exit(0 if result['status']=='PASS' else 1)
