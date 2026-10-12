"""Separate whole-story experiment: ideas -> plan -> prose -> extracted state.

Semantic extraction/review are fallible; typed admission and source binding do
not certify creativity or completeness. No historical engine is modified.
"""
import copy,hashlib,json,re,time
from decimal import Decimal
from pathlib import Path
from typing import Literal
from pydantic import Field
from src.spineforge_relay_v1_contracts import StrictModel,CharacterState,ObjectState,canonical_sha256
from src.spineforge_story_design import StoryRequestV1
from src.spineforge_seeded_design import verify_frozen_seed
from src.spineforge_production_compact_ranges import range_table
from src.spineforge_production_state_effects import _json
from src.spineforge_relay_v1_q5t import save
from src.model_registry import require_qualification_runtime_profile,normalize_openrouter_request
from src.generate import _extract_text_content

class SimpleConfigV1(StrictModel):
    schema_name: Literal['spineforge.simple-config.v1']='spineforge.simple-config.v1'
    budget_policy: Literal['BETWEEN_CALLS']='BETWEEN_CALLS'
    ideator: str='aion-labs/aion-3.5-mini'
    selector: str='anthropic/claude-sonnet-5.5'
    planner: str='openai/gpt-5.6-sol'
    writer: str='aion-labs/aion-3.5-mini'
    repairer: str='aion-labs/aion-3.5-mini'
    extractor: str='anthropic/claude-sonnet-5.5'
    reviewer: str='anthropic/claude-sonnet-5.5'
    max_total_cost_usd: float=Field(default=1.20,gt=0,allow_inf_nan=False,strict=True)
    max_calls: Literal[9]=9
    max_story_rewrites: Literal[1]=1
    automatic_retry: Literal[False]=False
    def models(self):return sorted({getattr(self,s) for s in ['ideator','selector','planner','writer','repairer','extractor','reviewer']})

class Idea(StrictModel):
    id: Literal['I1','I2','I3']
    synopsis: str=Field(min_length=1)
    conflict: str=Field(min_length=1)
    character_decision: str=Field(min_length=1)
    resolution: str=Field(min_length=1)
    distinctiveness: str=Field(min_length=1)
class Ideas(StrictModel):
    ideas: list[Idea]=Field(min_length=3,max_length=3)
class Selection(StrictModel):
    selected_id: Literal['I1','I2','I3']
    reason: str=Field(min_length=1)
    quality_limitations: list[str]
class Beat(StrictModel):
    purpose: str=Field(min_length=1)
    action: str=Field(min_length=1)
    consequence: str=Field(min_length=1)
class Plan(StrictModel):
    beats: list[Beat]=Field(min_length=2,max_length=12)
    ending: str=Field(min_length=1)
class Change(StrictModel):
    path: str=Field(min_length=1)
    value_json: str=Field(min_length=1)
    source_range_id: str=Field(min_length=1)
class Resolution(StrictModel):
    id: str=Field(min_length=1)
    source_range_id: str=Field(min_length=1)
class Extraction(StrictModel):
    source_sha256: str
    seed_sha256: str
    changes: list[Change]
    resolved_threads: list[Resolution]
    satisfied_obligations: list[Resolution]
    uncertainties: list[str]
class Finding(StrictModel):
    category: Literal['PROSE','STATE_EXTRACTION']
    reason: str=Field(min_length=1)
    repair_instruction: str=Field(min_length=1)
    source_range_id: str=Field(min_length=1)
class Review(StrictModel):
    source_sha256: str
    candidate_state_sha256: str
    decision: Literal['PASS','REWRITE']
    findings: list[Finding]
    summary: str=Field(min_length=1)

SCHEMAS={'ideator':Ideas,'selector':Selection,'planner':Plan,'extractor':Extraction,'reviewer':Review}

