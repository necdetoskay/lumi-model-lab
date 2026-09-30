from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.spineforge_v5_contract import SpineStructuralAssemblyV1
from src.spineforge_v7_contract import (
    StructuralBeatsV1,
    StructuralFrameV1,
    StructuralResolutionV1,
)
from src.spineforge_v7_structured_call import (
    SONNET_MODEL,
    SONNET_STRICT_SCHEMA_MAX_BYTES,
    build_provider_transport_schema,
    schema_size_bytes,
    validate_provider_schema_budget,
)


def test_partitioned_transport_schemas_are_bounded() -> None:
    models = [StructuralFrameV1, StructuralBeatsV1, StructuralResolutionV1]
    sizes = [
        schema_size_bytes(build_provider_transport_schema(m.model_json_schema(by_alias=True)))
        for m in models
    ]
    assert sizes == [1431, 856, 2891]
    assert max(sizes) < SONNET_STRICT_SCHEMA_MAX_BYTES


def test_v6_monolithic_structural_schema_exceeds_v7_budget() -> None:
    full = SpineStructuralAssemblyV1.model_json_schema(by_alias=True)
    assert schema_size_bytes(full) > SONNET_STRICT_SCHEMA_MAX_BYTES
    with pytest.raises(RuntimeError, match="oversized Sonnet strict transport schema"):
        validate_provider_schema_budget(
            model=SONNET_MODEL,
            task="compile_structural_frame",
            schema=full,
        )


def test_provider_schema_keeps_shape_and_drops_semantic_constraints() -> None:
    full = StructuralBeatsV1.model_json_schema(by_alias=True)
    transport = build_provider_transport_schema(full)
    dumped = json.dumps(transport)
    assert transport["type"] == "object"
    assert transport["additionalProperties"] is False
    assert "required" in transport
    assert '"pattern"' not in dumped
    assert '"minItems"' not in dumped
    assert '"maxItems"' not in dumped


def test_local_pydantic_still_enforces_semantic_constraints() -> None:
    with pytest.raises(ValidationError):
        StructuralBeatsV1.model_validate(
            {"schema": "spineforge-structural-beats.v1", "beats": []}
        )
