#!/usr/bin/env python3
"""Build disposable v0.7 research SQLite index; validate foreign keys offline."""
import json,sqlite3,sys
from pathlib import Path
from validate_tomb_raider_lau import ROOT,BASE,rows,validate
def build(target=ROOT/'.nova-cache/nova-tomb-raider-lau-v07.sqlite'):
    check=validate()
    if check['status']!='PASS':raise ValueError('source is not valid: '+repr(check.get('errors')))
    out=Path(target);out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE chronology(work_id TEXT PRIMARY KEY REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE event_links(id INTEGER PRIMARY KEY,from_id TEXT NOT NULL REFERENCES events(id),to_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE artifacts(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE artifact_evidence(artifact_id TEXT NOT NULL REFERENCES artifacts(id),event_id TEXT NOT NULL REFERENCES events(id),PRIMARY KEY(artifact_id,event_id));
CREATE TABLE classic_events(id TEXT PRIMARY KEY);
CREATE TABLE remake_links(id INTEGER PRIMARY KEY,lau_id TEXT NOT NULL REFERENCES events(id),classic_id TEXT NOT NULL REFERENCES classic_events(id),body TEXT NOT NULL);
CREATE TABLE boundaries(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),body TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE old_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE prior_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),old_mechanic_id TEXT NOT NULL REFERENCES old_mechanics(id),body TEXT NOT NULL);
""")
    ser=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True)
    for r in rows('works'):db.execute('INSERT INTO works VALUES (?,?)',(r['work_id'],ser(r)))
    for r in rows('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(r['source_id'],ser(r)))
    for r in rows('story_events'):db.execute('INSERT INTO events VALUES (?,?,?)',(r['event_id'],r['work_id'],ser(r)))
    for r in rows('narrative_chronology'):db.execute('INSERT INTO chronology VALUES (?,?)',(r['work_id'],ser(r)))
    for r in rows('narrative_links'):
        db.execute('INSERT INTO event_links(from_id,to_id,body) VALUES (?,?,?)',(r['from_event_id'],r['to_event_id'],ser(r)))
    for r in rows('artifacts'):
        db.execute('INSERT INTO artifacts VALUES (?,?,?)',(r['artifact_id'],r['primary_work_id'],ser(r)))
        for e in r['event_refs']:db.execute('INSERT INTO artifact_evidence VALUES (?,?)',(r['artifact_id'],e))
    classic=json.loads((ROOT/'data/nova/v0.6/source_records/tomb_raider_classic.json').read_text(encoding='utf8'))
    for r in classic['story_events']:db.execute('INSERT INTO classic_events VALUES (?)',(r['event_id'],))
    for r in rows('remake_analogues'):
        db.execute('INSERT INTO remake_links(lau_id,classic_id,body) VALUES (?,?,?)',(r['lau_event_id'],r['classic_event_id'],ser(r)))
    for r in rows('editorial_boundaries'):db.execute('INSERT INTO boundaries VALUES (?,?)',(r['id'],ser(r)))
    for r in rows('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(r['mechanic_id'],ser(r)))
    for r in rows('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES (?,?,?,?)',(r['evidence_id'],r['mechanic_id'],r['event_id'],ser(r)))
        for s in r['source_ids']:db.execute('INSERT INTO evidence_sources VALUES (?,?)',(r['evidence_id'],s))
    for file in [
      ROOT/'data/nova/v0.3/source_records/prince_mechanics.json',
      ROOT/'data/nova/v0.4/source_records/prototype_2009.json',
      ROOT/'data/nova/v0.5/source_records/tomb_raider_survivor.json',
      ROOT/'data/nova/v0.6/source_records/tomb_raider_classic.json']:
        for r in json.loads(file.read_text(encoding='utf8'))['mechanics']:
            db.execute('INSERT INTO old_mechanics VALUES (?)',(r['mechanic_id'],))
    for r in rows('prior_links'):
        db.execute('INSERT INTO prior_links(mechanic_id,old_mechanic_id,body) VALUES (?,?,?)',
            (r['mechanic_id'],r['prior_mechanic_id'],ser(r)))
    violations=db.execute('PRAGMA foreign_key_check').fetchall()
    if violations:raise ValueError('FK violations: '+str(violations))
    expected={'works':3,'sources':17,'events':36,'chronology':3,'event_links':16,
      'artifacts':7,'artifact_evidence':sum(len(a['event_refs']) for a in rows('artifacts')),
      'classic_events':36,'remake_links':5,'boundaries':6,'mechanics':18,
      'evidence':50,'old_mechanics':71,'prior_links':36}
    counts={}
    for table,n in expected.items():
        counts[table]=db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        if counts[table]!=n:raise ValueError(f'{table}: {counts[table]} != {n}')
    counts['evidence_sources']=db.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
    db.commit();db.close();tmp.replace(out)
    return {'status':'PASS','index_path':str(out),'counts':counts,
       'foreign_key_violations':0,'paid_model_calls':0,'story_quality_trials':0,
       'lumi_production_modified':False}
if __name__=='__main__':
    try:report=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-tomb-raider-lau-v07.sqlite')
    except Exception as ex:report={'status':'FAIL','fatal':repr(ex)}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(0 if report['status']=='PASS' else 1)
