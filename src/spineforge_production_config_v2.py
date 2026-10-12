"""No local output cap; a spend threshold is checked between complete calls."""
import json
from pathlib import Path
from typing import Literal
from src.spineforge_production_config import RunConfigV1

class RunConfigV2(RunConfigV1):
    schema_name: Literal['spineforge.run-config.v2']='spineforge.run-config.v2'
    budget_policy: Literal['BETWEEN_CALLS']='BETWEEN_CALLS'
    planner_max_tokens: None=None
    plan_guard_max_tokens: None=None
    writer_max_tokens: None=None
    scene_guard_max_tokens: None=None
    max_call_cost_usd: None=None
    max_scene_call_cost_usd: None=None

def load_run_config(path):
    raw=json.loads(Path(path).read_text(encoding='utf8'))
    return (RunConfigV2 if raw.get('schema_name')=='spineforge.run-config.v2' else RunConfigV1).model_validate(raw)
