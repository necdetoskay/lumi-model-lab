"""Budgeted completion of one saved story using bounded multi-scene patches."""
import hashlib
import json
import re
from pathlib import Path
from src.lighthouse_experiment import approved_input, bind_story, dependency_manifest, digest_json
from src.spineforge_v20_story_audit_artifact import _segment_story
from src.spineforge_v21_bounded_quality import split_findings
from src.spineforge_v21_model_adapter import _call, AUDIT_RESPONSE_SCHEMA, validate_schema
from src.spineforge_v21_quality_runtime import _usage
from src.lighthouse_audit_decision import SCHEMA as DECISION_SCHEMA, PROMPT as DECISION_PROMPT, decision

SOURCE = Path('evidence/lighthouse-paid-experiment/LIGHTHOUSE-PAID-01-20261005')
AUDIT_SOURCE = Path('evidence/lighthouse-quality-continuation/LIGHTHOUSE-QUALITY-01-20261005/calls.json')
PREPARED = Path('evidence/lighthouse-editorial/patch-campaign-prepared.json')
AUTH = Path('evidence/lighthouse-editorial/patch-campaign-authorization.json')
OUTPUT = Path('evidence/lighthouse-patch-campaign')
EXPERIMENT_ID = 'LIGHTHOUSE-SINGLE-STORY-COMPLETION-01'
RESUME_PATCH = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-01-20261005/calls.json')
RESUME_LEDGER = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-02-20261005/calls.json')
RESUME_TEXT = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-02-20261005/candidate-02.txt')
NEXT_RESUME_LEDGER = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-03-20261005/calls.json')
NEXT_RESUME_TEXT = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-03-20261005/accepted-story.txt')
EDITORIAL_REVIEW = Path('evidence/lighthouse-editorial/independent-review-03.json')
PRIOR_COST = 1.4986211
COMPLETION_AUDIT_SCHEMA = json.loads(json.dumps(AUDIT_RESPONSE_SCHEMA))
COMPLETION_AUDIT_SCHEMA['properties']['findings']['items']['properties']['reason']['maxLength'] = 2000
BUDGET = 3.0
PATCH_SCHEMA = {'type': 'object', 'additionalProperties': False, 'required': ['patches','summary'],
    'properties': {'summary': {'type':'string','maxLength':1200}, 'patches': {
        'type':'array','minItems':1,'maxItems':24,'items': {'type':'object',
        'additionalProperties':False,'required':['span_id','old_text','replacement_text'],
        'properties': {'span_id':{'type':'string','maxLength':16},
          'old_text':{'type':'string','maxLength':3000},
          'replacement_text':{'type':'string','minLength':1,'maxLength':3000}}}}}}