def prepare(request_path,seed_path,freeze_path,config_path):
    request=StoryRequestV1.model_validate_json(Path(request_path).read_bytes());seed=verify_frozen_seed(Path(seed_path),Path(freeze_path))
    config=SimpleConfigV1.model_validate_json(Path(config_path).read_bytes())
    for m in config.models():require_qualification_runtime_profile(m)
    paths=[Path(__file__).relative_to(Path.cwd()),Path('prompts/spineforge_simple_story.md')]+list(Path('src').glob('spineforge_relay_v1*.py'))
    paths += [Path(p) for p in ['src/spineforge_story_design.py','src/spineforge_seeded_design.py','src/spineforge_relay_v1_contracts.py','src/spineforge_relay_v1_q5t.py','src/spineforge_production_source_ranges.py','src/spineforge_production_compact_ranges.py','src/spineforge_source_spans.py','src/spineforge_production_state_effects.py','src/spineforge_state_fidelity.py','src/model_registry.py','src/generate.py','src/spineforge_v19_transport.py','src/spineforge_production_reservations_v2.py','src/spineforge_relay_v1_lease_context.py','src/spineforge_simple_paid_entry.py','configs/model_runtime_profiles.yaml','requirements.txt']]
    return dict(schema='spineforge.simple-preflight.v1',request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),config=config.model_dump(mode='json'),max_calls=9,budget_policy='BETWEEN_CALLS',provider_spend_cap_guaranteed=False,allowed_models=config.models(),production_write=False,automatic_retry=False,
        sources=[dict(path=p.as_posix(),sha256=hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()) for p in sorted(set(paths))],inputs=[dict(path=Path(p).as_posix(),sha256=hashlib.sha256(Path(p).read_bytes()).hexdigest()) for p in [request_path,seed_path,freeze_path,config_path]])

def request_for(stage,payload,config):
    prompt=Path('prompts/spineforge_simple_story.md').read_text(encoding='utf8')+'\nYour role: '+stage+'.'
    if stage!='writer':prompt+='\nReturn one JSON object matching output_schema, without Markdown or outside prose.'
    body={**payload}
    if stage in SCHEMAS:body['output_schema']=SCHEMAS[stage].model_json_schema()
    model=config.repairer if stage=='writer' and payload.get('rewrite') is not None else getattr(config,stage);fmt={'type':'text'} if stage=='writer' else {'type':'json_object'}
    kwargs=dict(model=model,system_prompt=prompt,user_prompt=json.dumps(body,ensure_ascii=False,separators=(',',':')),temperature=.7 if stage in ['ideator','writer'] else .2 if stage=='planner' else 0.,max_tokens=None,seed=None,request_class='spineforge_relay_v1_simple_'+stage,response_format=fmt,require_parameters=True)
    actual=normalize_openrouter_request(model,dict(model=model,messages=[dict(role='system',content=prompt),dict(role='user',content=kwargs['user_prompt'])],temperature=kwargs['temperature']),request_class=kwargs['request_class'],structured_output=False)
    actual['response_format']=fmt;actual['provider']={**actual.get('provider',{}),'require_parameters':True}
    return kwargs,actual

def quotation(prose,table,reference):
    if table!=range_table(prose):raise ValueError('Source table drift')
    choice=next((r for r in table['ranges'] if r[0]==reference),None)
    if choice is None:raise ValueError('Unknown evidence range')
    return prose[table['units'][choice[1]][0]:table['units'][choice[2]][1]]

