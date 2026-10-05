"""Run saved Writer/Audit deliveries through deterministic adapters; zero API spend."""
import json
from pathlib import Path
from src.story_delivery import normalize_marked_story
from src.audit_citation_projection import grounded_decision
from src.lighthouse_experiment import approved_input, digest_json
from src.story_delivery import sha
from src.lighthouse_writer_once import scene_artifact
from src.lighthouse_decision_qualification import payload

ROOT=Path('evidence/lighthouse-writer-prompt-trial')
WRITER_SOURCE=ROOT/'LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005'
AUDIT_SOURCE=ROOT/'LIGHTHOUSE-READ-AUDIT-01-20261005'
OUTPUT=ROOT/'DELIVERY-REPLAY-02-20261005'


def replay(output_dir=None):
    plan=approved_input()
    ledger=json.loads((WRITER_SOURCE/'calls.json').read_text())
    for row in ledger:
        if row['stage']!='WRITER': continue
        response=row['response']
        if response['actual_request']!=row['input']:
            raise RuntimeError('Saved dispatched Writer request drift')
        source_plan=json.loads(row['input']['messages'][1]['content'])
        if digest_json(source_plan)!=digest_json(plan):
            raise RuntimeError('Saved Writer plan differs from current approved source')
        choice=response['provider_response']['choices'][0]
        if choice['finish_reason']!='stop' or choice['message']['content']!=response['story']:
            raise RuntimeError('Saved Writer body incomplete or inconsistent')
    writers={r['variant']:r['response']['story'] for r in ledger if r['stage']=='WRITER'}
    audit_rows={'current_baseline':next(r for r in ledger if r['stage']=='AUDIT'),
                'five_category_appendix':json.loads((AUDIT_SOURCE/'calls.json').read_text())[0]}
    out=Path(output_dir) if output_dir is not None else OUTPUT
    out.mkdir(parents=True,exist_ok=False)
    cases=[]
    for name,raw in writers.items():
        marked,proof=normalize_marked_story(raw,[s['scene_id'] for s in plan['scenes']],
            encoding_provenance='latin1_decoded_utf8_sse')
        artifact=scene_artifact(marked,plan)
        data=payload(artifact['story'],plan)
        audit=audit_rows[name]
        expected_audit_story=scene_artifact(raw,plan)['story'] if name=='current_baseline' else artifact['story']
        if (audit['input']['full_story']!=expected_audit_story
                or audit['input']['source_story_sha256']!=sha(expected_audit_story)
                or digest_json(audit['input']['approved_plan'])!=digest_json(plan)):
            raise RuntimeError('Saved audit/story/plan binding drift')
        chosen,corrections=grounded_decision(audit['response'],data['story_segments'],plan)
        (out/(name+'-story.txt')).write_text(artifact['story'])
        value={'variant':name,'delivery_proof':proof,'story_sha256':artifact['story_sha256'],
               'word_count':artifact['word_count'],'citation_corrections':corrections,'decision':chosen}
        (out/(name+'-result.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        cases.append(value)
    result={'status':'SAVED_DELIVERY_REPLAY_PASS','new_api_calls':0,'new_cost_usd':0,
        'approved_plan_sha256':digest_json(plan),
        'source_files':[{'path':str(p),'sha256':sha(p.read_text())}
                        for p in [WRITER_SOURCE/'calls.json',AUDIT_SOURCE/'calls.json']],
        'semantic_story_repairs':0,'manual_intervention_during_replay':False,
        'live_transport_qualified':False,'audit_defect_coverage_qualified':False,
        'stories_publication_ready':False,'production_write':False,'cases':cases}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output-dir');args=p.parse_args()
    r=replay(args.output_dir);print(json.dumps({k:v for k,v in r.items() if k!='cases'}))
