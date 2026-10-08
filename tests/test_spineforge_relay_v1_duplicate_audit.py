import hashlib
import json
from pathlib import Path
from decimal import Decimal
import yaml
from src.spineforge_relay_v1_q7e_evidence import verify_q7e

BASE = Path("evidence/spineforge-relay")
AUDIT = BASE/"SFR-V1-Q7E-DUPLICATE-AUDIT-20261008"


def test_both_independent_q7e_records_replay_and_provider_ids_differ():
    local=BASE/"SFR-V1-Q7E-PLAN-COVERAGE-20261007-local"
    ci=BASE/"SFR-V1-Q7E-PLAN-COVERAGE-20261007"
    assert verify_q7e(local)["cost_usd"] == 0.15638
    assert verify_q7e(ci)["cost_usd"] == 0.157202
    assert json.loads((local/"SC05-1-writer-response.json").read_text(encoding="utf-8"))["id"] != json.loads((ci/"SC05-1-writer-response.json").read_text(encoding="utf-8"))["id"]


def test_audit_preserves_every_original_byte_and_overrun_accounting():
    audit=json.loads((AUDIT/"reconciliation.json").read_text(encoding="utf-8"))
    for path, expected in audit["preserved_hashes"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    assert sum(Decimal(str(audit[k])) for k in ("local_cost_usd","ci_cost_usd","q7d_cost_usd")) == Decimal("0.633931")
    assert Decimal(str(audit["total_cost_usd"]))-Decimal(str(audit["approved_cost_ceiling_usd"])) == Decimal("0.033931")


def test_all_legacy_direct_paid_workflow_jobs_are_disabled():
    for path in Path(".github/workflows").glob("spineforge-relay-v1-*-paid.yml"):
        workflow=yaml.safe_load(path.read_text(encoding="utf-8"))
        if path.name in {"spineforge-relay-v1-reserved-paid.yml", "spineforge-relay-v1-spatial-reserved-paid.yml", "spineforge-relay-v1-joint-reserved-paid.yml"}:
            assert set(workflow.get("on",workflow.get(True,{}))) == {"workflow_dispatch"}
            assert all(job['if'] == 'github.run_attempt == 1' for job in workflow['jobs'].values())
            entry = 'spineforge_joint_paid_entry' if 'joint-reserved' in path.name else ('spineforge_spatial_paid_entry' if 'spatial-reserved' in path.name else 'spineforge_relay_v1_paid_entry')
            assert '-m src.' + entry in path.read_text(encoding='utf-8')
            continue
        assert all(job["if"] == "${{ false }}" for job in workflow["jobs"].values())
