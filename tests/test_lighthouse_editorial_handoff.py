import json
import pytest
from src.lighthouse_editorial_handoff import SOURCE, APPROVAL, build


def test_approved_source_projects_all_scenes_and_remains_unpaid():
    result = build(SOURCE.read_bytes(), json.loads(APPROVAL.read_text()))
    assert len(result['scenes']) == 6
    assert all(s['approved_action'] and s['required_end_state'] for s in result['scenes'])
    assert result['paid_execution_authorized'] is False
    assert result['spine_architect_evaluated'] is False


def test_changed_source_invalidates_approval():
    with pytest.raises(ValueError):
        build(SOURCE.read_bytes() + b'changed', json.loads(APPROVAL.read_text()))


@pytest.mark.parametrize('field,value', [('verdict', 'REJECT'), ('scope', 'PAID'),
                                         ('paid_execution_authorized', True)])
def test_approval_scope_cannot_be_promoted(field, value):
    approval = json.loads(APPROVAL.read_text())
    approval[field] = value
    with pytest.raises(ValueError):
        build(SOURCE.read_bytes(), approval)
