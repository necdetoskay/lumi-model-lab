import hashlib,json
from pathlib import Path
from src.q25_entity_candidates import represent
BASE=Path('evidence/q25/Q25-P0-P4-OFFLINE-20261012')
ROOT=Path('evidence/q25/Q25-ENTITY-CANDIDATE-20261012')
def read(path):return json.loads(path.read_text(encoding='utf8'))

def test_q24_terminal_book_can_be_represented_without_seed_or_acceptance_change():
    seedpath=BASE/'frozen-evidence/Q24/seed-input.json';before=seedpath.read_bytes()
    result=represent(seed=read(seedpath),prose=read(BASE/'frozen-evidence/Q24/writer-2-text.json')['text'],proposal=read(ROOT/'proposal.json'))
    assert result==read(ROOT/'representation.json')
    book=result['candidate_objects'][0]['id']
    assert result['container_contents']['object:blue_atlas']==[]
    assert result['container_contents'][book]==['object:red_bookmark']
    assert 'object:red_bookmark' not in result['directly_held_objects'].get('character:Nisa',[])
    assert any(e['subject']=='object:red_bookmark' and e['kind']=='OWNED_BY' and e['target']=='character:Nisa' for e in result['relations'])
    assert not result['state_commit_authorized'] and seedpath.read_bytes()==before
    assert read(BASE/'frozen-evidence/Q24/result.json')['status']=='REJECT_NON_CONVERGENT'

def test_candidate_evidence_bytes_are_preserved():
    for name,sha in read(ROOT/'inventory.json')['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name

def test_candidate_command_is_read_only_and_reproducible():
    import subprocess,sys
    before={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in (ROOT,BASE) for p in folder.rglob('*') if p.is_file()}
    raw=subprocess.check_output([sys.executable,'-X','utf8','-m','src.q25_entity_candidates','--seed',str(BASE/'frozen-evidence/Q24/seed-input.json'),'--prose-record',str(BASE/'frozen-evidence/Q24/writer-2-text.json'),'--proposal',str(ROOT/'proposal.json')],text=True,encoding='utf8')
    assert json.loads(raw)==read(ROOT/'representation.json')
    assert before=={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for folder in (ROOT,BASE) for p in folder.rglob('*') if p.is_file()}