def extracted_state(seed,prose,extraction):
    table=range_table(prose)
    if extraction.source_sha256!=table['source_sha256'] or extraction.seed_sha256!=canonical_sha256(seed):raise ValueError('Stale extraction binding')
    initial=seed.initial_state('STORY');candidate=copy.deepcopy(initial);proof=[];seen=[]
    for change in extraction.changes:
        if not change.path.startswith('/') or re.search(r'~(?![01])',change.path):raise ValueError('Invalid state pointer')
        parts=[s.replace('~1','/').replace('~0','~') for s in change.path[1:].split('/')]
        if any(change.path==p or change.path.startswith(p+'/') or p.startswith(change.path+'/') for p in seen):raise ValueError('Overlapping state changes')
        seen.append(change.path)
        allowed=(len(parts)>=3 and parts[0]=='characters' and parts[1] in seed.characters and parts[2] in ['location','condition','inventory','knowledge','relationships']) or (len(parts)>=3 and parts[0]=='objects' and parts[1] in seed.objects and parts[2] in ['owner','location','state']) or (len(parts)>=2 and parts[0]=='world' and parts[1] in seed.world and parts[1] not in ['rules','spatial'])
        if not allowed:raise ValueError('Mutation outside authorized state families')
        node=candidate
        for part in parts[:-1]:
            if not isinstance(node,dict) or part not in node:raise ValueError('Missing mutation parent')
            node=node[part]
        if not isinstance(node,dict):raise ValueError('Replace lists as whole values')
        value=_json(change.value_json);quote=quotation(prose,table,change.source_range_id)
        proof.append(dict(path=change.path,before_present=parts[-1] in node,before=copy.deepcopy(node.get(parts[-1])),after=value,exact_text=quote));node[parts[-1]]=value
    for n,raw in candidate['characters'].items():CharacterState.model_validate(raw)
    for n,raw in candidate['objects'].items():ObjectState.model_validate(raw)
    # Only declared physical fields are compared; do not infer prose semantics.
    for box,raw in candidate['objects'].items():
        contents=raw['state'].get('contains')
        if isinstance(contents,list):
            for child in contents:
                if isinstance(child,str) and child in candidate['objects']:
                    physical=candidate['objects'][child]['state']
                    if 'container' in physical and physical['container']!=box:raise ValueError('Container/contents disagree')
    for n,entity in {**candidate['characters'],**candidate['objects']}.items():
        if entity['location'] not in seed.topology.locations:raise ValueError('Unknown final location')
        candidate['world']['spatial']['positions'][n]=entity['location']
    def resolve(items,allowed):
        ids=[r.id for r in items]
        if len(set(ids))!=len(ids) or not set(ids)<=set(allowed):raise ValueError('Unknown/duplicate resolution')
        for r in items:proof.append(dict(resolution_id=r.id,exact_text=quotation(prose,table,r.source_range_id)))
        return ids
    resolved=resolve(extraction.resolved_threads,seed.open_threads);satisfied=resolve(extraction.satisfied_obligations,[o.id for o in seed.narrative_obligations])
    candidate['open_threads']=[t for t in seed.open_threads if t not in resolved];candidate['resolved_threads']=resolved
    for obligation in candidate['narrative_obligations']:
        if obligation['id'] in satisfied:obligation['status']='SATISFIED'
    return candidate,proof

