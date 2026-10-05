"""Versioned English assertions grounded in exact quotes from the approved plan."""
from pathlib import Path
import json

def requirements(plan):
    data=json.loads(Path('evidence/lighthouse-editorial/audit-requirements.json').read_text())
    for row in data['requirements']:
        value=plan
        for part in row['source_pointer'].strip('/').split('/'):
            value=value[int(part)] if isinstance(value,list) else value[part]
        if row['source_quote'] not in value:raise RuntimeError('Requirement source quote drift: '+row['id'])
    return data['requirements']
