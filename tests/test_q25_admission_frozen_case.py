import hashlib,json,subprocess,sys
from pathlib import Path
from src.q25_state_admission import build_draft
ROOT=Path('evidence/q25/Q25-ADMISSION-DRAFT-20261012')
BASE=Path('evidence/q25/Q25-P0-P4-OFFLINE-20261012/frozen-evidence/Q24')
PREVIOUS=Path('evidence/q25/Q25-ENTITY-CANDIDATE-20261012')
def read(path):return json.loads(path.read_text(encoding='utf8'))

def test_q24_admission_replays_with_explicit_unknowns_and_no_revision():
    result=build_draft(seed=read(BASE/'seed-input.json'),prose=read(BASE/'writer-2-text.json')['text'],proposal=read(PREVIOUS/'proposal.json'),policy=read(ROOT/'policy.json'))
    assert result==read(ROOT/'admission-result.json')
    assert result['structural_admission']=='ELIGIBLE_DRAFT'
    draft=result['draft_state'];new=draft['objects']['red_bookmark']['container']['ref']
    assert draft['objects'][new]['owner']['status']=='UNKNOWN'
    assert draft['objects'][new]['location']['status']=='UNKNOWN'
    assert draft['objects'][new]['contains']==['red_bookmark']
    assert 'revision' not in draft and not result['state_commit_authorized']
    assert draft['objects']['red_bookmark']['properties']['found'] is False

def test_all_admission_sources_and_evidence_hashes_match():
    for name,sha in read(ROOT/'inventory.json')['files'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
    for row in read(ROOT/'provenance.json')['source_files']:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']

def test_read_only_command_does_not_mutate_frozen_seed_or_records():
    roots=[ROOT,BASE,PREVIOUS];before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.rglob('*') if p.is_file()}
    raw=subprocess.check_output([sys.executable,'-X','utf8','-m','src.q25_state_admission','--seed',str(BASE/'seed-input.json'),'--prose-record',str(BASE/'writer-2-text.json'),'--proposal',str(PREVIOUS/'proposal.json'),'--policy',str(ROOT/'policy.json')],text=True,encoding='utf8')
    assert json.loads(raw)==read(ROOT/'admission-result.json')
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for root in roots for p in root.rglob('*') if p.is_file()}