def execute(*,request_path,seed_path,freeze_path,config_path,preflight,output,api_key,call_fn):
    if preflight!=prepare(request_path,seed_path,freeze_path,config_path):raise ValueError('Frozen simple preflight drift')
    if not api_key:raise ValueError('Missing credential')
    output=Path(output);output.mkdir(parents=True,exist_ok=False);save(output/'preflight.json',preflight)
    config=SimpleConfigV1.model_validate_json(Path(config_path).read_bytes());seed=verify_frozen_seed(Path(seed_path),Path(freeze_path));request=StoryRequestV1.model_validate_json(Path(request_path).read_bytes())
    for name,path in [('request-input.json',request_path),('seed-input.json',seed_path),('frozen-seed.json',freeze_path),('config-input.json',config_path)]: (output/name).write_bytes(Path(path).read_bytes())
    ledger=[];result=dict(story_id=seed.story_id,status='REJECT_NON_CONVERGENT',phase='ideas',ledger=ledger,automatic_retry=False,state_advanced=False)
    base=dict(request=request.model_dump(mode='json'),immutable_seed=seed.model_dump(mode='json'),seed_sha256=canonical_sha256(seed))
    def call(stage,attempt,payload):
        spent=sum((Decimal(str(r.get('cost_usd') or 0)) for r in ledger),Decimal(0))
        if len(ledger)>=9 or spent>=Decimal(str(config.max_total_cost_usd)):raise RuntimeError('Between-call budget/count threshold')
        kwargs,expected=request_for(stage,payload,config);prefix=output/f'{stage}-{attempt}';save(str(prefix)+'-request.json',expected)
        row=dict(stage=stage,attempt=attempt,model=kwargs['model'],request_sha256=canonical_sha256(expected),status='STARTED',cost_usd=None);ledger.append(row);started=time.perf_counter()
        try:
            text,body,actual=call_fn(api_key=api_key,**kwargs)
            save(str(prefix)+'-response.json',{k:body[k] for k in ['id','model','choices','usage'] if k in body});save(str(prefix)+'-text.json',dict(text=text))
            usage=body.get('usage',{});cost=Decimal(str(usage.get('cost')))
            if not cost.is_finite() or cost<0 or isinstance(usage.get('cost'),bool):raise ValueError('Invalid usage cost')
            for key in ['prompt_tokens','completion_tokens','total_tokens']:
                if type(usage.get(key)) is not int or usage[key]<0:raise ValueError('Invalid token usage')
            if usage['total_tokens']!=usage['prompt_tokens']+usage['completion_tokens']:raise ValueError('Inconsistent usage')
            row.update(cost_usd=str(cost),input_tokens=usage['prompt_tokens'],output_tokens=usage['completion_tokens'],total_tokens=usage['total_tokens'])
            if actual!=expected or body['choices'][0]['finish_reason']!='stop':raise ValueError('Request drift/incomplete response')
            row['status']='COMPLETE';return text
        except Exception as exc:row.update(status='FAILED_NO_RETRY',failure_type=type(exc).__name__);raise
        finally:row['latency_seconds']=round(time.perf_counter()-started,3);save(str(prefix)+'-ledger.json',row)
    try:
        ideas=Ideas.model_validate_json(call('ideator',1,base))
        if {i.id for i in ideas.ideas}!={'I1','I2','I3'} or len({i.synopsis.strip() for i in ideas.ideas})!=3:raise ValueError('Ideas must be three distinct candidates')
        save(output/'ideas.json',ideas.model_dump(mode='json'));selection=Selection.model_validate_json(call('selector',1,{**base,**ideas.model_dump(mode='json')}));save(output/'selection.json',selection.model_dump(mode='json'))
        chosen=next(i for i in ideas.ideas if i.id==selection.selected_id);result['phase']='plan'
        plan=Plan.model_validate_json(call('planner',1,{**base,'selected_idea':chosen.model_dump(mode='json')}))
        if len(plan.beats)!=request.scene_count:raise ValueError('Outline must match requested beat count')
        save(output/'plan.json',plan.model_dump(mode='json'));rewrite=None;extraction_feedback=None;extraction_only=False
        for attempt in (1,2):
            if not extraction_only:
                result['phase']='writing';prose=call('writer',attempt,{**base,'selected_idea':chosen.model_dump(mode='json'),'plan':plan.model_dump(mode='json'),'rewrite':rewrite}).strip()
            if not prose or prose.startswith(('{','[','```')):raise ValueError('Writer must return complete plain prose')
            table=range_table(prose);result['phase']='extraction'
            try:
                raw_extraction=call('extractor',attempt,{**base,'candidate_prose':prose,'source_range_table':table,'extraction_repair':extraction_feedback})
                extraction=Extraction.model_validate_json(raw_extraction)
                candidate,proof=extracted_state(seed,prose,extraction)
            except ValueError as exc:
                if attempt==2 or ledger[-1]['status']!='COMPLETE':raise
                extraction_only=True;extraction_feedback=dict(reason=str(exc),previous_output=raw_extraction)
                save(output/'extraction-structural-feedback.json',extraction_feedback);continue
            save(output/f'extracted-state-{attempt}.json',dict(extraction=extraction.model_dump(mode='json'),candidate=candidate,evidence=proof,semantic_completeness_verified=False))
            result['phase']='review';review=Review.model_validate_json(call('reviewer',attempt,{**base,'candidate_prose':prose,'source_range_table':table,'candidate_state':candidate,'candidate_state_sha256':canonical_sha256(candidate),'extraction':extraction.model_dump(mode='json'),'uncertainties':extraction.uncertainties}))
            if review.source_sha256!=table['source_sha256'] or review.candidate_state_sha256!=canonical_sha256(candidate) or (review.decision=='PASS')!= (not review.findings):raise ValueError('Review binding/decision mismatch')
            bound=[{**f.model_dump(mode='json'),'exact_text':quotation(prose,table,f.source_range_id)} for f in review.findings]
            save(output/f'review-{attempt}.json',dict(review=review.model_dump(mode='json'),bound_findings=bound))
            if review.decision=='PASS' and not extraction.uncertainties and not candidate['open_threads'] and all(o['status']=='SATISFIED' for o in candidate['narrative_obligations']):
                verify_frozen_seed(Path(seed_path),Path(freeze_path));candidate.update(revision=1,completed_spine_beats=['STORY'],next_spine_beat=None)
                save(output/'accepted-state.json',candidate);save(output/'state-comparison.json',dict(initial=seed.initial_state('STORY'),final=candidate,evidence=proof,state_source='EXTRACTED_FROM_FINAL_PROSE',initial_seed_unchanged=True))
                (output/'assembled-story.md').write_bytes((prose+'\n').encode());result.update(status='ACCEPT',phase='complete',state_advanced=True,revision=1,story_rewrites=sum(r['stage']=='writer' and r['attempt']==2 for r in ledger),state_extraction_repairs=int(extraction_only),first_pass=attempt==1);break
            rewrite=dict(candidate_prose=prose,findings=bound,extraction_uncertainties=extraction.uncertainties,unresolved_threads=candidate['open_threads'],unsatisfied_obligations=[o for o in candidate['narrative_obligations'] if o['status']!='SATISFIED'])
            extraction_only=bool(review.findings) and all(f.category=='STATE_EXTRACTION' for f in review.findings)
            extraction_feedback=dict(previous_extraction=extraction.model_dump(mode='json'),findings=bound) if extraction_only else None
    except Exception as exc:result.update(reason='FAILED_CLOSED_NO_RETRY',failure_type=type(exc).__name__)
    total=sum((Decimal(str(r.get('cost_usd') or 0)) for r in ledger),Decimal(0))
    result.update(provider_calls=len(ledger),known_cost_usd=str(total),usage_complete=all(r['cost_usd'] is not None for r in ledger),budget_threshold_exceeded=total>Decimal(str(config.max_total_cost_usd)),provider_spend_cap_guaranteed=False)
    if result['status']!='ACCEPT' and 'reason' not in result:result['reason']='BOUNDED_REPAIR_EXHAUSTED'
    save(output/'result.json',result);save(output/'manifest.json',dict(files={p.relative_to(output).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.rglob('*')) if p.is_file()}))
    return result

