"""Qualify full-source audit on saved controls, then at most two bounded patches."""
import ast
import hashlib
import json
from pathlib import Path
from src.lighthouse_experiment import approved_input, bind_story, dependency_manifest, digest_json
from src.lighthouse_decision_qualification import payload
from src.plan_atomic_audit import compile_atomic_contract as compile_contract
from src.source_adjudication import SCHEMA, decision, adjudication_payload
from src.lighthouse_patch_campaign import PATCH_SCHEMA, apply_patches, scope_payload
from src.spineforge_v21_model_adapter import _call
from src.spineforge_v21_quality_runtime import _usage
from src.story_delivery import normalize_marked_story
from src.spineforge_v21_wire import project_payload
from src.cancel_queued_experiment import OUTPUT as CANCELLATION_PROOF, RUN as SUPERSEDED_RUN, COMMIT as SUPERSEDED_COMMIT

ID = 'LIGHTHOUSE-SOURCE-ADJUDICATION-HOSTED-01-20261005'
ROOT = Path('evidence/lighthouse-source-audit')
AUTH = Path('evidence/lighthouse-editorial/source-adjudication-hosted-authorization.json')
PROMPT = Path('prompts/approved_source_adjudication_v1.md')
PATCH_PROMPT = Path('prompts/lighthouse_patch_repair.md')
PRIOR_PATH = Path('evidence/lighthouse-source-audit/LIGHTHOUSE-SOURCE-AUDIT-03-20261005/result.json')
WRITER_LEDGER = Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005/calls.json')
CLEAN = Path('evidence/lighthouse-patch-campaign/LIGHTHOUSE-COMPLETION-06-20261005/accepted-story.txt')
FLAWED = Path('evidence/lighthouse-writer-prompt-trial/LIGHTHOUSE-WRITER-PROMPT-TRIAL-04-20261005/five_category_appendix-reading-story.txt')
CLEAN_NOTES = Path('evidence/lighthouse-source-audit/LIGHTHOUSE-SOURCE-AUDIT-02-20261005/calls.json')
NEGATIVE_NOTES = Path('evidence/lighthouse-source-audit/LIGHTHOUSE-SOURCE-AUDIT-03-20261005/calls.json')
WORKFLOW = Path('.github/workflows/lighthouse-source-adjudication-hosted.yml')
MAX_TOKENS = {'AUDIT': 3500, 'PATCH': 3500}


def audit_payload(story, plan, contract, notes=None):
    return adjudication_payload(payload(story,plan),contract,notes)


def qualification_passed(case, response, chosen):
    if case=='clean_control': return chosen['status']=='ACCEPT'
    f=chosen['findings']
    return chosen['status']=='REPAIR' and all(any(r['family'] in families and sid in r['span_ids'] for r in f)
        for families,sid in [({'state_continuity','causal_logic'},'S196'),({'spine_fidelity','spatial_consistency','physical_feasibility'},'S177'),({'closure_integrity','spine_fidelity'},'S200')])


def prepare():
    plan = approved_input(); contract = compile_contract(plan, digest_json(plan))
    prior = json.loads(PRIOR_PATH.read_text())
    if prior['confirmed_story_cost_usd'] != 2.42645486 or prior['unknown_call_reserve_usd'] != .04:
        raise RuntimeError('Prior immutable accounting checkpoint drift')
    cases = [('clean_control', CLEAN), ('recorded_deviations', FLAWED)]
    paths = {r['path'] for r in dependency_manifest()}
    paths.update(map(str, [Path(__file__).relative_to(Path.cwd()), PROMPT, PATCH_PROMPT,
        PRIOR_PATH, WRITER_LEDGER, CLEAN, FLAWED, WORKFLOW, CLEAN_NOTES, NEGATIVE_NOTES,
        Path('tests/test_lighthouse_source_adjudication_hosted.py'), Path('tests/test_lighthouse_source_adjudication.py'), Path('src/lighthouse_source_adjudication.py'), Path('src/cancel_queued_experiment.py'), Path('tests/test_cancel_queued_experiment.py')]))
    pending = list(paths)
    while pending:
        p = Path(pending.pop())
        if p.suffix != '.py': continue
        for n in ast.walk(ast.parse(p.read_text())):
            modules = [n.module] if isinstance(n, ast.ImportFrom) else [x.name for x in n.names] if isinstance(n, ast.Import) else []
            for m in modules:
                if m and m.startswith('src.'):
                    dep = m.replace('.', '/') + '.py'
                    if dep not in paths: paths.add(dep); pending.append(dep)
    manifest = [{'path': p, 'sha256': hashlib.sha256(Path(p).read_bytes()).hexdigest()} for p in sorted(paths)]
    return {'experiment_id': ID, 'plan_sha256': digest_json(plan),
        'contract_sha256': contract['contract_sha256'], 'runtime_manifest': manifest,
        'runtime_manifest_sha256': digest_json(manifest),
        'cases': [{'id': n, 'path': str(p), 'input_sha256': digest_json(audit_payload(p.read_text(), plan, contract, json.loads((CLEAN_NOTES if n=='clean_control' else NEGATIVE_NOTES).read_text())[0]))} for n,p in cases],
        'prior_confirmed_cost_usd': prior['confirmed_story_cost_usd'], 'unknown_prior_call_reserve_usd': .04,
        'total_story_budget_usd': 3, 'hosted_runner_cost_reserve_usd': .10, 'max_new_calls': 6, 'max_patch_cycles': 2,
        'max_tokens': MAX_TOKENS, 'writer_calls': 0, 'automatic_retry': False,
        'repair_requires_both_controls_pass': True, 'production_write': False}, plan, contract


