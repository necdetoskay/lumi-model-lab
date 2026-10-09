"""Trusted source IDs preserve original punctuation; no fuzzy quote matching."""
import hashlib
import re
from typing import Literal
from pydantic import Field, create_model
from src.spineforge_relay_v1_contracts import StrictModel
from src.spineforge_relay_v1_events import PredicateEvidenceV1
from src.spineforge_relay_v1_guard import SemanticGuardFindingV1
from src.spineforge_relay_v1_q5t import StructuredGuardV1


def referenced(name, model):
    fields = {k:(v.annotation,v) for k,v in model.model_fields.items() if k != "exact_text"}
    fields["source_span_ids"] = (list[str],Field(min_length=1,max_length=8))
    return create_model(name,__base__=StrictModel,**fields)


SpanPredicateV1 = referenced("SpanPredicateV1",PredicateEvidenceV1)
SpanFindingV1 = referenced("SpanFindingV1",SemanticGuardFindingV1)


class SpanResidualV1(StrictModel):
    schema_name: Literal["spineforge-relay.semantic-guard.v1"]
    decision: Literal["PASS","REWRITE"]
    findings: list[SpanFindingV1]
    summary: str = Field(min_length=1)


class SpanGuardV1(StrictModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    event_evidence: list[SpanPredicateV1]
    residual: SpanResidualV1


def source_table(prose):
    digest=hashlib.sha256(prose.encode("utf-8")).hexdigest()
    # Sentence-like units are aids to selection, not semantic parsing.
    pattern=r'\S.*?(?:[.!?]["”’\']*(?=\s|$)|\n|$)'
    spans=[{"id":digest[:16]+":"+str(i),"start":m.start(),"end":m.end(),"text":m.group()} for i,m in enumerate(re.finditer(pattern,prose,re.DOTALL))]
    if not spans:
        raise ValueError("No source spans")
    return {"source_sha256":digest,"offset_unit":"UNICODE_CODE_POINTS","spans":spans}


def resolve_span_guard(raw,prose):
    guard=SpanGuardV1.model_validate(raw)
    table=source_table(prose)
    if guard.source_sha256!=table["source_sha256"]:
        raise ValueError("Stale source binding")
    indexes={s["id"]:i for i,s in enumerate(table["spans"])}
    def resolve(row):
        data=row.model_dump(mode="json")
        ids=data.pop("source_span_ids")
        try:
            selected=[indexes[s] for s in ids]
        except KeyError:
            raise ValueError("Unknown source span") from None
        if selected!=list(range(selected[0],selected[0]+len(selected))):
            raise ValueError("Source spans must be unique, ordered and contiguous")
        first,last=table["spans"][selected[0]],table["spans"][selected[-1]]
        data["exact_text"]=prose[first["start"]:last["end"]]
        return data
    residual=guard.residual.model_dump(mode="json")
    residual["findings"]=[resolve(row) for row in guard.residual.findings]
    return StructuredGuardV1.model_validate({"event_evidence":[resolve(row) for row in guard.event_evidence],"residual":residual})


def strict_span_schema(table=None):
    schema=SpanGuardV1.model_json_schema()
    def strict(node):
        if isinstance(node,dict):
            node.pop("default",None)
            if node.get("type")=="object":
                node["required"]=list(node.get("properties",{}))
            for value in node.values():strict(value)
        elif isinstance(node,list):
            for value in node:strict(value)
    strict(schema)
    if table is not None:
        schema["properties"]["source_sha256"]["const"]=table["source_sha256"]
        ids=[s["id"] for s in table["spans"]]
        for name in ("SpanPredicateV1","SpanFindingV1"):
            schema["$defs"][name]["properties"]["source_span_ids"]["items"]["enum"]=ids
    return schema
