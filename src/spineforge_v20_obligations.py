from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.spineforge_v19_obligations import ReaderStoryObligationsV1


DEFAULT_CASES_PATH = Path(
    "data/specifications/story_lab/spineforge_v20_qualification_cases_v1.json"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QualificationCaseV20(StrictModel):
    case_id: str
    label: str
    obligations: ReaderStoryObligationsV1
    context_fixture_status: Literal["CANDIDATE", "FROZEN"]
    context_fixture_ref: str

    @model_validator(mode="after")
    def validate_fixture(self) -> "QualificationCaseV20":
        if not self.context_fixture_ref:
            raise ValueError("v20 qualification case requires context_fixture_ref")
        return self


class QualificationCaseSetV20(StrictModel):
    schema_id: Literal["spineforge-v20-qualification-cases.v1"] = Field(alias="schema")
    cases: list[QualificationCaseV20]

    @model_validator(mode="after")
    def validate_cases(self) -> "QualificationCaseSetV20":
        if len(self.cases) != 1:
            raise ValueError("v20 qualification set must contain exactly one case")
        return self


def load_qualification_cases(path: Path = DEFAULT_CASES_PATH) -> QualificationCaseSetV20:
    return QualificationCaseSetV20.model_validate_json(path.read_text(encoding="utf-8"))