def call_model(key, stage, data):
    schema = PATCH_SCHEMA if stage == 'PATCH' else SCHEMA
    return _call(api_key=key, payload=data, prompt_path=PATCH_PROMPT if stage == 'PATCH' else PROMPT,
        request_class='spineforge_v21_scene_repair' if stage == 'PATCH' else 'spineforge_v21_initial_blocking_audit',
        schema_name='lighthouse_patch_v1' if stage == 'PATCH' else 'approved_source_adjudication_v1',
        schema=schema, max_tokens=MAX_TOKENS[stage], stage=stage)


def run(auth, output_root, call_fn):
    prepared, plan, contract = prepare()
    if any(auth.get(k) != v for k,v in prepared.items()) or auth.get('explicit_paid_authorization') is not True:
        raise RuntimeError('Frozen authorization or runtime drift')
    proof=json.loads(CANCELLATION_PROOF.read_text())
    if (proof.get('superseded_run_id')!=SUPERSEDED_RUN or proof.get('superseded_commit')!=SUPERSEDED_COMMIT
            or proof.get('confirmed_cancelled') is not True or proof.get('paid_step_never_started') is not True):
        raise RuntimeError('Superseded paid run cancellation is not proven')
    out = Path(output_root)/ID; out.mkdir(parents=True, exist_ok=False)
    def save(name, value): (out/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    save('superseded-run-cancellation.json',proof); save('authorization-consumed.json', auth); save('prepared-input.json', prepared)
    save('contract.json', contract); save('response-schema.json', SCHEMA)
    calls=[]; cases=[]; cost=prepared['prior_confirmed_cost_usd']; unknown=.04
    result={'status':'STARTED', 'writer_calls':0, 'production_write':False,
            'live_writer_transport_qualified':False, 'qualification_passed':False}

    def invoke(stage, data, case):
        nonlocal cost, unknown
        schema = PATCH_SCHEMA if stage == 'PATCH' else SCHEMA
        prompt = PATCH_PROMPT if stage == 'PATCH' else PROMPT
        # Existing verified Sonnet profile: $2/M input, $10/M output. Byte allowance
        # includes schema/envelope; this is a conservative reservation, not tokenization.
        reserve = (len(json.dumps(project_payload(data), ensure_ascii=False).encode())
            + len(prompt.read_bytes()) + len(json.dumps(schema).encode()) + 12000)*2/1e6 + MAX_TOKENS[stage]*10/1e6
        if len(calls)>=6 or cost+unknown+.10+reserve>3: raise RuntimeError('Next call exceeds frozen call or budget limit')
        row={'stage':stage, 'case_id':case, 'input':data, 'status':'STARTED', 'reserved_cost_usd':reserve}
        calls.append(row); save('calls.json', calls)
        try:
            response=call_fn(stage, data); row['response']=response
            row['usage']=_usage(response, stage); cost+=row['usage']['cost_usd']
            row['status']='COMPLETED'; save('calls.json', calls)
            if cost+unknown+.10>3: raise RuntimeError('Reported actual spend exceeds budget; no further call')
            request=response.get('request', {})
            if (request.get('wire_payload') != project_payload(data)
                    or request.get('wire_payload_sha256') != digest_json(project_payload(data))
                    or request.get('max_tokens') != MAX_TOKENS[stage]):
                raise RuntimeError('Actual dispatched request differs from frozen input')
            return {k:response[k] for k in schema['properties']}
        except Exception as exc:
            row['status']='FAILED'; row['failure']=getattr(exc, 'diagnostic_message', str(exc))
            row['provider_evidence']=getattr(exc, 'provider_evidence', None)
            if 'usage' not in row:
                try: row['usage']=_usage({'usage':getattr(exc,'usage',None)},stage); cost+=row['usage']['cost_usd']
                except RuntimeError: unknown+=reserve
            save('calls.json', calls); raise

    try:
        negative=None
        for case in prepared['cases']:
            data=audit_payload(Path(case['path']).read_text(), plan, contract, json.loads((CLEAN_NOTES if case['id']=='clean_control' else NEGATIVE_NOTES).read_text())[0])
            response=invoke('AUDIT', data, case['id'])
            chosen=decision(response,data['story_segments'])
            passed=qualification_passed(case['id'], response, chosen)
            cases.append({'case_id':case['id'], 'passed':passed, **chosen}); save('case-results.json', cases)
            if case['id']=='recorded_deviations': negative=chosen
        if not all(c['passed'] for c in cases):
            result['status']='QUALIFICATION_FAILED'
        else:
            result['qualification_passed']=True
            ledger=json.loads(WRITER_LEDGER.read_text())
            writer=next(r for r in ledger if r['stage']=='WRITER' and r['variant']=='five_category_appendix')
            raw, proof=normalize_marked_story(writer['response']['story'], contract['scene_order'],
                encoding_provenance='latin1_decoded_utf8_sse')
            if bind_story(raw,plan)['story'] != FLAWED.read_text(): raise RuntimeError('Repair source differs from qualified story')
            save('delivery-proof.json',proof); (out/'original-marked-story.txt').write_text(raw)
            findings=negative['findings']
            for cycle in range(1,3):
                data, ids=scope_payload(raw,plan,findings)
                patch=invoke('PATCH',data,f'patch-{cycle}')
                raw,proof=apply_patches(raw,plan,ids,patch['patches'])
                save(f'patch-proof-{cycle:02}.json',proof)
                a=bind_story(raw,plan); (out/f'candidate-{cycle:02}.txt').write_text(a['story'])
                (out/f'candidate-{cycle:02}-marked.txt').write_text(raw)
                data=audit_payload(a['story'],plan,contract)
                response=invoke('AUDIT',data,f'candidate-{cycle}')
                chosen=decision(response,data['story_segments'])
                save(f'audit-decision-{cycle:02}.json',chosen); findings=chosen['findings']
                result.update(final_decision=chosen, patch_cycles=cycle)
                if chosen['status']=='ACCEPT':
                    (out/'accepted-story.txt').write_text(a['story'])
                    result.update(status='ACCEPT',word_count=a['word_count'],accepted_story_sha256=a['story_sha256']); break
                if chosen['status']=='UNRESOLVED': result['status']='UNRESOLVED'; break
            else: result['status']='BOUNDED_REPAIR_INCOMPLETE'
    except Exception as exc:
        result.update(status='REJECT_RUNTIME',failure_type=type(exc).__name__,failure=str(exc))
    result.update(cases=cases,new_call_count=len(calls),new_cost_usd=round(cost-prepared['prior_confirmed_cost_usd'],10),
        confirmed_story_cost_usd=round(cost,10),unknown_call_reserve_usd=unknown,
        hosted_runner_cost_reserve_usd=.10, budget_committed_total_usd=round(cost+unknown+.10,10),accounting_complete=False,
        new_calls_accounting_complete=all('usage' in c for c in calls),
        model_latency_seconds=round(sum(c.get('usage',{}).get('latency_seconds',0) for c in calls),3))
    save('result.json',result); return result


if __name__ == '__main__':
    import os
    r=run(json.loads(AUTH.read_text()),ROOT,lambda stage,data:call_model(os.environ['OPENROUTER_API_KEY'],stage,data))
    print(json.dumps({k:v for k,v in r.items() if k not in {'cases','final_decision'}},ensure_ascii=False))
    raise SystemExit(0 if r['status']=='ACCEPT' else 1)
