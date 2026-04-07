from __future__ import annotations

from pydantic import BaseModel, Field


class RawResponse(BaseModel):
    participant_id: str
    model: str
    question_id: str
    raw: str
    parsed: str | None


class RawResponses(BaseModel):
    run_id: str
    models: list[str]
    participants: list[dict]
    responses: list[RawResponse] = Field(default_factory=list)


class QuestionResult(BaseModel):
    real: dict[str, float]
    models: dict[str, dict[str, float]] = Field(default_factory=dict)


class RunResults(BaseModel):
    questions: dict[str, QuestionResult] = Field(default_factory=dict)


class ModelQuestionStats(BaseModel):
    chi_square_p: float | None
    kl_divergence: float
    js_divergence: float
    bias_direction: str
    per_option_delta: dict[str, float]
    parse_failure_rate: float = 0.0


class RunStats(BaseModel):
    # question_id -> model_id -> stats
    questions: dict[str, dict[str, ModelQuestionStats]] = Field(default_factory=dict)
