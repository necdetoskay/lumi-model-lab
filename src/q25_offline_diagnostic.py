"""Read-only Q25 diagnostic. No model call, semantic oracle or state commit."""
import hashlib
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)

class Span(Strict):
    start:int=Field(ge=0)
    end:int=Field(gt=0)
    text:str=Field(min_length=1)

class Finding(Strict):
    id:str=Field(min_length=1)
    category:Literal['HARD_INVALID','EDITORIAL_DEFECT','EDITORIAL_PREFERENCE']
    reason:str=Field(min_length=1)
    source_sha256:str
    span:Span
    authority_ref:str|None=None

class Assessment(Strict):
    finding_id:str
    support:Literal['SUPPORTED','UNSUPPORTED','UNRESOLVED']
    note:str=Field(min_length=1)
    independently_adjudicated:Literal[False]=False

class StateGap(Strict):
    kind:Literal['UNREPRESENTED_ENTITY','UNSUPPORTED_RELATION']
    description:str=Field(min_length=1)
    source_sha256:str
    span:Span

def digest(text):return hashlib.sha256(text.encode('utf8')).hexdigest()

def valid_span(text,sha,span):
    return sha==digest(text) and span.start<span.end<=len(text) and text[span.start:span.end]==span.text

def diagnose(*,prose,findings,assessments,gaps,authority_refs):
    """Draft semantic assessments never grant acceptance or persistence authority."""
    findings=[Finding.model_validate(f) for f in findings]
    assessments=[Assessment.model_validate(a) for a in assessments]
    gaps=[StateGap.model_validate(g) for g in gaps]
    ids=[f.id for f in findings]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate finding id')
    checks={a.finding_id:a for a in assessments}
    if len(checks)!=len(assessments) or set(checks)-set(ids):raise ValueError('Duplicate or unknown assessment')
    rows=[]
    for f in findings:
        citation=valid_span(prose,f.source_sha256,f.span)
        authority=f.category!='HARD_INVALID' or f.authority_ref in authority_refs
        a=checks.get(f.id)
        mechanical=citation and authority
        status='INVALID_REVIEW' if not mechanical else 'DISPUTED_REVIEW' if a and a.support=='UNSUPPORTED' else 'ADJUDICATION_REQUIRED'
        rows.append(dict(id=f.id,category=f.category,status=status,citation_bytes_valid=citation,authority_reference_valid=authority,semantic_support=a.support if a else 'UNRESOLVED',assessment_note=a.note if a else None,blocking_story=False,semantic_support_certified=False))
    for g in gaps:
        if not valid_span(prose,g.source_sha256,g.span):raise ValueError('State gap evidence invalid')
    return dict(schema='q25.offline-diagnostic.v1',narrative_status='UNVERIFIED',review_status='INVALID_REVIEW' if any(r['status']=='INVALID_REVIEW' for r in rows) else 'DISPUTED_REVIEW' if any(r['status']=='DISPUTED_REVIEW' for r in rows) else 'ADJUDICATION_REQUIRED',state_status='STATE_MODEL_GAP' if gaps else 'UNVERIFIED',persistence_status='BLOCKED',state_commit_authorized=False,story_rejection_authorized=False,independent_adjudication_required=True,findings=rows,state_gaps=[g.model_dump(mode='json') for g in gaps],provider_calls=0,semantic_quality_pass=False)

def main():
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(diagnose(**json.loads(args.input.read_text(encoding='utf8'))),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