def verify_saved(root):
    """Mechanical replay of an accepted record; no semantic inference or calls."""
    root=Path(root);read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
    result=read(root/'result.json');pf=read(root/'preflight.json')
    if result['status']!='ACCEPT':raise ValueError('Accepted record required')
    for name,digest in read(root/'manifest.json')['files'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Record hash drift')
    for row in pf['sources']:
        if hashlib.sha256(Path(row['path']).read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=row['sha256']:raise ValueError('Frozen source drift')
    config=SimpleConfigV1.model_validate(read(root/'config-input.json'));seed=verify_frozen_seed(root/'seed-input.json',root/'frozen-seed.json')
    request=StoryRequestV1.model_validate(read(root/'request-input.json'))
    if canonical_sha256(seed)!=pf['seed_sha256'] or canonical_sha256(request)!=pf['request_sha256'] or config.model_dump(mode='json')!=pf['config']:raise ValueError('Input binding drift')
    for name,row in zip(['request-input.json','seed-input.json','frozen-seed.json','config-input.json'],pf['inputs']):
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Input byte drift')
    ledger=result['ledger'];expected_orders=[['ideator','selector','planner','writer','extractor','reviewer'],['ideator','selector','planner','writer','extractor','reviewer','writer','extractor','reviewer'],['ideator','selector','planner','writer','extractor','reviewer','extractor','reviewer'],['ideator','selector','planner','writer','extractor','extractor','reviewer']]
    if [r['stage'] for r in ledger] not in expected_orders:raise ValueError('Unexpected calls')
    current_prose=None;candidate=None;spent=Decimal(0);ids=[];last_extraction_attempt=None;last_review=None
    ideas=Ideas.model_validate(read(root/'ideas.json'));selection=Selection.model_validate(read(root/'selection.json'));plan=Plan.model_validate(read(root/'plan.json'))
    chosen=next(i for i in ideas.ideas if i.id==selection.selected_id)
    for row in ledger:
        if spent>=Decimal(str(config.max_total_cost_usd)):raise ValueError('Budget dispatch after threshold')
        prefix=root/f"{row['stage']}-{row['attempt']}";sent=read(str(prefix)+'-request.json');body=read(str(prefix)+'-response.json');text=read(str(prefix)+'-text.json')['text'];payload=json.loads(sent['messages'][1]['content'])
        _,expected=request_for(row['stage'],payload,config)
        if sent!=expected or 'max_tokens' in sent or row['status']!='COMPLETE' or canonical_sha256(sent)!=row['request_sha256']:raise ValueError('Request/profile drift')
        if payload['immutable_seed']!=seed.model_dump(mode='json') or payload['request']!=request.model_dump(mode='json'):raise ValueError('Seed/request payload drift')
        if body['choices'][0]['finish_reason']!='stop' or _extract_text_content(body['choices'][0]['message'])!=text:raise ValueError('Raw text/incomplete response')
        if Decimal(str(body['usage']['cost']))!=Decimal(row['cost_usd']) or body['usage']['total_tokens']!=row['total_tokens']:raise ValueError('Usage mismatch')
        if body['usage']['total_tokens']!=body['usage']['prompt_tokens']+body['usage']['completion_tokens']:raise ValueError('Token sum mismatch')
        ids.append(body['id']);spent+=Decimal(row['cost_usd'])
        stage=row['stage']
        if stage=='ideator' and Ideas.model_validate_json(text)!=ideas:raise ValueError('Idea drift')
        if stage=='selector' and Selection.model_validate_json(text)!=selection:raise ValueError('Selection drift')
        if stage=='planner' and (Plan.model_validate_json(text)!=plan or payload['selected_idea']!=chosen.model_dump(mode='json')):raise ValueError('Plan drift')
        if stage=='writer':
            if payload['plan']!=plan.model_dump(mode='json') or payload['selected_idea']!=chosen.model_dump(mode='json'):raise ValueError('Writer input drift')
            current_prose=text.strip()
        if stage in ['extractor','reviewer']:
            if payload['candidate_prose']!=current_prose or payload['source_range_table']!=range_table(current_prose):raise ValueError('Prose/citation input drift')
        if stage=='extractor':
            try:
                ext=Extraction.model_validate_json(text);candidate,proof=extracted_state(seed,current_prose,ext)
            except ValueError:
                if row['attempt']!=1 or not (root/'extraction-structural-feedback.json').exists():raise
                continue
            saved=read(root/f"extracted-state-{row['attempt']}.json")
            if saved['candidate']!=candidate or saved['evidence']!=proof or saved['extraction']!=ext.model_dump(mode='json'):raise ValueError('Extraction replay mismatch')
            last_extraction_attempt=row['attempt']
        if stage=='reviewer':
            review=Review.model_validate_json(text)
            if payload['candidate_state']!=candidate or review.candidate_state_sha256!=canonical_sha256(candidate) or review.source_sha256!=range_table(current_prose)['source_sha256']:raise ValueError('Review replay mismatch')
            for finding in review.findings:quotation(current_prose,range_table(current_prose),finding.source_range_id)
            last_review=review
    if last_review.decision!='PASS' or last_review.findings or ext.uncertainties or candidate['open_threads'] or any(o['status']!='SATISFIED' for o in candidate['narrative_obligations']):raise ValueError('Invalid terminal acceptance')
    candidate.update(revision=1,completed_spine_beats=['STORY'],next_spine_beat=None)
    if read(root/'accepted-state.json')!=candidate or (root/'assembled-story.md').read_text(encoding='utf8')!=current_prose+'\n':raise ValueError('Final artifact drift')
    comparison=read(root/'state-comparison.json')
    if comparison['initial']!=seed.initial_state('STORY') or comparison['final']!=candidate or comparison['evidence']!=proof:raise ValueError('State comparison drift')
    if len(ids)!=len(set(ids)) or len(ids)!=result['provider_calls'] or spent!=Decimal(result['known_cost_usd']):raise ValueError('Ledger mismatch')
    return dict(status='OFFLINE_SIMPLE_REPLAY_PASS',provider_calls=len(ids),cost_usd=str(spent),revision=1,initial_seed_unchanged=True,final_state_sha256=canonical_sha256(candidate),semantic_completeness_verified=False,global_originality_verified=False)
