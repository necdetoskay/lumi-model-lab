#!/usr/bin/env python3
"""Disposable SQLite v0.9 comic issue, source, comparison and inference FK audit."""
import json,sqlite3,sys
from pathlib import Path
from validate_prototype_comics import ROOT,BASE,rows,validate
def build(path=ROOT/'.nova-cache/nova-prototype-comics-v09.sqlite'):
    check=validate()
    if check['status']!='PASS':raise ValueError('invalid corpus: '+str(check['errors']))
    output=Path(path);output.parent.mkdir(parents=True,exist_ok=True)
    tmp=output.with_suffix('.building.sqlite')
    if tmp.exists():tmp.unlink()
    db=sqlite3.connect(tmp)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript("""
CREATE TABLE works(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE sources(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE issues(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE collection(id TEXT PRIMARY KEY,isbn TEXT UNIQUE NOT NULL,body TEXT NOT NULL);
CREATE TABLE collection_issues(collection_id TEXT NOT NULL REFERENCES collection(id),issue_id TEXT NOT NULL REFERENCES issues(id),PRIMARY KEY(collection_id,issue_id));
CREATE TABLE observations(id TEXT PRIMARY KEY,work_id TEXT NOT NULL REFERENCES works(id),issue_id TEXT NOT NULL REFERENCES issues(id),body TEXT NOT NULL);
CREATE TABLE unverified_claims(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE previous_events(id TEXT PRIMARY KEY);
CREATE TABLE cross_game_links(id TEXT PRIMARY KEY,prior_event_id TEXT NOT NULL REFERENCES previous_events(id),work_id TEXT NOT NULL REFERENCES works(id),body TEXT NOT NULL);
CREATE TABLE mechanics(id TEXT PRIMARY KEY,body TEXT NOT NULL);
CREATE TABLE evidence(id TEXT PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),observation_id TEXT NOT NULL REFERENCES observations(id),issue_id TEXT NOT NULL REFERENCES issues(id),body TEXT NOT NULL);
CREATE TABLE evidence_source_links(evidence_id TEXT NOT NULL REFERENCES evidence(id),source_id TEXT NOT NULL REFERENCES sources(id),PRIMARY KEY(evidence_id,source_id));
CREATE TABLE previous_mechanics(id TEXT PRIMARY KEY);
CREATE TABLE prior_mechanic_links(id INTEGER PRIMARY KEY,mechanic_id TEXT NOT NULL REFERENCES mechanics(id),prior_id TEXT NOT NULL REFERENCES previous_mechanics(id),body TEXT NOT NULL);
""")
    ser=lambda x:json.dumps(x,ensure_ascii=False,sort_keys=True)
    for w in rows('works'):db.execute('INSERT INTO works VALUES (?,?)',(w['work_id'],ser(w)))
    for s in rows('sources'):db.execute('INSERT INTO sources VALUES (?,?)',(s['source_id'],ser(s)))
    for i in rows('issues'):db.execute('INSERT INTO issues VALUES (?,?,?)',(i['issue_id'],i['arc_id'],ser(i)))
    canonical=json.loads((BASE/'source_records/prototype_comic_bridge.json').read_text(encoding='utf8'))
    collection=canonical['collection']
    db.execute('INSERT INTO collection VALUES (?,?,?)',(collection['collection_id'],collection['isbn13'],ser(collection)))
    for issue in collection['contains_issues']:
        db.execute('INSERT INTO collection_issues VALUES (?,?)',(collection['collection_id'],issue))
    lookup={(i['arc_id'],i['part_number']):i['issue_id'] for i in rows('issues')}
    for e in rows('story_observations'):
        db.execute('INSERT INTO observations VALUES (?,?,?,?)',(e['event_id'],e['work_id'],lookup[(e['work_id'],e['part_number'])],ser(e)))
    for claim in rows('unverified_candidate_claims'):
        db.execute('INSERT INTO unverified_claims VALUES (?,?)',(claim['candidate_id'],ser(claim)))
    for file in ['data/nova/v0.4/source_records/prototype_2009.json','data/nova/v0.8/source_records/prototype2_2012.json']:
        prior=json.loads((ROOT/file).read_text(encoding='utf8'))
        for e in prior['story_events']:db.execute('INSERT INTO previous_events VALUES (?)',(e['event_id'],))
    for x in rows('prior_game_links'):
        db.execute('INSERT INTO cross_game_links VALUES (?,?,?,?)',
                   (x['link_id'],x['prior_event_id'],x['target_work_id'],ser(x)))
    for m in rows('mechanics'):db.execute('INSERT INTO mechanics VALUES (?,?)',(m['mechanic_id'],ser(m)))
    for e in rows('mechanic_evidence'):
        db.execute('INSERT INTO evidence VALUES (?,?,?,?,?)',
                   (e['evidence_id'],e['mechanic_id'],e['observation_id'],e['issue_id'],ser(e)))
        for source in e['source_ids']:db.execute('INSERT INTO evidence_source_links VALUES (?,?)',(e['evidence_id'],source))
    for file in [
       'data/nova/v0.3/source_records/prince_mechanics.json',
       'data/nova/v0.4/source_records/prototype_2009.json',
       'data/nova/v0.5/source_records/tomb_raider_survivor.json',
       'data/nova/v0.6/source_records/tomb_raider_classic.json',
       'data/nova/v0.7/source_records/tomb_raider_lau.json',
       'data/nova/v0.8/source_records/prototype2_2012.json']:
        old=json.loads((ROOT/file).read_text(encoding='utf8'))
        for mech in old['mechanics']:db.execute('INSERT INTO previous_mechanics VALUES (?)',(mech['mechanic_id'],))
    for x in rows('mechanic_prior_links'):
        db.execute('INSERT INTO prior_mechanic_links(mechanic_id,prior_id,body) VALUES (?,?,?)',
                   (x['mechanic_id'],x['prior_mechanic_id'],ser(x)))
    invalid=db.execute('PRAGMA foreign_key_check').fetchall()
    if invalid:raise ValueError('foreign key violations: '+repr(invalid))
    expected={'works':3,'sources':9,'issues':6,'collection':1,'collection_issues':6,
      'observations':12,'unverified_claims':4,'previous_events':36,'cross_game_links':5,
      'mechanics':12,'evidence':33,'previous_mechanics':103,'prior_mechanic_links':25}
    counts={}
    for table,n in expected.items():
        counts[table]=db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]
        if counts[table]!=n:raise ValueError(f'{table}: {counts[table]} != {n}')
    counts['evidence_source_links']=db.execute('SELECT COUNT(*) FROM evidence_source_links').fetchone()[0]
    db.commit();db.close();tmp.replace(output)
    return {'status':'PASS','path':str(output),'counts':counts,'foreign_key_violations':0,
       'primary_comic_panels_examined':0,'story_quality_trials':0,'paid_model_calls':0,
       'production_modified':False}
if __name__=='__main__':
    try:r=build(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'.nova-cache/nova-prototype-comics-v09.sqlite')
    except Exception as e:r={'status':'FAIL','fatal':repr(e)}
    print(json.dumps(r,ensure_ascii=False,indent=2))
    sys.exit(0 if r['status']=='PASS' else 1)
