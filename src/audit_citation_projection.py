"""Correct a uniquely provable adjacent non-defect citation, never a repair scope."""
import copy
from src.lighthouse_audit_decision import SCHEMA, decision
from src.spineforge_v21_model_adapter import validate_schema


def project_citations(response, segments):
    validate_schema({k:response[k] for k in SCHEMA['properties']},SCHEMA)
    positions = {row['span_id']: i for i,row in enumerate(segments)}
    if len(positions) != len(segments):
        raise RuntimeError('Duplicate source spans')
    projected = copy.deepcopy(response)
    corrections = []
    for check in projected['requirement_checks']:
        cited = check['span_ids']
        if len(set(cited)) != len(cited) or any(sid not in positions for sid in cited):
            raise RuntimeError('Invalid citation IDs')
        quote = check['exact_text']
        if not quote:
            continue  # Existing strict decision validator rejects missing required evidence.
        matches = [i for i,row in enumerate(segments)
                   if quote in row.get('repaired_text',row.get('text',''))]
        if any(segments[i]['span_id'] in cited for i in matches):
            continue
        # Never relocate material/uncertain findings or their repair targets.
        if check['assessment'] != 'SATISFIED' or len(matches) != 1:
            raise RuntimeError('Citation cannot be projected safely')
        i = matches[0]
        paragraph = segments[i].get('paragraph_id')
        neighbors = [sid for sid in cited if abs(positions[sid]-i) == 1
                     and paragraph and segments[positions[sid]].get('paragraph_id') == paragraph]
        if not neighbors:
            raise RuntimeError('Quote is outside the cited adjacent paragraph')
        original = list(cited)
        sid = segments[i]['span_id']
        cited.append(sid)
        corrections.append({'requirement_id':check['requirement_id'], 'exact_quote':quote,
            'original_span_ids':original, 'added_span_id':sid,
            'adjacent_cited_span_ids':neighbors, 'unique_literal_source_match':True,
            'assessment_changed':False, 'repair_scope_changed':False})
    return projected, corrections


def grounded_decision(response, segments, plan):
    projected, corrections = project_citations(response, segments)
    return decision(projected,segments,plan), corrections
