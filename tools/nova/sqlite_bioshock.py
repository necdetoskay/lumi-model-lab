#!/usr/bin/env python3
"""Build disposable, FK verified v0.10 research index (never production database)."""
import json,sqlite3,sys
from pathlib import Path
from validate_bioshock import ROOT,BASE,rows,validate
def build(path=ROOT/'.nova-cache/nova-bioshock-v010.sqlite'):
    gate=validate()
    if gate['status']!='PASS':raise ValueError('v0.10 corpus invalid: '+repr(gate['errors']))
    dst=Path(path);dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),kind TEXT NOT NULL,data TEXT NOT NULL);
CREATE TABLE knowledge(id TEXT PRIMARY KEY,setup_event TEXT NOT NULL REFERENCES events(id),reveal_event TEXT NOT NULL REFERENCES events(id),data TEXT NOT NULL);
CREATE TABLE event_links(id INTEGER PRIMARY KEY,source_id TEXT NOT NULL REFERENCES events(id),target_id TEXT NOT NULL REFERENCES events(id),data TEXT NOT NULL);
CREATE TABLE ending_variants(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),data TEXT NOT NULL);
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE prior_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),prior_id TEXT NOT NULL REFERENCES previous_mechanics(id),data TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),data TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE boundaries(id TEXT PRIMARY KEY,data TEXT NOT NULL);
""")
    ser=lambda o:json.dumps(o,ensure_ascii=False,sort_keys=True)
    for row in rows('works'):db.execute('INSERT INTO works VALUES (?,?)',(row['work_id'],ser(row)))
    for row in rows('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(row['source_id'],ser(row)))
    for row in rows('story_events'):db.execute('INSERT INTO events VALUES (?,?,?,?)',(row['event_id'],'BS2007',row['event_kind'],ser(row)))
    for row in rows('knowledge_states'):db.execute('INSERT INTO knowledge VALUES (?,?,?,?)',
      (row['state_id'],row['setup_event_id'],row['reveal_event_id'],ser(row)))
    for row in rows('narrative_links'):db.execute('INSERT INTO event_links(source_id,target_id,data) VALUES (?,?,?)',
      (row['from_event_id'],row['to_event_id'],ser(row)))
    for row in rows('ending_variants'):db.execute('INSERT INTO ending_variants VALUES (?,?,?)',
      (row['variant_id'],row['event_id'],ser(row)))
    for file in (
       'data/nova/v0.3/source_records/prince_mechanics.json',
       'data/nova/v0.4/source_records/prototype_2009.json',
       'data/nova/v0.5/source_records/tomb_raider_survivor.json',
       'data/nova/v0.6/source_records/tomb_raider_classic.json',
       'data/nova/v0.7/source_records/tomb_raider_lau.json',
       'data/nova/v0.8/source_records/prototype2_2012.json',
       'data/nova/v0.9/source_records/prototype_comic_bridge.json'):
        for row in json.loads((ROOT/file).read_text(encoding='utf8'))['mechanics']:
            db.execute('INSERT INTO previous_mechanics VALUES (?)',(row['mechanic_id'],))
    for row in rows('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(row['mechanic_id'],ser(row)))
    for row in rows('prior_mechanic_references'):
        db.execute('INSERT INTO prior_links(mechanic_id,prior_id,data) VALUES (?,?,?)',
          (row['mechanic_id'],row['prior_mechanic_id'],ser(row)))
    for row in rows('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES (?,?,?,?)',
          (row['evidence_id'],row['mechanic_id'],row['event_id'],ser(row)))
        for sid in row['source_ids']:
            db.execute('INSERT INTO evidence_sources VALUES (?,?)',(row['evidence_id'],sid))
    for row in rows('editorial_boundaries'):db.execute('INSERT INTO boundaries VALUES (?,?)',(row['id'],ser(row)))
    missing=db.execute('PRAGMA foreign_key_check').fetchall()
    if missing:raise ValueError('foreign_key_check: '+repr(missing))
    expected={'works':1,'sources':14,'events':23,'knowledge':5,'event_links':13,
       'ending_variants':2,'previous_mechanics':115,'mechanics':16,
       'prior_links':34,'evidence':48,'boundaries':6}
    count={}
    for name,n in expected.items():
        count[name]=db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
        if count[name]!=n:raise ValueError(f'{name} count {count[name]}, expected {n}')
    count['evidence_sources']=db.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
    db.commit();db.close();tmp.replace(dst)
    return {'status':'PASS','path':str(dst),'counts':count,'foreign_key_violations':0,
     'paid_model_calls':0,'story_quality_trials':0,'production_modified':False}
if __name__=='__main__':
    try:result=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-bioshock-v010.sqlite')
    except Exception as exc:result={'status':'FAIL','fatal':repr(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
