#!/usr/bin/env python3
"""Build disposable research-only SQLite index with verified foreign keys."""
import json,sqlite3,sys
from pathlib import Path
from validate_tomb_raider_classic import ROOT,BASE,records,validate
def build(target=ROOT/'.nova-cache/nova-tomb-raider-classic-v06.sqlite'):
    report=validate()
    if report['status']!='PASS':raise ValueError('Refuse SQLite on invalid canonical corpus: '+str(report.get('errors')))
    p=Path(target)
    p.parent.mkdir(parents=True,exist_ok=True)
    scratch=p.with_suffix('.building.sqlite')
    if scratch.exists():scratch.unlink()
    db=sqlite3.connect(scratch)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,record TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,record TEXT NOT NULL);
CREATE TABLE events(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),record TEXT NOT NULL);
CREATE TABLE narrative_links(id INTEGER PRIMARY KEY,from_event_id TEXT NOT NULL REFERENCES events(id),to_event_id TEXT NOT NULL REFERENCES events(id),record TEXT NOT NULL);
CREATE TABLE releases(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(id),record TEXT NOT NULL);
CREATE TABLE boundaries(id TEXT PRIMARY KEY,record TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,record TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),event_id TEXT NOT NULL REFERENCES events(id),record TEXT NOT NULL);
CREATE TABLE evidence_sources(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE old_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),old_mechanic_id TEXT NOT NULL REFERENCES old_mechanics(id),record TEXT NOT NULL);
""")
    ser=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True)
    for x in records('works'):db.execute('INSERT INTO works VALUES(?,?)',(x['work_id'],ser(x)))
    for x in records('sources'):db.execute('INSERT INTO sources VALUES(?,?)',(x['source_id'],ser(x)))
    for x in records('story_events'):db.execute('INSERT INTO events VALUES(?,?,?)',(x['event_id'],x['work_id'],ser(x)))
    for x in records('narrative_links'):
        db.execute('INSERT INTO narrative_links(from_event_id,to_event_id,record) VALUES(?,?,?)',(x['from_event_id'],x['to_event_id'],ser(x)))
    for x in records('supplementary_releases'):db.execute('INSERT INTO releases VALUES(?,?,?)',(x['release_id'],x['source_id'],ser(x)))
    for x in records('editorial_boundaries'):db.execute('INSERT INTO boundaries VALUES(?,?)',(x['issue_id'],ser(x)))
    for x in records('mechanics'):db.execute('INSERT INTO mechanics VALUES(?,?)',(x['mechanic_id'],ser(x)))
    for x in records('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES(?,?,?,?)',(x['evidence_id'],x['mechanic_id'],x['event_id'],ser(x)))
        for sid in x['source_ids']:db.execute('INSERT INTO evidence_sources VALUES(?,?)',(x['evidence_id'],sid))
    for version,file in [('0.3',ROOT/'data/nova/v0.3/source_records/prince_mechanics.json'),
                         ('0.4',ROOT/'data/nova/v0.4/source_records/prototype_2009.json'),
                         ('0.5',ROOT/'data/nova/v0.5/source_records/tomb_raider_survivor.json')]:
        for x in json.loads(file.read_text(encoding='utf8'))['mechanics']:
            db.execute('INSERT INTO old_mechanics VALUES(?)',(x['mechanic_id'],))
    for x in records('prior_links'):
        db.execute('INSERT INTO links(mechanic_id,old_mechanic_id,record) VALUES(?,?,?)',(x['mechanic_id'],x['older_mechanic_id'],ser(x)))
    violations=db.execute('PRAGMA foreign_key_check').fetchall()
    if violations:raise ValueError('Foreign key violations: '+repr(violations))
    expected={'works':6,'sources':21,'events':36,'narrative_links':10,
              'releases':3,'boundaries':3,'mechanics':19,'evidence':54,
              'old_mechanics':52,'links':38}
    counts={}
    for t,n in expected.items():
        counts[t]=db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0]
        if counts[t]!=n:raise ValueError(f'{t}: {counts[t]} != {n}')
    counts['evidence_sources']=db.execute('SELECT COUNT(*) FROM evidence_sources').fetchone()[0]
    db.commit()
    db.close()
    scratch.replace(p)
    return {'status':'PASS','index_path':str(p),'counts':counts,'foreign_key_violations':0,
           'paid_calls':0,'story_quality_trials':0,'lumi_production_modified':False}
if __name__=='__main__':
    try:r=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-tomb-raider-classic-v06.sqlite')
    except Exception as e:r={'status':'FAIL','fatal':repr(e)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='PASS' else 1)
