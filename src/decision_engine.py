from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

HARNESS_VERSION = "decision-engine-harness-v1"


class DecisionQuestion(BaseModel):
    question_id: str
    type: Literal["choice", "score", "boolean"]
    instructions: str
    choices: list[str] = Field(default_factory=list)
    score_min: float | None = None
    score_max: float | None = None


class DecisionWorkloadProfile(BaseModel):
    profile_id: str
    profile_version: str
    input_schema_version: str
    question_set_version: str
    risk_class: str
    deterministic_preconditions: list[str] = Field(default_factory=list)
    abstention_options: list[str] = Field(default_factory=list)


class DecisionCase(BaseModel):
    case_id: str
    state: Any
    questions: list[DecisionQuestion]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DecisionEngineIdentity(BaseModel):
    engine_family: str
    provider_runtime: str
    model_id: str
    model_revision: str | None = None
    artifact_hash: str | None = None
    quantization: str | None = None
    serving_stack: str | None = None
    hardware: str | None = None
    language_variant: str = "native"


class DecisionAnswer(BaseModel):
    question_id: str
    type: Literal["choice", "score", "boolean"]
    value: Any
    probabilities: dict[str, float] | None = None
    confidence: float | None = None


class DecisionEngineOutput(BaseModel):
    answers: list[DecisionAnswer]
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    raw_output: Any = None


class DecisionEngine(Protocol):
    identity: DecisionEngineIdentity

    def evaluate(
        self,
        *,
        workload: DecisionWorkloadProfile,
        case: DecisionCase,
    ) -> DecisionEngineOutput:
        ...


class DecisionEngineMalformedOutput(ValueError):
    pass


def validate_output(
    *,
    workload: DecisionWorkloadProfile,
    case: DecisionCase,
    output: DecisionEngineOutput,
) -> DecisionEngineOutput:
    expected = {q.question_id: q for q in case.questions}
    seen: set[str] = set()

    for answer in output.answers:
        if answer.question_id in seen:
            raise DecisionEngineMalformedOutput(
                f"duplicate answer for {answer.question_id}"
            )
        seen.add(answer.question_id)
        question = expected.get(answer.question_id)
        if question is None:
            raise DecisionEngineMalformedOutput(
                f"unexpected answer {answer.question_id}"
            )
        if answer.type != question.type:
            raise DecisionEngineMalformedOutput(
                f"{answer.question_id}: expected {question.type}, got {answer.type}"
            )

        if question.type == "choice":
            allowed = set(question.choices)
            if not allowed:
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: choice question has no choices"
                )
            if answer.value not in allowed:
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: value {answer.value!r} outside allowed choices"
                )

        elif question.type == "boolean":
            if not isinstance(answer.value, bool):
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: boolean answer must be bool"
                )

        elif question.type == "score":
            if isinstance(answer.value, bool) or not isinstance(answer.value, (int, float)):
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: score answer must be numeric"
                )
            if question.score_min is not None and answer.value < question.score_min:
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: score below minimum"
                )
            if question.score_max is not None and answer.value > question.score_max:
                raise DecisionEngineMalformedOutput(
                    f"{answer.question_id}: score above maximum"
                )

        if answer.confidence is not None and not 0.0 <= answer.confidence <= 1.0:
            raise DecisionEngineMalformedOutput(
                f"{answer.question_id}: confidence must be within [0,1]"
            )

        if answer.probabilities is not None:
            for key, probability in answer.probabilities.items():
                if not 0.0 <= probability <= 1.0:
                    raise DecisionEngineMalformedOutput(
                        f"{answer.question_id}: probability for {key!r} outside [0,1]"
                    )

    missing = sorted(set(expected) - seen)
    if missing:
        raise DecisionEngineMalformedOutput(
            "missing answers: " + ", ".join(missing)
        )

    choice_sets = [set(q.choices) for q in case.questions if q.type == "choice"]
    for abstention in workload.abstention_options:
        if choice_sets and not any(abstention in choices for choices in choice_sets):
            raise DecisionEngineMalformedOutput(
                f"workload abstention option {abstention!r} is not exposed by any choice question"
            )

    return output
