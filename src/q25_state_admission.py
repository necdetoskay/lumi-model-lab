"""Experimental admission policy and draft state; never commits production state."""
import copy
from typing import Literal
from src.q25_offline_diagnostic import Strict
from src.q25_entity_candidates import represent,fingerprint

class AdmissionPolicy(Strict):
    schema_name:Literal['q25.object-admission-policy.v1']='q25.object-admission-policy.v1'
    scope:Literal['EXPERIMENTAL_DRAFT_ONLY']='EXPERIMENTAL_DRAFT_ONLY'
    allow_new_ordinary_objects:bool=False
    allow_unknown_owner:bool=True
    allow_unknown_location:bool=True

def value(status,ref=None):return dict(status=status,ref=ref)

def build_draft(*,seed,prose,proposal,policy):
    """Recompute the graph, apply configured structural policy, preserve unknowns.

    Output deliberately has a different schema from historical StoryState. A
    policy allowing a role label does not prove narrative/evidence correctness.
    """
    policy=AdmissionPolicy.model_validate(policy)
    original=copy.deepcopy(seed);view=represent(seed=seed,prose=prose,proposal=proposal)
    reasons=[]
    if view['candidate_objects'] and not policy.allow_new_ordinary_objects:reasons.append('NEW_ORDINARY_OBJECTS_DISABLED')
    object_ids={**{'object:'+k:k for k in seed['objects']},**{c['id']:'new_'+c['id'].split(':')[1] for c in view['candidate_objects']}}
    if len(set(object_ids.values()))!=len(object_ids):raise ValueError('Entity identity collision')
    edges={(r['subject'],r['kind']):r['target'] for r in view['relations']}
    def resolve(ref):
        if ref is None:return None
        if ref in object_ids:return object_ids[ref]
        if ref.startswith(('character:','location:')):return ref.split(':',1)[1]
        raise ValueError('Unresolved relation reference')
    objects={}
    for ref,identity in object_ids.items():
        existing=ref.startswith('object:');raw=seed['objects'][identity] if existing else None
        owner=edges.get((ref,'OWNED_BY'));location=edges.get((ref,'LOCATED_IN'));box=edges.get((ref,'IN_CONTAINER'));holder=edges.get((ref,'HELD_BY'))
        cleared={(r['subject'],r['kind']) for r in view['cleared_relations']}
        # Existing non-character owners (e.g. a library) remain verbatim facts.
        ownership=value('KNOWN',resolve(owner)) if owner else value('NONE') if (ref,'OWNED_BY') in cleared else value('KNOWN',raw['owner']) if raw and raw.get('owner') is not None else value('UNKNOWN')
        position=value('KNOWN',resolve(location)) if location else value('UNKNOWN')
        if not existing and ownership['status']=='UNKNOWN' and not policy.allow_unknown_owner:reasons.append('UNKNOWN_NEW_OBJECT_OWNER:'+identity)
        if not existing and position['status']=='UNKNOWN' and not policy.allow_unknown_location:reasons.append('UNKNOWN_NEW_OBJECT_LOCATION:'+identity)
        properties=copy.deepcopy(raw.get('state',{})) if raw else {}
        # Relation fields have one source of truth in this draft schema.
        properties.pop('container',None);properties.pop('contains',None)
        objects[identity]=dict(identity_status='EXISTING' if existing else 'PROPOSED',owner=ownership,location=position,container=value('KNOWN',resolve(box)) if box else value('NONE'),held_by=value('KNOWN',resolve(holder)) if holder else value('NONE'),contains=sorted(resolve(child) for child in view['container_contents'].get(ref,[])),properties=properties)
    characters=copy.deepcopy(seed['characters'])
    for name,char in characters.items():char['inventory']={resolve(ref):1 for ref in view['directly_held_objects'].get('character:'+name,[])}
    draft=dict(schema='q25.draft-state.v1',base_seed_sha256=fingerprint(seed),source_sha256=view['source_sha256'],objects=objects,characters=characters,world=copy.deepcopy(seed['world']) if 'world' in seed else {},topology=copy.deepcopy(seed['topology']),identity_map=object_ids,initial_seed_unchanged=True,coverage='OBJECT_RELATIONS_ONLY_NOT_FULL_STORY_STATE',unresolved_fields=[dict(object_id=k,field=f) for k,obj in objects.items() for f in ('owner','location') if obj[f]['status']=='UNKNOWN'])
    assert seed==original
    return dict(schema='q25.admission-result.v1',policy=policy.model_dump(mode='json'),policy_sha256=fingerprint(policy.model_dump(mode='json')),structural_admission='BLOCKED_BY_POLICY' if reasons else 'ELIGIBLE_DRAFT',reasons=reasons,draft_state=None if reasons else draft,state_commit_authorized=False,semantic_support_certified=False,narrative_acceptance='UNVERIFIED',required_next_checks=['Independent semantic support and role classification','Complete story state coverage','Canonical schema/authority integration'],provider_calls=0)

def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('seed','prose-record','proposal','policy'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();read=lambda path:json.loads(path.read_text(encoding='utf8'))
    print(json.dumps(build_draft(seed=read(args.seed),prose=read(args.prose_record)['text'],proposal=read(args.proposal),policy=read(args.policy)),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
