#!/usr/bin/env python3
"""Disposable NOVA v0.13 SQLite foreign-key graph; no external or production database."""
import json,sqlite3,sys
from pathlib import Path
from validate_burial_at_sea import ROOT,BASE,rows,validate
def build(path=ROOT/'.nova-cache/nova-burial-at-sea-v013.sqlite'):
 gate=validate()
 if gate['status']!='PASS':raise ValueError('invalid research source: '+repr(gate['errors']))
 out=Path(path);out.parent.mkdir(parents=True,exist_ok=True);tmp=out.with_suffix('.building.sqlite')
 if tmp.exists():tmp.unlink()
 db=sqlite3.connect(tmp)
 db.execute('PRAGMA foreign_keys=ON')
 db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE knowledge(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),setup TEXT NOT NULL REFERENCES events(id),reveal TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE event_links(id INTEGER PRIMARY KEY,from_id TEXT NOT NULL REFERENCES events(id),to_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE previous_events(id TEXT PRIMARY KEY);
CREATE TABLE cross_game(id INTEGER PRIMARY KEY,new_id TEXT NOT NULL REFERENCES events(id),previous_id TEXT NOT NULL REFERENCES previous_events(id),body TEXT NOT NULL);
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE prior_links(id INTEGER PRIMARY KEY,new_id TEXT NOT NULL REFERENCES mechanics(id),old_id TEXT NOT NULL REFERENCES previous_mechanics(id),body TEXT NOT NULL);
CREATE TABLE boundaries(id TEXT PRIMARY KEY,body TEXT NOT NULL);
""")
 ser=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False)
 for x in rows('works'):db.execute('INSERT INTO works VALUES (?,?)',(x['work_id'],ser(x)))
 for x in rows('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(x['source_id'],ser(x)))
 for x in rows('story_events'):db.execute('INSERT INTO events VALUES (?,?,?)',(x['event_id'],x['work_id'],ser(x)))
 for x in rows('knowledge_states'):db.execute('INSERT INTO knowledge VALUES (?,?,?,?,?)',(x['state_id'],x['work_id'],x['setup_event_id'],x['reveal_event_id'],ser(x)))
 for x in rows('narrative_links'):db.execute('INSERT INTO event_links(from_id,to_id,body) VALUES (?,?,?)',(x['from_event_id'],x['to_event_id'],ser(x)))
 for x in rows('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(x['mechanic_id'],ser(x)))
 for x in rows('mechanic_evidence'):
  db.execute('INSERT INTO evidence VALUES (?,?,?,?)',(x['evidence_id'],x['mechanic_id'],x['event_id'],ser(x)))
  for sid in x['source_ids']:db.execute('INSERT INTO evidence_sources VALUES (?,?)',(x['evidence_id'],sid))
 for path in ('v0.10/source_records/bioshock_2007.json','v0.12/source_records/bioshock_infinite_2013.json'):
  for x in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['story_events']:
   db.execute('INSERT INTO previous_events VALUES (?)',(x['event_id'],))
 for x in rows('cross_game_links'):
  db.execute('INSERT INTO cross_game(new_id,previous_id,body) VALUES (?,?,?)',(x['from_event_id'],x['prior_event_id'],ser(x)))
 for path in ('v0.3/source_records/prince_mechanics.json','v0.4/source_records/prototype_2009.json',
    'v0.5/source_records/tomb_raider_survivor.json','v0.6/source_records/tomb_raider_classic.json',
    'v0.7/source_records/tomb_raider_lau.json','v0.8/source_records/prototype2_2012.json',
    'v0.9/source_records/prototype_comic_bridge.json','v0.10/source_records/bioshock_2007.json',
    'v0.11/source_records/bioshock2_minerva_2010.json','v0.12/source_records/bioshock_infinite_2013.json'):
  for x in json.loads((ROOT/'data/nova'/path).read_text(encoding='utf8'))['mechanics']:
   db.execute('INSERT INTO previous_mechanics VALUES (?)',(x['mechanic_id'],))
 for x in rows('prior_mechanic_links'):
  db.execute('INSERT INTO prior_links(new_id,old_id,body) VALUES (?,?,?)',(x['mechanic_id'],x['prior_mechanic_id'],ser(x)))
 for x in rows('editorial_boundaries'):db.execute('INSERT INTO boundaries VALUES (?,?)',(x['id'],ser(x)))
 violations=db.execute('PRAGMA foreign_key_check').fetchall()
 if violations:raise ValueError(repr(violations))
 expected={'works':2,'sources':14,'events':28,'knowledge':10,'event_links':15,
   'mechanics':16,'evidence':43,'previous_events':56,'cross_game':8,
   'previous_mechanics':169,'prior_links':32,'boundaries':16}
 counts={}
 for t,n in expected.items():
  counts[t]=db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]
  if counts[t]!=n:raise ValueError(f'{t}: expected {n}, actual {counts[t]}')
 counts['evidence_sources']=db.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
 db.commit();db.close();tmp.replace(out)
 return {'status':'PASS','path':str(out),'counts':counts,'foreign_key_violations':0,
  'story_quality_trials':0,'paid_calls':0,'prod_changed':False}
if __name__=='__main__':
 try:result=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-burial-at-sea-v013.sqlite')
 except Exception as e:result={'status':'FAIL','fatal':repr(e)}
 print(json.dumps(result,ensure_ascii=False,indent=2))
 sys.exit(0 if result['status']=='PASS' else 1)
