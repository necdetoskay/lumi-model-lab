#!/usr/bin/env python3
"""Disposable NOVA v0.5 research SQLite index; never touches production DB."""
import json,sqlite3,sys
from pathlib import Path
from validate_tomb_raider import ROOT,BASE,read,validate,EXPECTED
def build(dest=ROOT/'.nova-cache/nova-tomb-raider-survivor-v05.sqlite'):
    gate=validate()
    if gate['status']!='PASS':raise ValueError('Research source validation failed: '+str(gate['errors']))
    dest=Path(dest)
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,raw TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,raw TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),raw TEXT NOT NULL);
CREATE TABLE states(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),event_id TEXT NOT NULL REFERENCES events(id),raw TEXT NOT NULL);
CREATE TABLE game_links(id INTEGER PRIMARY KEY,from_id TEXT NOT NULL REFERENCES events(id),to_id TEXT NOT NULL REFERENCES events(id),raw TEXT NOT NULL);
CREATE TABLE releases(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),raw TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,raw TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),raw TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE prior_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE prior_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),prior_mechanic_id TEXT NOT NULL REFERENCES prior_mechanics(id),raw TEXT NOT NULL);
""")
    def raw(x):return json.dumps(x,ensure_ascii=False,sort_keys=True)
    for x in read('works'):db.execute('INSERT INTO works VALUES (?,?)',(x['work_id'],raw(x)))
    for x in read('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(x['source_id'],raw(x)))
    for x in read('story_events'):db.execute('INSERT INTO events VALUES (?,?,?)',(x['event_id'],x['work_id'],raw(x)))
    for x in read('character_states'):db.execute('INSERT INTO states VALUES (?,?,?,?)',(x['state_id'],x['work_id'],x['anchor_event_id'],raw(x)))
    for x in read('cross_work_links'):db.execute('INSERT INTO game_links(from_id,to_id,raw) VALUES (?,?,?)',(x['from_event_id'],x['to_event_id'],raw(x)))
    for x in read('supplementary_releases'):db.execute('INSERT INTO releases VALUES (?,?,?)',(x['release_id'],x['work_id'],raw(x)))
    for x in read('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(x['mechanic_id'],raw(x)))
    for x in read('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES (?,?,?,?)',(x['evidence_id'],x['mechanic_id'],x['event_id'],raw(x)))
        for sid in x['source_ids']:db.execute('INSERT INTO evidence_sources VALUES (?,?)',(x['evidence_id'],sid))
    for ver,path in (('0.3',ROOT/'data/nova/v0.3/source_records/prince_mechanics.json'),
                     ('0.4',ROOT/'data/nova/v0.4/source_records/prototype_2009.json')):
        records=json.loads(path.read_text(encoding='utf8'))
        for x in records['mechanics']:
            db.execute('INSERT INTO prior_mechanics VALUES (?)',(x['mechanic_id'],))
    for x in read('prior_links'):
        db.execute('INSERT INTO prior_links(mechanic_id,prior_mechanic_id,raw) VALUES (?,?,?)',(x['mechanic_id'],x['prior_mechanic_id'],raw(x)))
    fail=db.execute('PRAGMA foreign_key_check').fetchall()
    tables=('works','sources','events','states','game_links','releases','mechanics','evidence','evidence_sources','prior_mechanics','prior_links')
    counts={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in tables}
    expected={'works':3,'sources':18,'events':37,'states':9,'game_links':10,
              'releases':3,'mechanics':18,'evidence':59,'prior_mechanics':34,'prior_links':46}
    for k,n in expected.items():
        if counts[k]!=n:raise ValueError('Table '+k+' '+str(counts[k])+' != '+str(n))
    if fail:raise ValueError('Foreign key violations: '+str(fail))
    db.commit()
    db.close()
    tmp.replace(dest)
    return {'status':'PASS','index_path':str(dest),'counts':counts,
            'foreign_key_violations':0,'story_quality_trials':0,'paid_calls':0,'production_modified':False}
if __name__=='__main__':
    try:result=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-tomb-raider-survivor-v05.sqlite')
    except Exception as exc:result={'status':'FAIL','fatal':repr(exc)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)
