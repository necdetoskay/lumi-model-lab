import hashlib,json
from pathlib import Path
from src.q25_offline_diagnostic import diagnose

ROOT=Path('evidence/q25/Q25-P0-P4-OFFLINE-20261012')
def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))

def test_frozen_q24_replay_separates_results_without_promoting_draft_judgment():
    result=diagnose(**read('diagnostic-input.json'))
    assert result==read('diagnostic-result.json')
    assert result['narrative_status']=='UNVERIFIED' and result['review_status']=='DISPUTED_REVIEW'
    assert result['state_status']=='STATE_MODEL_GAP' and result['persistence_status']=='BLOCKED'
    assert not result['state_commit_authorized'] and not result['story_rejection_authorized']
    assert read('frozen-evidence/Q24/result.json')['status']=='REJECT_NON_CONVERGENT'
    assert read('frozen-evidence/Q22/result.json')['status']=='ACCEPT'

def test_all_frozen_artifacts_and_generated_case_bytes_match_inventory():
    for name,sha in read('inventory.json')['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,name
    for row in read('baseline-lineage.json')['source_records']:
        assert hashlib.sha256((ROOT/row['saved_path']).read_bytes()).hexdigest()==row['sha256']

def test_command_replays_saved_case_without_writing_any_evidence():
    import subprocess,sys
    before={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()}
    raw=subprocess.check_output([sys.executable,'-X','utf8','-m','src.q25_offline_diagnostic','--input',str(ROOT/'diagnostic-input.json')],text=True,encoding='utf8')
    assert json.loads(raw)==read('diagnostic-result.json')
    assert before=={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.rglob('*') if p.is_file()}
