#!/usr/bin/env python3
"""Disposable NOVA v0.8 SQLite FK audit; no production database or writes."""
import json,sqlite3,sys
from pathlib import Path
from validate_prototype2 import ROOT,BASE,rows,validate
def build(path=ROOT/'.nova-cache/nova-prototype2-v08.sqlite'):
    check=validate()
    if check['status']!='PASS':raise ValueError('Invalid source corpus: '+repr(check['errors']))
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE beliefs(id TEXT PRIMARY KEY,setup_event TEXT NOT NULL REFERENCES events(id),reveal_event TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE previous_events(id TEXT PRIMARY KEY);
CREATE TABLE cross_links(id INTEGER PRIMARY KEY,prev_event TEXT NOT NULL REFERENCES previous_events(id),new_event TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE prior_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),previous_id TEXT NOT NULL REFERENCES previous_mechanics(id),body TEXT NOT NULL);
CREATE TABLE editorial_boundaries(id TEXT PRIMARY KEY,body TEXT NOT NULL);
""")
    ser=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True)
    for r in rows('works'):db.execute('INSERT INTO works VALUES (?,?)',(r['work_id'],ser(r)))
    for r in rows('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(r['source_id'],ser(r)))
    for r in rows('story_events'):db.execute('INSERT INTO events VALUES (?,?,?)',(r['event_id'],'PROTOTYPE2-2012',ser(r)))
    for r in rows('belief_states'):db.execute('INSERT INTO beliefs VALUES (?,?,?,?)',
        (r['state_id'],r['setup_event_id'],r['reveal_event_id'],ser(r)))
    previous=json.loads((ROOT/'data/nova/v0.4/source_records/prototype_2009.json').read_text(encoding='utf8'))
    for r in previous['story_events']:db.execute('INSERT INTO previous_events VALUES (?)',(r['event_id'],))
    for r in rows('cross_game_links'):db.execute('INSERT INTO cross_links(prev_event,new_event,body) VALUES (?,?,?)',
        (r['from_prior_event_id'],r['to_event_id'],ser(r)))
    for r in rows('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(r['mechanic_id'],ser(r)))
    for r in rows('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES (?,?,?,?)',(r['evidence_id'],r['mechanic_id'],r['event_id'],ser(r)))
        for sid in r['source_ids']:db.execute('INSERT INTO evidence_sources VALUES (?,?)',(r['evidence_id'],sid))
    for f in [
      'data/nova/v0.3/source_records/prince_mechanics.json',
      'data/nova/v0.4/source_records/prototype_2009.json',
      'data/nova/v0.5/source_records/tomb_raider_survivor.json',
      'data/nova/v0.6/source_records/tomb_raider_classic.json',
      'data/nova/v0.7/source_records/tomb_raider_lau.json']:
        for m in json.loads((ROOT/f).read_text(encoding='utf8'))['mechanics']:
            db.execute('INSERT INTO previous_mechanics VALUES (?)',(m['mechanic_id'],))
    for r in rows('prior_links'):
        db.execute('INSERT INTO prior_links(mechanic_id,previous_id,body) VALUES (?,?,?)',
            (r['mechanic_id'],r['prior_mechanic_id'],ser(r)))
    for r in rows('editorial_boundaries'):db.execute('INSERT INTO editorial_boundaries VALUES (?,?)',(r['id'],ser(r)))
    violations=db.execute('PRAGMA foreign_key_check').fetchall()
    if violations:raise ValueError('FK violation '+repr(violations))
    expected={'works':1,'sources':11,'events':20,'beliefs':7,'previous_events':16,
      'cross_links':8,'mechanics':14,'evidence':42,'previous_mechanics':89,
      'prior_links':38,'editorial_boundaries':6}
    counts={}
    for table,n in expected.items():
        got=db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        counts[table]=got
        if got!=n:raise ValueError(f'{table} expected {n} got {got}')
    counts['evidence_sources']=db.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
    db.commit();db.close();tmp.replace(target)
    return {'status':'PASS','path':str(target),'counts':counts,'foreign_key_violations':0,
        'new_paid_calls':0,'story_quality_trials':0,'production_modified':False}
if __name__=='__main__':
    try:report=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-prototype2-v08.sqlite')
    except Exception as e:report={'status':'FAIL','fatal':repr(e)}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(0 if report['status']=='PASS' else 1)
