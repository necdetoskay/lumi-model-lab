#!/usr/bin/env python3
"""NOVA v0.11 disposable SQLite FK audit (strictly no production data)."""
import json,sqlite3,sys
from pathlib import Path
from validate_bioshock2 import ROOT,BASE,rows,validate
def build(target=ROOT/'.nova-cache/nova-bioshock2-minerva-v011.sqlite'):
    check=validate()
    if check['status']!='PASS':raise ValueError('source not valid: '+repr(check.get('errors')))
    destination=Path(target)
    destination.parent.mkdir(parents=True,exist_ok=True)
    tmp=destination.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    con=sqlite3.connect(tmp)
    con.execute('PRAGMA foreign_keys=ON')
    con.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE choices(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE choice_evidence(choice_id TEXT NOT NULL REFERENCES choices(id),event_id TEXT NOT NULL REFERENCES events(id),PRIMARY KEY(choice_id,event_id));
CREATE TABLE endings(id TEXT PRIMARY KEY,event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE knowledge(id TEXT PRIMARY KEY,setup_event TEXT NOT NULL REFERENCES events(id),reveal_event TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE event_links(id INTEGER PRIMARY KEY,from_id TEXT NOT NULL REFERENCES events(id),to_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE objects(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE object_evidence(object_id TEXT NOT NULL REFERENCES objects(id),event_id TEXT NOT NULL REFERENCES events(id),PRIMARY KEY(object_id,event_id));
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE previous_events(id TEXT PRIMARY KEY);
CREATE TABLE cross_game_links(id INTEGER PRIMARY KEY,previous_event_id TEXT NOT NULL REFERENCES previous_events(id),new_event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE previous_mechanic_links(id INTEGER PRIMARY KEY,new_mechanic_id TEXT NOT NULL REFERENCES mechanics(id),previous_mechanic_id TEXT NOT NULL REFERENCES previous_mechanics(id),body TEXT NOT NULL);
CREATE TABLE boundaries(id TEXT PRIMARY KEY,body TEXT NOT NULL);
""")
    ser=lambda row:json.dumps(row,ensure_ascii=False,sort_keys=True)
    for w in rows('works'):con.execute('INSERT INTO works VALUES (?,?)',(w['work_id'],ser(w)))
    for s in rows('sources'):con.execute('INSERT INTO sources VALUES (?,?)',(s['source_id'],ser(s)))
    for e in rows('story_events'):con.execute('INSERT INTO events VALUES (?,?,?)',(e['event_id'],e['work_id'],ser(e)))
    for x in rows('choice_axes'):
        con.execute('INSERT INTO choices VALUES (?,?)',(x['axis_id'],ser(x)))
        for id in x['evidence_event_ids']:con.execute('INSERT INTO choice_evidence VALUES (?,?)',(x['axis_id'],id))
    for x in rows('ending_outcomes'):con.execute('INSERT INTO endings VALUES (?,?,?)',(x['outcome_id'],x['event_ref'],ser(x)))
    for x in rows('knowledge_states'):con.execute('INSERT INTO knowledge VALUES (?,?,?,?)',(x['knowledge_id'],x['setup_event'],x['correction_event'],ser(x)))
    for x in rows('narrative_links'):con.execute('INSERT INTO event_links(from_id,to_id,body) VALUES (?,?,?)',(x['from_event_id'],x['to_event_id'],ser(x)))
    for x in rows('object_states'):
        con.execute('INSERT INTO objects VALUES (?,?,?)',(x['object_id'],x['work_id'],ser(x)))
        for id in x['event_refs']:con.execute('INSERT INTO object_evidence VALUES (?,?)',(x['object_id'],id))
    for x in rows('mechanics'):con.execute('INSERT INTO mechanics VALUES (?,?)',(x['mechanic_id'],ser(x)))
    for x in rows('mechanic_evidence'):
        con.execute('INSERT INTO evidence VALUES (?,?,?,?)',(x['evidence_id'],x['mechanic_id'],x['event_id'],ser(x)))
        for source in x['source_ids']:con.execute('INSERT INTO evidence_sources VALUES (?,?)',(x['evidence_id'],source))
    paths=[
     'data/nova/v0.3/source_records/prince_mechanics.json',
     'data/nova/v0.4/source_records/prototype_2009.json',
     'data/nova/v0.5/source_records/tomb_raider_survivor.json',
     'data/nova/v0.6/source_records/tomb_raider_classic.json',
     'data/nova/v0.7/source_records/tomb_raider_lau.json',
     'data/nova/v0.8/source_records/prototype2_2012.json',
     'data/nova/v0.9/source_records/prototype_comic_bridge.json',
     'data/nova/v0.10/source_records/bioshock_2007.json'
    ]
    for file in paths:
        prior=json.loads((ROOT/file).read_text(encoding='utf8'))
        for m in prior['mechanics']:con.execute('INSERT INTO previous_mechanics VALUES (?)',(m['mechanic_id'],))
        if file.endswith('bioshock_2007.json'):
            for ev in prior['story_events']:con.execute('INSERT INTO previous_events VALUES (?)',(ev['event_id'],))
    for x in rows('prior_bioshock_links'):
        con.execute('INSERT INTO cross_game_links(previous_event_id,new_event_id,body) VALUES (?,?,?)',(x['from_prior_event_id'],x['to_new_event_id'],ser(x)))
    for x in rows('mechanic_prior_links'):
        con.execute('INSERT INTO previous_mechanic_links(new_mechanic_id,previous_mechanic_id,body) VALUES (?,?,?)',(x['mechanic_id'],x['prior_mechanic_id'],ser(x)))
    for x in rows('editorial_boundaries'):con.execute('INSERT INTO boundaries VALUES (?,?)',(x['boundary_id'],ser(x)))
    violations=con.execute('PRAGMA foreign_key_check').fetchall()
    if violations:raise ValueError('foreign key violations '+repr(violations))
    expected={'works':2,'sources':19,'events':30,'choices':4,'choice_evidence':5,
      'endings':3,'knowledge':8,'event_links':16,'objects':6,'mechanics':18,'evidence':47,
      'previous_events':23,'cross_game_links':6,'previous_mechanics':131,
      'previous_mechanic_links':36,'boundaries':8}
    actual={}
    for table,count in expected.items():
        actual[table]=con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        if actual[table]!=count:raise ValueError(f'{table}: expected={count} actual={actual[table]}')
    actual['evidence_sources']=con.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
    actual['object_evidence']=con.execute('SELECT COUNT(*) FROM object_evidence').fetchone()[0]
    con.commit();con.close()
    tmp.replace(destination)
    return {'status':'PASS','path':str(destination),'counts':actual,
       'foreign_key_violations':0,'paid_model_calls':0,'story_quality_trials':0,
       'lumi_production_modified':False}
if __name__=='__main__':
    try:result=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-bioshock2-minerva-v011.sqlite')
    except Exception as err:result={'status':'FAIL','fatal':repr(err)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
