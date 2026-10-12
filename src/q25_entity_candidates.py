"""Evidence-bound object/relationship candidates. Never writes canonical state."""
import copy,hashlib,json
from typing import Literal
from pydantic import Field
from src.q25_offline_diagnostic import Strict,Span,digest,valid_span

def fingerprint(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf8')).hexdigest()

class ObjectProposal(Strict):
    key:str=Field(min_length=1,pattern=r'^[a-z][a-z0-9_]*$')
    description:str=Field(min_length=1)
    role:Literal['ORDINARY_OBJECT','DECISIVE_CLUE']
    mention:Span

class RelationProposal(Strict):
    subject:str
    kind:Literal['IN_CONTAINER','HELD_BY','OWNED_BY','LOCATED_IN']
    target:str|None
    evidence:Span

class Proposal(Strict):
    schema_name:Literal['q25.entity-proposal.v1']='q25.entity-proposal.v1'
    seed_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    source_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    objects:list[ObjectProposal]
    terminal_relations:list[RelationProposal]

def represent(*,seed,prose,proposal):
    """Resolve explicit annotated references; no extraction or semantic approval."""
    proposal=Proposal.model_validate(proposal)
    original=copy.deepcopy(seed)
    if proposal.seed_sha256!=fingerprint(seed) or proposal.source_sha256!=digest(prose):raise ValueError('Seed/source binding mismatch')
    characters=seed['characters'];objects=seed['objects'];locations=seed['topology']['locations']
    refs={**{'object:'+k:('OBJECT','object:'+k) for k in objects},**{'character:'+k:('CHARACTER','character:'+k) for k in characters},**{'location:'+k:('LOCATION','location:'+k) for k in locations}}
    candidates=[];keys=set()
    for item in proposal.objects:
        if item.key in keys:raise ValueError('Duplicate new-object key')
        keys.add(item.key)
        if item.role!='ORDINARY_OBJECT':raise ValueError('New decisive clue is outside ordinary-object proposal policy')
        if not valid_span(prose,proposal.source_sha256,item.mention):raise ValueError('Invalid object mention')
        identity='candidate:'+fingerprint(dict(seed=proposal.seed_sha256,source=proposal.source_sha256,key=item.key,mention=item.mention.model_dump(mode='json')))
        refs['new:'+item.key]=('OBJECT',identity)
        candidates.append(dict(id=identity,key=item.key,description=item.description,role=item.role,source_evidence=item.mention.model_dump(mode='json'),ownership_status='UNKNOWN_UNLESS_PROPOSED',canonical_admission='PENDING'))
    edges={};provenance={}
    def put(subject,kind,target):edges[(subject,kind)]=target
    for key,obj in objects.items():
        box=obj.get('state',{}).get('container')
        if box is not None:
            if box not in objects:raise ValueError('Seed container cannot be resolved')
            put('object:'+key,'IN_CONTAINER','object:'+box)
        if obj.get('owner') in characters:put('object:'+key,'OWNED_BY','character:'+obj['owner'])
        if obj.get('location') in locations:put('object:'+key,'LOCATED_IN','location:'+obj['location'])
    for name,char in characters.items():
        for key,count in char.get('inventory',{}).items():
            if key not in objects or type(count) is not int or count!=1:raise ValueError('Unsupported inventory identity/count')
            old=edges.get(('object:'+key,'HELD_BY'))
            if old is not None and old!='character:'+name:raise ValueError('Conflicting seed holders')
            put('object:'+key,'HELD_BY','character:'+name)
    changed=set()
    for relation in proposal.terminal_relations:
        if not valid_span(prose,proposal.source_sha256,relation.evidence):raise ValueError('Invalid relation evidence')
        subject=refs.get(relation.subject)
        if not subject or subject[0]!='OBJECT':raise ValueError('Subject must resolve to an existing or candidate object')
        edge=(subject[1],relation.kind)
        if edge in changed:raise ValueError('Duplicate/conflicting terminal relation')
        changed.add(edge)
        if relation.target is None:
            edges.pop(edge,None)
        else:
            target=refs.get(relation.target)
            expected={'IN_CONTAINER':'OBJECT','HELD_BY':'CHARACTER','OWNED_BY':'CHARACTER','LOCATED_IN':'LOCATION'}[relation.kind]
            if not target or target[0]!=expected:raise ValueError('Unknown or wrong-kind relation target')
            if subject[1]==target[1]:raise ValueError('Self containment')
            edges[edge]=target[1]
        provenance[edge]=relation.evidence.model_dump(mode='json')
    for subject,kind in edges:
        if kind=='IN_CONTAINER' and (subject,'HELD_BY') in edges:raise ValueError('Object cannot be both directly held and inside a container')
    containers={s:t for (s,k),t in edges.items() if k=='IN_CONTAINER'}
    for subject in containers:
        seen=set();current=subject
        while current in containers:
            if current in seen:raise ValueError('Containment cycle')
            seen.add(current);current=containers[current]
    contents={'object:'+k:[] for k,o in objects.items() if 'contains' in o.get('state',{})};held={}
    for subject,box in containers.items():contents.setdefault(box,[]).append(subject)
    for (subject,kind),target in edges.items():
        if kind=='HELD_BY':held.setdefault(target,[]).append(subject)
    # These are a derived relation view, not a SceneDelta or accepted StoryState.
    assert seed==original
    return dict(schema='q25.entity-representation.v1',seed_sha256=proposal.seed_sha256,source_sha256=proposal.source_sha256,representation_status='REPRESENTABLE_CANDIDATE',canonical_admission='PENDING_POLICY_AND_SEMANTIC_REVIEW',state_commit_authorized=False,semantic_support_certified=False,initial_seed_unchanged=True,candidate_objects=candidates,relations=[dict(subject=s,kind=k,target=t,evidence=provenance.get((s,k)),origin='PROPOSAL' if (s,k) in changed else 'SEED') for (s,k),t in sorted(edges.items())],cleared_relations=[dict(subject=s,kind=k,evidence=provenance[(s,k)]) for s,k in sorted(changed) if (s,k) not in edges],container_contents={k:sorted(v) for k,v in sorted(contents.items())},directly_held_objects={k:sorted(v) for k,v in sorted(held.items())},provider_calls=0)

def main():
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('seed','prose-record','proposal'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    seed=json.loads(args.seed.read_text(encoding='utf8'));prose=json.loads(args.prose_record.read_text(encoding='utf8'))['text'];proposal=json.loads(args.proposal.read_text(encoding='utf8'))
    print(json.dumps(represent(seed=seed,prose=prose,proposal=proposal),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