def prepare():
    plan = approved_input()
    raw = json.loads((SOURCE/'writer-raw.json').read_text())['story']
    artifact = bind_story(raw, plan)
    if artifact['story'] != (SOURCE/'original-story.txt').read_text():
        raise RuntimeError('Original story drift')
    calls = json.loads(AUDIT_SOURCE.read_text())
    if calls[0]['input']['source_story_sha256'] != artifact['story_sha256']:
        raise RuntimeError('Saved audit belongs to a different story')
    findings = calls[0]['response']['findings']
    paths = {r['path'] for r in dependency_manifest()}
    paths.update([str(SOURCE/'writer-raw.json'), str(SOURCE/'original-story.txt'), str(AUDIT_SOURCE),
                  'src/lighthouse_patch_campaign.py', 'tests/test_lighthouse_patch_campaign.py',str(RESUME_PATCH),str(RESUME_LEDGER),str(RESUME_TEXT),str(NEXT_RESUME_LEDGER),str(NEXT_RESUME_TEXT),str(EDITORIAL_REVIEW),
                  'prompts/lighthouse_patch_repair.md', 'prompts/lighthouse_completion_audit.md',str(DECISION_PROMPT),
                  'src/lighthouse_audit_decision.py','src/lighthouse_audit_requirements.py',
                  'evidence/lighthouse-editorial/audit-requirements.json','tests/test_lighthouse_audit_decision.py',
                  '.github/workflows/lighthouse-completion-once.yml'])
    manifest = [{'path': p, 'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    payload, ids = scope_payload(raw, plan, findings)
    raw, _ = apply_patches(raw, plan, ids, json.loads(RESUME_PATCH.read_text())[0]['response']['patches'])
    resume_calls = json.loads(RESUME_LEDGER.read_text())
    for row in resume_calls:
        if row['stage'] == 'PATCH' and row.get('response'):
            raw, _ = apply_patches(raw, plan, set(row['input']['allowed_span_ids']), row['response']['patches'])
    artifact = bind_story(raw, plan)
    if artifact['story'] != RESUME_TEXT.read_text():
        raise RuntimeError('Replay differs from saved candidate')
    findings = resume_calls[-1]['provider_evidence']['parsed_response']['findings']
    validate_schema(resume_calls[-1]['provider_evidence']['parsed_response'], COMPLETION_AUDIT_SCHEMA)
    next_calls = json.loads(NEXT_RESUME_LEDGER.read_text())
    for row in next_calls:
        if row['stage'] == 'PATCH' and row.get('response'):
            raw, _ = apply_patches(raw, plan, set(row['input']['allowed_span_ids']), row['response']['patches'])
    artifact = bind_story(raw, plan)
    if artifact['story'] != NEXT_RESUME_TEXT.read_text():
        raise RuntimeError('Latest replay differs from saved candidate')
    review = json.loads(EDITORIAL_REVIEW.read_text())
    if review['source_story_sha256'] != artifact['story_sha256']:
        raise RuntimeError('Editorial review belongs to another candidate')
    findings = next_calls[-1]['response']['findings'] + review['findings']
    prepared = {'experiment_id':EXPERIMENT_ID,'plan_sha256':digest_json(plan),
        'source_story_sha256':artifact['story_sha256'],'saved_findings_sha256':digest_json(findings),
        'resume_patch_sha256':hashlib.sha256(RESUME_PATCH.read_bytes()).hexdigest(),
        'runtime_manifest':manifest,'runtime_manifest_sha256':digest_json(manifest),
        'total_story_budget_usd':BUDGET,'prior_story_cost_usd':PRIOR_COST,
        'paid_execution_authorized':False,'new_writer_calls':0,'max_patch_spans':24}
    return prepared, plan, raw, findings

def apply_patches(raw, plan, allowed_ids, patches):
    artifact = bind_story(raw, plan)
    rows = {r['id']:r for r in _segment_story(artifact['story'])}
    segment_scenes = {r['span_id']:r['scene_id'] for r in artifact['segments']}
    bounds = {r['scene_id']:r for r in artifact['scene_bounds']}
    markers = list(re.finditer(r'^\[\[(SC\d{2})\]\][ \t]*$', raw, re.M))
    raw_starts = {}
    for i,m in enumerate(markers):
        end = markers[i+1].start() if i+1 < len(markers) else len(raw)
        body = raw[m.end():end]
        raw_starts[m[1]] = m.end() + len(body) - len(body.lstrip())
    seen=set(); edits=[]
    if not patches or len(patches)>24:raise RuntimeError('Invalid patch count')
    for p in patches:
        sid=p['span_id']
        if sid in seen or sid not in allowed_ids or sid not in rows:
            raise RuntimeError('Patch outside approved span scope or duplicate')
        seen.add(sid); row=rows[sid]; scene=segment_scenes[sid]
        if scene=='TITLE':raise RuntimeError('Title patch forbidden')
        old=p['old_text']
        if not old or row['text'].count(old)!=1:raise RuntimeError('Patch source mismatch or ambiguity')
        replacement=p['replacement_text']
        if (not replacement.strip() or '[[' in replacement or '\n' in replacement
                or replacement == p['old_text']):raise RuntimeError('Invalid or unchanged replacement')
        start=raw_starts[scene]+row['char_start']-bounds[scene]['char_start']+row['text'].index(old)
        end=start+len(old)
        if raw[start:end]!=old:raise RuntimeError('Raw/span alignment mismatch')
        edits.append((start,end,replacement))
    edits.sort()
    cursor=0; parts=[]; preserved=[]
    for start,end,replacement in edits:
        if start<cursor:raise RuntimeError('Overlapping patch')
        gap=raw[cursor:start];parts.extend([gap,replacement]);preserved.append(gap);cursor=end
    parts.append(raw[cursor:]);preserved.append(raw[cursor:])
    candidate=''.join(parts)
    bound=bind_story(candidate,plan)
    if bound['word_count']<plan['target_words']['min']:raise RuntimeError('Candidate below minimum')
    # Every non-target byte was copied directly, including whitespace and scene markers.
    return candidate, {'outside_patches_unchanged':True,'changed_span_ids':sorted(seen),
        'preserved_pieces_sha256':[hashlib.sha256(s.encode()).hexdigest() for s in preserved],
        'source_story_sha256':artifact['story_sha256'],'candidate_story_sha256':bound['story_sha256']}

def scope_payload(raw, plan, findings):
    artifact=bind_story(raw,plan)
    blocking,_=split_findings(findings)
    ids={sid for f in blocking for sid in f.span_ids}
    rows={r['span_id']:r for r in artifact['segments']}
    if not ids or len(ids)>24 or any(s not in rows or rows[s]['scene_id']=='TITLE' for s in ids):
        raise RuntimeError('Unsupported patch scope')
    return {'full_story':artifact['story'],'story_segments':artifact['segments'],
            'approved_plan':plan,'findings':findings,'allowed_span_ids':sorted(ids),
            'source_story_sha256':artifact['story_sha256']}, ids

def call_model(key,stage,payload):
    if stage=='AUDIT':
        from src.lighthouse_audit_requirements import requirements
        payload={**payload,'binding_requirements':requirements(payload['approved_plan'])}
    return _call(api_key=key,payload=payload,
        prompt_path=Path('prompts/lighthouse_patch_repair.md' if stage=='PATCH' else str(DECISION_PROMPT)),
        request_class='spineforge_v21_scene_repair' if stage=='PATCH' else 'spineforge_v21_initial_blocking_audit',
        schema_name='lighthouse_patch_v1' if stage=='PATCH' else 'lighthouse_audit_decision_v3',
        schema=PATCH_SCHEMA if stage=='PATCH' else DECISION_SCHEMA,
        max_tokens=3500,stage=stage)

def run(*,authorization,output_dir,call_fn):
    prepared,plan,raw,findings=prepare()
    for k in ['experiment_id','plan_sha256','source_story_sha256','saved_findings_sha256',
              'runtime_manifest_sha256','total_story_budget_usd','prior_story_cost_usd','resume_patch_sha256']:
        if authorization.get(k)!=prepared[k]:raise RuntimeError('Authorization drift: '+k)
    if authorization.get('explicit_paid_authorization') is not True:raise RuntimeError('Paid authorization required')
    aid=authorization.get('authorization_id','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',aid):raise RuntimeError('Invalid authorization ID')
    out=Path(output_dir)/aid;out.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    save('authorization-consumed.json',authorization);save('prepared-input.json',prepared)
    ledger=[];cost=PRIOR_COST;result={'status':'STARTED','writer_calls':0,'prior_story_cost_usd':PRIOR_COST,
        'transport_retries':0,'production_write':False,'translation_executed':False}
    def invoke(stage,payload):
        nonlocal cost
        # Reserve conservative UTF-8 input allowance plus schema/envelope allowance and output cap.
        input_allowance=len(json.dumps(payload,ensure_ascii=False).encode())+len(Path(
            'prompts/lighthouse_patch_repair.md' if stage=='PATCH' else str(DECISION_PROMPT)).read_bytes())+12000
        reserve=input_allowance*2/1e6+(3500)*10/1e6
        if cost+reserve>BUDGET:raise RuntimeError('Story budget lacks next-call reservation')
        row={'stage':stage,'input':payload,'status':'STARTED','reserved_cost_usd':reserve};ledger.append(row)
        save('calls.json',ledger)
        try:
            response=call_fn(stage,payload)
            row['response']=response;row['usage']=_usage(response,stage)
            cost+=row['usage']['cost_usd'];row['status']='COMPLETED';save('calls.json',ledger)
            if cost>BUDGET:raise RuntimeError('Actual story budget exceeded; no further calls')
            validate_schema({k:response[k] for k in (PATCH_SCHEMA if stage=='PATCH' else DECISION_SCHEMA)['properties']},
                            PATCH_SCHEMA if stage=='PATCH' else DECISION_SCHEMA)
            return response
        except Exception as exc:
            row['status']='FAILED';row['failure_message']=getattr(exc,'diagnostic_message',str(exc))
            row['provider_evidence']=getattr(exc,'provider_evidence',None)
            if 'usage' not in row:
                try:
                    row['usage']=_usage({'usage':getattr(exc,'usage',None)},stage);cost+=row['usage']['cost_usd']
                except RuntimeError:pass
            save('calls.json',ledger);raise
    try:
        for cycle in range(30):
            blocking,_=split_findings(findings)
            if not blocking:
                a=bind_story(raw,plan)
                (out/'accepted-story.txt').write_text(a['story'])
                result.update(status='ACCEPT',accepted_story_sha256=a['story_sha256'],word_count=a['word_count'])
                break
            payload,ids=scope_payload(raw,plan,findings)
            patch=invoke('PATCH',payload)
            raw,proof=apply_patches(raw,plan,ids,patch['patches'])
            save(f'patch-proof-{cycle+1:02}.json',proof)
            (out/f'candidate-{cycle+1:02}.txt').write_text(bind_story(raw,plan)['story'])
            a=bind_story(raw,plan)
            audit_payload={'full_story':a['story'],'story_segments':a['segments'],'approved_plan':plan,
                           'previous_findings':findings,'patch_proof':proof,'reader_profile':{'age':12,'language':'en'}}
            response=invoke('AUDIT',audit_payload)
            audit_result=decision(response,a['segments'],plan)
            save(f'audit-decision-{cycle+1:02}.json',audit_result)
            findings=audit_result['findings']
            result.update(final_advisory_notes=audit_result['advisory_notes'],
                          final_verified_requirements=audit_result['verified_requirements'])
            known={r['span_id'] for r in a['segments']}
            if any(s not in known for f in findings for s in f['span_ids']):raise RuntimeError('Audit unknown span')
        else:raise RuntimeError('Non-convergent after 30 patch cycles')
    except Exception as exc:
        result.update(status='REJECT_RUNTIME',failure_type=type(exc).__name__,failure_message=str(exc))
    result.update(new_call_count=len(ledger),total_story_cost_usd=cost,
        new_cost_usd=round(cost-PRIOR_COST,12),accounting_complete=all('usage' in c for c in ledger),
        model_latency_seconds=sum(c.get('usage',{}).get('latency_seconds',0) for c in ledger),
        final_findings=findings)
    save('result.json',result);return result

if __name__=='__main__':
    import argparse,os
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:
        value,*_=prepare();PREPARED.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({k:v for k,v in value.items() if k!='runtime_manifest'}))
    else:
        key=os.environ.get('OPENROUTER_API_KEY')
        if not key:p.error('API key required')
        result=run(authorization=json.loads(AUTH.read_text()),output_dir=OUTPUT,
                   call_fn=lambda stage,payload:call_model(key,stage,payload))
        print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['status']=='ACCEPT' else 1)
