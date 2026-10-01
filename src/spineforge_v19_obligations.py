from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


DEFAULT_CASES_PATH = Path(
    "data/specifications/story_lab/spineforge_v19_qualification_cases_v1.json"
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReaderStoryObligationsV1(StrictModel):
    schema_id: Literal["reader-story-obligations.v1"] = Field(alias="schema")
    profile_id: str
    exact_age: int = Field(ge=3, le=120)
    story_family: str
    required_capabilities: list[str] = Field(min_length=1)
    reject_signals: list[str] = Field(min_length=1)
    decision_required: bool
    minimum_discovery_turns: int = Field(ge=0, le=8)
    maturity_notes: list[str] = Field(min_length=1)


class QualificationCaseV19(StrictModel):
    case_id: str
    label: str
    obligations: ReaderStoryObligationsV1
    context_fixture_status: Literal["FROZEN", "PENDING_PRODUCTION_FIXTURE"]
    context_fixture_ref: str | None = None

    @model_validator(mode="after")
    def validate_fixture_ref(self) -> "QualificationCaseV19":
        if self.context_fixture_status == "FROZEN" and not self.context_fixture_ref:
            raise ValueError("FROZEN case requires context_fixture_ref")
        return self


class QualificationCaseSetV19(StrictModel):
    schema_id: Literal["spineforge-v19-qualification-cases.v1"] = Field(alias="schema")
    cases: list[QualificationCaseV19]

    @model_validator(mode="after")
    def validate_cases(self) -> "QualificationCaseSetV19":
        if len(self.cases) != 6:
            raise ValueError("v19 qualification set must contain exactly six cases")
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("qualification case ids must be unique")
        return self


def load_qualification_cases(path: Path = DEFAULT_CASES_PATH) -> QualificationCaseSetV19:
    return QualificationCaseSetV19.model_validate_json(path.read_text(encoding="utf-8"))
